/*
 * modules/local/sex_check.nf  (SEX_CHECK_V1)
 *
 * Infer sample sex from mosdepth per-region depth: median chrX depth over
 * median autosomal depth, each region normalised within its own class
 * (exon target vs CNV backbone tile); chrY is used where the BED has it.
 * Expected X/A ~0.5 male, ~1.0 female. Compares with the samplesheet value
 * and writes <sample>.sex_check.tsv (one row). PREPROCESSING reads
 * resolved_sex from it and writes meta.sex only when the sheet says
 * 'unknown'. A MISMATCH never overrides the sheet; it is flagged.
 *
 * Container: GATK image for its Python 3.6; bin/sex_check.py is stdlib only.
 */

process SEX_CHECK {
    tag        "${meta.id}"
    label      'process_low'
    container  'docker://broadinstitute/gatk:4.5.0.0'

    input:
        tuple val(meta),
              path(regions),
              path(regions_csi),
              path(thresholds),
              path(thresholds_csi)

    output:
        tuple val(meta), path("${meta.id}.sex_check.tsv"), emit: tsv
        path "versions.yml", emit: versions

    stub:
        def sheet_sex = meta.sex ?: 'unknown'
        """
        printf 'sample\\tsheet_sex\\tinferred_sex\\tresolved_sex\\tstatus\\tx_auto_ratio\\ty_auto_ratio\\ty_status\\tn_auto\\tn_x\\tn_y\\tauto_median_exon\\tauto_median_backbone\\tn_par_excluded\\tn_noncanonical_skipped\\tflags\\n' > ${meta.id}.sex_check.tsv
        printf '${meta.id}\\t${sheet_sex}\\tindeterminate\\t${sheet_sex}\\tSTUB\\tNA\\tNA\\tNA\\t0\\t0\\t0\\tNA\\tNA\\t0\\t0\\tstub\\n' >> ${meta.id}.sex_check.tsv
        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            stub: true
        END_VERSIONS
        """

    script:
        def sheet_sex = meta.sex ?: 'unknown'
        """
        sex_check.py \\
            --regions ${regions} \\
            --sample ${meta.id} \\
            --sheet-sex ${sheet_sex} \\
            --out ${meta.id}.sex_check.tsv

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            python: \$(python3 --version 2>&1 | awk '{print \$2}')
        END_VERSIONS
        """
}
