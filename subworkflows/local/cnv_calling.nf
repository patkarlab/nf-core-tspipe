/*
 * subworkflows/local/cnv_calling.nf
 *
 * nf-core CNV wiring v1 (apply_nfcore_cnv_wiring_part1)
 *
 * Per-sample CNV pipeline.
 *
 * Replaces:
 *   scripts/12_cnv_calling.py          (bin/cnvkit.py, see part 2)
 *   scripts/12b_cnv_plots.py           (bin/cnv_plots.py)
 *   scripts/12d_zscore_cnv.py          (bin/zscore_cnv.py)
 *   scripts/12e_cnv_concordance.py     (bin/cnv_concordance.py)
 *   scripts/12f_cnv_clinical_report.py (bin/cnv_clinical_report.py)
 *   scripts/18_cnv_annotate.py         (bin/cnv_annotate.py)
 *
 * scripts/12g_exon_cnv.py is intentionally not part of this DAG. Partial
 * gene events (KMT2A-PTD, IKZF1 Ik6, focal CDKN2A/CDKN2B) are surfaced via
 * the combined per-chromosome scatter plots produced by CNV_PLOTS for
 * human review. cnv_concordance.py and cnv_clinical_report.py both treat
 * exon input as optional (argparse default=None), so dropping EXON_CNV
 * requires no bin/ script changes.
 *
 * The dropped training-time scripts (12c_build_sex_pon, 12c_cnv_loo_qc,
 * 12d_cn_mops, 12d_panelcn_mops, 12d_ifcnv*) feed BUILD_PON, not the
 * per-sample DAG.
 */

include { CNVKIT               } from '../../modules/local/cnvkit'
include { ZSCORE_CNV           } from '../../modules/local/zscore_cnv'
include { CNV_PLOTS            } from '../../modules/local/cnv_plots'
include { CNV_CONCORDANCE      } from '../../modules/local/cnv_concordance'
include { CNV_CLINICAL_REPORT  } from '../../modules/local/cnv_clinical_report'
include { CNV_ANNOTATE         } from '../../modules/local/cnv_annotate'

workflow CNV_CALLING {

    take:
        bam_ch              // [meta, bam, bai]
        reference_ch        // value [fasta, fai, dict]
        bed_ch              // value path (panel BED)
        pon_male_ch         // value path (cnvkit_pon_male.cnn)
        pon_female_ch       // value path (cnvkit_pon_female.cnn)
        loo_summary_ch      // value path (cnvkit_loo_summary.tsv)
        noisy_bins_ch       // value path (cnvkit_noisy_bins.bed)
        noise_profile_ch    // value path (loo_bin_noise_profile.tsv)
        cytoband_ch         // value path (cytoBand_hg38.txt)
        clingen_ch          // value path (ClinGen_gene_curation_list_GRCh38.tsv)
        scatter_regions_ch  // value path (cnv_scatter_regions.txt)

    main:

        // ----- 1. CNVKit batch + call + genemetrics + annotate -----------
        CNVKIT(
            bam_ch,
            reference_ch,
            bed_ch,
            pon_male_ch,
            pon_female_ch,
            noisy_bins_ch,
            loo_summary_ch,
        )

        // ----- 2. Z-score caller (consumes CNVKit .cnr) ------------------
        ZSCORE_CNV(
            CNVKIT.out.cnr,
            noise_profile_ch,
            loo_summary_ch,
        )

        // ----- 3. Diagnostic plots ---------------------------------------
        // 12b consumes .cnr, .cns, .call.cns, annotated genemetrics, plus
        // BED, cytoband, LOO summary, and the chr-gene scatter regions.
        ch_plots_in = CNVKIT.out.cnr
            .join(CNVKIT.out.cns,          by: 0)
            .join(CNVKIT.out.call_cns,     by: 0)
            .join(CNVKIT.out.genemetrics,  by: 0)
        CNV_PLOTS(
            ch_plots_in,
            bed_ch,
            cytoband_ch,
            loo_summary_ch,
            scatter_regions_ch,
        )

        // ----- 4. Two-caller concordance (CNVKit + Z-score) --------------
        ch_concordance_in = CNVKIT.out.genemetrics
            .join(ZSCORE_CNV.out.zscore_genes, by: 0)
        CNV_CONCORDANCE(ch_concordance_in)

        // ----- 5. Clinical tiered report ---------------------------------
        ch_clinical_in = CNV_CONCORDANCE.out.tsv
            .join(CNVKIT.out.call_cns,         by: 0)
            .join(ZSCORE_CNV.out.zscore_genes, by: 0)
            .join(CNVKIT.out.genemetrics,      by: 0)
        CNV_CLINICAL_REPORT(ch_clinical_in)

        // ----- 6. Clinical annotation (cytoband + ClinGen + heme) --------
        CNV_ANNOTATE(
            CNV_CONCORDANCE.out.tsv,
            loo_summary_ch,
            cytoband_ch,
            clingen_ch,
            bed_ch,
        )

    emit:
        cnvkit_calls       = CNVKIT.out.call_cns
        zscore_calls       = ZSCORE_CNV.out.zscore_genes
        concordance        = CNV_CONCORDANCE.out.tsv
        clinical_report    = CNV_CLINICAL_REPORT.out.tsv
        annotated          = CNV_ANNOTATE.out.tsv
        plots_dir          = CNV_PLOTS.out.plots_dir
        plot_pdfs          = CNV_PLOTS.out.pdfs
        cnvkit_diagram_pdf = CNV_PLOTS.out.diagram_pdf
        cnvkit_scatter_png = CNV_PLOTS.out.scatter_png
}
