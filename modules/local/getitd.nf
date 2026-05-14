/*
 * modules/local/getitd.nf
 *
 * getITD (Blaetsch 2019). FLT3-ITD caller on FASTQ input.
 *
 * CRITICAL parameter from the original pipeline:
 *   -min_bqs 20  -- the default of 30 rejects ALL reads from BQSR'd BAMs,
 *                   whose quality scores are rescaled into the low-to-mid 20s.
 *                   This was a hard-won finding from the original work.
 *
 * The original orchestrator did "cd into getITD source dir then mv output"
 * because getITD writes to <sample>_getitd/ in CWD. In Nextflow each process
 * has its own work directory, so this directory-collision hack is unnecessary.
 */

process GETITD {
    tag        "${meta.id}"
    label      'process_low'
    label      'error_ignore'

    // getITD ships as a Python script with bundled annotation files.
    // Install path: /home/hemat/programs/getitd/ (anno/ files relative to getitd.py)
    // Easiest: build a container that bakes getitd.py + anno/ into a known path.
    // container 'your-registry/getitd:1.5.15'

    input:
        tuple val(meta), path(reads1), path(reads2)

    output:
        tuple val(meta), path("${meta.id}_getitd"), emit: calls, optional: true
    stub:
        // nf-core stub blocks v1 (apply_nfcore_add_stub_blocks)
        """
        mkdir -p ${meta.id}_getitd
        """


    script:
        def min_bqs   = task.ext.min_bqs   ?: 20    // see header note
        def getitd_py = params.getitd_path ?: '/home/hemat/programs/getitd/getitd.py'
        """
        # getITD scans relative to its own source dir; run from the install dir
        # and use absolute paths for inputs/outputs.
        cd \$(dirname ${getitd_py})

        python getitd.py \\
            -nkern ${task.cpus} \\
            -min_bqs ${min_bqs} \\
            ${meta.id} \\
            \$(realpath ${reads1}) \\
            \$(realpath ${reads2})

        # getITD wrote <sample>_getitd into the install dir; move to work dir
        mv ${meta.id}_getitd \$OLDPWD/
        """
}
