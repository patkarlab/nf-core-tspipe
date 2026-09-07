/*
 * modules/local/chrom_pages.nf  (CHROM_PAGES_V1)
 *
 * Per-sample, per-chromosome CNV pages in target space (bin/plot_targets_trio.py):
 * depth per exon/backbone/SNP window (TITAN colours), BAF from the v2-catalog
 * allelic counts, PURPLE copy number per target, gene bands, and one exon
 * panel per gene with DECoN brackets. One PNG per chromosome with targets,
 * plus an index TSV for the dashboard. GATK container (Python 3.6 +
 * matplotlib 3.2). DECoN table and PURPLE directory are optional inputs
 * (empty lists when those arms are off).
 */

process CHROM_PAGES {
    tag        "${meta.id}"
    label      'process_low'
    container  'docker://broadinstitute/gatk:4.5.0.0'

    input:
        tuple val(meta), path(consensus_json), path(allelic), path(decon_filtered), path(purple_dir)
        path panel_bed
        path snp_base_bed
        path baf_background

    output:
        tuple val(meta), path("chrom_pages/${meta.id}.chrom_pages.tsv"), emit: index
        tuple val(meta), path("chrom_pages/*.png"),                      emit: pngs, optional: true
        tuple val(meta), path("chrom_pages"),                            emit: dir

    stub:
        """
        mkdir -p chrom_pages
        printf 'sample\\tlabel\\tchroms\\tn_targets\\tn_depth_bins\\tn_baf_sites\\tn_purple_targets\\tfile\\n' > chrom_pages/${meta.id}.chrom_pages.tsv
        """

    script:
        def decon_arg  = decon_filtered ? "--decon ${decon_filtered}" : ''
        def purple_arg = purple_dir     ? "--purple-dir ${purple_dir}" : ''
        def snp_arg    = snp_base_bed   ? "--targets ${snp_base_bed}" : ''
        def bg_arg     = baf_background ? "--background ${baf_background}" : ''
        """
        export MPLCONFIGDIR=\$PWD/.mpl
        export XDG_CACHE_HOME=\$PWD/.cache
        mkdir -p \$MPLCONFIGDIR \$XDG_CACHE_HOME chrom_pages

        plot_targets_trio.py \\
            --sample ${meta.id} \\
            --consensus-json ${consensus_json} \\
            --allelic ${allelic} \\
            ${decon_arg} ${purple_arg} \\
            --targets ${panel_bed} ${snp_arg} ${bg_arg} \\
            --every-chrom \\
            --decon-min-bf ${params.exon_plot_min_bf} \\
            --out chrom_pages/${meta.id} \\
            --index chrom_pages/${meta.id}.chrom_pages.tsv
        """
}
