/*
 * modules/local/sample_dashboard.nf
 *
 * Per-sample QC dashboard renderer. Reads HSMETRICS output + the
 * per-exon coverage TSV from PARSE_EXON_COVERAGE and writes a single
 * self-contained HTML file (matplotlib chart embedded as base64 PNG,
 * CSS inline, no external assets, no JS framework).
 *
 * Container: GATK 4.5 image, which already ships python3 + matplotlib
 * 3.2.1 (used by several GATK plotting commands). It's already cached
 * on gandalf for PARSE_EXON_COVERAGE so no new pull is needed.
 *
 * Output: ${meta.id}_dashboard.html in
 *   ${params.outdir}/${meta.id}/dashboard/
 * Opens identically when emailed, archived, or printed.
 */

process SAMPLE_DASHBOARD {
    tag        "${meta.id}"
    label      'process_low'
    container  'docker://broadinstitute/gatk:4.5.0.0'
    publishDir "${params.outdir}/${meta.id}/dashboard", mode: 'copy'

    input:
        tuple val(meta), path(hsmetrics), path(exon_coverage)
        val panel_name
        val commit_sha
        val run_date

    output:
        tuple val(meta), path("${meta.id}_dashboard.html"), emit: html
        path "versions.yml",                                emit: versions

    stub:
        """
        touch ${meta.id}_dashboard.html versions.yml
        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            stub: true
        END_VERSIONS
        """

    script:
        """
        set -eo pipefail

        # render_dashboard.py is auto-staged onto PATH by Nextflow from
        # bin/. Inputs are the Picard HsMetrics text file and the per-
        # exon coverage TSV; provenance values are passed through so
        # the dashboard footer is auditable.
        render_dashboard.py \\
            --sample        ${meta.id} \\
            --exon-coverage ${exon_coverage} \\
            --hsmetrics     ${hsmetrics} \\
            --output        ${meta.id}_dashboard.html \\
            --panel-name    "${panel_name}" \\
            --commit-sha    "${commit_sha}" \\
            --run-date      "${run_date}"

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            python: \$(python3 --version 2>&1 | awk '{print \$2}')
            matplotlib: \$(python3 -c "import matplotlib; print(matplotlib.__version__)")
        END_VERSIONS
        """
}
