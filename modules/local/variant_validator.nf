/*
 * modules/local/variant_validator.nf
 *
 * VariantValidator HGVS validation.
 *
 * TEMPORARY HOST-LOCAL EXECUTION (TODO: containerize):
 *   This module bypasses singularity and invokes the production script
 *   directly via the targeted-seq conda env. The VariantValidator REST
 *   service runs on the gandalf host at localhost:5001, which is only
 *   reachable from host-local processes. Containerizing requires either
 *   --net=host (docker) or running the REST service inside the same
 *   singularity instance (out of scope today).
 *
 *   See conf/modules.config (executor block) and the production script
 *   at /home/hemat/targeted-seq-pipeline/scripts/17_variant_validator.py.
 */

process VARIANT_VALIDATOR {
    tag        "${meta.id}"
    label      'process_medium'

    input:
        tuple val(meta), path(tsv)

    output:
        tuple val(meta), path("${meta.id}.validated.tsv"), emit: tsv
        path "versions.yml",                               emit: versions

    stub:
        // nf-core stub blocks v2 (port-aware: real script writes
        // ${meta.id}.somaticseq.clinical.validated.tsv which is renamed
        // to ${meta.id}.validated.tsv to match the emit).
        """
        touch ${meta.id}.validated.tsv
        cat <<-END_VERSIONS > versions.yml
        "TSPIPE:ANNOTATION:VARIANT_VALIDATOR":
            stub: true
        END_VERSIONS
        """

    script:
        """
        # Stage input under the production-expected name so the script's
        # default --input resolution (if relied upon) works. We also pass
        # --input explicitly so this is belt-and-braces.
        if [ ! -f "${meta.id}.somaticseq.clinical.tsv" ]; then
            ln -sf ${tsv} ${meta.id}.somaticseq.clinical.tsv
        fi

        /home/hemat/anaconda3/envs/targeted-seq/bin/python \
            /home/hemat/targeted-seq-pipeline/scripts/17_variant_validator.py \
            --sample ${meta.id} \
            --input ${meta.id}.somaticseq.clinical.tsv \
            --outdir . \
            --vv-url http://localhost:5001 \
            --threads 1 \
            --timeout 120

        # Rename to match the channel emit declared in this module
        if [ -f "${meta.id}.somaticseq.clinical.validated.tsv" ]; then
            mv ${meta.id}.somaticseq.clinical.validated.tsv ${meta.id}.validated.tsv
        else
            echo "ERROR: variant_validator.py did not produce expected output" >&2
            ls -la >&2
            exit 1
        fi

        cat <<-END_VERSIONS > versions.yml
        "TSPIPE:ANNOTATION:VARIANT_VALIDATOR":
            python: \$(/home/hemat/anaconda3/envs/targeted-seq/bin/python --version 2>&1 | sed 's/Python //')
            vv_url: http://localhost:5001
        END_VERSIONS
        """
}
