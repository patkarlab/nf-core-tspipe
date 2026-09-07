/*
 * subworkflows/local/cnv_calling.nf  (CNV_CALLING_V2, MARKER CNV_RETIRE_7B)
 *
 * Per-sample CNVkit arm (K) of the multi-arm consensus. The legacy chain that
 * once hung off it (ZSCORE_CNV, CNV_PLOTS, CNV_CONCORDANCE, CNV_CLINICAL_REPORT,
 * CNV_ANNOTATE) was retired on 2026-09-07 (handoff item 7b): the consensus,
 * exon plots, chromosome pages, reconCNV and the dashboard CNV tab read the
 * CNVkit outputs emitted here and the other arms directly.
 *
 * Sex-stratified reference selection happens inside CNVKIT from meta.sex
 * (SEXSTRAT_V1; params.cnv_sex_fallback for anything else).
 */

include { CNVKIT } from '../../modules/local/cnvkit'

workflow CNV_CALLING {

    take:
        bam_ch                 // [meta, bam, bai]
        reference_ch           // value [fasta, fai, dict]
        bed_ch                 // value path (panel BED)
        pon_male_ch            // value path (cnvkit_pon_male.cnn)
        pon_female_ch          // value path (cnvkit_pon_female.cnn)
        loo_summary_ch         // value path (cnvkit_loo_summary.tsv)
        noisy_bins_ch          // value path (cnvkit_noisy_bins.bed)
        loo_summary_female_ch  // SEXSTRAT_V1 value path (cnvkit_loo_summary_female.tsv, or the male file)
        noisy_bins_female_ch   // SEXSTRAT_V1 value path (cnvkit_noisy_bins_female.bed, or the male file)

    main:
        CNVKIT(
            bam_ch,
            reference_ch,
            bed_ch,
            pon_male_ch,
            pon_female_ch,
            noisy_bins_ch,
            loo_summary_ch,
            noisy_bins_female_ch,   // SEXSTRAT_V1
            loo_summary_female_ch,  // SEXSTRAT_V1
        )

    emit:
        cnvkit_calls       = CNVKIT.out.call_cns
        cnvkit_cnr         = CNVKIT.out.cnr
        cnvkit_cns         = CNVKIT.out.cns
        cnvkit_genemetrics = CNVKIT.out.genemetrics
}
