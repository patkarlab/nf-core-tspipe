/*
 * modules/local/sv_callers.nf
 *
 * Manta + Delly + SvABA
 *
 * Note: SV callers + merge. See scripts/11_sv_callers.py.
 *
 * TODO: this is a stub. Fill in the script: block with the actual command line.
 * The original Python wrapper in scripts/ shows the exact invocation -- this
 * module just needs to translate that to a Nextflow process body.
 */

process SV_CALLERS {
    tag        "${meta.id}"
    label      'process_medium'

    input:
        tuple val(meta), path(bam), path(bai)
        tuple path(fasta), path(fai), path(dict)
        path bed

    output:
        tuple val(meta), path("${meta.id}.sv.vcf.gz"), emit: vcf
        tuple val(meta), path("${meta.id}.sv.txt"), emit: txt
    stub:
        // nf-core stub blocks v1 (apply_nfcore_add_stub_blocks)
        """
        touch ${meta.id}.sv.vcf.gz ${meta.id}.sv.txt
        """


    script:
        """
        # TODO: replace this stub with the tool invocation from the source script.
        echo "STUB: SV_CALLERS for ${meta.id}" >&2
        # Touch output filename(s) so downstream channels don't break during DAG validation:
        touch ${meta.id}.sv.vcf.gz
        touch ${meta.id}.sv.txt
        """
}
