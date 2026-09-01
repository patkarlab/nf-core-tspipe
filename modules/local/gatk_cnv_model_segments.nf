/*
 * modules/local/gatk_cnv_model_segments.nf  (TGC_V1; allelic input BAF_V1)
 *
 * ModelSegments on denoised copy ratios plus per-sample allelic counts:
 * joint segmentation of total copy ratio and minor-allele fraction,
 * tumor-only mode. Also emits the sample's het sites table.
 */

process GATK_CNV_MODEL_SEGMENTS {
    tag   "${meta.id}"
    label 'process_medium'

    input:
        tuple val(meta), path(denoised), path(allelic)

    output:
        tuple val(meta), path("${meta.id}.cr.seg"),         emit: cr_seg
        tuple val(meta), path("${meta.id}.modelFinal.seg"), emit: model_final
        tuple val(meta), path("${meta.id}.hets.tsv"),       emit: hets
        tuple val(meta), path("${meta.id}.cr.igv.seg"),     emit: igv_seg, optional: true

    stub:
        """
        touch ${meta.id}.cr.seg ${meta.id}.modelFinal.seg ${meta.id}.hets.tsv ${meta.id}.cr.igv.seg
        """

    script:
        def xmx   = task.memory ? Math.max(4, task.memory.toGiga() - 2) : 12
        def extra = task.ext.args ?: ''
        """
        gatk --java-options "-Xmx${xmx}g" ModelSegments \\
            --denoised-copy-ratios ${denoised} \\
            --allelic-counts ${allelic} \\
            ${extra} \\
            --output . \\
            --output-prefix ${meta.id}
        """
}
