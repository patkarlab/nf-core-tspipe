/*
 * modules/local/cnv_loo_qc.nf
 *
 * Leave-One-Out CNV noise assessment. Replaces scripts/12c_cnv_loo_qc.py
 * (now copied to bin/cnv_loo_qc.py).
 *
 * For each normal in the PON:
 *   1. Build a temporary reference from the other N-1 normals
 *   2. Run cnvkit.py fix + segment on the held-out normal
 *   3. Collect per-bin log2 ratios and false-positive CNV calls
 *
 * Outputs feed back into the main pipeline as:
 *   - params.cnv_loo_summary
 *   - params.cnv_noise_profile
 *   - params.cnv_noisy_bins
 */

process CNV_LOO_QC {
    tag        "loo_qc"
    label      'process_high'
    label      'process_long'

    conda      'bioconda::cnvkit=0.9.10 conda-forge::matplotlib=3.8.2 conda-forge::pandas=2.1.4 conda-forge::numpy=1.26'
    container  'quay.io/biocontainers/cnvkit:0.9.10--pyhdfd78af_0'

    input:
        path  cov_dir          // contains the *.targetcoverage.cnn / *.antitargetcoverage.cnn from cnvkit_pon_build
        path  bed

    output:
        path  "loo_qc/loo_summary.tsv",          emit: summary
        path  "loo_qc/loo_bin_noise_profile.tsv",emit: noise_profile
        path  "loo_qc/cnvkit_noisy_bins.bed",    emit: noisy_bins
        path  "loo_qc/loo_iterations",           emit: iterations  // per-sample LOO .cnr files
        path  "loo_qc/loo_heatmap.png",          emit: heatmap, optional: true
        path  "loo_qc",                          emit: dir

    script:
        """
        mkdir -p loo_qc
        cnv_loo_qc.py \\
            --cov-dir ${cov_dir} \\
            --bed ${bed} \\
            --outdir loo_qc \\
            -j ${task.cpus}
        """
}
