/*
 * modules/local/flt3_consensus.nf
 *
 * Build a 4-caller FLT3-ITD consensus TSV by merging per-tool calls
 * from GETITD, FLT3_ITD_EXT, FILT3R, and Pindel (FLT3-filtered). Wraps
 * bin/flt3_consensus.py, the canonical port of production
 * scripts/09b_flt3_consensus.py.
 *
 * The four caller inputs MUST arrive already joined by meta key. The
 * subworkflow is responsible for the .join(by:0) chain before invoking
 * this process. Declaring four separate inputs here would let Nextflow
 * pair them positionally, which is the cross-sample mispairing bug
 * shape that broke SomaticSeq before commit 3bf7eb4. See
 * bin/flt3_consensus.py docstring for CLI details.
 *
 * Container: this module is pure-Python, no external dependencies
 * beyond the stdlib. We reuse the cnvkit container because it is
 * already cached on every node and ships a working Python 3 -- the
 * same reuse pattern adopted for ZSCORE_CNV / CNV_CONCORDANCE in the
 * CNV wiring (no separate pandas-only image exists on quay).
 *
 * Pindel was added as the 4th caller in commit <SHA> (2026-05-19) to
 * close the missing 4th-voter gap relative to production. See
 * docs/audit/2026-05-19/backlog_next.md (D1).
 */

process FLT3_CONSENSUS {
    tag        "${meta.id}"
    label      'process_low'

    container  'quay.io/biocontainers/cnvkit:0.9.10--pyhdfd78af_0'

    input:
        tuple val(meta),
              path(getitd_hc),
              path(flt3_itd_ext_vcf),
              path(filt3r_vcf),
              path(pindel_flt3_vcf)

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
            --pindel        ${pindel_flt3_vcf} \\
            --out           ${meta.id}_flt3_consensus.tsv
        """
}
