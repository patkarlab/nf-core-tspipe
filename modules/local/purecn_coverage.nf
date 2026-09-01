/*
 * modules/local/purecn_coverage.nf  (PCN_V1)
 *
 * PureCN GC-normalised loess coverage for the tumor sample, over the
 * same interval file the NormalDB was built from. Runs on the dedicated
 * purecn conda env (PureCN 2.16.0; envs/purecn.environment.yml) via the
 * PURECN.* beforeScript in conf/twist_apply.config.
 */

process PURECN_COVERAGE {
    tag   "${meta.id}"
    label 'process_medium'

    input:
        tuple val(meta), path(bam), path(bai)
        path intervals

    output:
        tuple val(meta), path("*_coverage_loess.txt.gz"), emit: coverage

    stub:
        """
        touch ${meta.id}.final_coverage_loess.txt.gz
        """

    script:
        """
        Rscript ${params.purecn_extdata}/Coverage.R \\
            --bam ${bam} \\
            --intervals ${intervals} \\
            --out-dir . \\
            --cores ${task.cpus} \\
            --force
        ls *_coverage_loess.txt.gz
        """
}
