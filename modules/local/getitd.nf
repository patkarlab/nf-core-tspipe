/*
 * modules/local/getitd.nf
 *
 * getITD (Blaette et al., Leukemia 2019) FLT3-ITD detection via local
 * Python install packaged in `local/getitd:v0.1`. Mirrors production
 * scripts/09_flt3_itd.py step 3.
 *
 * Container layout (built from /tmp/getitd_docker_build):
 *   /opt/getitd/getitd.py
 *   /opt/getitd/anno/amplicon.txt          (WT amplicon reference)
 *   /opt/getitd/anno/amplicon_kayser.tsv   (chr13/transcript/protein anno)
 *
 * getITD's default -reference and -anno are relative paths (./anno/...).
 * Nextflow's CWD inside the container is the work directory, NOT
 * /opt/getitd, so we pass both flags with absolute paths -- otherwise
 * getITD looks for ./anno/ in the work dir and fails.
 *
 * -min_bqs 20 mirrors production: getITD's default of 30 is too strict
 * for BAMs that have been through BWA + BQSR + ABRA2, whose BQS values
 * are typically rescaled into the low-to-mid 20s.
 *
 * getITD writes its outputs into <sample>_getitd/ in CWD. The canonical
 * high-confidence TSV is itds_collapsed-is-same_is-similar_is-close_is-same_trailing_hc.tsv
 * and is only created when at least one ITD is found. We rename a copy
 * to ${meta.id}_getitd_hc.tsv for the consensus step; for FLT3-ITD
 * negative samples we emit a header-only TSV so the consensus parser
 * has a valid schema to read.
 */

process GETITD {
    tag        "${meta.id}"
    label      'process_low'
    label      'error_ignore'   // soft-fail per production orchestrator semantics

    container  'local/getitd:v0.1'

    input:
        tuple val(meta), path(r1), path(r2)

    output:
        tuple val(meta), path("${meta.id}_getitd_hc.tsv"), emit: hc_tsv
        tuple val(meta), path("${meta.id}_getitd/"),       emit: audit_dir, optional: true

    stub:
        // nf-core stub blocks v1 (apply_nfcore_add_stub_blocks)
        """
        mkdir -p ${meta.id}_getitd
        touch ${meta.id}_getitd/stub.txt
        touch ${meta.id}_getitd_hc.tsv
        """

    script:
        // Header for the negative-sample fallback TSV. 25 columns,
        // tab-separated, copied verbatim from a known-good production
        // run on 25NGS1307. Must stay in sync with the local getITD
        // install -- if getITD's output schema ever changes, this
        // string and bin/flt3_consensus.py both need updating.
        def hc_header = [
            'sample', 'length', 'start', 'vaf', 'ar', 'coverage', 'counts',
            'trailing', 'seq', 'sense', 'external_bp', 'domains',
            'start_chr13_bp', 'start_transcript_bp', 'start_protein_as',
            'end_chr13_bp', 'end_transcript_bp', 'end_protein_as',
            'insertion_site_chr13_bp', 'insertion_site_transcript_bp',
            'insertion_site_protein_as', 'insertion_site_domain',
            'file', 'counts_unique_each', 'counts_unique_total',
        ].join('\t')

        """
        # Run getITD. The two -reference / -anno absolute paths point
        # inside the container; the FASTQs are staged into CWD by Nextflow.
        python /opt/getitd/getitd.py \\
            -reference /opt/getitd/anno/amplicon.txt \\
            -anno      /opt/getitd/anno/amplicon_kayser.tsv \\
            -nkern     ${task.cpus} \\
            -min_bqs   20 \\
            ${meta.id} ${r1} ${r2}

        # Locate the canonical high-confidence TSV (renamed for downstream
        # consumption). If getITD found no ITDs the file does not exist,
        # so write a schema-valid header-only TSV in its place.
        hc_tsv="${meta.id}_getitd/itds_collapsed-is-same_is-similar_is-close_is-same_trailing_hc.tsv"
        if [ -s "\${hc_tsv}" ]; then
            cp "\${hc_tsv}" ${meta.id}_getitd_hc.tsv
        else
            printf '%s\\n' '${hc_header}' > ${meta.id}_getitd_hc.tsv
        fi
        """
}
