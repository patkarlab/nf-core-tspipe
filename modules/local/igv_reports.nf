/*
 * modules/local/igv_reports.nf
 *
 * Generate per-sample self-contained IGV HTML reports for clinical variant
 * review. Wraps bin/igv_reports.py, which is the canonical port of
 * production scripts/16_igv_reports.py.
 *
 * Input shape matches what reporting.nf joins together: meta + clinical
 * TSV + BAM + BAI. Reference FASTA + FAI are passed separately as
 * value channels.
 *
 * Output filename matches production: ${sample}_igv_report.html (singular).
 * Note the stub previously declared "_igv_reports.html" (plural); aligned
 * with production here so downstream organize_output picks the same name
 * the clinical team is used to seeing.
 *
 * Container: a public igv-reports biocontainer. The image is small (~150 MB)
 * and ships create_report + python3 + pysam. The bin script uses pysam for
 * VCF compression and indexing because the image does not include the
 * standalone bgzip and tabix binaries.
 *
 * Duplicate handling: create_report defaults to --exclude-flags 1536, which
 * filters duplicate and QC-fail reads from the pileup. Production does the
 * same (also does not pass --exclude-flags). Note this DIVERGES from this
 * site's coverage convention (clinical convention here is to INCLUDE
 * duplicates in coverage metrics, --flag 772 in mosdepth). Whether the same
 * inclusion rule should apply to IGV visual review is an open audit item.
 */

process IGV_REPORTS {
    tag        "${meta.id}"
    label      'process_medium'

    container  'quay.io/biocontainers/igv-reports:1.12.0--pyh7cba7a3_0'

    input:
        tuple val(meta), path(clinical_tsv), path(bam), path(bai)
        tuple path(fasta), path(fai), path(dict)

    output:
        tuple val(meta), path("${meta.id}_igv_report.html"), emit: html
        path  "versions.yml",                                emit: versions

    stub:
        // nf-core stub blocks v1
        """
        touch ${meta.id}_igv_report.html
        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            stub: true
        END_VERSIONS
        """

    script:
        """
        igv_reports.py \\
            --sample  ${meta.id} \\
            --input   ${clinical_tsv} \\
            --bam     ${bam} \\
            --fasta   ${fasta} \\
            --output  ${meta.id}_igv_report.html

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            igv-reports: \$(create_report --help 2>&1 | head -1 || echo unknown)
            python: \$(python3 --version 2>&1 | awk '{print \$2}')
        END_VERSIONS
        """
}
