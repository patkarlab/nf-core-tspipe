/*
 * modules/local/variant_filter.nf
 *
 * Apply quality/region/blacklist filters to annotated variants and
 * merge in U2AF1 rescue hits. Mirrors production scripts/14_variant_filter.py.
 *
 * Filter precedence (priority 0 wins):
 *     BLACKLIST -> LowVAF / LowDepth / OffTarget / etc.
 *
 * BLACKLIST rows stay in filtered.tsv but are excluded from clinical.tsv.
 *
 * The wrapped bin/variant_filter.py discovers its inputs by convention
 * from --outdir, looking for ${meta.id}.somaticseq.annotated.tsv and
 * (optionally) ${meta.id}_u2af1_rescue.tsv. We symlink the annotated
 * TSV to the expected name; the U2AF1 TSV already arrives with the
 * right filename from U2AF1_RESCUE.
 */

process VARIANT_FILTER {
    tag        "${meta.id}"
    label      'process_low'

    conda      'conda-forge::pandas=2.1.4'

    input:
        tuple val(meta), path(annotated_tsv), path(u2af1_tsv)
        path  blacklist     // path or empty list

    output:
        tuple val(meta), path("${meta.id}.somaticseq.filtered.tsv"), emit: filtered
        tuple val(meta), path("${meta.id}.somaticseq.clinical.tsv"), emit: clinical
        path  "versions.yml",                                         emit: versions

    stub:
        // nf-core stub blocks v1
        """
        touch ${meta.id}.somaticseq.filtered.tsv ${meta.id}.somaticseq.clinical.tsv versions.yml
        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            stub: true
        END_VERSIONS
        """

    script:
        def bl_arg = blacklist ? "--blacklist ${blacklist}" : ''
        """
        # Rename VEP_ANNOTATE output to the filename variant_filter.py expects.
        # ln -sf is idempotent across retries in the same work dir.
        ln -sf ${annotated_tsv} ${meta.id}.somaticseq.annotated.tsv

        variant_filter.py \\
            --sample ${meta.id} \\
            --outdir . \\
            ${bl_arg}

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            python: \$(python --version 2>&1 | sed 's/Python //')
            pandas: \$(python -c "import pandas; print(pandas.__version__)")
        END_VERSIONS
        """
}
