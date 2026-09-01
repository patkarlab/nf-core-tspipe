/*
 * modules/local/bpt_gatk_annotate_intervals.nf
 *
 * AnnotateIntervals GC-content track over the preprocessed interval list.
 * Always runs (seconds); whether CreateReadCountPanelOfNormals consumes
 * it is gated by params.pon_gc_correction (module-review item).
 */

process BPT_GATK_ANNOTATE_INTERVALS {
    tag   "annotate_intervals"
    label 'process_low'

    input:
        path interval_list
        path fasta
        path fai
        path dict

    output:
        path 'targets.gc.annotated.tsv', emit: annotated

    stub:
        """
        touch targets.gc.annotated.tsv
        """

    script:
        def xmx = task.memory ? Math.max(2, task.memory.toGiga() - 2) : 8
        """
        gatk --java-options "-Xmx${xmx}g" AnnotateIntervals \\
            -L ${interval_list} \\
            -R ${fasta} \\
            --interval-merging-rule OVERLAPPING_ONLY \\
            -O targets.gc.annotated.tsv

        echo "[ok] GC annotation written (consumed by RC PoN: ${params.pon_gc_correction})"
        """
}
