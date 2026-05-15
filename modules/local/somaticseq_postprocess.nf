/*
 * modules/local/somaticseq_postprocess.nf
 *
 * Post-processing for SomaticSeq consensus VCFs.
 *
 * Split out from SOMATICSEQ_ENSEMBLE on 2026-05-17 because the
 * lethalfang/somaticseq:3.7.4 container lacks bcftools/bgzip/tabix
 * on PATH. This module uses the gatk4 container which has all three.
 *
 * Pipeline:
 *   1. Sort each consensus VCF (headers first, then chr/pos sort)
 *   2. bgzip + tabix index
 *   3. bcftools concat -> final merged ${sample}.somaticseq.vcf
 *   4. Rename caller INFO field codes to MVDKFPID
 */

process SOMATICSEQ_POSTPROCESS {
    tag        "${meta.id}"
    label      'process_low'
    container  'docker://broadinstitute/gatk:4.5.0.0'

    input:
        tuple val(meta), path(snv_raw), path(indel_raw)

    output:
        tuple val(meta), path("${meta.id}.somaticseq.vcf"),                        emit: vcf
        tuple val(meta), path("${meta.id}.somaticseq.consensus_snv.vcf.gz"),       emit: snv_vcf
        tuple val(meta), path("${meta.id}.somaticseq.consensus_snv.vcf.gz.tbi"),   emit: snv_tbi
        tuple val(meta), path("${meta.id}.somaticseq.consensus_indel.vcf.gz"),     emit: indel_vcf
        tuple val(meta), path("${meta.id}.somaticseq.consensus_indel.vcf.gz.tbi"), emit: indel_tbi
        path  "versions.yml",                                                      emit: versions

    stub:
        """
        touch ${meta.id}.somaticseq.vcf ${meta.id}.somaticseq.consensus_snv.vcf.gz ${meta.id}.somaticseq.consensus_snv.vcf.gz.tbi ${meta.id}.somaticseq.consensus_indel.vcf.gz ${meta.id}.somaticseq.consensus_indel.vcf.gz.tbi versions.yml
        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            stub: true
        END_VERSIONS
        """

    script:
        """
        set -eo pipefail
        SAMPLE=${meta.id}
        SNV_SORTED=\${SAMPLE}.somaticseq.consensus_snv.vcf
        INDEL_SORTED=\${SAMPLE}.somaticseq.consensus_indel.vcf

        grep '^#'    ${snv_raw}   >  \$SNV_SORTED
        grep -v '^#' ${snv_raw}   | sort -k1,1V -k2,2g >> \$SNV_SORTED || true
        grep '^#'    ${indel_raw} >  \$INDEL_SORTED
        grep -v '^#' ${indel_raw} | sort -k1,1V -k2,2g >> \$INDEL_SORTED || true

        bgzip -c \$SNV_SORTED   > \${SNV_SORTED}.gz
        bgzip -c \$INDEL_SORTED > \${INDEL_SORTED}.gz
        tabix -p vcf \${SNV_SORTED}.gz
        tabix -p vcf \${INDEL_SORTED}.gz

        bcftools concat -a \${SNV_SORTED}.gz \${INDEL_SORTED}.gz -o \${SAMPLE}.somaticseq.vcf

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
print(f"[somaticseq_postprocess] renamed caller INFO -> MVDKFPID", file=sys.stderr)
PYRENAME

        SNV_N=\$(grep -cv '^#' \${SNV_SORTED}) || SNV_N=0
        INDEL_N=\$(grep -cv '^#' \${INDEL_SORTED}) || INDEL_N=0
        FINAL_N=\$(grep -cv '^#' \${SAMPLE}.somaticseq.vcf) || FINAL_N=0
        echo "[somaticseq_postprocess ${meta.id}] SNV=\$SNV_N  INDEL=\$INDEL_N  FINAL=\$FINAL_N" 1>&2

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            bcftools: \$(bcftools --version | head -n1 | sed 's/bcftools //')
        END_VERSIONS
        """
}
