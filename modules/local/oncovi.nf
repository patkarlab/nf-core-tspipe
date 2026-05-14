/*
 * modules/local/oncovi.nf
 *
 * OncoVI oncogenicity scoring
 *
 * Note: OncoVI scoring per Horak 2022 guidelines. See scripts/15_oncovi.py.
 *
 * TODO: this is a stub. Fill in the script: block with the actual command line.
 * The original Python wrapper in scripts/ shows the exact invocation -- this
 * module just needs to translate that to a Nextflow process body.
 */

process ONCOVI {
    tag        "${meta.id}"
    label      'process_medium'

    input:
        tuple val(meta), path(tsv)

    output:
        tuple val(meta), path("${meta.id}.oncovi.tsv"), emit: tsv
    stub:
        // nf-core stub blocks v1 (apply_nfcore_add_stub_blocks)
        """
        touch ${meta.id}.oncovi.tsv
        """


    script:
        """
        # TODO: replace this stub with the tool invocation from the source script.
        echo "STUB: ONCOVI for ${meta.id}" >&2
        # Touch output filename(s) so downstream channels don't break during DAG validation:
        touch ${meta.id}.oncovi.tsv
        """
}
