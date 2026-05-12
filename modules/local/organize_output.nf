/*
 * modules/local/organize_output.nf
 *
 * Output organizer
 *
 * Note: Bundle deliverables into a per-sample folder with FLT3 section + variant TSV fallback. See scripts/20_organize_output.py.
 *
 * TODO: this is a stub. Fill in the script: block with the actual command line.
 * The original Python wrapper in scripts/ shows the exact invocation -- this
 * module just needs to translate that to a Nextflow process body.
 */

process ORGANIZE_OUTPUT {
    tag        "${meta.id}"
    label      'process_medium'

    input:
        tuple val(meta), path(clinical_tsv), path(cnv_report), path(sv_annotated), path(flt3_consensus), path(igv_html)

    output:
        path "deliverables/*", emit: bundle

    script:
        """
        # TODO: replace this stub with the tool invocation from the source script.
        echo "STUB: ORGANIZE_OUTPUT for ${meta.id}" >&2
        # Touch output filename(s) so downstream channels don't break during DAG validation:
        mkdir -p deliverables && touch deliverables/*
        """
}
