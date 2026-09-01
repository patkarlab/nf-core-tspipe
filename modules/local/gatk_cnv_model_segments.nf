/*
 * modules/local/gatk_cnv_model_segments.nf  (TGC_V1)
 *
 * ModelSegments on denoised copy ratios. Copy-ratio-only in v1; the
 * --allelic-counts input joins with the BAF/cnLOH caller so the
 * allele-specific machinery lands once, coherently.
 */

process GATK_CNV_MODEL_SEGMENTS {
    tag   "${meta.id}"
    label 'process_medium'

    input:
        tuple val(meta), path(denoised)

    output:
        tuple val(meta), path("${meta.id}.cr.seg"),         emit: cr_seg
        tuple val(meta), path("${meta.id}.modelFinal.seg"), emit: model_final
        tuple val(meta), path("${meta.id}.cr.igv.seg"),     emit: igv_seg, optional: true

    stub:
        """
        touch ${meta.id}.cr.seg ${meta.id}.modelFinal.seg ${meta.id}.cr.igv.seg
        """

    script:
        def xmx   = task.memory ? Math.max(4, task.memory.toGiga() - 2) : 12
        def extra = task.ext.args ?: ''
        """
        gatk --java-options "-Xmx${xmx}g" ModelSegments \\
            --denoised-copy-ratios ${denoised} \\
            ${extra} \\
            --output . \\
            --output-prefix ${meta.id}
        """
}
