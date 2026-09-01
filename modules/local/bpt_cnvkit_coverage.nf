/*
 * modules/local/bpt_cnvkit_coverage.nf
 *
 * Per-sample CNVkit coverage over the split targets. Runs on EVERY
 * samplesheet row (including excluded females) so per-sample QC exists
 * for the whole cohort; stratum membership is enforced downstream at
 * reference construction.
 *
 * When antitargets.bed is empty a header-only antitarget .cnn is written
 * directly instead of invoking cnvkit on a zero-length BED. This keeps
 * the file contract expected by cnvkit reference and bin/cnv_loo_qc.py.
 */

process BPT_CNVKIT_COVERAGE {
    tag   "${meta.id}"
    label 'process_medium'

    input:
        tuple val(meta), path(bam), path(bai)
        path targets
        path antitargets

    output:
        tuple val(meta), path("${meta.id}.targetcoverage.cnn"), path("${meta.id}.antitargetcoverage.cnn"), emit: cov

    stub:
        """
        touch ${meta.id}.targetcoverage.cnn ${meta.id}.antitargetcoverage.cnn
        """

    script:
        """
        cnvkit.py coverage ${bam} ${targets} -p ${task.cpus} -o ${meta.id}.targetcoverage.cnn

        if [ -s ${antitargets} ]; then
            cnvkit.py coverage ${bam} ${antitargets} -p ${task.cpus} -o ${meta.id}.antitargetcoverage.cnn
        else
            printf 'chromosome\\tstart\\tend\\tgene\\tdepth\\tlog2\\n' > ${meta.id}.antitargetcoverage.cnn
            echo "[ok] ${meta.id}: header-only antitarget coverage (empty antitarget BED)"
        fi

        n=\$(tail -n +2 ${meta.id}.targetcoverage.cnn | wc -l)
        echo "[ok] ${meta.id}: \$n target coverage bins"
        if [ "\$n" -lt 1000 ]; then
            echo "[error] ${meta.id}: implausibly few coverage bins (\$n)" >&2
            exit 1
        fi
        """
}
