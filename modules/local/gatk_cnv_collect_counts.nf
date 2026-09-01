/*
 * modules/local/gatk_cnv_collect_counts.nf  (TGC_V1)
 *
 * Per-sample CollectReadCounts over the PoN's preprocessed interval
 * list. The merging rule MUST match the PoN build (OVERLAPPING_ONLY).
 * No conda/container directives: the GATK_CNV_.* umbrella in
 * conf/twist_apply.config supplies the host env (GATK 4.6.2.0 parity).
 */

process GATK_CNV_COLLECT_COUNTS {
    tag   "${meta.id}"
    label 'process_low'

    input:
        tuple val(meta), path(bam), path(bai)
        tuple path(fasta), path(fai), path(dict)
        path interval_list

    output:
        tuple val(meta), path("${meta.id}.gatkcnv.counts.hdf5"), emit: counts

    stub:
        """
        touch ${meta.id}.gatkcnv.counts.hdf5
        """

    script:
        def xmx = task.memory ? Math.max(2, task.memory.toGiga() - 2) : 8
        """
        gatk --java-options "-Xmx${xmx}g" CollectReadCounts \\
            -I ${bam} \\
            -L ${interval_list} \\
            -R ${fasta} \\
            --interval-merging-rule OVERLAPPING_ONLY \\
            --format HDF5 \\
            -O ${meta.id}.gatkcnv.counts.hdf5
        """
}
