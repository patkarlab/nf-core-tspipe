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
              path(fastp_json),   // MARKER DASH_QC_V2
              path(igv_report),
              path(dashboard),
              // MARKER CNV_RETIRE_7B: legacy CNV inputs (clinical/annotated tables, CNVkit plots) removed
              path(cnv_consensus_genes), path(cnv_consensus_segments), path(cnv_consensus_json),   // MARKER ORG_CNV_V1
              path(exon_plots_dir), path(chrom_pages_dir),
              path(decon_filtered), path(decon_genes),
              path(purple_summary), path(purple_genes), path(purple_dir),
              path(sex_check),
              path(reconcnv_dir),   // MARKER VIZ_V1 (MARKER VIZ_V1b: styled_scatter_dir removed)
              path(spikein),   // MARKER SPIKEIN_V1: SPIKEIN_SITES genotype table
              path(baf_summary), path(baf_plot)   // BAF_V2B: per-arm BAF summary + two-track figure (sentinel when absent)

    output:
        tuple val(meta), path("clinical/"), emit: clinical
        path  "versions.yml",                emit: versions

    script:
        // ORG_CNV_V1: optional v2 CNV args
        def cnv_consensus_genes_arg = cnv_consensus_genes ? "--cnv-consensus-genes ${cnv_consensus_genes}" : ''
        def cnv_consensus_segments_arg = cnv_consensus_segments ? "--cnv-consensus-segments ${cnv_consensus_segments}" : ''
        def cnv_consensus_json_arg = cnv_consensus_json ? "--cnv-consensus-json ${cnv_consensus_json}" : ''
        def exon_plots_dir_arg = exon_plots_dir ? "--exon-plots-dir ${exon_plots_dir}" : ''
        def chrom_pages_dir_arg = chrom_pages_dir ? "--chrom-pages-dir ${chrom_pages_dir}" : ''
        def decon_filtered_arg = decon_filtered ? "--decon-filtered ${decon_filtered}" : ''
        def decon_genes_arg = decon_genes ? "--decon-genes ${decon_genes}" : ''
        def purple_summary_arg = purple_summary ? "--purple-summary ${purple_summary}" : ''
        def purple_genes_arg = purple_genes ? "--purple-genes ${purple_genes}" : ''
        def purple_dir_arg = purple_dir ? "--purple-dir ${purple_dir}" : ''
        def sex_check_arg = sex_check ? "--sex-check ${sex_check}" : ''
        def reconcnv_dir_arg = reconcnv_dir ? "--reconcnv-dir ${reconcnv_dir}" : ''
        def spikein_arg = spikein ? "--spikein-snps ${spikein}" : ''   // SPIKEIN_V1
        def baf_args = "--baf-summary ${baf_summary} --baf-plot ${baf_plot}"   // BAF_V2B
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
            --fastp-json          ${fastp_json} \\
            --igv-report          ${igv_report} \\
            --dashboard           ${dashboard} \\
            ${cnv_consensus_genes_arg} \\
            ${cnv_consensus_segments_arg} \\
            ${cnv_consensus_json_arg} \\
            ${exon_plots_dir_arg} \\
            ${chrom_pages_dir_arg} \\
            ${decon_filtered_arg} \\
            ${decon_genes_arg} \\
            ${purple_summary_arg} \\
            ${purple_genes_arg} \\
            ${purple_dir_arg} \\
            ${sex_check_arg} \\
            ${reconcnv_dir_arg} \\
            ${spikein_arg} \\
            ${baf_args}

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
        touch clinical/${meta.id}_fastp.json
        touch clinical/${meta.id}_igv_report.html
        touch clinical/${meta.id}_dashboard.html
        touch clinical/${meta.id}.spikein_snps.tsv
        touch versions.yml
        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            stub: true
        END_VERSIONS
        """
}
