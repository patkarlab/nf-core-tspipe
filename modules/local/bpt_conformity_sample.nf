/*
 * modules/local/bpt_conformity_sample.nf
 *
 * Per-sample capture-conformity metrics: NPM1_exon_11 and JAK2_exon_15
 * mean depth (mosdepth --flag 772: duplicates INCLUDED per lab
 * convention) plus BAM-wide mean insert size (samtools stats). These are
 * the sentinels that separated the conforming 8-plex/16 hr captures from
 * the failed 12-plex arm in the 2026-09-01 survey.
 *
 * REPORT-ONLY in v1: metrics feed BPT_CONFORMITY_REPORT; no sample is
 * dropped by this process.
 */

process BPT_CONFORMITY_SAMPLE {
    tag   "${meta.id}"
    label 'process_medium'

    input:
        tuple val(meta), path(bam), path(bai)
        path exonwise

    output:
        tuple val(meta), path("${meta.id}.conformity.tsv"), emit: row

    stub:
        """
        printf 'sample\\tnpm1_exon_11_mean\\tjak2_exon_15_mean\\tinsert_size_mean\\n' >  ${meta.id}.conformity.tsv
        printf '${meta.id}\\t0\\t0\\t0\\n'                                             >> ${meta.id}.conformity.tsv
        """

    script:
        """
        capture_conformity_gate.py --mode sample \\
            --bam ${bam} \\
            --sample ${meta.id} \\
            --exonwise ${exonwise} \\
            --threads ${task.cpus} \\
            --out ${meta.id}.conformity.tsv
        """
}
