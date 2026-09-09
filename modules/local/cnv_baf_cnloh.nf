/*
 * modules/local/cnv_baf_cnloh.nf  (BAF_V1 17p; BAF_V2 genome-wide per arm, 2026-09-09)
 *
 * Per-arm BAF-shift / cnLOH / allelic-imbalance detector. V1 text follows for the method. Corrects per-site sample allele
 * fractions against the male-cohort background (baf_background.tsv,
 * informative sites), computes the mirrored-BAF deviation across
 * sample-het sites, estimates the clonal fraction from the shift, and
 * classifies NEUTRAL / CNLOH_17P / DEL_17P / INDETERMINATE using the
 * 17p denoised copy-ratio median. Thresholds are params (v1 heuristics;
 * pending validation on known del(17p) / cnLOH material).
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
            --out-prefix ${meta.id}.baf
        """
}
