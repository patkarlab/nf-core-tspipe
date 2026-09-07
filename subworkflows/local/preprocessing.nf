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
include { SEX_CHECK              } from '../../modules/local/sex_check'   // MARKER SEX_CHECK_V1
include { SAMPLE_DASHBOARD       } from '../../modules/local/sample_dashboard'

// MARKER SEX_CHECK_V1: rewrite meta.sex on a [meta, ...] channel from the per-sample
// resolved sex keyed on meta.id. Samplesheet male/female always wins; 'unknown'
// takes the inference; a sample with no SEX_CHECK row keeps its meta. The key
// set of meta is unchanged, so task hashes only move when the value moves.
def withResolvedSex(ch, sex_by_id) {
    ch.map { it -> [ it[0].id, it ] }
      .join(sex_by_id, remainder: true)
      .filter { id, tup, sex -> tup != null }
      .map { id, tup, sex ->
          def meta     = tup[0]
          def resolved = (meta.sex in ['male', 'female']) ? meta.sex : (sex ?: meta.sex)
          [ meta + [sex: resolved] ] + tup.drop(1)
      }
}

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
                def exts = ['.amb', '.ann', '.pac', '.bwt.2bit.64', '.0123']
                // MARKER alt_staging: bwa-mem2 is alt-aware only when <prefix>.alt is
                // staged beside the index in the task dir (audit 2026-09-02 D1).
                if( file("${fasta.toString()}.alt").exists() ) exts << '.alt'
                exts.collect { ext -> file("${fasta.toString()}${ext}") }
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
        // MARKER SEX_CHECK_V1: sex from the mosdepth regions (X/A ratio); one row per sample.
        // resolved_sex = sheet value if male/female, else the inference.
        // MARKER SEX_CHECK_V2: chrX heterozygosity at the panel het catalog is the deciding
        // vote (CollectAllelicCounts inside SEX_CHECK on the final BAM); X/A confirms or
        // raises X_DEPTH_CONFLICT. Panels without assets/<panel>/het_catalog.tsv stage []
        // and keep the depth-only inference.
        def sex_het_catalog_path = (params.containsKey('sex_check_het_catalog') && params.sex_check_het_catalog)
            ? params.sex_check_het_catalog
            : "${projectDir}/assets/${params.panel}/het_catalog.tsv"
        def sex_het_catalog_file = file(sex_het_catalog_path)
        if( !sex_het_catalog_file.exists() )
            log.warn "[SEX_CHECK] no het catalog at ${sex_het_catalog_path}; sex inference is depth-only"
        ch_sex_het_catalog = Channel.value( sex_het_catalog_file.exists() ? sex_het_catalog_file : [] )
        SEX_CHECK(
            MOSDEPTH.out.regions_thresholds.join(ABRA2.out.bam, by: 0),
            reference_ch,
            ch_sex_het_catalog
        )
        // MARKER SEX_CHECK_V1a: the map closure is replayed per consumer of ch_sex_by_id; log once.
        def sex_check_logged = java.util.concurrent.ConcurrentHashMap.newKeySet()
        ch_sex_by_id = SEX_CHECK.out.tsv
            .splitCsv(header: true, sep: '\t', elem: 1)
            .map { meta, row ->
                if( sex_check_logged.add(meta.id) ) {
                    if( row.status == 'MISMATCH' )
                        log.warn "[SEX_CHECK] ${meta.id}: samplesheet sex=${row.sheet_sex} but data infers ${row.inferred_sex} (X/A=${row.x_auto_ratio}); keeping the samplesheet value"
                    else if( row.sheet_sex == 'unknown' )
                        log.info "[SEX_CHECK] ${meta.id}: samplesheet sex unknown; using inferred ${row.resolved_sex} (method=${row.method}, X het=${row.x_het_frac}, X/A=${row.x_auto_ratio}, status=${row.status})"
                    // MARKER SEX_CHECK_V2: the two votes disagree; heterozygosity decided
                    if( (row.flags ?: '').contains('X_DEPTH_CONFLICT') )
                        log.warn "[SEX_CHECK] ${meta.id}: chrX heterozygosity says ${row.het_inferred_sex}, depth says ${row.depth_inferred_sex} (X het=${row.x_het_frac}, X/A=${row.x_auto_ratio}); using ${row.inferred_sex}; a chrX copy-number change in the tumour is likely"
                }
                [ meta.id, row.resolved_sex ]
            }


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

        // MARKER SEX_CHECK_V1: resolved meta.sex on every emit so downstream joins stay consistent
        ch_sexed_trimmed = withResolvedSex(FASTP.out.reads, ch_sex_by_id)
        ch_sexed_aligned = withResolvedSex(BWA_MEM.out.bam, ch_sex_by_id)
        ch_sexed_dedup = withResolvedSex(PICARD_MARKDUPLICATES.out.bam, ch_sex_by_id)
        ch_sexed_recal = withResolvedSex(GATK4_BQSR.out.bam, ch_sex_by_id)
        ch_sexed_final_bam = withResolvedSex(ABRA2.out.bam, ch_sex_by_id)
        ch_sexed_hsmetrics = withResolvedSex(HSMETRICS.out.metrics, ch_sex_by_id)
        ch_sexed_exon_coverage = withResolvedSex(PARSE_EXON_COVERAGE.out.tsv, ch_sex_by_id)
        ch_sexed_dashboard = withResolvedSex(SAMPLE_DASHBOARD.out.html, ch_sex_by_id)
        ch_sexed_fastp_html = withResolvedSex(FASTP.out.html, ch_sex_by_id)
        ch_sexed_sex_check = withResolvedSex(SEX_CHECK.out.tsv, ch_sex_by_id)

    emit:
        trimmed       = ch_sexed_trimmed
        aligned       = ch_sexed_aligned
        dedup         = ch_sexed_dedup
        recal         = ch_sexed_recal
        final_bam     = ch_sexed_final_bam
        hsmetrics     = ch_sexed_hsmetrics
        exon_coverage = ch_sexed_exon_coverage
        dashboard     = ch_sexed_dashboard
        fastp_html    = ch_sexed_fastp_html
        sex_check     = ch_sexed_sex_check
}
