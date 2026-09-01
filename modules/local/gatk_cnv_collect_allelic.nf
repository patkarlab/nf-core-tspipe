/*
 * modules/local/gatk_cnv_collect_allelic.nf  (BAF_V1)
 *
 * Per-sample CollectAllelicCounts over the panel's BAF SNP catalog
 * (snp_sites.baf.bed: 370 x 17p probe windows + 4 autosomal anchors).
 * Feeds both ModelSegments (minor-allele-fraction track) and the
 * CNV_BAF_CNLOH detector. Host env via the GATK_CNV_.* umbrella in
 * conf/twist_apply.config (GATK 4.6.2.0 parity with the build side).
 */

process GATK_CNV_COLLECT_ALLELIC {
    tag   "${meta.id}"
    label 'process_medium'

    input:
        tuple val(meta), path(bam), path(bai)
        tuple path(fasta), path(fai), path(dict)
        path snp_bed

    output:
        tuple val(meta), path("${meta.id}.allelicCounts.tsv"), emit: allelic

    stub:
        """
        touch ${meta.id}.allelicCounts.tsv
        """

    script:
        def xmx = task.memory ? Math.max(2, task.memory.toGiga() - 2) : 8
        """
        gatk --java-options "-Xmx${xmx}g" CollectAllelicCounts \\
            -I ${bam} \\
            -L ${snp_bed} \\
            -R ${fasta} \\
            -O ${meta.id}.allelicCounts.tsv
        """
}
