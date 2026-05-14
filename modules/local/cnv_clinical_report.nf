/*
 * modules/local/cnv_clinical_report.nf
 *
 * nf-core CNV wiring v1 (apply_nfcore_cnv_wiring_part1)
 *
 * Tiered clinical CNV report. Combines concordance output with CNVKit
 * called segments, Z-score gene results, and annotated genemetrics into
 * the TIER_1/TIER_2/TIER_3/FILTERED layered report.
 *
 * Replaces scripts/12f_cnv_clinical_report.py (bin/cnv_clinical_report.py).
 *
 * Note: bin/cnv_clinical_report.py's --cnvkit-calls argument historically
 * pointed at a {sample}.filtered.call.cns file. We pass {sample}.call.cns
 * here; downstream filtering (if any) lives inside the script itself.
 */

process CNV_CLINICAL_REPORT {
    tag        "${meta.id}"
    label      'process_low'

    conda      'bioconda::cnvkit=0.9.10 conda-forge::pandas=2.1.4 conda-forge::numpy=1.26'
    container  'quay.io/biocontainers/cnvkit:0.9.10--pyhdfd78af_0'

    input:
        // From subworkflow:
        //   CNV_CONCORDANCE.out.tsv
        //     .join(CNVKIT.out.call_cns,         by: 0)
        //     .join(ZSCORE_CNV.out.zscore_genes, by: 0)
        //     .join(CNVKIT.out.genemetrics,      by: 0)
        tuple val(meta),
              path(concordance),
              path(cnvkit_call_cns),
              path(zscore_genes),
              path(genemetrics)

    output:
        tuple val(meta), path("${meta.id}_cnv_clinical.tsv"), emit: tsv
        tuple val(meta), path("${meta.id}_cnv_clinical.txt"), emit: txt, optional: true
    stub:
        // nf-core stub blocks v1 (apply_nfcore_add_stub_blocks)
        """
        touch ${meta.id}_cnv_clinical.tsv ${meta.id}_cnv_clinical.txt
        """


    script:
        """
        cnv_clinical_report.py \\
            -s ${meta.id} \\
            --concordance ${concordance} \\
            --cnvkit-calls ${cnvkit_call_cns} \\
            --zscore-genes ${zscore_genes} \\
            --genemetrics ${genemetrics} \\
            -o .

        # Normalise possible output filenames into the module's declared
        # output basenames (the bin/ script's filename convention has
        # varied across versions; this shim catches the known variants).
        for src in ${meta.id}.cnv_clinical_report.tsv ${meta.id}.cnv_clinical.tsv ${meta.id}_clinical_report.tsv; do
            if [ -f "\$src" ] && [ ! -f "${meta.id}_cnv_clinical.tsv" ]; then
                mv "\$src" "${meta.id}_cnv_clinical.tsv"
            fi
        done
        for src in ${meta.id}.cnv_clinical_report.txt ${meta.id}.cnv_clinical.txt ${meta.id}_clinical_report.txt; do
            if [ -f "\$src" ] && [ ! -f "${meta.id}_cnv_clinical.txt" ]; then
                mv "\$src" "${meta.id}_cnv_clinical.txt"
            fi
        done
        """
}
