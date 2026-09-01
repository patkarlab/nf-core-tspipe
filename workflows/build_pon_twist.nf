/*
 * workflows/build_pon_twist.nf
 *
 * BUILD_PON_TWIST -- sex-stratified panel-of-normals builder for the Twist
 * myeloid panel (TE-99430185). Replaces BUILD_PON for this panel; the
 * myeloid / myeloid_cnv clinical path is untouched.
 *
 * Design record: docs/audit/2026-09-01/ (exclusion criteria, batch-effect
 * attribution, single-artifact filtered BED).
 *
 * Architecture: both strata are wired; population is controlled by
 * (a) params.pon_strata and (b) the include_in_pon column of the
 * samplesheet. As of 2026-09-01 only the male stratum has conforming
 * normals (24 x 8-plex); the 24 female normals were captured at 12-plex
 * and carry include_in_pon=false until re-hybridised.
 *
 * Per-sample steps (CollectAllelicCounts, conformity gate, CNVkit coverage,
 * CollectReadCounts) run on EVERY samplesheet row regardless of include
 * flag; only reference construction (CNVkit reference, GATK read-count PoN,
 * LOO QC) filters on sex + include_in_pon.
 *
 * Run:
 *   nextflow run main.nf -entry BUILD_PON_TWIST -profile gandalf \
 *       --pon_input pon_samplesheets/twist_normals_48.csv \
 *       --pon_fasta /path/to/hg38.fa \
 *       --outdir /goast/hemat_data/pon_twist/build_v2
 */

nextflow.enable.dsl = 2

// ---------------------------------------------------------------------------
// Workflow-scoped parameter defaults. Lowest precedence: any config file or
// CLI value overrides these. Kept here (not in nextflow.config) so the
// clinical config surface is not modified by this workflow's existence.
// ---------------------------------------------------------------------------
params.pon_input         = null            // samplesheet CSV (required)
params.pon_fasta         = null            // hg38 fasta; .fai and .dict must sit alongside (required)
params.pon_strata        = 'male'          // comma-separated subset of: male,female
params.pon_panel         = 'twist_myeloid' // passed explicitly to cnv_loo_qc.py (its default is 'myeloid')
params.pon_assets        = "${projectDir}/assets/twist_myeloid"

// OPEN DECISION (handoff item 2): cohort for the BAF background table.
// 'male' = conforming males only; 'all' = all 48 with per-site depth filter.
// Changing this re-runs only BPT_AGGREGATE_BAF under -resume.
params.pon_baf_cohort    = 'male'
params.pon_baf_min_depth = 20
params.pon_baf_min_het   = 3               // samples in 0.2-0.8 AF band for a site to be flagged informative

// GATK AnnotateIntervals GC track fed to CreateReadCountPanelOfNormals.
// Flagged for module review; annotation itself always runs (cheap), this
// flag only controls whether the PoN consumes it.
params.pon_gc_correction = true

// Antitarget handling. 'empty' = header-only antitarget coverage (the
// in-panel CNV backbone already provides genome-wide bins; off-target
// bins would be redundant). 'auto' is intentionally unimplemented in v1.
params.pon_antitarget    = 'empty'

// Capture-conformity gate thresholds (REPORT-ONLY in v1; no sample is
// dropped). Defaults chosen against the 2026-09-01 survey: conforming
// males sit at NPM1_exon_11 >= ~300x, the 12-plex failure at ~47x.
// insert_min 150 deliberately flags watch-item Male12 (131.8 bp).
params.pon_npm1_min      = 100
params.pon_jak2_min      = 100
params.pon_insert_min    = 150

// ---------------------------------------------------------------------------

include { BPT_CHECK_SAMPLESHEET       } from '../modules/local/bpt_check_samplesheet'
include { BPT_CNVKIT_PREP             } from '../modules/local/bpt_cnvkit_prep'
include { BPT_CNVKIT_COVERAGE         } from '../modules/local/bpt_cnvkit_coverage'
include { BPT_GATK_PREPROCESS_INTERVALS } from '../modules/local/bpt_gatk_preprocess_intervals'
include { BPT_GATK_ANNOTATE_INTERVALS } from '../modules/local/bpt_gatk_annotate_intervals'
include { BPT_GATK_COLLECT_READ_COUNTS } from '../modules/local/bpt_gatk_collect_read_counts'
include { BPT_GATK_COLLECT_ALLELIC_COUNTS } from '../modules/local/bpt_gatk_collect_allelic_counts'
include { BPT_AGGREGATE_BAF           } from '../modules/local/bpt_aggregate_baf'
include { BPT_CONFORMITY_SAMPLE       } from '../modules/local/bpt_conformity_sample'
include { BPT_CONFORMITY_REPORT       } from '../modules/local/bpt_conformity_report'
include { BPT_TOOL_VERSIONS           } from '../modules/local/bpt_tool_versions'

include { BPT_STRATUM as STRATUM_MALE   } from '../subworkflows/local/bpt_stratum'
include { BPT_STRATUM as STRATUM_FEMALE } from '../subworkflows/local/bpt_stratum'

workflow BUILD_PON_TWIST {

    main:

    // ---- fail-fast validation ------------------------------------------
    if( !params.pon_input )
        error "[BPT] --pon_input <samplesheet.csv> is required"

    // Fasta resolution (BPT_FASTA_DEFAULT_V1): default to the pipeline
    // alignment reference so the PoN is built on the same fasta the BAMs
    // were aligned to (gandalf profile: params.reference = hg38_broad
    // masked). --pon_fasta overrides for cross-site use.
    def pon_fasta_path = params.pon_fasta
    if( !pon_fasta_path && params.containsKey('reference') && params.reference )
        pon_fasta_path = params.reference
    if( !pon_fasta_path )
        error "[BPT] no reference fasta: pass --pon_fasta or run with a profile that defines params.reference (.fai and .dict must sit alongside)"

    def strata = params.pon_strata.tokenize(',').collect{ it.trim() }.findAll{ it }
    def bad_strata = strata.findAll{ !(it in ['male','female']) }
    if( bad_strata )
        error "[BPT] unknown strata ${bad_strata}; pon_strata must be a subset of male,female"
    if( !strata )
        error "[BPT] pon_strata resolved to an empty list"

    def fasta_f = file(pon_fasta_path)
    def fai_f   = file("${pon_fasta_path}.fai")
    def dict_f  = file(pon_fasta_path.replaceAll(/\.(fa|fasta)(\.gz)?$/, '') + '.dict')
    [fasta_f, fai_f, dict_f].each { f ->
        if( !f.exists() ) error "[BPT] missing reference companion file: ${f}"
    }

    ch_fasta = Channel.value(fasta_f)
    ch_fai   = Channel.value(fai_f)
    ch_dict  = Channel.value(dict_f)

    // Reference files are value channels (queue channels are one-shot).
    ch_bed      = Channel.value(file("${params.pon_assets}/panel.combined.filtered.bed", checkIfExists: true))
    ch_snp_bed  = Channel.value(file("${params.pon_assets}/snp_sites.baf.bed",           checkIfExists: true))
    ch_exonwise = Channel.value(file("${params.pon_assets}/targets.exonwise.bed",        checkIfExists: true))

    // ---- samplesheet ----------------------------------------------------
    BPT_CHECK_SAMPLESHEET( Channel.value(file(params.pon_input, checkIfExists: true)) )
    ch_sheet = BPT_CHECK_SAMPLESHEET.out.csv.first()

    ch_samples = BPT_CHECK_SAMPLESHEET.out.csv
        .splitCsv(header: true)
        .map { row ->
            def meta = [
                id:      row.sample,
                sex:     row.sex,
                include: row.include_in_pon == 'true'
            ]
            tuple( meta, file(row.bam), file(row.bai) )
        }

    // ---- global prep (stratum-independent) ------------------------------
    BPT_CNVKIT_PREP( ch_bed )
    BPT_GATK_PREPROCESS_INTERVALS( ch_bed, ch_fasta, ch_fai, ch_dict )
    BPT_GATK_ANNOTATE_INTERVALS( BPT_GATK_PREPROCESS_INTERVALS.out.interval_list, ch_fasta, ch_fai, ch_dict )

    ch_targets = BPT_CNVKIT_PREP.out.targets.first()
    ch_anti    = BPT_CNVKIT_PREP.out.antitargets.first()
    ch_ilist   = BPT_GATK_PREPROCESS_INTERVALS.out.interval_list.first()
    ch_annot   = BPT_GATK_ANNOTATE_INTERVALS.out.annotated.first()

    // ---- per-sample steps: ALL rows -------------------------------------
    BPT_CNVKIT_COVERAGE( ch_samples, ch_targets, ch_anti )
    BPT_GATK_COLLECT_READ_COUNTS( ch_samples, ch_ilist, ch_fasta, ch_fai, ch_dict )
    BPT_GATK_COLLECT_ALLELIC_COUNTS( ch_samples, ch_snp_bed, ch_fasta, ch_fai, ch_dict )
    BPT_CONFORMITY_SAMPLE( ch_samples, ch_exonwise )

    // ---- per-stratum reference construction -----------------------------
    // Reference-building membership = sex match AND include_in_pon=true.
    ch_cov = BPT_CNVKIT_COVERAGE.out.cov
    ch_cnt = BPT_GATK_COLLECT_READ_COUNTS.out.counts

    if( 'male' in strata ) {
        male_cov = ch_cov
            .filter { meta, tcnn, acnn -> meta.sex == 'male' && meta.include }
            .ifEmpty { error "[BPT] stratum 'male' selected but 0 samples have sex=male and include_in_pon=true" }
            .map { meta, tcnn, acnn -> [ tcnn, acnn ] }
            .flatten()
            .collect()
        male_cnt = ch_cnt
            .filter { meta, hdf5 -> meta.sex == 'male' && meta.include }
            .map { meta, hdf5 -> hdf5 }
            .collect()
        STRATUM_MALE( 'male', male_cov, male_cnt, ch_bed, ch_fasta, ch_fai, ch_annot )
    }

    if( 'female' in strata ) {
        female_cov = ch_cov
            .filter { meta, tcnn, acnn -> meta.sex == 'female' && meta.include }
            .ifEmpty { error "[BPT] stratum 'female' selected but 0 samples have sex=female and include_in_pon=true (female arm is gated on conforming re-hybridised normals; see 2026-09-01 audit memo)" }
            .map { meta, tcnn, acnn -> [ tcnn, acnn ] }
            .flatten()
            .collect()
        female_cnt = ch_cnt
            .filter { meta, hdf5 -> meta.sex == 'female' && meta.include }
            .map { meta, hdf5 -> hdf5 }
            .collect()
        STRATUM_FEMALE( 'female', female_cov, female_cnt, ch_bed, ch_fasta, ch_fai, ch_annot )
    }

    // ---- cohort-level aggregations --------------------------------------
    BPT_AGGREGATE_BAF(
        BPT_GATK_COLLECT_ALLELIC_COUNTS.out.allelic.map { meta, tsv -> tsv }.collect(),
        ch_sheet,
        ch_snp_bed
    )
    BPT_CONFORMITY_REPORT(
        BPT_CONFORMITY_SAMPLE.out.row.map { meta, tsv -> tsv }.collect(),
        ch_sheet
    )
    BPT_TOOL_VERSIONS()
}
