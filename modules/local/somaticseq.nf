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
        // All 8 caller VCFs joined by meta in tspipe.nf
        tuple val(meta),
              path(mutect2_vcf),
              path(vardict_vcf),
              path(varscan_vcf),
              path(strelka_vcf),
              path(freebayes_vcf),
              path(platypus_vcf),
              path(pindel_vcf),
              path(deepsomatic_vcf)
        tuple val(_meta_bam), path(bam), path(bai)
        tuple path(fasta), path(fai), path(dict)
        path  bed
        path  dbsnp_vcf

    output:
        tuple val(meta), path("${meta.id}.somaticseq.vcf"),                       emit: vcf
        tuple val(meta), path("${meta.id}.somaticseq.consensus_snv.vcf.gz"),      emit: snv_vcf
        tuple val(meta), path("${meta.id}.somaticseq.consensus_indel.vcf.gz"),    emit: indel_vcf
        path  "${meta.id}.somaticseq_workdir",                                    emit: workdir
        path  "versions.yml",                                                     emit: versions
    stub:
        // nf-core stub blocks v1 (apply_nfcore_add_stub_blocks)
        """
        mkdir -p ${meta.id}.somaticseq_workdir
        touch ${meta.id}.somaticseq.vcf ${meta.id}.somaticseq.consensus_snv.vcf.gz ${meta.id}.somaticseq.consensus_indel.vcf.gz versions.yml
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

        for ENTRY in "freebayes:${freebayes_vcf}" "platypus:${platypus_vcf}" \\
                     "pindel:${pindel_vcf}" "deepsomatic:${deepsomatic_vcf}"; do
            CALLER=\${ENTRY%%:*}
            SRC=\${ENTRY#*:}
            if [ -z "\$SRC" ] || [ ! -e "\$SRC" ]; then
                echo "[somaticseq] \$CALLER: no VCF provided, skipping" 1>&2
                continue
            fi

            # Decompress if gzipped (splitVcf.py expects plain text)
            if [[ "\$SRC" == *.gz ]]; then
                zcat "\$SRC" > "\${CALLER}.decompressed.vcf"
                SRC="\${CALLER}.decompressed.vcf"
            fi

            N=\$(grep -cv '^#' "\$SRC" 2>/dev/null || echo 0)
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

        # ----------------------------------------------------------------
        # 3. Sort + bgzip + index consensus VCFs
        # ----------------------------------------------------------------
        SNV_RAW=\$WORK/Consensus.sSNV.vcf
        INDEL_RAW=\$WORK/Consensus.sINDEL.vcf

        SNV_SORTED=\${SAMPLE}.somaticseq.consensus_snv.vcf
        INDEL_SORTED=\${SAMPLE}.somaticseq.consensus_indel.vcf

        grep '^#'    \$SNV_RAW   >  \$SNV_SORTED
        grep -v '^#' \$SNV_RAW   | sort -k1,1V -k2,2g >> \$SNV_SORTED
        grep '^#'    \$INDEL_RAW >  \$INDEL_SORTED
        grep -v '^#' \$INDEL_RAW | sort -k1,1V -k2,2g >> \$INDEL_SORTED

        bgzip -c \$SNV_SORTED   > \${SNV_SORTED}.gz
        bgzip -c \$INDEL_SORTED > \${INDEL_SORTED}.gz
        bcftools index -t \${SNV_SORTED}.gz
        bcftools index -t \${INDEL_SORTED}.gz

        # ----------------------------------------------------------------
        # 4. Merge SNV + INDEL into final VCF
        # ----------------------------------------------------------------
        bcftools concat -a \${SNV_SORTED}.gz \${INDEL_SORTED}.gz -o \${SAMPLE}.somaticseq.vcf

        # ----------------------------------------------------------------
        # 5. Rename caller INFO field codes (8-caller version)
        # ----------------------------------------------------------------
        python3 - "\${SAMPLE}.somaticseq.vcf" <<'PYRENAME'
import re, sys
path = sys.argv[1]
caller_labels = ["Mutect2", "VarDict", "VarScan", "Strelka",
                 "FreeBayes", "Platypus", "Pindel", "DeepSomatic"]
label_csv = ", ".join(caller_labels)
with open(path) as f:
    content = f.read()
content = re.sub(
    r'##INFO=<ID=([A-Z]+\\d+),Number=\\d+,Type=\\w+,'
    r'Description="Calling decision of the \\d+ algorithms:[^"]*">',
    f'##INFO=<ID=MVDKFPID,Number=8,Type=String,'
    f'Description="Calling decision of the 8 algorithms: {label_csv}">',
    content,
)
content = re.sub(r'\\b[A-Z]{2,}\\d+(?==)', 'MVDKFPID', content)
with open(path, "w") as f:
    f.write(content)
print(f"[somaticseq] renamed caller INFO -> MVDKFPID ({label_csv})", file=sys.stderr)
PYRENAME

        # ----------------------------------------------------------------
        # 6. Final summary
        # ----------------------------------------------------------------
        for LABEL in "SNV consensus" "INDEL consensus" "Merged VCF"; do : ; done  # no-op for clarity
        SNV_N=\$(grep -cv '^#' \${SNV_SORTED} || echo 0)
        INDEL_N=\$(grep -cv '^#' \${INDEL_SORTED} || echo 0)
        FINAL_N=\$(grep -cv '^#' \${SAMPLE}.somaticseq.vcf || echo 0)
        echo "[somaticseq ${meta.id}] SNV=\$SNV_N  INDEL=\$INDEL_N  FINAL=\$FINAL_N" 1>&2

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            somaticseq: \$(somaticseq_parallel.py --version 2>&1 | sed 's/.*v//' | head -n1)
            bcftools:   \$(bcftools --version | head -n1 | sed 's/bcftools //')
        END_VERSIONS
        """
}
