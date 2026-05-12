/*
 * modules/local/variant_filter.nf
 *
 * Apply quality/region/blacklist filters to annotated variants.
 * Mirrors scripts/14_variant_filter.py with --blacklist support.
 *
 * Filter precedence (priority 0 wins):
 *     BLACKLIST -> LowVAF / LowDepth / OffTarget / etc.
 *
 * BLACKLIST rows stay in filtered.tsv but are excluded from clinical.tsv.
 */

process VARIANT_FILTER {
    tag        "${meta.id}"
    label      'process_low'

    conda      'conda-forge::pandas=2.1.4 conda-forge::pysam=0.22.0'

    input:
        tuple val(meta), path(annotated_tsv)
        path  blacklist     // path or empty list

    output:
        tuple val(meta), path("${meta.id}.filtered.tsv"), emit: filtered
        tuple val(meta), path("${meta.id}.clinical.tsv"), emit: clinical
        path  "versions.yml",                              emit: versions

    script:
        def bl_arg = blacklist ? "--blacklist ${blacklist}" : ''
        """
        variant_filter.py \\
            --sample ${meta.id} \\
            --input ${annotated_tsv} \\
            ${bl_arg} \\
            --filtered ${meta.id}.filtered.tsv \\
            --clinical ${meta.id}.clinical.tsv

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            python: \$(python --version | sed 's/Python //')
            pandas: \$(python -c "import pandas; print(pandas.__version__)")
        END_VERSIONS
        """
}
