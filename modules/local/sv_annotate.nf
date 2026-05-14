/*
 * modules/local/sv_annotate.nf
 *
 * AnnotSV
 *
 * Note: AnnotSV. See scripts/19_sv_annotate.py.
 *
 * TODO: this is a stub. Fill in the script: block with the actual command line.
 * The original Python wrapper in scripts/ shows the exact invocation -- this
 * module just needs to translate that to a Nextflow process body.
 */

process SV_ANNOTATE {
    tag        "${meta.id}"
    label      'process_medium'

    input:
        tuple val(meta), path(sv_vcf)

    output:
        tuple val(meta), path("${meta.id}_sv_annotated.tsv"), emit: tsv
    stub:
        // nf-core stub blocks v1 (apply_nfcore_add_stub_blocks)
        """
        touch ${meta.id}_sv_annotated.tsv
        """


    script:
        """
        # TODO: replace this stub with the tool invocation from the source script.
        echo "STUB: SV_ANNOTATE for ${meta.id}" >&2
        # Touch output filename(s) so downstream channels don't break during DAG validation:
        touch ${meta.id}_sv_annotated.tsv
        """
}
