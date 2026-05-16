/*
 * modules/local/flt3_consensus.nf
 *
 * Build a 3-caller FLT3-ITD consensus TSV by merging per-tool calls from
 * GETITD, FLT3_ITD_EXT, and FILT3R. Wraps bin/flt3_consensus.py, which
 * is the canonical port of production scripts/09b_flt3_consensus.py.
 *
 * The three caller inputs MUST arrive already joined by meta key. The
 * subworkflow is responsible for the .join(by:0) before invoking this
 * process. Declaring three separate inputs here would let Nextflow pair
 * them positionally, which is the same bug shape that caused
 * cross-sample BAM/VCF mispairing in the SomaticSeq fix (commit
 * 3bf7eb4). See bin/flt3_consensus.py docstring for CLI details.
 *
 * Container: this module is pure-Python, no external dependencies
 * beyond the stdlib. We reuse the cnvkit container because it is
 * already cached on every node and ships a working Python 3 -- the
 * same reuse pattern adopted for ZSCORE_CNV / CNV_CONCORDANCE in the
 * CNV wiring (no separate pandas-only image exists on quay).
 */

process FLT3_CONSENSUS {
    tag        "${meta.id}"
    label      'process_low'

    container  'quay.io/biocontainers/cnvkit:0.9.10--pyhdfd78af_0'

    input:
        tuple val(meta),
              path(getitd_hc),
              path(flt3_itd_ext_vcf),
              path(filt3r_vcf)

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
            --sample        ${meta.id} \\
            --getitd        ${getitd_hc} \\
            --flt3-itd-ext  ${flt3_itd_ext_vcf} \\
            --filt3r        ${filt3r_vcf} \\
            --out           ${meta.id}_flt3_consensus.tsv
        """
}
