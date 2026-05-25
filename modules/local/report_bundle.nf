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
 *    clinical/ directories DASHBOARD produces, plus the shared
 *    assets/ directory DASHBOARD emits.
 *
 * 2. Sample IDs are inferred from the *_report.html filename inside
 *    each staged clinical/ directory (v2: bash-glob skips IGV reports
 *    without using regex). This is robust against DASHBOARD's
 *    *\/clinical glob being emitted in an order that does not match
 *    the workflow's original sample channel ordering. Previous
 *    versions of this module took a parallel val sample_ids list and
 *    zipped it positionally with the staged dirs, which could
 *    mis-pair when glob expansion reordered things.
 *
 * 3. Host execution. The bundler is stdlib-only Python 3, no extra
 *    dependencies.
 *
 * 4. publishDir scope: params.outdir is the run directory. The
 *    bundler writes zips as <sample>/<sample>_report.zip; publishDir
 *    copies them to the run directory alongside the existing
 *    clinical/ folder.
 *
 * 5. Symlink staging. cnvkit_plots can be ~35 MB per sample. We
 *    symlink rather than copy so the only real I/O is the zip write.
 *
 * 6. --force at every invocation. A Nextflow re-run that bypasses
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
        // DASHBOARD's patched per-sample clinical/ directories and the
        // shared assets/ directory. Sample IDs are derived from file
        // naming inside each clinical dir (see design note 2).
        path clinical_dirs, stageAs: 'src/?/clinical'
        path assets_dir,    stageAs: 'assets'

    output:
        path '*/*_report.zip', emit: zips
        path 'versions.yml',   emit: versions

    when:
        task.ext.when == null || task.ext.when

    script:
        def bundler_py = "${projectDir}/tools/make_report_bundle.py"
        """
        set -euo pipefail

        # ----------------------------------------------------------------
        # Re-stage: src/<i>/clinical/  +  ./assets/   ->   bundle_view/
        # ----------------------------------------------------------------
        # For each staged clinical dir, find its sample ID by scanning
        # for the per-sample <sid>_report.html file (NOT the IGV one).
        # Pure bash globbing, no regex inside the GString.
        #
        # Symlink rather than copy: cnvkit_plots is ~35 MB per sample
        # and we do not need a duplicate copy before the zip step.

        mkdir -p bundle_view
        ln -sfn "\$(readlink -f assets)" bundle_view/assets

        for src in src/*/clinical; do
            report=""
            for f in "\${src}"/*_report.html; do
                # If the glob did not match, f is the literal pattern.
                if [[ ! -f "\$f" ]]; then
                    continue
                fi
                # Skip the IGV per-sample report.
                if [[ "\$f" == *_igv_report.html ]]; then
                    continue
                fi
                report="\$f"
                break
            done

            if [[ -z "\$report" ]]; then
                echo "ERROR: no per-sample *_report.html in \${src}" >&2
                exit 1
            fi

            sid=\$(basename "\$report" _report.html)
            mkdir -p "bundle_view/\${sid}"
            ln -sfn "\$(readlink -f "\$src")" "bundle_view/\${sid}/clinical"
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
        for bundle_zip in bundle_view/*/*_report.zip; do
            if [[ ! -e "\$bundle_zip" ]]; then
                continue
            fi
            sid=\$(basename "\$bundle_zip" _report.zip)
            mkdir -p "\${sid}"
            mv "\$bundle_zip" "\${sid}/\${sid}_report.zip"
        done

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            python: \$(python3 --version 2>&1 | awk '{print \$2}')
            make_report_bundle: '0.2'
        END_VERSIONS
        """

    stub:
        """
        # Stub: emit one placeholder zip per staged clinical dir.
        i=0
        for src in src/*/clinical; do
            i=\$((i + 1))
            sid="STUB_SAMPLE_\${i}"
            mkdir -p "\${sid}"
            touch "\${sid}/\${sid}_report.zip"
        done
        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            stub: true
        END_VERSIONS
        """
}
