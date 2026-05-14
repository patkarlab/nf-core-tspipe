/*
 * modules/local/igv_reports.nf
 *
 * IGV HTML reports
 *
 * Note: igv-reports HTML per variant. See scripts/16_igv_reports.py.
 *
 * TODO: this is a stub. Fill in the script: block with the actual command line.
 * The original Python wrapper in scripts/ shows the exact invocation -- this
 * module just needs to translate that to a Nextflow process body.
 */

process IGV_REPORTS {
    tag        "${meta.id}"
    label      'process_medium'

    input:
        tuple val(meta), path(clinical_tsv), path(bam), path(bai)

    output:
        tuple val(meta), path("${meta.id}_igv_reports.html"), emit: html
    stub:
        // nf-core stub blocks v1 (apply_nfcore_add_stub_blocks)
        """
        touch ${meta.id}_igv_reports.html
        """


    script:
        """
        # TODO: replace this stub with the tool invocation from the source script.
        echo "STUB: IGV_REPORTS for ${meta.id}" >&2
        # Touch output filename(s) so downstream channels don't break during DAG validation:
        touch ${meta.id}_igv_reports.html
        """
}
