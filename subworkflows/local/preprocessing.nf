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
include { HSMETRICS              } from '../../modules/local/hsmetrics'
include { MOSDEPTH               } from '../../modules/local/mosdepth'
include { PARSE_EXON_COVERAGE    } from '../../modules/local/parse_exon_coverage'
include { SAMPLE_DASHBOARD       } from '../../modules/local/sample_dashboard'

workflow PREPROCESSING {

    take:
        reads_ch
        reference_ch
        bed_ch
        exonwise_bed_ch  // exon-collapsed BED for MOSDEPTH/PARSE_EXON_COVERAGE only
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

        // QC: per-target capture metrics + per-exon coverage.
        // HSMETRICS runs in the GATK container. Per-exon coverage
        // is a two-step pipeline because the mosdepth biocontainer
        // has no Python: MOSDEPTH writes regions/thresholds bed.gz,
        // then PARSE_EXON_COVERAGE (GATK container, has Python)
        // joins them with the panel BED labels into a per-exon TSV.
        HSMETRICS(ABRA2.out.bam, reference_ch, bed_ch)
        MOSDEPTH(ABRA2.out.bam, exonwise_bed_ch)
        PARSE_EXON_COVERAGE(MOSDEPTH.out.regions_thresholds, exonwise_bed_ch)

        // Per-sample dashboard: join HsMetrics + per-exon coverage on meta.id,
        // then render a self-contained HTML report. Provenance values are
        // pulled from Nextflow's workflow object (commit + start time) and
        // params.panel_name, with permissive defaults.
        ch_dashboard_input = HSMETRICS.out.metrics
            .join(PARSE_EXON_COVERAGE.out.tsv)
        SAMPLE_DASHBOARD(
            ch_dashboard_input,
            params.panel_name ?: 'MYOPOOL hg38',
            workflow.commitId ?: '(uncommitted)',
            workflow.start.format('yyyy-MM-dd')
        )

    emit:
        trimmed   = FASTP.out.reads
        aligned   = BWA_MEM.out.bam
        dedup     = PICARD_MARKDUPLICATES.out.bam
        recal     = GATK4_BQSR.out.bam
        final_bam     = ABRA2.out.bam
        hsmetrics     = HSMETRICS.out.metrics
        exon_coverage = PARSE_EXON_COVERAGE.out.tsv
        dashboard     = SAMPLE_DASHBOARD.out.html
        fastp_html    = FASTP.out.html
}
