/*
 * subworkflows/local/bpt_stratum.nf
 *
 * One stratum of the Twist myeloid PoN: pooled CNVkit reference (no -y;
 * params.male_reference retired for this panel), GATK read-count PoN, and
 * per-stratum leave-one-out QC.
 *
 * Instantiated once per stratum via aliased includes in
 * workflows/build_pon_twist.nf (STRATUM_MALE / STRATUM_FEMALE), so process
 * fully-qualified names stay distinct while the BPT_* simple names keep
 * matching the conf/modules.config umbrella selector.
 */

include { BPT_CNVKIT_REFERENCE   } from '../../modules/local/bpt_cnvkit_reference'
include { BPT_GATK_CREATE_RC_PON } from '../../modules/local/bpt_gatk_create_rc_pon'
include { BPT_CNV_LOO_QC         } from '../../modules/local/bpt_cnv_loo_qc'

workflow BPT_STRATUM {

    take:
        stratum        // 'male' | 'female'
        cov_files      // collected list: per-sample *.targetcoverage.cnn + *.antitargetcoverage.cnn
        count_files    // collected list: per-sample *.counts.hdf5
        bed            // panel.combined.filtered.bed (value channel)
        fasta          // reference fasta (value channel)
        fai            // reference .fai (value channel)
        annotated      // AnnotateIntervals GC table (value channel; consumed only if params.pon_gc_correction)

    main:
        BPT_CNVKIT_REFERENCE( stratum, cov_files, fasta, fai )
        BPT_GATK_CREATE_RC_PON( stratum, count_files, annotated )
        BPT_CNV_LOO_QC( stratum, cov_files, bed )

    emit:
        cnvkit_ref  = BPT_CNVKIT_REFERENCE.out.ref
        rc_pon      = BPT_GATK_CREATE_RC_PON.out.pon
        loo_summary = BPT_CNV_LOO_QC.out.summary
        noisy_bins  = BPT_CNV_LOO_QC.out.noisy_bins
}
