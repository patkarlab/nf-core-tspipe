/*
 * modules/local/gatk_cnv_denoise.nf  (TGC_V1)
 *
 * DenoiseReadCounts against the sex-matched read-count PoN
 * (gatk_rc_pon_male.hdf5, built 2026-09-01 with GATK 4.6.2.0; a PoN
 * must be applied with the version that built it).
 */

process GATK_CNV_DENOISE {
    tag   "${meta.id}"
    label 'process_medium'

    input:
        tuple val(meta), path(counts)
        path rc_pon

    output:
        tuple val(meta), path("${meta.id}.denoisedCR.tsv"),     emit: denoised
        tuple val(meta), path("${meta.id}.standardizedCR.tsv"), emit: standardized

    stub:
        """
        touch ${meta.id}.denoisedCR.tsv ${meta.id}.standardizedCR.tsv
        """

    script:
        def xmx = task.memory ? Math.max(4, task.memory.toGiga() - 2) : 12
        """
        gatk --java-options "-Xmx${xmx}g" DenoiseReadCounts \\
            -I ${counts} \\
            --count-panel-of-normals ${rc_pon} \\
            --standardized-copy-ratios ${meta.id}.standardizedCR.tsv \\
            --denoised-copy-ratios ${meta.id}.denoisedCR.tsv
        """
}
