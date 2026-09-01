/*
 * modules/local/bpt_gatk_create_rc_pon.nf
 *
 * CreateReadCountPanelOfNormals for one stratum. The GC-annotated
 * intervals file is always staged; whether it is passed is gated by
 * params.pon_gc_correction.
 */

process BPT_GATK_CREATE_RC_PON {
    tag   "${stratum}"
    label 'process_medium'

    input:
        val  stratum
        path count_files
        path annotated

    output:
        tuple val(stratum), path("gatk_rc_pon_${stratum}.hdf5"), emit: pon

    stub:
        """
        touch gatk_rc_pon_${stratum}.hdf5
        """

    script:
        def cl        = count_files instanceof List ? count_files : [count_files]
        def in_args   = cl.collect { "-I ${it}" }.join(' \\\n            ')
        def annot_arg = params.pon_gc_correction ? "--annotated-intervals ${annotated}" : ''
        def xmx       = task.memory ? Math.max(4, task.memory.toGiga() - 2) : 16
        def extra     = task.ext.args ?: ''
        """
        n=\$(ls *.counts.hdf5 2>/dev/null | wc -l)
        echo "[ok] stratum=${stratum}: \$n read-count files (gc_correction=${params.pon_gc_correction})"
        if [ "\$n" -lt 2 ]; then
            echo "[error] stratum=${stratum}: need >= 2 read-count files, found \$n" >&2
            exit 1
        fi

        gatk --java-options "-Xmx${xmx}g" CreateReadCountPanelOfNormals \\
            ${in_args} \\
            ${annot_arg} \\
            ${extra} \\
            -O gatk_rc_pon_${stratum}.hdf5

        echo "[ok] wrote gatk_rc_pon_${stratum}.hdf5"
        """
}
