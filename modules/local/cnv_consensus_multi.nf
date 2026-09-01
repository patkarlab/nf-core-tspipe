/*
 * modules/local/cnv_consensus_multi.nf  (CMX_V1; PureCN inputs PCN_V1)
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
        tuple val(meta), path(concordance), path(cnr), path(call_cns),
              path(gatk_genes), path(gatk_called), path(denoised),
              path(baf_summary), path(baf_sites),
              path(purecn_genes), path(purecn_summary)
        path loo_summary

    output:
        tuple val(meta), path("${meta.id}.cnv_consensus4.genes.tsv"),    emit: genes
        tuple val(meta), path("${meta.id}.cnv_consensus4.segments.tsv"), emit: segments
        tuple val(meta), path("${meta.id}.cnv_consensus4.json"),         emit: json

    stub:
        """
        touch ${meta.id}.cnv_consensus4.genes.tsv ${meta.id}.cnv_consensus4.segments.tsv ${meta.id}.cnv_consensus4.json
        """

    script:
        """
        cnv_consensus_multi.py \\
            --sample ${meta.id} \\
            --concordance ${concordance} \\
            --cnr ${cnr} \\
            --call-cns ${call_cns} \\
            --gatk-genes ${gatk_genes} \\
            --gatk-called ${gatk_called} \\
            --denoised ${denoised} \\
            --baf-summary ${baf_summary} \\
            --baf-sites ${baf_sites} \\
            --loo-summary ${loo_summary} \\
            --purecn-genes ${purecn_genes} \\
            --purecn-summary ${purecn_summary} \\
            --out-prefix ${meta.id}.cnv_consensus4
        """
}
