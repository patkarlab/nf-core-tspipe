/*
 * modules/local/cnv_clinical_report.nf
 *
 * CNV clinical report
 *
 * Note: Clinical-friendly CNV report. See scripts/12f_cnv_clinical_report.py.
 *
 * TODO: this is a stub. Fill in the script: block with the actual command line.
 * The original Python wrapper in scripts/ shows the exact invocation -- this
 * module just needs to translate that to a Nextflow process body.
 */

process CNV_CLINICAL_REPORT {
    tag        "${meta.id}"
    label      'process_medium'

    input:
        tuple val(meta), path(concordance_tsv)

    output:
        tuple val(meta), path("${meta.id}_cnv_clinical.tsv"), emit: tsv

    script:
        """
        # TODO: replace this stub with the tool invocation from the source script.
        echo "STUB: CNV_CLINICAL_REPORT for ${meta.id}" >&2
        # Touch output filename(s) so downstream channels don't break during DAG validation:
        touch ${meta.id}_cnv_clinical.tsv
        """
}
