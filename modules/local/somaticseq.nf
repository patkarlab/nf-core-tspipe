/*
 * modules/local/somaticseq.nf
 *
 * SomaticSeq ensemble - 8-caller integration (nf-core port goes beyond
 * production's 6-caller setup).
 *
 * Native callers (SomaticSeq has built-in parsers, passed via --mutect2-vcf etc.):
 *   - Mutect2  (FilterMutectCalls-annotated)
 *   - VarDict
 *   - VarScan2
 *   - Strelka2
 *
 * Arbitrary callers (passed via --arbitrary-snvs / --arbitrary-indels after
 * sort + splitVcf preprocessing):
 *   - FreeBayes
 *   - Platypus
 *   - Pindel    (NEW vs production; not fed into prod SomaticSeq)
 *   - DeepSomatic (NEW vs production; PASS-only via deepsomatic.nf upstream)
 *
 * Workflow mirrors scripts/07_somaticseq.py:
 *   1. Skip arbitrary VCFs that are empty (header-only)
 *   2. Sort each arbitrary VCF
 *   3. Split into SNV + INDEL via splitVcf.py (SomaticSeq utility)
 *   4. Sort each split VCF
 *   5. Run somaticseq_parallel.py (xgboost, single-sample mode)
 *   6. Fall back to --threads 1 if parallel mode hits the empty-chromosome
 *      FileNotFoundError + CombineVariants bug (a known SomaticSeq issue)
 *   7. Sort, bgzip, index Consensus SNV + INDEL VCFs
 *   8. bcftools concat -> final ${sample}.somaticseq.vcf
 *   9. Rename caller INFO field codes to MVDKFP + iD (8 callers)
 *
 * SomaticSeq Docker image contains: somaticseq_parallel.py, splitVcf.py,
 * bcftools, bgzip, tabix, python3, awk, sort, grep.
 *
 * Output channel surface:
 *   vcf              = final merged SNV+INDEL VCF with renamed INFO (consumed
 *                      by ANNOTATION subworkflow downstream)
 *   snv_vcf, indel_vcf = bgzip+indexed individual consensus VCFs
 *   workdir          = somaticseq working directory (audit trail)
 *   versions
 */

process SOMATICSEQ_ENSEMBLE {
    tag        "${meta.id}"
    label      'process_high'

    conda      'bioconda::somaticseq=3.7.4'
    container  'lethalfang/somaticseq:3.7.4'

    input:
        // All 8 caller VCFs + BAM joined by meta in tspipe.nf
        tuple val(meta),
              path(mutect2_vcf),
              path(vardict_vcf),
              path(varscan_vcf),
              path(strelka_vcf),
              path(freebayes_vcf),
              path(platypus_vcf),
              path(pindel_vcf),
              path(deepsomatic_vcf),
              path(bam),
              path(bai)
        tuple path(fasta), path(fai), path(dict)
        path  bed
        path  dbsnp_vcf

    output:
        // Module 1 (ensemble): emit raw consensus VCFs + workdir.
        // Post-processing (sort/bgzip/index/concat/rename) is in
        // SOMATICSEQ_POSTPROCESS which uses a gatk4 container (has bcftools).
        tuple val(meta), path("${meta.id}.somaticseq_workdir/Consensus.sSNV.vcf"),   emit: consensus_snv
        tuple val(meta), path("${meta.id}.somaticseq_workdir/Consensus.sINDEL.vcf"), emit: consensus_indel
        path  "${meta.id}.somaticseq_workdir",                                       emit: workdir
        path  "versions.yml",                                                        emit: versions
    stub:
        // nf-core stub blocks v1 (apply_nfcore_add_stub_blocks)
        """
        mkdir -p ${meta.id}.somaticseq_workdir
        mkdir -p ${meta.id}.somaticseq_workdir
        touch ${meta.id}.somaticseq_workdir/Consensus.sSNV.vcf ${meta.id}.somaticseq_workdir/Consensus.sINDEL.vcf versions.yml
        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            stub: true
        END_VERSIONS
        """


    script:
        def algo    = task.ext.algorithm ?: 'xgboost'
        def dbsnp_arg = dbsnp_vcf ? "--dbsnp-vcf ${dbsnp_vcf}" : ""
        """
        set -eo pipefail
        SAMPLE=${meta.id}
        WORK=\${SAMPLE}.somaticseq_workdir
        mkdir -p \$WORK

        # ----------------------------------------------------------------
        # 1. Preprocess arbitrary callers (FreeBayes, Platypus, Pindel, DeepSomatic)
        # ----------------------------------------------------------------
        ARB_SNV_LIST=()
        ARB_INDEL_LIST=()

        # 2026-05-17: arbitrary-caller loop covers all four arbitrary
        # callers, matching production's 8-caller setup in
        # scripts/07_somaticseq.py. Pindel was previously dropped because
        # splitVcf.py crashes on its symbolic-allele records (SV calls
        # like <INS>/<DEL>, breakend notation, <NON_REF>). The SV
        # pre-filter inserted further down strips those before splitVcf
        # runs, which lets Pindel contribute SNV/INDEL votes without
        # affecting flow for FreeBayes and Platypus (which only emit
        # plain alleles). DeepSomatic is also re-enabled; in this
        # pipeline it runs in PASS-only mode and rarely emits symbolic
        # records, but the same pre-filter protects against the corner
        # cases. If a caller still crashes after this change, the
        # filter's per-caller stderr logging makes the failure mode
        # visible in .command.err.
        for ENTRY in "freebayes:${freebayes_vcf}" "platypus:${platypus_vcf}" "pindel:${pindel_vcf}" "deepsomatic:${deepsomatic_vcf}"; do
            CALLER=\${ENTRY%%:*}
            SRC=\${ENTRY#*:}
            if [ -z "\$SRC" ] || [ ! -e "\$SRC" ]; then
                echo "[somaticseq] \$CALLER: no VCF provided, skipping" 1>&2
                continue
            fi

            # Fail-fast on 0-byte input (corruption check).
            # We've observed PINDEL + DEEPSOMATIC outputs getting zeroed
            # during parallel/resume races; treating it as a hard error here
            # is louder than the silent header-only VCF that splitVcf.py
            # would otherwise produce. Applies to both .vcf and .vcf.gz.
            if [ ! -s "\$SRC" ]; then
                echo "[somaticseq] \$CALLER: input \$SRC is 0 bytes; treating as corruption" 1>&2
                echo "  hint: remove the upstream task work dir + .nextflow/cache entry and resume" 1>&2
                exit 2
            fi

            # Decompress if gzipped (splitVcf.py expects plain text)
            if [[ "\$SRC" == *.gz ]]; then
                zcat "\$SRC" > "\${CALLER}.decompressed.vcf"
                SRC="\${CALLER}.decompressed.vcf"
            fi

            N=\$(grep -cv '^#' "\$SRC" 2>/dev/null) || N=0
            if [ "\$N" -eq 0 ]; then
                echo "[somaticseq] \$CALLER: header-only, skipping" 1>&2
                continue
            fi

            # Strip symbolic-allele records before splitVcf.py sees them.
            # SomaticSeq's arbitrary-caller path only handles plain SNVs
            # and INDELs; symbolic alleles (Pindel SVs like <INS>/<DEL>,
            # <NON_REF>, <*>, breakends like "G]chr5:1000]") and "." no-
            # call ALTs crash or get misclassified by splitVcf.py. The
            # awk filter keeps header lines verbatim and passes through
            # only records whose REF is plain nucleotides (A/C/G/T/N,
            # any case) and whose ALT is plain nucleotides with commas
            # allowed for multi-allelic. No-op for FreeBayes and Platypus.
            FILTERED="\${CALLER}.snv_indel_only.vcf"
            awk 'BEGIN{FS=OFS="\\t"} /^#/ {print; next} \$4 ~ /^[ACGTNacgtn]+\$/ && \$5 ~ /^[ACGTNacgtn,]+\$/ {print}' "\$SRC" > "\$FILTERED"
            N_FILT=\$(grep -cv '^#' "\$FILTERED" 2>/dev/null) || N_FILT=0
            DROPPED=\$((N - N_FILT))
            if [ "\$DROPPED" -gt 0 ]; then
                echo "[somaticseq] \$CALLER: dropped \$DROPPED non-SNV/INDEL records (symbolic alleles, SVs, breakends, no-calls)" 1>&2
            fi
            if [ "\$N_FILT" -eq 0 ]; then
                echo "[somaticseq] \$CALLER: no SNV/INDEL records after filter, skipping" 1>&2
                continue
            fi
            # ----------------------------------------------------------------
            # Drop alt-contig and decoy records (2026-05-24).
            # SomaticSeq enforces reference-dict ordering: chr1..chr22, chrX,
            # chrY, chrM, then alt/decoy. The `sort -V` below misorders alt
            # contigs (places chr1_KI270706v1_random between chr1 and chr2
            # because `_` sorts after digits in version-sort), and SomaticSeq's
            # vcf2tsv rejects the file. Alt-contig somatic calls have no
            # clinical interpretation in panel sequencing of unplaced sequence,
            # so dropping them here is safe. Upstream variant callers and
            # CNV_CALLING still see the alt contig.
            # ----------------------------------------------------------------
            PURGED="\${CALLER}.main_chroms_only.vcf"
            awk 'BEGIN{FS=OFS="\\t"} /^#/ {print; next} \$1 ~ /^chr([1-9]|1[0-9]|2[0-2]|X|Y|M)\$/ {print}' "\$FILTERED" > "\$PURGED"
            N_PURGE=\$(grep -cv '^#' "\$PURGED" 2>/dev/null) || N_PURGE=0
            DROPPED_ALT=\$((N_FILT - N_PURGE))
            if [ "\$DROPPED_ALT" -gt 0 ]; then
                echo "[somaticseq] \$CALLER: dropped \$DROPPED_ALT records on alt/decoy contigs" 1>&2
            fi
            if [ "\$N_PURGE" -eq 0 ]; then
                echo "[somaticseq] \$CALLER: no main-chromosome records after alt-drop, skipping" 1>&2
                continue
            fi

            N=\$N_PURGE
            SRC="\$PURGED"

            # Sort the source VCF (headers first, then chr/pos sort)
            SORTED="\${CALLER}.sorted.vcf"
            grep '^#'   "\$SRC" >  "\$SORTED"
            grep -v '^#' "\$SRC" | sort -k1,1V -k2,2g >> "\$SORTED"

            # Split into SNV + INDEL
            SNV="\${CALLER}_snvs.vcf"
            INDEL="\${CALLER}_indels.vcf"
            splitVcf.py -infile "\$SORTED" -snv "\$SNV" -indel "\$INDEL"

            # Sort each split VCF
            for VCF in "\$SNV" "\$INDEL"; do
                OUT="\${VCF%.vcf}_sorted.vcf"
                grep '^#'    "\$VCF" >  "\$OUT"
                # `|| true` tolerates header-only split VCFs. Pindel
                # after the SV pre-filter often has zero plain SNVs
                # in its FLT3+UBTF scope, so \$VCF here can be
                # header-only. Under `set -eo pipefail`, grep -v's
                # no-match exit code 1 would otherwise kill the task.
                # Same convention as the sort step in
                # modules/local/somaticseq_postprocess.nf.
                grep -v '^#' "\$VCF" | sort -k1,1V -k2,2g >> "\$OUT" || true
                mv "\$OUT" "\$VCF"
            done

            ARB_SNV_LIST+=("\$SNV")
            ARB_INDEL_LIST+=("\$INDEL")
            echo "[somaticseq] \$CALLER: prepared (records=\$N)" 1>&2
        done

        # ----------------------------------------------------------------
        # 2. Build and run SomaticSeq command
        # ----------------------------------------------------------------
        # Strip 'set -e' temporarily so we can catch parallel-mode failure
        set +e

        somaticseq_parallel.py \\
            --output-directory \$WORK \\
            --genome-reference ${fasta} \\
            --threads ${task.cpus} \\
            --algorithm ${algo} \\
            --inclusion-region ${bed} \\
            ${dbsnp_arg} \\
            single \\
              --bam-file ${bam} \\
              --sample-name \${SAMPLE} \\
              --mutect2-vcf ${mutect2_vcf} \\
              --vardict-vcf ${vardict_vcf} \\
              --varscan-vcf ${varscan_vcf} \\
              --strelka-vcf ${strelka_vcf} \\
              \$( [ \${#ARB_SNV_LIST[@]} -gt 0 ]   && echo "--arbitrary-snvs   \${ARB_SNV_LIST[@]}" ) \\
              \$( [ \${#ARB_INDEL_LIST[@]} -gt 0 ] && echo "--arbitrary-indels \${ARB_INDEL_LIST[@]}" ) \\
            > somaticseq_stdout.log 2> somaticseq_stderr.log
        RC=\$?

        # Detect the known empty-chromosome FileNotFoundError + CombineVariants bug
        if [ \$RC -ne 0 ] \\
           && grep -q "FileNotFoundError" somaticseq_stderr.log \\
           && grep -q "CombineVariants"  somaticseq_stderr.log; then
            echo "[somaticseq] parallel mode crashed (empty-chromosome bug); retrying single-threaded" 1>&2
            rm -rf \$WORK
            mkdir -p \$WORK
            somaticseq_parallel.py \\
                --output-directory \$WORK \\
                --genome-reference ${fasta} \\
                --threads 1 \\
                --algorithm ${algo} \\
                --inclusion-region ${bed} \\
                ${dbsnp_arg} \\
                single \\
                  --bam-file ${bam} \\
                  --sample-name \${SAMPLE} \\
                  --mutect2-vcf ${mutect2_vcf} \\
                  --vardict-vcf ${vardict_vcf} \\
                  --varscan-vcf ${varscan_vcf} \\
                  --strelka-vcf ${strelka_vcf} \\
                  \$( [ \${#ARB_SNV_LIST[@]} -gt 0 ]   && echo "--arbitrary-snvs   \${ARB_SNV_LIST[@]}" ) \\
                  \$( [ \${#ARB_INDEL_LIST[@]} -gt 0 ] && echo "--arbitrary-indels \${ARB_INDEL_LIST[@]}" ) \\
                > somaticseq_stdout.log 2> somaticseq_stderr.log
            RC=\$?
        fi

        set -eo pipefail
        if [ \$RC -ne 0 ]; then
            echo "[somaticseq] FAILED (rc=\$RC). stderr tail:" 1>&2
            tail -30 somaticseq_stderr.log 1>&2
            exit \$RC
        fi

        # Module 1 emits raw consensus VCFs from \$WORK.
        # Sort/bgzip/index/concat/rename happens in SOMATICSEQ_POSTPROCESS
        # (uses gatk4 container which has bcftools+bgzip+tabix on PATH).
        echo "[somaticseq \${SAMPLE}] consensus VCFs ready:" 1>&2
        ls -la \$WORK/Consensus.s{SNV,INDEL}.vcf 1>&2 || true

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            somaticseq: \$(somaticseq_parallel.py --version 2>&1 | sed 's/.*v//' | head -n1)
        END_VERSIONS
        """
}
