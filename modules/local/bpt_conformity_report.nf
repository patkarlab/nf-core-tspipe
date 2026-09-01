/*
 * modules/local/bpt_conformity_report.nf
 *
 * Merges per-sample conformity rows against the validated samplesheet and
 * applies the report-only thresholds. Expected v1 behaviour on the 48
 * staged normals: 24 males PASS except Male12 (WARN on insert size,
 * 131.8 bp vs 150 floor); all 24 females WARN on NPM1/JAK2 depth
 * (12-plex collapse signature).
 */

process BPT_CONFORMITY_REPORT {
    tag   "conformity_report"
    label 'process_single'

    input:
        path rows
        path sheet

    output:
        path 'conformity_report.tsv', emit: report

    stub:
        """
        touch conformity_report.tsv
        """

    script:
        """
        capture_conformity_gate.py --mode merge \\
            --sheet ${sheet} \\
            --npm1-min ${params.pon_npm1_min} \\
            --jak2-min ${params.pon_jak2_min} \\
            --insert-min ${params.pon_insert_min} \\
            --out conformity_report.tsv \\
            *.conformity.tsv
        """
}
