/*
 * subworkflows/local/variant_calling.nf
 *
 * Stage 2: Mutect2 first. Other callers will follow incrementally as their
 * stub modules get filled in.
 */

include { GATK4_MUTECT2       } from '../../modules/local/mutect2'
// include { VARDICT             } from '../../modules/local/vardict'
// include { VARSCAN             } from '../../modules/local/varscan'
// include { STRELKA             } from '../../modules/local/strelka'
// include { FREEBAYES           } from '../../modules/local/freebayes'
// include { PLATYPUS            } from '../../modules/local/platypus'
// include { DEEPSOMATIC         } from '../../modules/local/deepsomatic'
// include { SOMATICSEQ_ENSEMBLE } from '../../modules/local/somaticseq'
// include { PINDEL              } from '../../modules/local/pindel'
// include { U2AF1_RESCUE        } from '../../modules/local/u2af1_rescue'

workflow VARIANT_CALLING {

    take:
        bam_ch          // [meta, bam, bai]
        reference_ch    // [fasta, fai, dict] - MASKED hg38 (clinical decision)
        bed_ch
        gnomad_ch       // path to gnomad vcf
        gnomad_tbi_ch   // path to gnomad vcf.tbi

    main:
        GATK4_MUTECT2(bam_ch, reference_ch, bed_ch, gnomad_ch, gnomad_tbi_ch)

    emit:
        mutect2_vcf = GATK4_MUTECT2.out.vcf
}
