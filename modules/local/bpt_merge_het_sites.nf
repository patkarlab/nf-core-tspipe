/*
 * modules/local/bpt_merge_het_sites.nf  (BAF_CATALOG_V1)
 *
 * Genome-wide BAF site catalog: sites heterozygous in >= pon_het_min_samples
 * include_in_pon normals (chrX: females only), outside PARALOG_LIMITED
 * exons, appended as 1-bp intervals to the base catalog (17p probe windows).
 * Feeds BPT_GATK_COLLECT_ALLELIC_COUNTS and BPT_AGGREGATE_BAF.
 */

process BPT_MERGE_HET_SITES {
    tag   "het_catalog"
    label 'process_low'

    input:
        path hets_files
        path sheet
        path base_bed
        path paralog_exons

    output:
        path 'snp_sites.baf.bed',  emit: bed
        path 'het_catalog.tsv',    emit: catalog

    stub:
        """
        cp ${base_bed} snp_sites.baf.bed
        printf 'chrom\\tpos\\tref\\talt\\tn_het\\tn_het_male\\tn_het_female\\tmedian_af\\tsource\\n' > het_catalog.tsv
        """

    script:
        def paralog_arg = paralog_exons ? "--paralog-exons ${paralog_exons}" : ''
        """
        merge_het_sites.py \\
            --sheet ${sheet} \\
            --base-bed ${base_bed} \\
            ${paralog_arg} \\
            --min-samples ${params.pon_het_min_samples} \\
            --min-depth ${params.pon_het_min_depth} \\
            --af-lo ${params.pon_het_af_lo} \\
            --af-hi ${params.pon_het_af_hi} \\
            --out-bed snp_sites.baf.bed \\
            --out-catalog het_catalog.tsv \\
            *.hets.tsv
        """
}
