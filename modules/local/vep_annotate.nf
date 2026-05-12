/*
 * modules/local/vep_annotate.nf
 *
 * VEP + ANNOVAR
 *
 * Note: VEP + ANNOVAR. params.vep_cache + params.annovar_db. See scripts/13_annotate.py.
 *
 * TODO: this is a stub. Fill in the script: block with the actual command line.
 * The original Python wrapper in scripts/ shows the exact invocation -- this
 * module just needs to translate that to a Nextflow process body.
 */

process VEP_ANNOTATE {
    tag        "${meta.id}"
    label      'process_medium'

    input:
        tuple val(meta), path(vcf)
        tuple path(fasta), path(fai), path(dict)

    output:
        tuple val(meta), path("${meta.id}.annotated.tsv"), emit: tsv

    script:
        """
        # TODO: replace this stub with the tool invocation from the source script.
        echo "STUB: VEP_ANNOTATE for ${meta.id}" >&2
        # Touch output filename(s) so downstream channels don't break during DAG validation:
        touch ${meta.id}.annotated.tsv
        """
}
