/*
 * modules/local/hsmetrics.nf
 *
 * Picard CollectHsMetrics
 *
 * Note: gatk CollectHsMetrics. Bait + target interval lists derived from BED via BedToIntervalList.
 *
 * TODO: this is a stub. Fill in the script: block with the actual command line.
 * The original Python wrapper in scripts/ shows the exact invocation -- this
 * module just needs to translate that to a Nextflow process body.
 */

process HSMETRICS {
    tag        "${meta.id}"
    label      'process_medium'
    container  'docker://broadinstitute/gatk:4.5.0.0'

    input:
        tuple val(meta), path(bam), path(bai)
        tuple path(fasta), path(fai), path(dict)
        path bed

    output:
        tuple val(meta), path("${meta.id}_hsmetrics.txt"), emit: metrics
        path  "versions.yml",                              emit: versions

    stub:
        // nf-core stub blocks v1 (apply_nfcore_add_stub_blocks)
        """
        touch ${meta.id}_hsmetrics.txt versions.yml
        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            stub: true
        END_VERSIONS
        """

    script:
        """
        set -eo pipefail
        SAMPLE=${meta.id}

        # Step 1. Convert panel BED to a Picard interval_list.
        # CollectHsMetrics requires interval_list format (BED is not
        # accepted directly). Sequence dictionary identifies which
        # contigs are valid for the reference build.
        gatk BedToIntervalList \\
            -I ${bed} \\
            -O \${SAMPLE}.interval_list \\
            -SD ${dict}

        # Step 2. Run CollectHsMetrics. The panel BED is used as both
        # bait and target intervals (matches production's choice in
        # scripts/10_hsmetrics.py). VALIDATION_STRINGENCY=LENIENT lets
        # the run continue past minor BAM header quirks that are not
        # informative for capture metrics.
        gatk CollectHsMetrics \\
            -I ${bam} \\
            -O \${SAMPLE}_hsmetrics.txt \\
            -BAIT_INTERVALS \${SAMPLE}.interval_list \\
            -TARGET_INTERVALS \${SAMPLE}.interval_list \\
            -R ${fasta} \\
            --VALIDATION_STRINGENCY LENIENT

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            gatk4: \$(gatk --version 2>&1 | grep -oE '[0-9]+\\.[0-9]+\\.[0-9]+' | head -n1)
        END_VERSIONS
        """
}
