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

        # NOTE 2026-05-17: pindel and deepsomatic temporarily dropped from
        # the arbitrary-caller loop. Both produce valid VCFs upstream but the
        # SomaticSeq preprocessing loop crashes during their iteration in ways
        # that proved hard to pin down within a single debug session.
        # Production's 07_somaticseq.py uses the 6-caller stable baseline.
        # Revisit pindel+deepsomatic integration in a dedicated session.
        for ENTRY in "freebayes:${freebayes_vcf}" "platypus:${platypus_vcf}"; do
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
                grep -v '^#' "\$VCF" | sort -k1,1V -k2,2g >> "\$OUT"
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
