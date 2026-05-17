/*
 * modules/local/parse_exon_coverage.nf
 *
 * Second half of the exon-coverage pipeline. Consumes mosdepth's
 * regions.bed.gz + thresholds.bed.gz outputs and joins them with the
 * panel BED's labels to produce a per-exon TSV.
 *
 * Container: the GATK biocontainer is used here only because it has
 * a Python 3.6 interpreter already, and we don't need a dedicated
 * Python image. bin/parse_exon_coverage.py is pure-stdlib (gzip,
 * csv, re, pathlib, argparse, logging) so any Python >= 3.6 works.
 *
 * Output: ${meta.id}_exon_coverage.tsv (columns: Gene, Exon, Chr,
 * Start, End, Length_bp, Mean_Coverage, Pct_100x, Pct_250x, Pct_500x,
 * Flag). LOW_COVERAGE flag is set on rows < 100x mean.
 */

process PARSE_EXON_COVERAGE {
    tag        "${meta.id}"
    label      'process_low'
    container  'docker://broadinstitute/gatk:4.5.0.0'

    input:
        tuple val(meta),
              path(regions),
              path(regions_csi),
              path(thresholds),
              path(thresholds_csi)
        path bed

    output:
        tuple val(meta), path("${meta.id}_exon_coverage.tsv"), emit: tsv
        path "versions.yml", emit: versions

    stub:
        """
        touch ${meta.id}_exon_coverage.tsv versions.yml
        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            stub: true
        END_VERSIONS
        """

    script:
        """
        set -eo pipefail

        # parse_exon_coverage.py is auto-staged onto PATH by Nextflow.
        # No mosdepth invocation here; just gzip-read the two bed.gz
        # files and join with the panel BED labels.
        parse_exon_coverage.py \\
            --sample ${meta.id} \\
            --bed ${bed} \\
            --regions ${regions} \\
            --thresholds ${thresholds} \\
            --output-dir .

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            python: \$(python3 --version 2>&1 | awk '{print \$2}')
        END_VERSIONS
        """
}
