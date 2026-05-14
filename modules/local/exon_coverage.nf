/*
 * modules/local/exon_coverage.nf
 *
 * Per-exon coverage
 *
 * Note: Per-exon depth via samtools bedcov / mosdepth.
 *
 * TODO: this is a stub. Fill in the script: block with the actual command line.
 * The original Python wrapper in scripts/ shows the exact invocation -- this
 * module just needs to translate that to a Nextflow process body.
 */

process EXON_COVERAGE {
    tag        "${meta.id}"
    label      'process_medium'

    input:
        tuple val(meta), path(bam), path(bai)
        path bed

    output:
        tuple val(meta), path("${meta.id}_exon_coverage.tsv"), emit: tsv
    stub:
        // nf-core stub blocks v1 (apply_nfcore_add_stub_blocks)
        """
        touch ${meta.id}_exon_coverage.tsv
        """


    script:
        """
        # TODO: replace this stub with the tool invocation from the source script.
        echo "STUB: EXON_COVERAGE for ${meta.id}" >&2
        # Touch output filename(s) so downstream channels don't break during DAG validation:
        touch ${meta.id}_exon_coverage.tsv
        """
}
