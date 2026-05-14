/*
 * modules/local/varscan.nf
 *
 * VarScan2 somatic caller: samtools mpileup -> varscan mpileup2snp +
 * mpileup2indel -> bcftools concat. Mirrors scripts/06_variant_callers.py
 * run_varscan().
 *
 * Critical thresholds (from production):
 *   --min-coverage 10  --min-reads2 5  --min-avg-qual 15
 *   --p-value 1e-4
 *   --min-var-freq 0.003  (overridden to 0.03 on gandalf, see gandalf.config)
 *
 * The min-var-freq is exposed as task.ext.min_var_freq so site config can tune.
 */

process VARSCAN {
    tag        "${meta.id}"
    label      'process_medium'

    input:
        tuple val(meta), path(bam), path(bai)
        tuple path(fasta), path(fai), path(dict)
        path  bed

    output:
        tuple val(meta), path("${meta.id}.varscan.vcf"), emit: vcf
        path  "versions.yml",                             emit: versions
    stub:
        // nf-core stub blocks v1 (apply_nfcore_add_stub_blocks)
        """
        touch ${meta.id}.varscan.vcf versions.yml
        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            stub: true
        END_VERSIONS
        """


    script:
        def min_cov  = task.ext.min_coverage ?: '10'
        def min_r2   = task.ext.min_reads2   ?: '5'
        def min_qual = task.ext.min_avg_qual ?: '15'
        def min_vaf  = task.ext.min_var_freq ?: '0.003'
        def pval     = task.ext.p_value      ?: '1e-4'
        """
        # Generate mpileup once, reuse twice (SNP + indel).
        samtools mpileup \\
            -f ${fasta} \\
            -l ${bed} \\
            ${bam} \\
          > ${meta.id}.mpileup

        # SNPs
        varscan mpileup2snp ${meta.id}.mpileup \\
            --min-coverage ${min_cov} \\
            --min-reads2 ${min_r2} \\
            --min-avg-qual ${min_qual} \\
            --min-var-freq ${min_vaf} \\
            --p-value ${pval} \\
            --output-vcf 1 \\
          > ${meta.id}.varscan_snp.vcf

        # Indels
        varscan mpileup2indel ${meta.id}.mpileup \\
            --min-coverage ${min_cov} \\
            --min-reads2 ${min_r2} \\
            --min-avg-qual ${min_qual} \\
            --min-var-freq ${min_vaf} \\
            --p-value ${pval} \\
            --output-vcf 1 \\
          > ${meta.id}.varscan_indel.vcf

        # bgzip + tabix + concat
        bgzip ${meta.id}.varscan_snp.vcf
        bgzip ${meta.id}.varscan_indel.vcf
        tabix -p vcf ${meta.id}.varscan_snp.vcf.gz
        tabix -p vcf ${meta.id}.varscan_indel.vcf.gz

        bcftools concat -a \\
            ${meta.id}.varscan_snp.vcf.gz \\
            ${meta.id}.varscan_indel.vcf.gz \\
          > ${meta.id}.varscan.vcf

        rm ${meta.id}.mpileup

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            varscan: \$(varscan 2>&1 | grep -oP 'VarScan v\\K[0-9.]+' | head -n1 || echo unknown)
            samtools: \$(samtools --version | head -n1 | sed 's/samtools //')
            bcftools: \$(bcftools --version | head -n1 | sed 's/bcftools //')
        END_VERSIONS
        """
}
