/*
 * modules/local/cnvkit.nf
 *
 * nf-core CNV wiring v1 (apply_nfcore_cnv_wiring_part2)
 *
 * CNVKit-based copy-number calling with a sex-matched PoN.
 * Wraps bin/cnvkit.py, which is itself the ported and trimmed version of
 * production scripts/12_cnv_calling.py (sex auto-inference removed; sex
 * resolved upstream via meta.sex).
 *
 * PoN selection logic:
 *   meta.sex == 'male'   -> pon_male
 *   meta.sex == 'female' -> pon_female
 *   meta.sex == 'unknown' (or unset) -> pon_female (with a warning;
 *     chrX on a male sample run against a female PoN will show as
 *     systematic ~-1 log2 loss, which is reviewable but not silent)
 *
 * Both PoN files are staged (small cost); only one is referenced by
 * cnvkit.py batch. Outputs follow the production naming convention so
 * downstream modules (CNV_PLOTS, ZSCORE_CNV, CNV_CONCORDANCE,
 * CNV_CLINICAL_REPORT) can consume by exact basename.
 */

process CNVKIT {
    tag        "${meta.id}"
    label      'process_medium'

    conda      'bioconda::cnvkit=0.9.10 conda-forge::pandas=2.1.4 conda-forge::numpy=1.26'
    container  'quay.io/biocontainers/cnvkit:0.9.10--pyhdfd78af_0'

    input:
        tuple val(meta), path(bam), path(bai)
        tuple path(fasta), path(fai), path(dict)
        path  bed
        path  pon_male
        path  pon_female
        path  noisy_bins
        path  loo_summary

    output:
        // Downstream-consumed bin/segment/genemetrics outputs
        tuple val(meta), path("${meta.id}.cnr"),                       emit: cnr
        tuple val(meta), path("${meta.id}.cns"),                       emit: cns
        tuple val(meta), path("${meta.id}.call.cns"),                  emit: call_cns
        tuple val(meta), path("${meta.id}.genemetrics.annotated.tsv"), emit: genemetrics
        // Side-channel exports (optional; failures are non-fatal in bin/cnvkit.py)
        tuple val(meta), path("${meta.id}.seg"),                       emit: seg,         optional: true
        tuple val(meta), path("${meta.id}.cnv.vcf"),                   emit: vcf,         optional: true
        tuple val(meta), path("${meta.id}.genemetrics.tsv"),           emit: genemetrics_raw, optional: true
        // Plots produced inline by cnvkit.py batch / scatter
        tuple val(meta), path("${meta.id}.scatter.png"),               emit: scatter_png, optional: true
        tuple val(meta), path("${meta.id}.scatter.chr*.png"),          emit: chr_scatters, optional: true
        tuple val(meta), path("${meta.id}.final-diagram.pdf"),         emit: diagram_pdf, optional: true
        tuple val(meta), path("${meta.id}.final-scatter.png"),         emit: final_scatter_png, optional: true
        tuple val(meta), path("${meta.id}.final-scatter.pdf"),         emit: final_scatter_pdf, optional: true
    stub:
        // nf-core stub blocks v1 (apply_nfcore_add_stub_blocks)
        """
        touch ${meta.id}.cnr ${meta.id}.cns ${meta.id}.call.cns ${meta.id}.genemetrics.annotated.tsv ${meta.id}.seg ${meta.id}.cnv.vcf ${meta.id}.genemetrics.tsv ${meta.id}.scatter.png ${meta.id}.scatter.chr1.png ${meta.id}.final-diagram.pdf ${meta.id}.final-scatter.png ${meta.id}.final-scatter.pdf
        """


    script:
        def sex     = meta.sex ?: 'unknown'
        def pon_use = (sex == 'male') ? pon_male : pon_female
        """
        if [ "${sex}" = "unknown" ]; then
            echo "[WARN] meta.sex=unknown for ${meta.id}; using female PoN as fallback." >&2
            echo "[WARN]   If this sample is male, chrX will show systematic loss in the CNR." >&2
        fi

        cnvkit.py \\
            --bam ${bam} \\
            -s ${meta.id} \\
            -o . \\
            --pon ${pon_use} \\
            --sex ${sex} \\
            --blacklist ${noisy_bins} \\
            --loo-summary ${loo_summary}
        """
}
