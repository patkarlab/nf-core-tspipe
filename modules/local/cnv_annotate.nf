/*
 * modules/local/cnv_annotate.nf
 *
 * CNV annotate
 *
 * Note: CNV annotation. See scripts/18_cnv_annotate.py.
 *
 * TODO: this is a stub. Fill in the script: block with the actual command line.
 * The original Python wrapper in scripts/ shows the exact invocation -- this
 * module just needs to translate that to a Nextflow process body.
 */

process CNV_ANNOTATE {
    tag        "${meta.id}"
    label      'process_medium'

    input:
        tuple val(meta), path(cnv_tsv)

    output:
        tuple val(meta), path("${meta.id}_cnv_annotated.tsv"), emit: tsv

    script:
        """
        # TODO: replace this stub with the tool invocation from the source script.
        echo "STUB: CNV_ANNOTATE for ${meta.id}" >&2
        # Touch output filename(s) so downstream channels don't break during DAG validation:
        touch ${meta.id}_cnv_annotated.tsv
        """
}
