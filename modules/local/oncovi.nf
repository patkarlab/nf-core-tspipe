/*
 * modules/local/oncovi.nf
 *
 * OncoVI oncogenicity scoring (Horak 2022 guidelines).
 *
 * TEMPORARY HOST-LOCAL EXECUTION (TODO: containerize):
 *   This module bypasses singularity and invokes the production script
 *   directly via the targeted-seq conda env. The OncoVI tool and its
 *   resources directory live at ${params.legacy_root}/software/oncovi/
 *   and would require bind-mounts to run in a container.
 *
 *   The two paths into the legacy production tree are parameterised via
 *   params.legacy_root and params.legacy_python_env. See nextflow.config
 *   for defaults and docs/INSTALL.md for the site-override workflow.
 */

process ONCOVI {
    tag        "${meta.id}"
    label      'process_medium'

    input:
        tuple val(meta), path(tsv)

    output:
        tuple val(meta), path("${meta.id}.oncovi.tsv"), emit: tsv
        path "versions.yml",                            emit: versions

    stub:
        """
        touch ${meta.id}.oncovi.tsv
        cat <<-END_VERSIONS > versions.yml
        "TSPIPE:ANNOTATION:ONCOVI":
            stub: true
        END_VERSIONS
        """

    script:
        """
        # Stage upstream VARIANT_VALIDATOR output under the production-expected
        # filename so 15_oncovi.py's path-derivation in main() resolves it.
        # The script prefers ${meta.id}.somaticseq.clinical.validated.tsv but
        # falls back to ${meta.id}.somaticseq.clinical.tsv with a warning.
        if [ ! -f "${meta.id}.somaticseq.clinical.validated.tsv" ]; then
            ln -sf ${tsv} ${meta.id}.somaticseq.clinical.validated.tsv
        fi

        ${params.legacy_python_env}/bin/python \\
            ${projectDir}/bin/oncovi.py \\
            --sample ${meta.id} \\
            --outdir . \\
            --oncovi-dir ${params.oncovi_dir}

        # Rename to match the channel emit declared in this module
        if [ -f "${meta.id}.somaticseq.clinical.final.tsv" ]; then
            mv ${meta.id}.somaticseq.clinical.final.tsv ${meta.id}.oncovi.tsv
        else
            echo "ERROR: oncovi.py did not produce expected output" >&2
            ls -la >&2
            exit 1
        fi

        cat <<-END_VERSIONS > versions.yml
        "TSPIPE:ANNOTATION:ONCOVI":
            python: \$(${params.legacy_python_env}/bin/python --version 2>&1 | sed 's/Python //')
        END_VERSIONS
        """
}
