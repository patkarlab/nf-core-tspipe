/*
 * modules/local/flt3_consensus.nf
 *
 * Cluster ITD calls across the four tools and emit PASS_HIGH / PASS_LOW /
 * REVIEW_REQUIRED classifications. The clustering / scoring logic lives in
 * bin/flt3_consensus.py (moved verbatim from scripts/09b_flt3_consensus.py).
 *
 * Cluster tolerance: +/-2bp on ITD length.
 * Rules: 3+ tools agree -> PASS_HIGH ; 2 -> PASS_LOW ; 1 -> REVIEW_REQUIRED.
 */

process FLT3_CONSENSUS {
    tag        "${meta.id}"
    label      'process_low'

    conda      'conda-forge::pandas=2.1.4'
    container  'quay.io/biocontainers/pandas:2.1.4'

    input:
        tuple val(meta), path(flt3_ext_out), path(filt3r_json), path(getitd_out), path(pindel_vcf)

    output:
        tuple val(meta), path("${meta.id}_flt3_consensus.tsv"), emit: tsv
    stub:
        // nf-core stub blocks v1 (apply_nfcore_add_stub_blocks)
        """
        touch ${meta.id}_flt3_consensus.tsv
        """


    script:
        """
        flt3_consensus.py \\
            --sample ${meta.id} \\
            --flt3-itd-ext ${flt3_ext_out} \\
            --filt3r ${filt3r_json} \\
            --getitd ${getitd_out} \\
            --pindel ${pindel_vcf} \\
            --out ${meta.id}_flt3_consensus.tsv
        """
}
