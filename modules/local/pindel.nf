/*
 * modules/local/pindel.nf
 *
 * Pindel
 *
 * Note: pindel + pindel2vcf using pindel_targets_hg38.bed subset.
 *
 * TODO: this is a stub. Fill in the script: block with the actual command line.
 * The original Python wrapper in scripts/ shows the exact invocation -- this
 * module just needs to translate that to a Nextflow process body.
 */

process PINDEL {
    tag        "${meta.id}"
    label      'process_medium'

    input:
        tuple val(meta), path(bam), path(bai)
        tuple path(fasta), path(fai), path(dict)
        path pindel_bed

    output:
        tuple val(meta), path("${meta.id}_pindel.vcf"), emit: vcf

    script:
        """
        # TODO: replace this stub with the tool invocation from the source script.
        echo "STUB: PINDEL for ${meta.id}" >&2
        # Touch output filename(s) so downstream channels don't break during DAG validation:
        touch ${meta.id}_pindel.vcf
        """
}
