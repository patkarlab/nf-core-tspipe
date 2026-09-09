/*
 * modules/local/bam_quickcheck.nf
 *
 * MARKER HARDEN_Q4_V1 (audit Q4): samtools quickcheck on the final (ABRA2) BAM.
 * Fails the run on a truncated or unreadable BAM. Runs as its own process so
 * that adding it does not invalidate any cached task; downstream processes are
 * not gated on it, but a failure here terminates the run.
 */
process BAM_QUICKCHECK {
    tag "$meta.id"
    cpus 1
    memory '2 GB'
    container 'quay.io/biocontainers/samtools:1.18--h50ea8bc_1'

    input:
    tuple val(meta), path(bam), path(bai)

    output:
    tuple val(meta), path("${meta.id}.quickcheck.txt"), emit: report
    path "versions.yml",                                emit: versions

    script:
    """
    if samtools quickcheck -vv ${bam} > ${meta.id}.quickcheck.txt 2>&1; then
        echo "OK ${bam} (\$(stat -L -c %s ${bam}) bytes)" >> ${meta.id}.quickcheck.txt
    else
        echo "[BAM_QUICKCHECK] ${meta.id}: ${bam} failed samtools quickcheck" >&2
        cat ${meta.id}.quickcheck.txt >&2
        exit 1
    fi

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        samtools: \$(samtools --version | head -n1 | sed 's/samtools //')
    END_VERSIONS
    """

    stub:
    """
    echo "OK ${bam} (stub)" > ${meta.id}.quickcheck.txt
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        samtools: stub
    END_VERSIONS
    """
}
