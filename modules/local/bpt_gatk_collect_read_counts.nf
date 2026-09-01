/*
 * modules/local/bpt_gatk_collect_read_counts.nf
 *
 * Per-sample CollectReadCounts (HDF5) over the preprocessed interval
 * list. Runs on every samplesheet row; stratum filtering happens at
 * CreateReadCountPanelOfNormals.
 */

process BPT_GATK_COLLECT_READ_COUNTS {
    tag   "${meta.id}"
    label 'process_low'

    input:
        tuple val(meta), path(bam), path(bai)
        path interval_list
        path fasta
        path fai
        path dict

    output:
        tuple val(meta), path("${meta.id}.counts.hdf5"), emit: counts

    stub:
        """
        touch ${meta.id}.counts.hdf5
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
            -O ${meta.id}.counts.hdf5

        echo "[ok] ${meta.id}: read counts written"
        """
}
