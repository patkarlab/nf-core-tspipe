/*
 * modules/local/vardict.nf
 *
 * VarDict
 *
 * Note: VarDict | teststrandbias.R | var2vcf_valid.pl. See scripts/06_variant_callers.py.
 *
 * TODO: this is a stub. Fill in the script: block with the actual command line.
 * The original Python wrapper in scripts/ shows the exact invocation -- this
 * module just needs to translate that to a Nextflow process body.
 */

process VARDICT {
    tag        "${meta.id}"
    label      'process_medium'

    input:
        tuple val(meta), path(bam), path(bai)
        tuple path(fasta), path(fai), path(dict)
        path bed

    output:
        tuple val(meta), path("${meta.id}.vardict.vcf.gz"), emit: vcf

    script:
        """
        # TODO: replace this stub with the tool invocation from the source script.
        echo "STUB: VARDICT for ${meta.id}" >&2
        # Touch output filename(s) so downstream channels don't break during DAG validation:
        touch ${meta.id}.vardict.vcf.gz
        """
}
