/*
 * modules/local/flt3_to_variants.nf
 *
 * FLT3 -> variants merge
 *
 * Note: Tag SNV-path FLT3 hits as Confirmed_by_FLT3_ITD_ensemble; append PASS_HIGH/PASS_LOW ITDs as rows. See scripts/17b_flt3_to_variants.py.
 *
 * TODO: this is a stub. Fill in the script: block with the actual command line.
 * The original Python wrapper in scripts/ shows the exact invocation -- this
 * module just needs to translate that to a Nextflow process body.
 */

process FLT3_TO_VARIANTS {
    tag        "${meta.id}"
    label      'process_medium'

    input:
        tuple val(meta), path(clinical_tsv), path(flt3_consensus_tsv)

    output:
        tuple val(meta), path("${meta.id}.final.tsv"), emit: tsv

    script:
        """
        # TODO: replace this stub with the tool invocation from the source script.
        echo "STUB: FLT3_TO_VARIANTS for ${meta.id}" >&2
        # Touch output filename(s) so downstream channels don't break during DAG validation:
        touch ${meta.id}.final.tsv
        """
}
