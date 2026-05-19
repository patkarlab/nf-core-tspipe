/*
 * modules/local/pindel_flt3_filter.nf
 *
 * Subset the panel-wide Pindel VCF to the FLT3 locus and keep only
 * DUP/INS structural variant types. Output is consumed as the fourth
 * caller by FLT3_CONSENSUS.
 *
 * Mirrors production scripts/09_flt3_itd.py:step_pindel_filter(), which
 * runs:
 *     bcftools view -t chr13:28003000-28101000 <pindel.vcf>
 *     | bcftools view -i 'INFO/SVTYPE="DUP" || INFO/SVTYPE="INS"'
 *
 * The Pindel VCF is plain text (uncompressed, unindexed) coming out of
 * the PINDEL module. bcftools accepts that fine with -t, no need to
 * bgzip/tabix first.
 *
 * Region default is panel-agnostic for myeloid (FLT3 hg38 transcript +
 * flanking). Override via params.flt3_region.
 *
 * Container: a tiny bcftools image. Reuse the existing samtools tag
 * since samtools containers ship bcftools too, avoiding a fresh
 * container pull on every node.
 */

process PINDEL_FLT3_FILTER {
    tag        "${meta.id}"
    label      'process_low'

    container  'quay.io/biocontainers/bcftools:1.20--h8b25389_0'

    input:
        tuple val(meta), path(pindel_vcf)
        val   flt3_region

    output:
        tuple val(meta), path("${meta.id}.pindel_flt3.vcf"), emit: vcf
        path  "versions.yml",                                emit: versions

    stub:
        // nf-core stub blocks v1
        """
        touch ${meta.id}.pindel_flt3.vcf
        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            stub: true
        END_VERSIONS
        """

    script:
        """
        # Subset to FLT3 locus, then keep only DUP/INS SV types.
        # -t accepts CHR:START-END without an index (unlike -r).
        bcftools view -t ${flt3_region} ${pindel_vcf} \\
            | bcftools view \\
                -i 'INFO/SVTYPE="DUP" || INFO/SVTYPE="INS"' \\
                -o ${meta.id}.pindel_flt3.vcf

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            bcftools: \$(bcftools --version | head -1 | awk '{print \$2}')
        END_VERSIONS
        """
}
