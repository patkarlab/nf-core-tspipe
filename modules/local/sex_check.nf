/*
 * modules/local/sex_check.nf  (SEX_CHECK_V2; supersedes SEX_CHECK_V1)
 *
 * Two votes on sample sex, both computed here so meta.sex is resolved before
 * any CNV arm runs.
 *
 *   1. Heterozygosity (decides): GATK CollectAllelicCounts on the final BAM at
 *      the panel het catalog sites (assets/<panel>/het_catalog.tsv, v2). A male
 *      has no heterozygous chrX sites outside the PAR whatever the tumour does
 *      to chrX copy number; a female has about the autosomal het fraction.
 *   2. Depth (confirms): mosdepth per-region chrX/autosome ratio, per region
 *      class, PAR excluded (the SEX_CHECK_V1 method). A somatic chrX gain or
 *      loss moves this ratio; disagreement with vote 1 is X_DEPTH_CONFLICT.
 *
 * Panels without a het catalog stage [] and keep the depth-only inference.
 * Samplesheet male/female always wins; 'unknown' takes the inference; a
 * MISMATCH is flagged, never applied. Output <sample>.sex_check.tsv keeps the
 * sixteen V1 columns and appends seven.
 *
 * Container: GATK image (CollectAllelicCounts + Python 3.6); bin/sex_check.py
 * is stdlib only.
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
              path(thresholds_csi),
              path(bam),
              path(bai)
        tuple path(fasta), path(fai), path(dict)
        path het_catalog

    output:
        tuple val(meta), path("${meta.id}.sex_check.tsv"), emit: tsv
        path "${meta.id}.sexcheck.allelicCounts.tsv", optional: true, emit: allelic
        path "versions.yml", emit: versions

    stub:
        def sheet_sex = meta.sex ?: 'unknown'
        """
        printf 'sample\\tsheet_sex\\tinferred_sex\\tresolved_sex\\tstatus\\tx_auto_ratio\\ty_auto_ratio\\ty_status\\tn_auto\\tn_x\\tn_y\\tauto_median_exon\\tauto_median_backbone\\tn_par_excluded\\tn_noncanonical_skipped\\tflags\\tmethod\\thet_inferred_sex\\tdepth_inferred_sex\\tx_het_frac\\tauto_het_frac\\tn_x_het_sites\\tn_auto_het_sites\\n' > ${meta.id}.sex_check.tsv
        printf '${meta.id}\\t${sheet_sex}\\tindeterminate\\t${sheet_sex}\\tSTUB\\tNA\\tNA\\tNA\\t0\\t0\\t0\\tNA\\tNA\\t0\\t0\\tstub\\tnone\\tNA\\tNA\\tNA\\tNA\\t0\\t0\\n' >> ${meta.id}.sex_check.tsv
        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            stub: true
        END_VERSIONS
        """

    script:
        def sheet_sex = meta.sex ?: 'unknown'
        def xmx       = task.memory ? Math.max(2, task.memory.toGiga() - 2) : 4
        def ac        = "${meta.id}.sexcheck.allelicCounts.tsv"
        def het_cmd   = het_catalog ? """awk -F'\\t' 'NR > 1 { printf "%s\\t%d\\t%s\\n", \$1, \$2 - 1, \$2 }' ${het_catalog} > sexcheck_sites.bed
        gatk --java-options "-Xmx${xmx}g" CollectAllelicCounts \\
            -I ${bam} \\
            -L sexcheck_sites.bed \\
            -R ${fasta} \\
            -O ${ac}
        n_sites=\$(grep -vc '^@' ${ac})
        echo "[sex_check] ${meta.id}: \$n_sites allelic-count records at het catalog sites (incl. header)"
        """ : "echo '[sex_check] ${meta.id}: no het catalog staged; depth vote only'"
        def het_args  = het_catalog ? "--allelic-counts ${ac} --het-catalog ${het_catalog}" : ''
        """
        ${het_cmd}

        sex_check.py \\
            --regions ${regions} \\
            --sample ${meta.id} \\
            --sheet-sex ${sheet_sex} \\
            ${het_args} \\
            --out ${meta.id}.sex_check.tsv

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            python: \$(python3 --version 2>&1 | awk '{print \$2}')
            gatk: \$(gatk --version 2>&1 | grep -m1 -oE '[0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+' || echo unknown)
        END_VERSIONS
        """
}
