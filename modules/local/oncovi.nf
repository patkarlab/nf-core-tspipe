/*
 * modules/local/oncovi.nf
 *
 * OncoVI oncogenicity scoring (Horak 2022 guidelines).
 *
 * TEMPORARY HOST-LOCAL EXECUTION (TODO: containerize):
 *   This module bypasses singularity and invokes the production script
 *   directly via the targeted-seq conda env. The OncoVI tool and its
 *   resources directory live at /home/hemat/targeted-seq-pipeline/software/oncovi/
 *   and would require bind-mounts to run in a container.
 *
 *   See conf/modules.config (executor block) and the production scripts
 *   at /home/hemat/targeted-seq-pipeline/scripts/15_oncovi.py and
 *   /home/hemat/targeted-seq-pipeline/software/oncovi/src/03_OncoVI_SOP.py.
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

        /home/hemat/anaconda3/envs/targeted-seq/bin/python \
            /home/hemat/targeted-seq-pipeline/scripts/15_oncovi.py \
            --sample ${meta.id} \
            --outdir .

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
            python: \$(/home/hemat/anaconda3/envs/targeted-seq/bin/python --version 2>&1 | sed 's/Python //')
        END_VERSIONS
        """
}
