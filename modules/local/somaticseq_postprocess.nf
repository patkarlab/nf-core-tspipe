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
# Rename SomaticSeq's caller-decision INFO field to the stable token
# "MVDKFP" that downstream parsers (bin/annotate.py) look for. We
# match production's INFO_TAG exactly; production's 07_somaticseq.py
# docstring notes downstream parsers match the literal string "MVDKFP".
#
# Number=N is parsed from SomaticSeq's emitted header rather than
# hardcoded, so this stays consistent if a caller's VCF was empty and
# got skipped (N < 8), or if upstream is currently feeding fewer
# callers than the maximum (N = 6 with Pindel + DeepSomatic disabled).
#
# Native-caller emit order is fixed by SomaticSeq itself:
#   MuTect, VarScan2, VarDict, Strelka  (NOT VarDict before VarScan).
# Arbitrary callers follow in the order they were passed to
# somaticseq_parallel.py in modules/local/somaticseq.nf.
import re, sys
path = sys.argv[1]
caller_labels = ["Mutect2", "VarScan", "VarDict", "Strelka",
                 "FreeBayes", "Platypus", "Pindel", "DeepSomatic"]
INFO_TAG = "MVDKFP"

with open(path) as f:
    content = f.read()

# Parse the existing caller-decision header to learn N (bitmap width).
m = re.search(
    r'##INFO=<ID=[A-Z]+\\d+,Number=(\\d+),Type=\\w+,'
    r'Description="Calling decision of the \\d+ algorithms:[^"]*">',
    content,
)
if not m:
    print("[somaticseq_postprocess] WARNING: no caller-decision INFO "
          "header found; nothing renamed", file=sys.stderr)
    sys.exit(0)

n = int(m.group(1))
active = caller_labels[:n]
label_csv = ", ".join(active)

# Rewrite the header to use INFO_TAG and the parsed N, with the
# description listing only the callers that actually contributed.
content = re.sub(
    r'##INFO=<ID=[A-Z]+\\d+,Number=\\d+,Type=\\w+,'
    r'Description="Calling decision of the \\d+ algorithms:[^"]*">',
    f'##INFO=<ID={INFO_TAG},Number={n},Type=String,'
    f'Description="Calling decision of the {n} algorithms: {label_csv}">',
    content,
)
# Rewrite per-record field names. The pattern matches things like
# MVDK01=, MVDK0123=, etc. - uppercase-letters-then-digits followed
# by "=" - and rewrites the prefix to INFO_TAG. Sample IDs and other
# tokens do not match because they lack the uppercase+digits shape
# immediately before an "=".
content = re.sub(r'\\b[A-Z]{2,}\\d+(?==)', INFO_TAG, content)

with open(path, "w") as f:
    f.write(content)

print(f"[somaticseq_postprocess] renamed caller INFO -> {INFO_TAG} "
      f"(Number={n}: {label_csv})", file=sys.stderr)
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
