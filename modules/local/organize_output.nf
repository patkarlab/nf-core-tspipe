process ORGANIZE_OUTPUT {
    tag        "${meta.id}"
    label      'process_low'
    container  'docker://broadinstitute/gatk:4.5.0.0'
    // publishDir is configured via conf/modules.config (withName: 'ORGANIZE_OUTPUT')
    // to keep the project's single-source-of-truth convention.

    input:
        tuple val(meta),
              path(bam), path(bai),
              path(clinical_tsv),
              path(filtered_tsv),
              path(u2af1_report,      stageAs: 'NO_FILE_u2af1_report.txt'),
              path(u2af1_rescue,      stageAs: 'NO_FILE_u2af1_rescue.tsv'),
              path(flt3_consensus),
              path(hsmetrics),
              path(exon_coverage),
              path(fastp_html),
              path(igv_report),
              path(dashboard),
              path(cnv_clinical_tsv),
              path(cnv_annotated_tsv),
              path(cnvkit_diagram),
              path(cnvkit_scatter),
              path(cnvkit_plots_dir)

    output:
        tuple val(meta), path("clinical/"), emit: clinical
        path  "versions.yml",                emit: versions

    script:
        """
        organize_output.py \\
            --sample              ${meta.id} \\
            --outdir              . \\
            --bam                 ${bam} \\
            --bai                 ${bai} \\
            --clinical-tsv        ${clinical_tsv} \\
            --filtered-tsv        ${filtered_tsv} \\
            --u2af1-report        ${u2af1_report} \\
            --u2af1-rescue        ${u2af1_rescue} \\
            --flt3-consensus      ${flt3_consensus} \\
            --hsmetrics           ${hsmetrics} \\
            --exon-coverage       ${exon_coverage} \\
            --fastp-html          ${fastp_html} \\
            --igv-report          ${igv_report} \\
            --dashboard           ${dashboard} \\
            --cnv-clinical-tsv    ${cnv_clinical_tsv} \\
            --cnv-annotated-tsv   ${cnv_annotated_tsv} \\
            --cnvkit-diagram-pdf  ${cnvkit_diagram} \\
            --cnvkit-scatter-png  ${cnvkit_scatter} \\
            --cnvkit-plots-dir    ${cnvkit_plots_dir}

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            python: \$(python3 --version 2>&1 | awk '{print \$2}')
        END_VERSIONS
        """

    stub:
        """
        mkdir -p clinical
        # Touch every deliverable that organize_output.py would hardlink in.
        # Useful for downstream stub validation and matches the real bin
        # script's output layout.
        touch clinical/${meta.id}.final.bam
        touch clinical/${meta.id}.final.bam.bai
        touch clinical/${meta.id}.somaticseq.clinical.final.tsv
        touch clinical/${meta.id}.somaticseq.filtered.tsv
        touch clinical/${meta.id}_flt3_consensus.tsv
        touch clinical/${meta.id}_hsmetrics.txt
        touch clinical/${meta.id}_exon_coverage.tsv
        touch clinical/${meta.id}_fastp.html
        touch clinical/${meta.id}_igv_report.html
        touch clinical/${meta.id}_dashboard.html
        touch versions.yml
        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            stub: true
        END_VERSIONS
        """
}
