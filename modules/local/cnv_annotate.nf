/*
 * modules/local/cnv_annotate.nf
 *
 * nf-core CNV wiring v1 (apply_nfcore_cnv_wiring_part1)
 *
 * Annotate the CNV concordance table with cytoband, ClinGen HI/TS scores,
 * gene role (TSG/Oncogene/Both), and heme clinical significance. Also
 * runs CDKN2A/2B partner-rescue logic and 9p/9q co-deletion commenting.
 *
 * Replaces scripts/18_cnv_annotate.py (bin/cnv_annotate.py).
 */

process CNV_ANNOTATE {
    tag        "${meta.id}"
    label      'process_low'

    conda      'bioconda::cnvkit=0.9.10 conda-forge::pandas=2.1.4 conda-forge::numpy=1.26'
    container  'quay.io/biocontainers/cnvkit:0.9.10--pyhdfd78af_0'

    input:
        tuple val(meta), path(concordance)
        path  loo_summary
        path  cytoband
        path  clingen
        path  bed

    output:
        tuple val(meta), path("${meta.id}_cnv_annotated.tsv"), emit: tsv
    stub:
        // nf-core stub blocks v1 (apply_nfcore_add_stub_blocks)
        """
        touch ${meta.id}_cnv_annotated.tsv
        """


    script:
        """
        python3 ${projectDir}/bin/cnv_annotate.py \\
            --sample ${meta.id} \\
            --concordance ${concordance} \\
            --loo-summary ${loo_summary} \\
            --cytoband ${cytoband} \\
            --clingen ${clingen} \\
            --bed ${bed} \\
            --outdir .
        """
}
