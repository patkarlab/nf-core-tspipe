/*
 * modules/local/exon_plots.nf  (EXON_PLOTS_V1)
 *
 * Per-sample exon-level copy-ratio figures from the CMX consensus JSON
 * (CNVkit bins with depth and weight): one PNG per chromosome that carries
 * a non-neutral consensus gene, a DECoN call at BF >= params.exon_plot_min_bf
 * (sub-threshold calls on purpose), or a focal-CNV gene; all panel genes of
 * that chromosome on the axis; DECoN calls drawn as brackets. Index TSV
 * for the dashboard. GATK container for Python 3.6 + matplotlib 3.2.
 */

process EXON_PLOTS {
    tag        "${meta.id}"
    label      'process_low'
    container  'docker://broadinstitute/gatk:4.5.0.0'

    input:
        tuple val(meta), path(consensus_json), path(consensus_genes), path(decon_filtered)
        path focal_bed
        path gene_blacklist   // MARKER CNV_BLACKLIST_V1

    output:
        tuple val(meta), path("exon_plots/${meta.id}.exon_plots.tsv"), emit: index
        tuple val(meta), path("exon_plots/*.png"),                     emit: pngs, optional: true
        tuple val(meta), path("exon_plots"),                           emit: dir

    stub:
        """
        mkdir -p exon_plots
        printf 'sample\\tchrom\\tn_genes\\treasons\\tfile\\n' > exon_plots/${meta.id}.exon_plots.tsv
        """

    script:
        def decon_arg = decon_filtered ? "--decon ${decon_filtered}" : ''
        def focal_arg = focal_bed      ? "--focal-bed ${focal_bed}"  : ''
        def blacklist_arg = gene_blacklist ? "--gene-blacklist ${gene_blacklist}" : ''   // CNV_BLACKLIST_V1
        """
        export MPLCONFIGDIR=\$PWD/.mpl
        export XDG_CACHE_HOME=\$PWD/.cache
        mkdir -p \$MPLCONFIGDIR \$XDG_CACHE_HOME

        plot_exon_ratio_batch.py \\
            --sample ${meta.id} \\
            --json ${consensus_json} \\
            --genes-tsv ${consensus_genes} \\
            ${decon_arg} ${focal_arg} ${blacklist_arg} \\
            --min-bf ${params.exon_plot_min_bf} \\
            --outdir exon_plots
        """
}
