/*
 * modules/local/dashboard.nf
 *
 * Build the static HTML cohort dashboard against every sample's
 * per-sample clinical/ directory in a run.
 *
 * Design notes:
 *
 * 1. This is a single cohort-level process. ORGANIZE_OUTPUT already
 *    publishes each sample's clinical-bound artifacts as a self-
 *    contained <sample>/clinical/ directory (hardlinked from the
 *    pipeline's other outputs). DASHBOARD just collects those
 *    directories, layouts them where build.py --subdir clinical
 *    expects, and runs the builder.
 *
 * 2. Host execution, not a container. The dashboard_builder relies on
 *    jinja2 + pandas which are not in the pipeline's existing
 *    container set. The production conda env at
 *    ${params.legacy_python_env} already has both (it is where
 *    dashboard_builder runs in production). This matches the existing
 *    executor='local' pattern used by VARIANT_VALIDATOR, ONCOVI, and
 *    FLT3_TO_VARIANTS in conf/modules.config.
 *
 * 3. IGV report handling. The builder patches <sample>_igv_report.html
 *    in place (idempotent hash-router injection). We re-stage each
 *    sample's clinical/ directory with cp -L for the IGV report and
 *    ln -s for everything else, so the patch lands on a module-owned
 *    copy and never touches the file ORGANIZE_OUTPUT hardlinked into
 *    the published outputs.
 *
 * 4. publishDir scope. params.outdir for this pipeline IS the run
 *    directory (e.g. test_run/20260522_171414/), one level above
 *    the per-sample <sample>/ subdirectories. The dashboard writes
 *    cohort_index.html + assets/ at that top level, and the patched
 *    per-sample report HTML + IGV report files back under
 *    <sample>/clinical/.
 */

process DASHBOARD {
    tag        'cohort'
    label      'process_low'

    // Same host-execution pattern as VARIANT_VALIDATOR / ONCOVI /
    // FLT3_TO_VARIANTS. The targeted-seq conda env (which production
    // uses to run dashboard_builder v0.4.4 standalone) already has
    // jinja2 and pandas installed.
    executor   'local'

    publishDir "${params.outdir}",
        mode:    'copy',
        saveAs:  { fn -> fn == 'versions.yml' ? null : fn }

    input:
        // Collected list of all per-sample clinical/ directories.
        // The accompanying sample_ids list (same length, same order) is
        // used to name the staged copies, since the channel-staged
        // directories all arrive as 'clinical' otherwise.
        val sample_ids
        path clinical_dirs, stageAs: 'src/?/clinical'

    output:
        path 'cohort_index.html',                          emit: cohort_html
        path 'assets',                                     emit: assets
        path '*/clinical/*_report.html',                   emit: sample_reports
        path "*/clinical/*_cache.json",   emit: caches,          optional: true
        path 'versions.yml',                               emit: versions

    when:
        task.ext.when == null || task.ext.when

    script:

        def builder_dir   = "${projectDir}/bin/dashboard_builder"
        def py            = params.dashboard_python ?: "${params.legacy_python_env}/bin/python"
        def sample_ids_sh = sample_ids.collect { "'${it}'" }.join(' ')
        """
        set -euo pipefail

        # ----------------------------------------------------------------
        # Re-stage: src/<i>/clinical/ -> dashboard_view/<sample>/clinical/
        # ----------------------------------------------------------------
        # Nextflow stages each input path under src/1, src/2, etc. The
        # sample identity comes from the parallel sample_ids list. We
        # symlink everything except <sample>_igv_report.html, which is
        # copied so the in-place hash-router patch is safe.

        mkdir -p dashboard_view
        sample_ids=( ${sample_ids_sh} )
        i=1
        for sid in "\${sample_ids[@]}"; do
            src="src/\${i}/clinical"
            dst="dashboard_view/\${sid}/clinical"
            mkdir -p "\${dst}"
            for entry in "\${src}"/*; do
                [ -e "\${entry}" ] || continue
                name=\$(basename "\${entry}")
                if [ -f "\${entry}" ] && [ "\${name}" = "\${sid}_igv_report.html" ]; then
                    cp -L "\${entry}" "\${dst}/\${name}"
                else
                    ln -sfn "\$(readlink -f "\${entry}")" "\${dst}/\${name}"
                fi
            done
            i=\$((i + 1))
        done

        # ----------------------------------------------------------------
        # Run the builder. GeneBe annotation is added conditionally; the
        # credentials live in an untracked credentials.config (see
        # docs/dashboard.md for setup).
        # ----------------------------------------------------------------
        ${py} ${builder_dir}/build.py \\
            dashboard_view \\
            --subdir clinical \\
            ${ params.genebe_enabled ? "--annotate-genebe" : "" } \\
            ${ params.genebe_enabled && params.genebe_user ? "--genebe-user '" + params.genebe_user + "'" : "" } \\
            ${ params.genebe_enabled && params.genebe_key  ? "--genebe-key '"  + params.genebe_key  + "'" : "" } \\
            ${ params.oncokb_enabled ? "--annotate-oncokb" : "" } \\
            ${ params.oncokb_enabled && params.oncokb_token ? "--oncokb-token '" + params.oncokb_token + "'" : "" } \\
            ${task.ext.args ?: ''}

        # ----------------------------------------------------------------
        # publishDir picks files up by pattern (cohort_index.html,
        # assets/**, */clinical/*_report.html, */clinical/*_igv_report.html).
        # Promote them to the work-dir root so the pattern matches without
        # needing a saveAs callback to strip 'dashboard_view/'.
        # ----------------------------------------------------------------
        mv dashboard_view/cohort_index.html cohort_index.html
        mv dashboard_view/assets            assets
        for sid in "\${sample_ids[@]}"; do
            if [ -d "dashboard_view/\${sid}" ]; then
                mkdir -p "\${sid}"
                mv "dashboard_view/\${sid}/clinical" "\${sid}/clinical"
            fi
        done

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            python: \$(${py} --version 2>&1 | awk '{print \$2}')
            dashboard_builder: \$(grep '^BUILDER_VERSION' ${builder_dir}/build.py | sed -E 's/.*"([^"]+)".*/\\1/')
        END_VERSIONS
        """

    stub:
        def sample_ids_sh = sample_ids.collect { "'${it}'" }.join(' ')
        """
        mkdir -p assets
        touch cohort_index.html
        for sid in ${sample_ids_sh}; do
            mkdir -p "\${sid}/clinical"
            touch "\${sid}/clinical/\${sid}_report.html"
            touch "\${sid}/clinical/\${sid}_igv_report.html"
        done
        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            stub: true
        END_VERSIONS
        """
}
