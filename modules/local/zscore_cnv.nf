/*
 * modules/local/zscore_cnv.nf
 *
 * Z-score CNV
 *
 * Note: Z-score CNV vs PoN. Uses params.cnv_loo_summary + params.cnv_noise_profile.
 *
 * TODO: this is a stub. Fill in the script: block with the actual command line.
 * The original Python wrapper in scripts/ shows the exact invocation -- this
 * module just needs to translate that to a Nextflow process body.
 */

process ZSCORE_CNV {
    tag        "${meta.id}"
    label      'process_medium'

    input:
        tuple val(meta), path(bam), path(bai)
        path bed

    output:
        tuple val(meta), path("${meta.id}_zscore_cnv.tsv"), emit: calls

    script:
        """
        # TODO: replace this stub with the tool invocation from the source script.
        echo "STUB: ZSCORE_CNV for ${meta.id}" >&2
        # Touch output filename(s) so downstream channels don't break during DAG validation:
        touch ${meta.id}_zscore_cnv.tsv
        """
}
