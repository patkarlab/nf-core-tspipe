/*
 * modules/local/bpt_cnv_loo_qc.nf
 *
 * Per-stratum leave-one-out CNV noise assessment. Wraps bin/cnv_loo_qc.py
 * (shared with the legacy BUILD_PON path) but:
 *   - passes --panel explicitly (script default is 'myeloid'),
 *   - passes -y for the male stratum only (haploid-X reference;
 *     BPT_HAPLOID_X_V1),
 *   - stages the stratum's coverage .cnn files flat and passes
 *     --cov-dir .
 *
 * VERIFY BEFORE FIRST RUN (flagged in handoff): that cnv_loo_qc.py globs
 * *.targetcoverage.cnn / *.antitargetcoverage.cnn directly under
 * --cov-dir rather than requiring the legacy build_dir layout.
 *
 * Known quirk carried from CNV_LOO_QC: publishing directory outputs can
 * create an empty references/<panel>/ in outdir while work-dir files are
 * correct. Mitigation here: reference-grade files are emitted and
 * published individually (saveAs flattens them into the stratum dir);
 * verify presence post-run regardless.
 */

process BPT_CNV_LOO_QC {
    tag   "loo_${stratum}"
    label 'process_high'
    label 'process_long'

    input:
        val  stratum
        path cov_files
        path bed

    output:
        tuple val(stratum), path("references/${params.pon_panel}/cnvkit_loo_summary.tsv"), emit: summary
        tuple val(stratum), path("references/${params.pon_panel}/cnvkit_noisy_bins.bed"),  emit: noisy_bins
        path "loo_qc/loo_bin_noise_profile.tsv",                                           emit: noise_profile
        path "loo_qc/loo_iterations",                                                      emit: iterations
        path "loo_qc/plots/loo_summary_heatmap.png",                                       emit: heatmap, optional: true

    stub:
        """
        mkdir -p references/${params.pon_panel} loo_qc/loo_iterations loo_qc/plots
        touch references/${params.pon_panel}/cnvkit_loo_summary.tsv \\
              references/${params.pon_panel}/cnvkit_noisy_bins.bed \\
              loo_qc/loo_bin_noise_profile.tsv \\
              loo_qc/plots/loo_summary_heatmap.png
        """

    script:
        def yflag = (stratum == 'male') ? '-y' : ''
        """
        n_t=\$(ls *.targetcoverage.cnn 2>/dev/null | wc -l)
        echo "[ok] LOO stratum=${stratum}: \$n_t coverage files staged"
        if [ "\$n_t" -lt 3 ]; then
            echo "[error] LOO stratum=${stratum}: need >= 3 coverage files for leave-one-out, found \$n_t" >&2
            exit 1
        fi

        mkdir -p loo_qc references/${params.pon_panel}
        cnv_loo_qc.py \\
            --cov-dir . \\
            --bed ${bed} \\
            --outdir loo_qc \\
            --panel ${params.pon_panel} \\
            ${yflag} \\
            -j ${task.cpus}
        """
}
