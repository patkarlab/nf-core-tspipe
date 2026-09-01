/*
 * subworkflows/local/gatk_cnv_calling.nf
 *
 * GATK somatic CNV path (TGC_V1) + allele-specific track (BAF_V1) for
 * the twist_myeloid panel.
 *
 * Per sample: CollectReadCounts -> DenoiseReadCounts vs the sex-matched
 * read-count PoN; CollectAllelicCounts over the panel BAF SNP catalog;
 * ModelSegments jointly on denoised copy ratios + allelic counts
 * (tumor-only) -> CallCopyRatioSegments -> gene projection; and the
 * CNV_BAF_CNLOH detector classifying 17p allelic state against the
 * male-cohort background.
 *
 * Gating and version parity: see conf/twist_apply.config (host env for
 * GATK 4.6.2.0 / cnvkit 0.9.12 parity; legacy panels never reach this
 * subworkflow).
 */

include { GATK_CNV_COLLECT_COUNTS  } from '../../modules/local/gatk_cnv_collect_counts'
include { GATK_CNV_COLLECT_ALLELIC } from '../../modules/local/gatk_cnv_collect_allelic'
include { GATK_CNV_DENOISE         } from '../../modules/local/gatk_cnv_denoise'
include { GATK_CNV_MODEL_SEGMENTS  } from '../../modules/local/gatk_cnv_model_segments'
include { GATK_CNV_CALL_SEGMENTS   } from '../../modules/local/gatk_cnv_call_segments'
include { GATK_CNV_GENE_PROJECT    } from '../../modules/local/gatk_cnv_gene_project'
include { CNV_BAF_CNLOH            } from '../../modules/local/cnv_baf_cnloh'

workflow GATK_CNV_CALLING {

    take:
        bam_ch          // [meta, bam, bai]
        reference_ch    // value [fasta, fai, dict]
        interval_list   // value path (targets.preprocessed.interval_list)
        rc_pon          // value path (gatk_rc_pon_<stratum>.hdf5)
        exonwise_bed    // value path (panel exonwise BED)
        baf_snp_bed     // value path (snp_sites.baf.bed)
        baf_background  // value path (baf_background.tsv)

    main:
        GATK_CNV_COLLECT_COUNTS( bam_ch, reference_ch, interval_list )
        GATK_CNV_COLLECT_ALLELIC( bam_ch, reference_ch, baf_snp_bed )
        GATK_CNV_DENOISE( GATK_CNV_COLLECT_COUNTS.out.counts, rc_pon )

        ch_model_in = GATK_CNV_DENOISE.out.denoised
            .join( GATK_CNV_COLLECT_ALLELIC.out.allelic, by: 0 )
        GATK_CNV_MODEL_SEGMENTS( ch_model_in )
        GATK_CNV_CALL_SEGMENTS( GATK_CNV_MODEL_SEGMENTS.out.cr_seg )

        ch_project_in = GATK_CNV_CALL_SEGMENTS.out.called
            .join( GATK_CNV_DENOISE.out.denoised, by: 0 )
        GATK_CNV_GENE_PROJECT( ch_project_in, exonwise_bed )

        ch_baf_in = GATK_CNV_COLLECT_ALLELIC.out.allelic
            .join( GATK_CNV_DENOISE.out.denoised, by: 0 )
        CNV_BAF_CNLOH( ch_baf_in, baf_snp_bed, baf_background )

    emit:
        counts      = GATK_CNV_COLLECT_COUNTS.out.counts
        allelic     = GATK_CNV_COLLECT_ALLELIC.out.allelic
        denoised    = GATK_CNV_DENOISE.out.denoised
        cr_seg      = GATK_CNV_MODEL_SEGMENTS.out.cr_seg
        model_final = GATK_CNV_MODEL_SEGMENTS.out.model_final
        hets        = GATK_CNV_MODEL_SEGMENTS.out.hets
        called      = GATK_CNV_CALL_SEGMENTS.out.called
        genes       = GATK_CNV_GENE_PROJECT.out.genes
        plot        = GATK_CNV_GENE_PROJECT.out.plot
        baf_summary = CNV_BAF_CNLOH.out.summary
        baf_sites   = CNV_BAF_CNLOH.out.sites
        baf_plot    = CNV_BAF_CNLOH.out.plot
}
