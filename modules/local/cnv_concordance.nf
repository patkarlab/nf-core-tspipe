/*
 * modules/local/cnv_concordance.nf
 *
 * nf-core CNV wiring v1 (apply_nfcore_cnv_wiring_part1)
 *
 * Two-caller concordance: CNVKit + Z-score. The exon-level caller
 * (scripts/12g_exon_cnv.py) is intentionally not part of the per-sample
 * DAG; partial gene events are surfaced via the combined per-chromosome
 * scatter plots in CNV_PLOTS for human review.
 *
 * Replaces scripts/12e_cnv_concordance.py (bin/cnv_concordance.py).
 */

process CNV_CONCORDANCE {
    tag        "${meta.id}"
    label      'process_low'

    conda      'bioconda::cnvkit=0.9.10 conda-forge::pandas=2.1.4 conda-forge::numpy=1.26'
    container  'quay.io/biocontainers/cnvkit:0.9.10--pyhdfd78af_0'

    input:
        // From subworkflow:
        //   CNVKIT.out.genemetrics .join(ZSCORE_CNV.out.zscore_genes, by: 0)
        tuple val(meta), path(cnvkit_genemetrics), path(zscore_genes)

    output:
        tuple val(meta), path("${meta.id}_cnv_concordance.tsv"), emit: tsv
    stub:
        // nf-core stub blocks v1 (apply_nfcore_add_stub_blocks)
        """
        touch ${meta.id}_cnv_concordance.tsv
        """


    script:
        """
        cnv_concordance.py \\
            -s ${meta.id} \\
            --cnvkit-genemetrics ${cnvkit_genemetrics} \\
            --zscore-genes ${zscore_genes} \\
            -o .

        # bin/cnv_concordance.py writes ${meta.id}.cnv_concordance.tsv
        # (dot-separated). Normalise to the module's declared underscore form.
        if [ -f "${meta.id}.cnv_concordance.tsv" ] && \\
           [ ! -f "${meta.id}_cnv_concordance.tsv" ]; then
            mv "${meta.id}.cnv_concordance.tsv" "${meta.id}_cnv_concordance.tsv"
        fi
        """
}
