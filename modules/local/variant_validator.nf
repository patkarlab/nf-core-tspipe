/*
 * modules/local/variant_validator.nf
 *
 * VariantValidator HGVS
 *
 * Note: HGVS nomenclature validation via VariantValidator. See scripts/17_variant_validator.py.
 *
 * TODO: this is a stub. Fill in the script: block with the actual command line.
 * The original Python wrapper in scripts/ shows the exact invocation -- this
 * module just needs to translate that to a Nextflow process body.
 */

process VARIANT_VALIDATOR {
    tag        "${meta.id}"
    label      'process_medium'

    input:
        tuple val(meta), path(tsv)

    output:
        tuple val(meta), path("${meta.id}.validated.tsv"), emit: tsv
    stub:
        // nf-core stub blocks v1 (apply_nfcore_add_stub_blocks)
        """
        touch ${meta.id}.validated.tsv
        """


    script:
        """
        # TODO: replace this stub with the tool invocation from the source script.
        echo "STUB: VARIANT_VALIDATOR for ${meta.id}" >&2
        # Touch output filename(s) so downstream channels don't break during DAG validation:
        touch ${meta.id}.validated.tsv
        """
}
