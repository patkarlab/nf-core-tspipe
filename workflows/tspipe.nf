/*
 * workflows/tspipe.nf
 *
 * Main workflow. Replaces run_sample_pipeline.py end-to-end.
 *
 * Step ordering matches the original runner:
 *     PREPROCESSING -> VARIANT_CALLING -> FLT3_ITD
 *                   -> CNV_CALLING -> SV_CALLING
 *                   -> ANNOTATION -> REPORTING
 *
 * As in the original, U2AF1 rescue branches off the final ABRA2 BAM in parallel
 * with variant calling; FLT3 consensus depends on Pindel (step 08) too, so it
 * runs after variant calling.
 */

include { PREPROCESSING   } from '../subworkflows/local/preprocessing'
include { VARIANT_CALLING } from '../subworkflows/local/variant_calling'
include { FLT3_ITD        } from '../subworkflows/local/flt3_itd'
include { CNV_CALLING     } from '../subworkflows/local/cnv_calling'
include { SV_CALLING      } from '../subworkflows/local/sv_calling'
include { ANNOTATION      } from '../subworkflows/local/annotation'
include { REPORTING       } from '../subworkflows/local/reporting'

workflow TSPIPE {

    // ----- Validate required params -------------------------------------
    if (!params.input)     { error "Missing --input (samplesheet CSV)" }
    if (!params.reference) { error "Missing --reference (hg38 FASTA)"  }
    if (!params.bed)       { error "Missing --bed (panel BED)"         }

    // Channels for fixed references shared across processes.
    ch_reference = Channel.value([
        file(params.reference, checkIfExists: true),
        file(params.reference + '.fai', checkIfExists: true),
        file(params.reference.replaceFirst(/\.fa(sta)?$/, '.dict'), checkIfExists: true)
    ])
    ch_bed       = Channel.fromPath(params.bed,        checkIfExists: true)
    ch_blacklist = params.snv_blacklist
                       ? Channel.fromPath(params.snv_blacklist, checkIfExists: true)
                       : Channel.value([])

    // Known-sites VCFs for BQSR. Each tuple is [vcf, tbi].
    ch_dbsnp = Channel.value([
        file(params.dbsnp_vcf, checkIfExists: true),
        file(params.dbsnp_vcf + '.tbi', checkIfExists: true)
    ])
    ch_mills = Channel.value([
        file(params.mills_vcf, checkIfExists: true),
        file(params.mills_vcf + '.tbi', checkIfExists: true)
    ])

    // ----- Parse the samplesheet ----------------------------------------
    ch_input = Channel.fromPath(params.input, checkIfExists: true)
        .splitCsv(header: true)
        .map { row ->
            def meta = [
                id:  row.sample,
                sex: row.sex ?: 'unknown'
            ]
            [ meta,
              file(row.fastq_1, checkIfExists: true),
              file(row.fastq_2, checkIfExists: true) ]
        }

    // ----- 1. Preprocessing: fastp -> bwa -> markdup -> bqsr -> abra2 ---
    PREPROCESSING(ch_input, ch_reference, ch_bed, ch_dbsnp, ch_mills)
    ch_final_bam = PREPROCESSING.out.final_bam   // [meta, bam, bai]

    // ----- 2. Variant calling + somaticseq ensemble + pindel ------------
    // VARIANT_CALLING(ch_final_bam, ch_reference, ch_bed)
    // ch_somaticseq = VARIANT_CALLING.out.somaticseq_vcf
    // ch_pindel_vcf = VARIANT_CALLING.out.pindel_vcf

    // ----- 3. FLT3-ITD 4-tool ensemble ----------------------------------
    // FLT3_ITD(ch_final_bam, ch_pindel_vcf)
    // ch_flt3_consensus = FLT3_ITD.out.consensus_tsv

    // ----- 4. CNV calling (CNVKit + Z-score + concordance) --------------
    // CNV_CALLING(ch_final_bam, ch_reference, ch_bed)

    // ----- 5. SV calling -----------------------------------------------
    // SV_CALLING(ch_final_bam, ch_reference, ch_bed)

    // ----- 6. Annotation: VEP -> ANNOVAR -> filter -> validator -> oncovi
    // ANNOTATION(
    // ch_somaticseq,
    // ch_flt3_consensus,
    // ch_blacklist,
    // ch_reference
    // )

    // ----- 7. Reporting: IGV reports + organize_output ------------------
    // REPORTING(
    // ANNOTATION.out.clinical_tsv,
    // ch_final_bam,
    // CNV_CALLING.out.clinical_report,
    // SV_CALLING.out.annotated,
    // FLT3_ITD.out.consensus_tsv
    // )
}
