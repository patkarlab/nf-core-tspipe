/*
 * modules/local/gatk_cnv_call_segments.nf  (TGC_V1)
 *
 * CallCopyRatioSegments: labels each copy-ratio segment +, -, or 0.
 */

process GATK_CNV_CALL_SEGMENTS {
    tag   "${meta.id}"
    label 'process_low'

    input:
        tuple val(meta), path(cr_seg)

    output:
        tuple val(meta), path("${meta.id}.called.seg"), emit: called

    stub:
        """
        touch ${meta.id}.called.seg
        """

    script:
        def xmx = task.memory ? Math.max(2, task.memory.toGiga() - 2) : 8
        """
        gatk --java-options "-Xmx${xmx}g" CallCopyRatioSegments \\
            -I ${cr_seg} \\
            -O ${meta.id}.called.seg
        """
}
