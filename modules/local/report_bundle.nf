/*
 * modules/local/report_bundle.nf
 *
 * Build self-contained, shareable zip bundles of per-sample reports.
 *
 * One zip per sample, published as:
 *     ${params.outdir}/<sample>/<sample>_report.zip
 *
 * Each zip is independently openable: a fellow downloads it, unzips
 * it, and double-clicks <sample>_report.html. All asset paths (CSS,
 * JS, PDFs, sub-iframes) resolve correctly because the bundler script
 * copies the shared assets/ directory into each bundle and rewrites
 * the report's relative paths from ../../assets/ to ./assets/.
 *
 * Design notes:
 *
 * 1. Cohort-level process, like DASHBOARD. Consumes the patched
 *    clinical/ directories DASHBOARD produces (those have the IGV
 *    hash-router patch applied to <sample>_igv_report.html), plus
 *    the shared assets/ directory DASHBOARD emits. Stages them into
 *    a bundle_view/ tree that the bundler script expects, then runs
 *    the bundler over all samples in a single invocation.
 *
 * 2. Host execution. The bundler is stdlib-only Python 3, no extra
 *    dependencies. Same executor='local' pattern as DASHBOARD, but
 *    uses plain python3 on PATH (no need for the legacy env).
 *
 * 3. publishDir scope. params.outdir is the run directory. The
 *    bundler writes zips as <sample>/<sample>_report.zip; publishDir
 *    copies them to ${params.outdir}/<sample>/<sample>_report.zip
 *    alongside the existing clinical/ folder.
 *
 * 4. Symlink staging. cnvkit_plots can be ~35 MB per sample. We
 *    symlink the staged inputs into bundle_view/ rather than copying,
 *    so the only real I/O is the zip write itself. shutil.copytree
 *    in the bundler follows symlinks for source paths.
 *
 * 5. --force at every invocation. A Nextflow re-run that bypasses
 *    cache legitimately wants to replace existing zips, so we always
 *    pass --force. The bundler is idempotent.
 */

process REPORT_BUNDLE {
    tag        'cohort'
    label      'process_low'

    executor   'local'

    publishDir "${params.outdir}",
        mode:    'copy',
        saveAs:  { fn -> fn == 'versions.yml' ? null : fn }

    input:
        // Same shape as DASHBOARD: parallel lists of sample IDs and
        // their (patched) clinical directories, plus the shared
        // assets/ directory.
        val  sample_ids
        path clinical_dirs, stageAs: 'src/?/clinical'
        path assets_dir,    stageAs: 'assets'

    output:
        path '*/*_report.zip', emit: zips
        path 'versions.yml',   emit: versions

    when:
        task.ext.when == null || task.ext.when

    script:
        def bundler_py    = "${projectDir}/tools/make_report_bundle.py"
        def sample_ids_sh = sample_ids.collect { "'${it}'" }.join(' ')
        """
        set -euo pipefail

        # ----------------------------------------------------------------
        # Re-stage: src/<i>/clinical/  +  ./assets/   ->   bundle_view/
        # ----------------------------------------------------------------
        # The bundler expects the layout:
        #     <outdir>/<sample>/clinical/...
        #     <outdir>/assets/...
        # Build that under bundle_view/ via symlinks. Avoids copying
        # the ~35 MB of cnvkit_plots per sample before the zip step.

        mkdir -p bundle_view
        ln -sfn "\$(readlink -f assets)" bundle_view/assets

        sample_ids=( ${sample_ids_sh} )
        i=1
        for sid in "\${sample_ids[@]}"; do
            mkdir -p "bundle_view/\${sid}"
            ln -sfn "\$(readlink -f src/\${i}/clinical)" "bundle_view/\${sid}/clinical"
            i=\$((i + 1))
        done

        # ----------------------------------------------------------------
        # Run the bundler over all samples.
        # ----------------------------------------------------------------
        python3 ${bundler_py} --outdir bundle_view --force

        # ----------------------------------------------------------------
        # Promote zips to the work-dir root so publishDir's pattern
        # '*/*_report.zip' picks them up at
        #     <outdir>/<sample>/<sample>_report.zip
        # rather than under a bundle_view/ prefix.
        # ----------------------------------------------------------------
        for sid in "\${sample_ids[@]}"; do
            mkdir -p "\${sid}"
            mv "bundle_view/\${sid}/\${sid}_report.zip" "\${sid}/\${sid}_report.zip"
        done

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            python: \$(python3 --version 2>&1 | awk '{print \$2}')
            make_report_bundle: '0.1'
        END_VERSIONS
        """

    stub:
        def sample_ids_sh = sample_ids.collect { "'${it}'" }.join(' ')
        """
        for sid in ${sample_ids_sh}; do
            mkdir -p "\${sid}"
            touch "\${sid}/\${sid}_report.zip"
        done
        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            stub: true
        END_VERSIONS
        """
}
