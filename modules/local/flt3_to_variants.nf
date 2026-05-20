/*
 * modules/local/flt3_to_variants.nf
 *
 * Merge FLT3 consensus ITDs into the per-sample clinical variant TSV.
 *
 * TEMPORARY HOST-LOCAL EXECUTION (TODO: containerize):
 *   This module follows the same pattern as VARIANT_VALIDATOR and ONCOVI.
 *   The 17b script is pure stdlib (no pandas) so containerizing it would
 *   actually be easy, but we keep all three stub-replacements consistent
 *   for now -- the only barrier to lifting is testing in a container.
 *
 *   The two paths into the legacy production tree are parameterised via
 *   params.legacy_root and params.legacy_python_env. See nextflow.config
 *   for defaults and docs/INSTALL.md for the site-override workflow.
 */

process FLT3_TO_VARIANTS {
    tag        "${meta.id}"
    label      'process_low'

    input:
        tuple val(meta), path(clinical_tsv), path(flt3_consensus_tsv)

    output:
        tuple val(meta), path("${meta.id}.final.tsv"), emit: tsv
        path "versions.yml",                           emit: versions

    stub:
        """
        touch ${meta.id}.final.tsv
        cat <<-END_VERSIONS > versions.yml
        "TSPIPE:ANNOTATION:FLT3_TO_VARIANTS":
            stub: true
        END_VERSIONS
        """

    script:
        """
        # The production script reads consensus from <sample-dir>/flt3/
        # so synthesize that layout from the staged consensus TSV.
        mkdir -p flt3
        ln -sf ${flt3_consensus_tsv} flt3/${meta.id}_flt3_consensus.tsv

        ${params.legacy_python_env}/bin/python \\
            ${params.legacy_root}/scripts/17b_flt3_to_variants.py \\
            --sample-dir . \\
            --sample ${meta.id} \\
            --variant-tsv ${clinical_tsv}

        # The production script writes <variant_tsv stem>.with_flt3.tsv.
        # Find it and rename to match our emit declaration.
        STEM=\$(basename ${clinical_tsv} .tsv)
        if [ -f "\${STEM}.with_flt3.tsv" ]; then
            mv "\${STEM}.with_flt3.tsv" ${meta.id}.final.tsv
        else
            echo "ERROR: flt3_to_variants.py did not produce expected output" >&2
            ls -la >&2
            exit 1
        fi

        cat <<-END_VERSIONS > versions.yml
        "TSPIPE:ANNOTATION:FLT3_TO_VARIANTS":
            python: \$(${params.legacy_python_env}/bin/python --version 2>&1 | sed 's/Python //')
        END_VERSIONS
        """
}
