/*
 * modules/local/run_bundle.nf  (RUN_BUNDLE_V1)
 *
 * One shareable zip for the whole run, next to the per-sample bundles:
 *     ${params.outdir}/<run>_reports.zip      (<run> = basename of params.outdir)
 *
 * Unpacks to <run>_reports/ with cohort_index.html (links rewritten to
 * <S>/<S>_report.html), assets/ once, and one <S>/ folder per sample holding
 * the report (asset paths rewritten to ../assets/, cohort link kept as
 * ../cohort_index.html), dashboard, fastp and IGV reports, and the cnv/ tree.
 * Same content per sample as REPORT_BUNDLE's zips, which remain the way to
 * send one sample on its own.
 *
 * Cohort-level, host execution (tools/make_run_bundle.py, stdlib Python 3),
 * symlinked staging, --force at every invocation. Consumes DASHBOARD's
 * clinical/ directories, assets/ and cohort_index.html directly, so it runs
 * beside REPORT_BUNDLE rather than after it.
 */

process RUN_BUNDLE {
    tag        'cohort'
    label      'process_low'

    executor   'local'

    publishDir "${params.outdir}",
        mode:    'copy',
        saveAs:  { fn -> fn == 'versions.yml' ? null : fn }

    input:
        path clinical_dirs, stageAs: 'src/?/clinical'
        path assets_dir,    stageAs: 'assets'
        path cohort_html,   stageAs: 'cohort_index.html'

    output:
        path '*_reports.zip', emit: zip
        path 'versions.yml',  emit: versions

    when:
        task.ext.when == null || task.ext.when

    script:
        def bundler_py = "${projectDir}/tools/make_run_bundle.py"
        def run_name   = file(params.outdir).name
        """
        set -euo pipefail

        # Re-stage src/<i>/clinical + assets + cohort_index.html -> bundle_view/ (symlinks; sample id from
        # the per-sample <sid>_report.html, skipping the IGV report - same rule as REPORT_BUNDLE)
        mkdir -p bundle_view
        ln -sfn "\$(readlink -f assets)" bundle_view/assets
        cp -L cohort_index.html bundle_view/cohort_index.html

        for src in src/*/clinical; do
            report=""
            for f in "\${src}"/*_report.html; do
                if [[ ! -f "\$f" ]]; then
                    continue
                fi
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

        python3 ${bundler_py} --outdir bundle_view --name ${run_name} --out ${run_name}_reports.zip --force

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            python: \$(python3 --version 2>&1 | awk '{print \$2}')
            make_run_bundle: '1.0'   // RUN_BUNDLE_V1
        END_VERSIONS
        """

    stub:
        """
        touch STUB_reports.zip
        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            stub: true
        END_VERSIONS
        """
}
