/*
 * subworkflows/local/preprocessing.nf
 *
 * fastp -> bwa-mem2 -> markdup -> BQSR -> ABRA2
 */

include { FASTP                  } from '../../modules/local/fastp'
include { BWA_MEM                } from '../../modules/local/bwa_mem'
include { PICARD_MARKDUPLICATES  } from '../../modules/local/markduplicates'
include { GATK4_BQSR             } from '../../modules/local/bqsr'
include { ABRA2                  } from '../../modules/local/abra2'

workflow PREPROCESSING {

    take:
        reads_ch
        reference_ch
        bed_ch
        dbsnp_ch       // [vcf, tbi]
        mills_ch       // [vcf, tbi]

    main:
        // BWA-mem2 index files staged alongside FASTA
        ch_bwa_index = reference_ch
            .map { fasta, fai, dict ->
                ['.amb', '.ann', '.pac', '.bwt.2bit.64', '.0123']
                    .collect { ext -> file("${fasta.toString()}${ext}") }
            }
            .flatten()
            .collect()

        FASTP(reads_ch)
        BWA_MEM(FASTP.out.reads, reference_ch, ch_bwa_index)
        PICARD_MARKDUPLICATES(BWA_MEM.out.bam)
        GATK4_BQSR(PICARD_MARKDUPLICATES.out.bam, reference_ch, dbsnp_ch, mills_ch)
        ABRA2(GATK4_BQSR.out.bam, reference_ch, bed_ch)

    emit:
        trimmed   = FASTP.out.reads
        aligned   = BWA_MEM.out.bam
        dedup     = PICARD_MARKDUPLICATES.out.bam
        recal     = GATK4_BQSR.out.bam
        final_bam = ABRA2.out.bam
}
