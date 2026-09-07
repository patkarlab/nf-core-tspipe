/*
 * modules/local/cnv_consensus_multi.nf  (CMX_V2 arms K/G/B/P/E; PureCN PCN_V1; DECoN DECON_V1; MARKER CMX_V2_1: --sex)
 *
 * Four-caller CNV consensus for the twist_myeloid panel: CNVkit
 * (segments -> gene calls derived from call.cns), Z-score (gene table
 * passthrough with call-column autodetect), GATK ModelSegments (gene
 * projection + called segments), and the 17p BAF/cnLOH verdict. Also
 * annotates per-gene LOO false-positive rates and emits the single JSON
 * payload that the Phase-4 three-view report consumes (schema documented
 * in bin/cnv_consensus_multi.py).
 *
 * Lives inside the gated twist block; legacy panels keep the existing
 * two-caller CNV_CONCORDANCE untouched.
 */

process CNV_CONSENSUS_MULTI {
    tag   "${meta.id}"
    label 'process_low'

    input:
        tuple val(meta), path(cnr), path(call_cns),   // MARKER CNV_RETIRE_7B: concordance input removed
              path(gatk_genes), path(gatk_called), path(denoised),
              path(baf_summary), path(baf_sites),
              path(purecn_genes), path(purecn_summary),
              path(decon_genes),   // MARKER DECON_V1 (empty list when DECoN is off)
              path(purple_genes), path(purple_summary)   // MARKER HMF_PURPLE_V1 (empty lists when hmftools is off)
        path loo_summary
        path loo_summary_female, stageAs: 'female_stratum/*'   // MARKER SEXSTRAT_V1
        path gene_blacklist   // MARKER CNV_BLACKLIST_V1 (empty list when the panel has none)

    output:
        tuple val(meta), path("${meta.id}.cnv_consensus4.genes.tsv"),    emit: genes
        tuple val(meta), path("${meta.id}.cnv_consensus4.segments.tsv"), emit: segments
        tuple val(meta), path("${meta.id}.cnv_consensus4.json"),         emit: json

    stub:
        """
        touch ${meta.id}.cnv_consensus4.genes.tsv ${meta.id}.cnv_consensus4.segments.tsv ${meta.id}.cnv_consensus4.json
        """

    script:
        // SEXSTRAT_V1
        def stratum = (meta.sex in ['male', 'female']) ? meta.sex : (params.cnv_sex_fallback ?: 'male')
        def loo_use = (stratum == 'female') ? loo_summary_female : loo_summary
        def decon_arg = decon_genes ? "--decon-genes ${decon_genes}" : ''   // DECON_V1
        def blacklist_arg = gene_blacklist ? "--gene-blacklist ${gene_blacklist}" : ''   // CNV_BLACKLIST_V1
        def purple_arg = (purple_genes && purple_summary) ? "--purple-genes ${purple_genes} --purple-summary ${purple_summary}" : ''   // HMF_PURPLE_V1
        """
        echo "[SEXSTRAT] ${meta.id}: sex=${meta.sex} stratum=${stratum} loo=${loo_use}"
        # consensus rule version: CMX_V2_4; inputs CNV_RETIRE_7B (bash comment; busts the task cache)
        cnv_consensus_multi.py \\
            --sample ${meta.id} \\
            --sex ${meta.sex ?: 'unknown'} \\
            --cnr ${cnr} \\
            --call-cns ${call_cns} \\
            --gatk-genes ${gatk_genes} \\
            --gatk-called ${gatk_called} \\
            --denoised ${denoised} \\
            --baf-summary ${baf_summary} \\
            --baf-sites ${baf_sites} \\
            --loo-summary ${loo_use} \\
            --purecn-genes ${purecn_genes} \\
            --purecn-summary ${purecn_summary} \\
            ${decon_arg} \\
            ${blacklist_arg} \\
            ${purple_arg} \\
            --out-prefix ${meta.id}.cnv_consensus4
        """
}
