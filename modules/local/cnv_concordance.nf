/*
 * modules/local/cnv_concordance.nf
 *
 * CNV concordance merge
 *
 * Note: Merge calls from multiple CNV callers. See scripts/12e_cnv_concordance.py.
 *
 * TODO: this is a stub. Fill in the script: block with the actual command line.
 * The original Python wrapper in scripts/ shows the exact invocation -- this
 * module just needs to translate that to a Nextflow process body.
 */

process CNV_CONCORDANCE {
    tag        "${meta.id}"
    label      'process_medium'

    input:
        tuple val(meta), path(cnvkit_calls), path(exon_calls), path(zscore_calls)

    output:
        tuple val(meta), path("${meta.id}_cnv_concordance.tsv"), emit: tsv

    script:
        """
        # TODO: replace this stub with the tool invocation from the source script.
        echo "STUB: CNV_CONCORDANCE for ${meta.id}" >&2
        # Touch output filename(s) so downstream channels don't break during DAG validation:
        touch ${meta.id}_cnv_concordance.tsv
        """
}
