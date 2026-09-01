/*
 * subworkflows/local/gatk_cnv_calling.nf
 *
 * GATK somatic copy-ratio CNV path (TGC_V1) -- caller 3 for the
 * twist_myeloid panel, running alongside CNVkit + Z-score.
 *
 * Per sample: CollectReadCounts (HDF5, same intervals/merging rule the
 * PoN was built with) -> DenoiseReadCounts against the sex-matched
 * read-count PoN -> ModelSegments (copy ratios only in v1; allelic
 * counts join with the BAF caller) -> CallCopyRatioSegments -> gene
 * projection onto the panel's exonwise intervals plus a matplotlib
 * genome plot (the GATK R plotters need optparse/data.table, absent on
 * the host env; deliberately not used).
 *
 * Gating: invoked from workflows/tspipe.nf only when params.cnv_gatk_pon
 * is defined (conf/twist_apply.config). Legacy panels never reach this
 * subworkflow. Version parity: the PoN was built with GATK 4.6.2.0 from
 * the host conda env; the twist_apply.config umbrella runs every
 * GATK_CNV_* process on that env.
 */

include { GATK_CNV_COLLECT_COUNTS } from '../../modules/local/gatk_cnv_collect_counts'
include { GATK_CNV_DENOISE        } from '../../modules/local/gatk_cnv_denoise'
include { GATK_CNV_MODEL_SEGMENTS } from '../../modules/local/gatk_cnv_model_segments'
include { GATK_CNV_CALL_SEGMENTS  } from '../../modules/local/gatk_cnv_call_segments'
include { GATK_CNV_GENE_PROJECT   } from '../../modules/local/gatk_cnv_gene_project'

workflow GATK_CNV_CALLING {

    take:
        bam_ch          // [meta, bam, bai]
        reference_ch    // value [fasta, fai, dict]
        interval_list   // value path (targets.preprocessed.interval_list; PoN-matched)
        rc_pon          // value path (gatk_rc_pon_<stratum>.hdf5)
        exonwise_bed    // value path (panel exonwise BED for gene projection)

    main:
        GATK_CNV_COLLECT_COUNTS( bam_ch, reference_ch, interval_list )
        GATK_CNV_DENOISE( GATK_CNV_COLLECT_COUNTS.out.counts, rc_pon )
        GATK_CNV_MODEL_SEGMENTS( GATK_CNV_DENOISE.out.denoised )
        GATK_CNV_CALL_SEGMENTS( GATK_CNV_MODEL_SEGMENTS.out.cr_seg )

        ch_project_in = GATK_CNV_CALL_SEGMENTS.out.called
            .join( GATK_CNV_DENOISE.out.denoised, by: 0 )
        GATK_CNV_GENE_PROJECT( ch_project_in, exonwise_bed )

    emit:
        counts      = GATK_CNV_COLLECT_COUNTS.out.counts
        denoised    = GATK_CNV_DENOISE.out.denoised
        cr_seg      = GATK_CNV_MODEL_SEGMENTS.out.cr_seg
        model_final = GATK_CNV_MODEL_SEGMENTS.out.model_final
        called      = GATK_CNV_CALL_SEGMENTS.out.called
        genes       = GATK_CNV_GENE_PROJECT.out.genes
        plot        = GATK_CNV_GENE_PROJECT.out.plot
}
