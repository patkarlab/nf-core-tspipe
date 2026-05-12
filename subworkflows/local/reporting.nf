/*
 * subworkflows/local/reporting.nf
 *
 * Replaces scripts/16_igv_reports.py + 20_organize_output.py.
 */

include { IGV_REPORTS     } from '../../modules/local/igv_reports'
include { ORGANIZE_OUTPUT } from '../../modules/local/organize_output'

workflow REPORTING {

    take:
        clinical_tsv_ch    // [meta, tsv]
        bam_ch             // [meta, bam, bai]
        cnv_report_ch
        sv_annotated_ch
        flt3_consensus_ch

    main:
        // IGV reports need both the clinical TSV and the BAM.
        ch_igv_in = clinical_tsv_ch.join(bam_ch)
        IGV_REPORTS(ch_igv_in)

        // Final output organizer bundles per-sample deliverables.
        ch_organize_in = clinical_tsv_ch
            .join(cnv_report_ch)
            .join(sv_annotated_ch)
            .join(flt3_consensus_ch)
            .join(IGV_REPORTS.out.html)
        ORGANIZE_OUTPUT(ch_organize_in)
}
