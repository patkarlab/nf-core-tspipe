/*
 * subworkflows/local/variant_calling.nf
 *
 * Equivalent to scripts/06_variant_callers.py + 07_somaticseq.py + 08_pindel.py
 * + scripts/u2af1_rescue.py (U2AF1 pileup-based rescue on the final BAM).
 *
 * All seven somatic callers run in parallel on the same BAM:
 *     Mutect2, VarDict, VarScan, Strelka, FreeBayes, Platypus, DeepSomatic
 *
 * SomaticSeq then merges them into a single consensus VCF.
 * Pindel runs independently for indel discovery.
 */

include { GATK4_MUTECT2       } from '../../modules/local/mutect2'
include { VARDICT             } from '../../modules/local/vardict'
include { VARSCAN             } from '../../modules/local/varscan'
include { STRELKA             } from '../../modules/local/strelka'
include { FREEBAYES           } from '../../modules/local/freebayes'
include { PLATYPUS            } from '../../modules/local/platypus'
include { DEEPSOMATIC         } from '../../modules/local/deepsomatic'
include { SOMATICSEQ_ENSEMBLE } from '../../modules/local/somaticseq'
include { PINDEL              } from '../../modules/local/pindel'
include { U2AF1_RESCUE        } from '../../modules/local/u2af1_rescue'

workflow VARIANT_CALLING {

    take:
        bam_ch        // [meta, bam, bai]
        reference_ch
        bed_ch

    main:

        // ----- Seven somatic callers, all on the final BAM in parallel --
        GATK4_MUTECT2(bam_ch, reference_ch, bed_ch)
        VARDICT      (bam_ch, reference_ch, bed_ch)
        VARSCAN      (bam_ch, reference_ch, bed_ch)
        STRELKA      (bam_ch, reference_ch, bed_ch)
        FREEBAYES    (bam_ch, reference_ch, bed_ch)
        PLATYPUS     (bam_ch, reference_ch, bed_ch)
        DEEPSOMATIC  (bam_ch, reference_ch, bed_ch)

        // Group all caller VCFs by sample, then send to somaticseq.
        ch_all_vcfs = GATK4_MUTECT2.out.vcf
            .join(VARDICT.out.vcf)
            .join(VARSCAN.out.vcf)
            .join(STRELKA.out.vcf)
            .join(FREEBAYES.out.vcf)
            .join(PLATYPUS.out.vcf)
            .join(DEEPSOMATIC.out.vcf)

        SOMATICSEQ_ENSEMBLE(ch_all_vcfs, bam_ch, reference_ch, bed_ch)

        // ----- Pindel (step 08) — independent --------------------------
        PINDEL(bam_ch, reference_ch, bed_ch)

        // ----- U2AF1 pileup rescue (step 05b in old runner) ------------
        U2AF1_RESCUE(bam_ch, reference_ch)

    emit:
        somaticseq_vcf = SOMATICSEQ_ENSEMBLE.out.vcf
        pindel_vcf     = PINDEL.out.vcf
        u2af1_tsv      = U2AF1_RESCUE.out.tsv
}
