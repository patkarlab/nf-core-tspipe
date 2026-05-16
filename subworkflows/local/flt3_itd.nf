//
// FLT3-ITD detection subworkflow.
//
// Takes a per-sample post-ABRA2 BAM and produces a 3-caller consensus
// TSV per sample. The three callers (FLT3_ITD_EXT, getITD, filt3r) run
// in parallel; the consensus step joins their outputs by meta key with
// full-outer-join semantics (.join with remainder: true) so a single-
// caller soft failure degrades the call to PASS_LOW / REVIEW_REQUIRED
// rather than silently dropping the sample.
//
// Caller fallbacks: each caller process carries label 'error_ignore'.
// When a caller soft-fails, its emit channel produces nothing for that
// sample, and the join's remainder=true leaves a null in that slot.
// The .map step substitutes a header-only placeholder file from
// assets/flt3/ so the consensus script always receives three real
// paths and parses "zero records from this caller" cleanly.
//
// Inputs:
//   ch_bam : tuple val(meta), path(bam), path(bai)
//            BAM is the post-ABRA2 locally-realigned final BAM, named
//            ${meta.id}.final.bam per upstream convention.
//
// Outputs:
//   consensus_tsv : tuple val(meta), path("${meta.id}_flt3_consensus.tsv")
//

include { BAM_TO_FLT3_FASTQ } from '../../modules/local/bam_to_flt3_fastq'
include { FLT3_ITD_EXT      } from '../../modules/local/flt3_itd_ext'
include { GETITD            } from '../../modules/local/getitd'
include { FILT3R            } from '../../modules/local/filt3r'
include { FLT3_CONSENSUS    } from '../../modules/local/flt3_consensus'


workflow FLT3_ITD {
    take:
        ch_bam   // tuple val(meta), path(bam), path(bai)

    main:
        // FLT3_ITD_EXT operates on the BAM directly (soft-clip realignment).
        FLT3_ITD_EXT(ch_bam)

        // BAM_TO_FLT3_FASTQ extracts FLT3-region paired FASTQs; getITD and
        // filt3r both consume those FASTQs for k-mer / assembly-based ITD
        // detection. Reusing one extraction step across both callers
        // avoids samtools-view'ing the same region twice.
        BAM_TO_FLT3_FASTQ(ch_bam)
        GETITD(BAM_TO_FLT3_FASTQ.out.reads)
        FILT3R(BAM_TO_FLT3_FASTQ.out.reads)

        // Join the three caller outputs by meta key with full-outer-join
        // semantics. Missing slots (caller soft-failed for this sample)
        // fall back to header-only placeholder files. The consensus
        // script reads zero records from those, routing the call to
        // PASS_LOW or REVIEW_REQUIRED based on how many real callers
        // survived.
        //
        // CRITICAL: the three caller emits MUST arrive joined by meta
        // before FLT3_CONSENSUS is invoked. Declaring three separate
        // inputs on FLT3_CONSENSUS would let Nextflow pair positionally,
        // which is the cross-sample mispairing bug shape that broke
        // SomaticSeq before commit 3bf7eb4.
        // Driver channel: ch_bam has every sample by construction. Starting
        // the join chain from ch_bam (rather than from one of the caller
        // emits) guarantees that every sample produces exactly one
        // 4-element tuple even when multiple callers soft-fail for the
        // same sample. .join(remainder: true) only fills nulls when at
        // least one side has the key; using ch_bam as the always-present
        // left side ensures that condition holds.
        ch_for_consensus = ch_bam
            .map { meta, bam, bai -> [meta] }
            .join(GETITD.out.hc_tsv,    by: 0, remainder: true)
            .join(FLT3_ITD_EXT.out.vcf, by: 0, remainder: true)
            .join(FILT3R.out.vcf,       by: 0, remainder: true)
            .map { meta, getitd, flt3_ext, filt3r ->
                tuple(
                    meta,
                    getitd   ?: file("${projectDir}/assets/flt3/empty_getitd_hc.tsv",
                                     checkIfExists: true),
                    flt3_ext ?: file("${projectDir}/assets/flt3/empty_flt3_itd_ext.vcf",
                                     checkIfExists: true),
                    filt3r   ?: file("${projectDir}/assets/flt3/empty_filt3r.vcf",
                                     checkIfExists: true),
                )
            }

        FLT3_CONSENSUS(ch_for_consensus)

    emit:
        consensus_tsv = FLT3_CONSENSUS.out.tsv
}
