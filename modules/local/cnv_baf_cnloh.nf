/*
 * modules/local/cnv_baf_cnloh.nf  (BAF_V1)
 *
 * 17p BAF-shift / cnLOH detector. Corrects per-site sample allele
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
        tuple val(meta), path("${meta.id}.baf17p.summary.tsv"), emit: summary
        tuple val(meta), path("${meta.id}.baf17p.sites.tsv"),   emit: sites
        tuple val(meta), path("${meta.id}.baf17p.png"),         emit: plot, optional: true

    stub:
        """
        touch ${meta.id}.baf17p.summary.tsv ${meta.id}.baf17p.sites.tsv ${meta.id}.baf17p.png
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
            --out-prefix ${meta.id}.baf17p
        """
}
