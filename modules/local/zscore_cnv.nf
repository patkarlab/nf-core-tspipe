/*
 * modules/local/zscore_cnv.nf
 *
 * nf-core CNV wiring v1 (apply_nfcore_cnv_wiring_part1)
 *
 * Z-score CNV caller. Compares each tumor bin's log2 to the LOO per-bin
 * noise null distribution and calls significant gains/losses.
 *
 * Replaces scripts/12d_zscore_cnv.py (bin/zscore_cnv.py).
 */

process ZSCORE_CNV {
    tag        "${meta.id}"
    label      'process_low'

    conda      'bioconda::cnvkit=0.9.10 conda-forge::pandas=2.1.4 conda-forge::numpy=1.26'
    container  'quay.io/biocontainers/cnvkit:0.9.10--pyhdfd78af_0'

    input:
        tuple val(meta), path(cnr)
        path  noise_profile
        path  loo_summary

    output:
        tuple val(meta), path("${meta.id}.zscore_genes.tsv"), emit: zscore_genes
        tuple val(meta), path("${meta.id}.zscore_bins.tsv"),  emit: zscore_bins, optional: true
    stub:
        // nf-core stub blocks v1 (apply_nfcore_add_stub_blocks)
        """
        touch ${meta.id}.zscore_genes.tsv ${meta.id}.zscore_bins.tsv
        """


    script:
        """
        zscore_cnv.py \\
            -s ${meta.id} \\
            --cnr ${cnr} \\
            --noise-profile ${noise_profile} \\
            --loo-summary ${loo_summary} \\
            -o .
        """
}
