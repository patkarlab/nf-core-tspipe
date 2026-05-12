/*
 * subworkflows/local/flt3_itd.nf
 *
 * 4-tool FLT3-ITD ensemble. Replaces scripts/09_flt3_itd.py + 09b_flt3_consensus.py.
 *
 * Tools:
 *   1. FLT3_ITD_EXT (Docker container, BAM input)
 *   2. filt3r       (FASTQ input - FLT3-region only)
 *   3. getITD       (FASTQ input - FLT3-region only)
 *   4. Pindel       (BAM input - already ran in VARIANT_CALLING)
 *
 * Consensus rule (PASS_HIGH / PASS_LOW / REVIEW_REQUIRED) is implemented in
 * bin/flt3_consensus.py — moved verbatim from scripts/09b_flt3_consensus.py.
 *
 * NOTE on the original Python orchestrator's pain point: it depended on Docker
 * volume mounts using absolute paths (-v $PWD/...). In Nextflow each process
 * gets its own work dir with files staged in, so the "rm -rf then mv" hack in
 * step_getitd() is no longer needed — process isolation handles re-runs
 * naturally.
 */

include { BAM_TO_FLT3_FASTQ } from '../../modules/local/bam_to_flt3_fastq'
include { FLT3_ITD_EXT      } from '../../modules/local/flt3_itd_ext'
include { FILT3R            } from '../../modules/local/filt3r'
include { GETITD            } from '../../modules/local/getitd'
include { FLT3_CONSENSUS    } from '../../modules/local/flt3_consensus'

workflow FLT3_ITD {

    take:
        bam_ch         // [meta, bam, bai]
        pindel_vcf_ch  // [meta, vcf]

    main:
        // ----- Extract FLT3-region FASTQs from the BAM ------------------
        BAM_TO_FLT3_FASTQ(bam_ch)
        ch_flt3_fastqs = BAM_TO_FLT3_FASTQ.out.reads  // [meta, R1, R2]

        // ----- Run the four tools in parallel --------------------------
        FLT3_ITD_EXT(bam_ch)
        FILT3R(ch_flt3_fastqs)
        GETITD(ch_flt3_fastqs)

        // Join all four ITD-call outputs by sample
        ch_calls = FLT3_ITD_EXT.out.calls
            .join(FILT3R.out.calls)
            .join(GETITD.out.calls)
            .join(pindel_vcf_ch)

        FLT3_CONSENSUS(ch_calls)

    emit:
        consensus_tsv = FLT3_CONSENSUS.out.tsv
}
