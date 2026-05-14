/*
 * modules/local/build_sex_pon.nf
 *
 * Classify normals by chrX log2 (from LOO .cnr files), then build
 * sex-specific CNVKit PoN references.
 *
 * Replaces scripts/12c_build_sex_pon.py (now bin/build_sex_pon.py).
 *
 * Outputs:
 *   - cnvkit_pon_male.cnn
 *   - cnvkit_pon_female.cnn
 *   - cnvkit_pon_sex_assignment.tsv  (which sample classified as which sex)
 */

process BUILD_SEX_PON {
    tag        "sex_pon"
    label      'process_medium'

    conda      'bioconda::cnvkit=0.9.10 conda-forge::pandas=2.1.4'
    container  'quay.io/biocontainers/cnvkit:0.9.10--pyhdfd78af_0'

    input:
        path  cov_dir          // *.targetcoverage.cnn + *.antitargetcoverage.cnn
        path  loo_iterations   // loo_qc/loo_iterations from CNV_LOO_QC

    output:
        path  "cnvkit_pon_male.cnn",            emit: pon_male
        path  "cnvkit_pon_female.cnn",          emit: pon_female
        path  "cnvkit_pon_sex_assignment.tsv",  emit: sex_assignment
    stub:
        // nf-core stub blocks v1 (apply_nfcore_add_stub_blocks)
        """
        touch cnvkit_pon_male.cnn cnvkit_pon_female.cnn cnvkit_pon_sex_assignment.tsv
        """


    script:
        def excludes = task.ext.exclude_samples ?: 'OCIAML3'
        def thresh   = task.ext.chrx_threshold  ?: -0.4
        """
        build_sex_pon.py \\
            --cov-dir ${cov_dir} \\
            --loo-dir ${loo_iterations} \\
            --out-dir . \\
            --chrx-threshold ${thresh} \\
            --exclude ${excludes}
        """
}
