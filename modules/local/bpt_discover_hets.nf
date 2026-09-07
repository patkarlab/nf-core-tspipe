/*
 * modules/local/bpt_discover_hets.nf  (BAF_CATALOG_V1)
 *
 * Heterozygous SNP candidates per normal over the panel targets
 * (bcftools mpileup/call, per chromosome in parallel via
 * bin/discover_hets.sh). Runs on every samplesheet row; membership and
 * the >= N-samples rule are applied in BPT_MERGE_HET_SITES.
 */

process BPT_DISCOVER_HETS {
    tag   "${meta.id}"
    label 'process_medium'

    input:
        tuple val(meta), path(bam), path(bai)
        path bed
        path fasta
        path fai

    output:
        tuple val(meta), path("${meta.id}.hets.tsv"), emit: hets

    stub:
        """
        printf 'chr17\\t7676000\\tA\\tG\\t400\\t200,200\\n' > ${meta.id}.hets.tsv
        """

    script:
        """
        discover_hets.sh ${bam} ${bed} ${fasta} ${task.cpus} ${meta.id}.hets.tsv ${params.pon_het_mapq}
        """
}
