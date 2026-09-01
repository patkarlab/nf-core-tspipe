/*
 * modules/local/bpt_gatk_preprocess_intervals.nf
 *
 * PreprocessIntervals from panel.combined.filtered.bed: bin-length 0,
 * padding 0, OVERLAPPING_ONLY merging. Every downstream GATK count step
 * must use the same merging rule against this list.
 */

process BPT_GATK_PREPROCESS_INTERVALS {
    tag   "preprocess_intervals"
    label 'process_low'

    input:
        path bed
        path fasta
        path fai
        path dict

    output:
        path 'targets.preprocessed.interval_list', emit: interval_list

    stub:
        """
        touch targets.preprocessed.interval_list
        """

    script:
        def xmx   = task.memory ? Math.max(2, task.memory.toGiga() - 2) : 8
        def extra = task.ext.args ?: ''
        """
        gatk --java-options "-Xmx${xmx}g" PreprocessIntervals \\
            -L ${bed} \\
            -R ${fasta} \\
            --bin-length 0 \\
            --padding 0 \\
            --interval-merging-rule OVERLAPPING_ONLY \\
            ${extra} \\
            -O targets.preprocessed.interval_list

        n=\$(grep -vc '^@' targets.preprocessed.interval_list)
        echo "[ok] preprocessed intervals: \$n (from ${bed})"
        """
}
