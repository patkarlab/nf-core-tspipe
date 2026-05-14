/*
 * modules/local/cnv_plots.nf
 *
 * nf-core CNV wiring v1 (apply_nfcore_cnv_wiring_part1)
 *
 * Clinical-grade CNV plots. Produces a `plots/` subtree with combined,
 * overview, per_chromosome, and per_gene subdirectories. The chr-gene
 * scatter PDF (added in 2026-05-14, commit a84ba72) is surfaced as a
 * top-level deliverable for clinical review; the rest of the tree is for
 * case-by-case browsing under cnv/plots/details/.
 *
 * Note: top-level scatter PDFs/PNGs (final-diagram.pdf, final-scatter.png,
 * per-chromosome panel-gene PNGs) are produced by CNVKIT, not by CNV_PLOTS.
 *
 * Replaces scripts/12b_cnv_plots.py (bin/cnv_plots.py).
 */

process CNV_PLOTS {
    tag        "${meta.id}"
    label      'process_medium'

    conda      'bioconda::cnvkit=0.9.10 conda-forge::matplotlib=3.8.2 conda-forge::pandas=2.1.4 conda-forge::numpy=1.26'
    container  'quay.io/biocontainers/cnvkit:0.9.10--pyhdfd78af_0'

    input:
        // From subworkflow:
        //   CNVKIT.out.cnr
        //     .join(CNVKIT.out.cns,         by: 0)
        //     .join(CNVKIT.out.call_cns,    by: 0)
        //     .join(CNVKIT.out.genemetrics, by: 0)
        tuple val(meta),
              path(cnr),
              path(cns),
              path(call_cns),
              path(genemetrics)
        path  bed
        path  cytoband
        path  loo_summary
        path  scatter_regions

    output:
        tuple val(meta), path("plots"),                  emit: plots_dir
        tuple val(meta), path("${meta.id}*.pdf"),        emit: pdfs, optional: true
    stub:
        // nf-core stub blocks v1 (apply_nfcore_add_stub_blocks)
        """
        mkdir -p plots
        touch ${meta.id}stub.pdf
        """


    script:
        """
        cnv_plots.py \\
            -s ${meta.id} \\
            -o . \\
            --bed ${bed} \\
            --cytoband ${cytoband} \\
            --loo-summary ${loo_summary} \\
            --genemetrics ${genemetrics} \\
            --scatter-regions ${scatter_regions}
        """
}
