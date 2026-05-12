/*
 * modules/local/cnv_plots.nf
 *
 * CNV plots
 *
 * Note: Diagnostic CNV plots. See scripts/12b_cnv_plots.py.
 *
 * TODO: this is a stub. Fill in the script: block with the actual command line.
 * The original Python wrapper in scripts/ shows the exact invocation -- this
 * module just needs to translate that to a Nextflow process body.
 */

process CNV_PLOTS {
    tag        "${meta.id}"
    label      'process_medium'

    input:
        tuple val(meta), path(cnr)

    output:
        tuple val(meta), path("${meta.id}_cnv_plot.pdf"), emit: pdf

    script:
        """
        # TODO: replace this stub with the tool invocation from the source script.
        echo "STUB: CNV_PLOTS for ${meta.id}" >&2
        # Touch output filename(s) so downstream channels don't break during DAG validation:
        touch ${meta.id}_cnv_plot.pdf
        """
}
