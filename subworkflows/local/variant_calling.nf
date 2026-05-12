/*
 * subworkflows/local/variant_calling.nf
 *
 * Stage 2: Mutect2 + U2AF1 rescue + VarDict + VarScan. More callers to follow.
 */

include { GATK4_MUTECT2       } from '../../modules/local/mutect2'
include { U2AF1_RESCUE        } from '../../modules/local/u2af1_rescue'
include { VARDICT             } from '../../modules/local/vardict'
include { VARSCAN             } from '../../modules/local/varscan'
// include { STRELKA             } from '../../modules/local/strelka'
// include { FREEBAYES           } from '../../modules/local/freebayes'
// include { PLATYPUS            } from '../../modules/local/platypus'
// include { DEEPSOMATIC         } from '../../modules/local/deepsomatic'
// include { SOMATICSEQ_ENSEMBLE } from '../../modules/local/somaticseq'
// include { PINDEL              } from '../../modules/local/pindel'

workflow VARIANT_CALLING {

    take:
        bam_ch
        reference_ch
        bed_ch
        gnomad_ch
        gnomad_tbi_ch

    main:
        GATK4_MUTECT2(bam_ch, reference_ch, bed_ch, gnomad_ch, gnomad_tbi_ch)
        U2AF1_RESCUE(bam_ch)
        VARDICT(bam_ch, reference_ch, bed_ch)
        VARSCAN(bam_ch, reference_ch, bed_ch)

    emit:
        mutect2_vcf  = GATK4_MUTECT2.out.vcf
        u2af1_tsv    = U2AF1_RESCUE.out.tsv
        vardict_vcf  = VARDICT.out.vcf
        varscan_vcf  = VARSCAN.out.vcf
}
