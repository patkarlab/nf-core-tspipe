/*
 * modules/local/u2af1_rescue.nf
 *
 * U2AF1 pileup rescue
 *
 * Note: Pileup-based rescue for hg38 paralog-collapsed U2AF1 loci. Cannot rely on standard callers here.
 *
 * TODO: this is a stub. Fill in the script: block with the actual command line.
 * The original Python wrapper in scripts/ shows the exact invocation -- this
 * module just needs to translate that to a Nextflow process body.
 */

process U2AF1_RESCUE {
    tag        "${meta.id}"
    label      'process_medium'

    input:
        tuple val(meta), path(bam), path(bai)
        tuple path(fasta), path(fai), path(dict)

    output:
        tuple val(meta), path("${meta.id}_u2af1_rescue.tsv"), emit: tsv

    script:
        """
        # TODO: replace this stub with the tool invocation from the source script.
        echo "STUB: U2AF1_RESCUE for ${meta.id}" >&2
        # Touch output filename(s) so downstream channels don't break during DAG validation:
        touch ${meta.id}_u2af1_rescue.tsv
        """
}
