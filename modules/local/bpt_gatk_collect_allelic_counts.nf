/*
 * modules/local/bpt_gatk_collect_allelic_counts.nf
 *
 * Per-sample CollectAllelicCounts over snp_sites.baf.bed (374 x 120 bp
 * probe windows: 370 x 17p + 4 autosomal). Runs on ALL 48 rows by design:
 * the informative-site subset and the cohort choice (handoff decision 2)
 * are applied downstream in BPT_AGGREGATE_BAF, so flipping the cohort
 * never re-runs collection.
 */

process BPT_GATK_COLLECT_ALLELIC_COUNTS {
    tag   "${meta.id}"
    label 'process_medium'

    input:
        tuple val(meta), path(bam), path(bai)
        path snp_bed
        path fasta
        path fai
        path dict

    output:
        tuple val(meta), path("${meta.id}.allelicCounts.tsv"), emit: allelic

    stub:
        """
        touch ${meta.id}.allelicCounts.tsv
        """

    script:
        def xmx   = task.memory ? Math.max(2, task.memory.toGiga() - 2) : 8
        def extra = task.ext.args ?: ''
        """
        gatk --java-options "-Xmx${xmx}g" CollectAllelicCounts \\
            -I ${bam} \\
            -L ${snp_bed} \\
            -R ${fasta} \\
            ${extra} \\
            -O ${meta.id}.allelicCounts.tsv

        n=\$(grep -vc '^@' ${meta.id}.allelicCounts.tsv)
        echo "[ok] ${meta.id}: \$n allelic-count records (incl. header)"
        """
}
