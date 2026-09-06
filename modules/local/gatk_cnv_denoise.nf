/*
 * modules/local/gatk_cnv_denoise.nf  (TGC_V1)
 *
 * DenoiseReadCounts against the sex-matched read-count PoN (SEXSTRAT_V1:
 * male or female HDF5 chosen per sample from meta.sex)
 * (gatk_rc_pon_male.hdf5, built 2026-09-01 with GATK 4.6.2.0; a PoN
 * must be applied with the version that built it).
 */

process GATK_CNV_DENOISE {
    tag   "${meta.id}"
    label 'process_medium'

    input:
        tuple val(meta), path(counts)
        path rc_pon
        path rc_pon_female, stageAs: 'female_stratum/*'   // MARKER SEXSTRAT_V1

    output:
        tuple val(meta), path("${meta.id}.denoisedCR.tsv"),     emit: denoised
        tuple val(meta), path("${meta.id}.standardizedCR.tsv"), emit: standardized

    stub:
        """
        touch ${meta.id}.denoisedCR.tsv ${meta.id}.standardizedCR.tsv
        """

    script:
        def xmx = task.memory ? Math.max(4, task.memory.toGiga() - 2) : 12
        // SEXSTRAT_V1
        def stratum = (meta.sex in ['male', 'female']) ? meta.sex : (params.cnv_sex_fallback ?: 'male')
        def pon_use = (stratum == 'female') ? rc_pon_female : rc_pon
        """
        echo "[SEXSTRAT] ${meta.id}: sex=${meta.sex} stratum=${stratum} pon=${pon_use}"
        gatk --java-options "-Xmx${xmx}g" DenoiseReadCounts \\
            -I ${counts} \\
            --count-panel-of-normals ${pon_use} \\
            --standardized-copy-ratios ${meta.id}.standardizedCR.tsv \\
            --denoised-copy-ratios ${meta.id}.denoisedCR.tsv
        """
}
