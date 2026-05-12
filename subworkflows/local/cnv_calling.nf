/*
 * subworkflows/local/cnv_calling.nf
 *
 * Replaces scripts/12_cnv_calling.py + 12b/12d/12e/12f/12g.
 *
 * Note: the dropped scripts (12c_build_sex_pon, 12c_cnv_loo_qc, 12d_cn_mops,
 * 12d_panelcn_mops, 12d_ifcnv*) are training-time / alternative-caller code
 * that never makes it into the per-sample DAG. They live in assets/training/
 * and are not part of this workflow.
 */

include { CNVKIT               } from '../../modules/local/cnvkit'
include { EXON_CNV             } from '../../modules/local/exon_cnv'
include { ZSCORE_CNV           } from '../../modules/local/zscore_cnv'
include { CNV_PLOTS            } from '../../modules/local/cnv_plots'
include { CNV_CONCORDANCE      } from '../../modules/local/cnv_concordance'
include { CNV_CLINICAL_REPORT  } from '../../modules/local/cnv_clinical_report'
include { CNV_ANNOTATE         } from '../../modules/local/cnv_annotate'

workflow CNV_CALLING {

    take:
        bam_ch        // [meta, bam, bai]
        reference_ch
        bed_ch

    main:
        CNVKIT(bam_ch, reference_ch, bed_ch)
        EXON_CNV(bam_ch, reference_ch, bed_ch)
        ZSCORE_CNV(bam_ch, bed_ch)

        // Join all three CNV outputs per sample
        ch_cnv_outputs = CNVKIT.out.calls
            .join(EXON_CNV.out.calls)
            .join(ZSCORE_CNV.out.calls)

        CNV_CONCORDANCE(ch_cnv_outputs)
        CNV_PLOTS(CNVKIT.out.cnr)
        CNV_CLINICAL_REPORT(CNV_CONCORDANCE.out.tsv)
        CNV_ANNOTATE(CNV_CONCORDANCE.out.tsv)

    emit:
        cnvkit_calls    = CNVKIT.out.calls
        clinical_report = CNV_CLINICAL_REPORT.out.tsv
        annotated       = CNV_ANNOTATE.out.tsv
}
