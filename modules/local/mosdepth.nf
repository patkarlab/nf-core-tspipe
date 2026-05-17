/*
 * modules/local/mosdepth.nf
 *
 * Run mosdepth on the post-ABRA2 BAM with per-region coverage and
 * three threshold cutoffs (100x, 250x, 500x).
 *
 * This module is the first of a two-step exon-coverage pipeline:
 *   MOSDEPTH (this module) emits regions.bed.gz + thresholds.bed.gz
 *   PARSE_EXON_COVERAGE consumes those + the panel BED to write
 *   {sample}_exon_coverage.tsv
 *
 * The split exists because the mosdepth biocontainer is minimal
 * (mosdepth binary only, no python3), so the parsing step needs
 * to run in a separate container with Python.
 */

process MOSDEPTH {
    tag        "${meta.id}"
    label      'process_medium'
    container  'quay.io/biocontainers/mosdepth:0.3.10--h4e814b3_1'

    input:
        tuple val(meta), path(bam), path(bai)
        path bed

    output:
        tuple val(meta),
              path("${meta.id}.regions.bed.gz"),
              path("${meta.id}.regions.bed.gz.csi"),
              path("${meta.id}.thresholds.bed.gz"),
              path("${meta.id}.thresholds.bed.gz.csi"),
              emit: regions_thresholds
        tuple val(meta),
              path("${meta.id}.mosdepth.summary.txt"),
              path("${meta.id}.mosdepth.global.dist.txt"),
              path("${meta.id}.mosdepth.region.dist.txt"),
              emit: summary
        path "versions.yml", emit: versions

    stub:
        """
        touch ${meta.id}.regions.bed.gz ${meta.id}.regions.bed.gz.csi \\
              ${meta.id}.thresholds.bed.gz ${meta.id}.thresholds.bed.gz.csi \\
              ${meta.id}.mosdepth.summary.txt \\
              ${meta.id}.mosdepth.global.dist.txt \\
              ${meta.id}.mosdepth.region.dist.txt \\
              versions.yml
        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            stub: true
        END_VERSIONS
        """

    script:
        """
        set -eo pipefail

        # --by panel.bed:        per-region stats restricted to BED
        # --no-per-base:         skip the dense per-position output we
        #                         don't need (saves ~95% of runtime/disk)
        # --thresholds:          emit fraction-of-bases >= each cutoff
        # output prefix is just the sample id; mosdepth appends its
        #   own suffix for each file (.regions.bed.gz, etc.)
        mosdepth \\
            --by ${bed} \\
            --threads ${task.cpus} \\
            --no-per-base \\
            --thresholds 100,250,500 \\
            ${meta.id} \\
            ${bam}

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            mosdepth: \$(mosdepth --version 2>&1 | awk '{print \$2}')
        END_VERSIONS
        """
}
