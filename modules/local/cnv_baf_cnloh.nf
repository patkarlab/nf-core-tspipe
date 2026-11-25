/*
 * modules/local/cnv_baf_cnloh.nf  (BAF_V1 17p; BAF_V2 genome-wide per arm, 2026-09-09;
 * MARKER BAF_HETLOSS_V1 heterozygosity-loss test, 2026-11-25)
 *
 * Per-arm BAF-shift / cnLOH / allelic-imbalance detector (bin/baf_cnloh_detect.py; the method
 * is in its header). Corrects per-site sample allele fractions against the cohort background
 * (baf_background.tsv, informative sites), computes the mirrored-BAF deviation across the
 * sample's heterozygous sites, estimates the clonal fraction from the shift, and classifies
 * each arm NEUTRAL / CNLOH / DEL / GAIN / IMBALANCE / INDETERMINATE using the arm's denoised
 * copy-ratio median.
 *
 * BAF_HETLOSS_V1: an event in more than about 80 % of the cells (89 % for a deletion) moves the
 * arm's heterozygous sites below 0.10 / above 0.90, where the statistic above no longer sees
 * them and the arm came out INDETERMINATE. Such an arm is now judged on its heterozygous loci
 * observed against expected and on the residual sites (verdicts as above, plus ROH when
 * heterozygosity is absent at neutral copy ratio). On by default; params.baf_het_loss = false
 * restores the BAF_V2 verdicts exactly.
 *
 * BAF_HETLOSS_V1B (decision of 25 Nov 2026): a call over part of an arm and an arm without
 * heterozygosity (ROH) both vote in the consensus. params.baf_segment_votes = false and
 * params.baf_roh_votes = false make either advisory again (LOW confidence, shown, no vote).
 */

process CNV_BAF_CNLOH {
    tag   "${meta.id}"
    label 'process_low'

    input:
        tuple val(meta), path(allelic), path(denoised)
        path snp_bed
        path background

    output:
        tuple val(meta), path("${meta.id}.baf.summary.tsv"), emit: summary   // BAF_V2: one row per arm
        tuple val(meta), path("${meta.id}.baf.sites.tsv"),   emit: sites
        tuple val(meta), path("${meta.id}.baf.png"),         emit: plot, optional: true

    stub:
        """
        touch ${meta.id}.baf.summary.tsv ${meta.id}.baf.sites.tsv ${meta.id}.baf.png
        """

    script:
        // BAF_HETLOSS_V1: on unless a config sets baf_het_loss = false (an overlay that does not define it leaves it on)
        def het_loss_arg = (params.baf_het_loss == false) ? '--no-het-loss' : ''
        // BAF_HETLOSS_V1B: both findings vote unless a config sets the parameter to false
        def segment_arg  = (params.baf_segment_votes == false) ? '--loh-segment-advisory' : ''
        def roh_arg      = (params.baf_roh_votes == false) ? '--roh-advisory' : ''
        """
        baf_cnloh_detect.py \\
            --allelic ${allelic} \\
            --denoised ${denoised} \\
            --background ${background} \\
            --snp-bed ${snp_bed} \\
            --sample ${meta.id} \\
            --min-depth ${params.baf_min_depth} \\
            --min-het-sites ${params.baf_min_het_sites} \\
            --f-min ${params.baf_f_min} \\
            --cr-del ${params.baf_cr_del} \\
            --cr-gain ${params.baf_cr_gain} \\
            ${het_loss_arg} ${segment_arg} ${roh_arg} \\
            --out-prefix ${meta.id}.baf
        """
}
