/*
 * modules/local/bpt_aggregate_baf.nf
 *
 * Aggregates per-sample allelic counts into the per-site reference-bias
 * background table. OPEN DECISION 2 (handoff) is parameterised here:
 * params.pon_baf_cohort = 'male' (conforming males only) or 'all'
 * (all 48 with per-site depth filter). Changing it re-runs only this
 * process under -resume.
 */

process BPT_AGGREGATE_BAF {
    tag   "baf_${params.pon_baf_cohort}"
    label 'process_low'

    input:
        path allelic_files
        path sheet
        path snp_bed

    output:
        path 'baf_background.tsv', emit: background

    stub:
        """
        touch baf_background.tsv
        """

    script:
        """
        aggregate_baf_background.py \\
            --sheet ${sheet} \\
            --snp-bed ${snp_bed} \\
            --cohort ${params.pon_baf_cohort} \\
            --min-depth ${params.pon_baf_min_depth} \\
            --min-het-samples ${params.pon_baf_min_het} \\
            --out baf_background.tsv \\
            *.allelicCounts.tsv
        """
}
