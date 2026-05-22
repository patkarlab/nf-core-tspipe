/*
 * workflows/tspipe.nf
 *
 * Main workflow. Replaces run_sample_pipeline.py end-to-end.
 *
 * Step ordering matches the original runner:
 *     PREPROCESSING -> VARIANT_CALLING -> SOMATICSEQ_ENSEMBLE -> FLT3_ITD
 *                   -> CNV_CALLING -> SV_CALLING
 *                   -> ANNOTATION -> REPORTING
 *
 * As in the original, U2AF1 rescue branches off the final ABRA2 BAM in parallel
 * with variant calling; FLT3 consensus depends on Pindel (step 08) too, so it
 * runs after variant calling.
 *
 * SomaticSeq design: 8-caller ensemble (port goes beyond production's 6-caller
 * setup; adds Pindel + DeepSomatic via --arbitrary). See modules/local/somaticseq.nf
 * for the rationale.
 */

include { PREPROCESSING       } from '../subworkflows/local/preprocessing'
include { VARIANT_CALLING     } from '../subworkflows/local/variant_calling'
include { SOMATICSEQ_ENSEMBLE } from '../modules/local/somaticseq'
include { SOMATICSEQ_POSTPROCESS } from '../modules/local/somaticseq_postprocess'
include { FLT3_ITD            } from '../subworkflows/local/flt3_itd'
include { CNV_CALLING         } from '../subworkflows/local/cnv_calling'
include { SV_CALLING          } from '../subworkflows/local/sv_calling'
include { ANNOTATION          } from '../subworkflows/local/annotation'
include { REPORTING           } from '../subworkflows/local/reporting'
include { IGV_REPORTS         } from '../modules/local/igv_reports'
include { ORGANIZE_OUTPUT     } from '../modules/local/organize_output'
include { DASHBOARD           } from '../modules/local/dashboard'

workflow TSPIPE {

    // ----- Validate required params -------------------------------------
    if (!params.input)     { error "Missing --input (samplesheet CSV)" }
    if (!params.reference) { error "Missing --reference (hg38 FASTA)"  }
    if (!params.bed)       { error "Missing --bed (panel BED)"         }
    if (!params.exonwise_bed) { error "Missing --exonwise_bed (Exonwise hg38 BED for per-exon coverage)" }

    // Channels for fixed references shared across processes.
    ch_reference = Channel.value([
        file(params.reference, checkIfExists: true),
        file(params.reference + '.fai', checkIfExists: true),
        file(params.reference.replaceFirst(/\.fa(sta)?$/, '.dict'), checkIfExists: true)
    ])
    ch_bed       = Channel.value(file(params.bed, checkIfExists: true))
    ch_exonwise_bed = Channel.value(file(params.exonwise_bed, checkIfExists: true))
    ch_pindel_bed = Channel.value(file(params.pindel_bed, checkIfExists: true))
    // ch_blacklist must be a VALUE channel (broadcasts to every
    // VARIANT_FILTER task instance), not a queue channel (which would
    // emit once and starve all subsequent samples).
    ch_blacklist = params.snv_blacklist
                       ? Channel.value(file(params.snv_blacklist, checkIfExists: true))
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

    // dbsnp VCF only (path, no .tbi) - SomaticSeq's --dbsnp-vcf expects the path
    ch_dbsnp_vcf = Channel.value(file(params.dbsnp_vcf, checkIfExists: true))

    // gnomAD for Mutect2 germline filtering
    ch_gnomad     = Channel.value(file(params.gnomad_af_only, checkIfExists: true))
    ch_gnomad_tbi = Channel.value(file(params.gnomad_af_only + '.tbi', checkIfExists: true))

    // ----- CNV reference channels (asset defaults, runtime-overridable) -
    // nf-core CNV wiring v1 (apply_nfcore_cnv_wiring_part1)
    // Sex-specific PoNs. CNVKIT module selects via meta.sex at process time;
    // sex=='unknown' falls back to the female PoN with a log.warn.
    ch_cnv_pon_male   = Channel.value(file(
        params.cnv_pon_male   ?: "${projectDir}/assets/${params.panel}/cnvkit_pon_male.cnn",
        checkIfExists: true))
    ch_cnv_pon_female = Channel.value(file(
        params.cnv_pon_female ?: "${projectDir}/assets/${params.panel}/cnvkit_pon_female.cnn",
        checkIfExists: true))
    // Panel-specific LOO QC artefacts produced by BUILD_PON.
    ch_cnv_loo_summary   = Channel.value(file(
        params.cnv_loo_summary   ?: "${projectDir}/assets/${params.panel}/cnvkit_loo_summary.tsv",
        checkIfExists: true))
    ch_cnv_noisy_bins    = Channel.value(file(
        params.cnv_noisy_bins    ?: "${projectDir}/assets/${params.panel}/cnvkit_noisy_bins.bed",
        checkIfExists: true))
    ch_cnv_noise_profile = Channel.value(file(
        params.cnv_noise_profile ?: "${projectDir}/assets/${params.panel}/loo_bin_noise_profile.tsv",
        checkIfExists: true))
    // Panel-agnostic annotation references.
    ch_cytoband = Channel.value(file(
        params.cytoband ?: "${projectDir}/assets/references/cytoBand_hg38.txt",
        checkIfExists: true))
    ch_clingen  = Channel.value(file(
        params.clingen  ?: "${projectDir}/assets/references/ClinGen_gene_curation_list_GRCh38.tsv",
        checkIfExists: true))
    // Panel-specific chr-gene scatter regions (no runtime override; lives in panel assets).
    ch_scatter_regions = Channel.value(file(
        "${projectDir}/assets/${params.panel}/cnv_scatter_regions.txt",
        checkIfExists: true))

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
    PREPROCESSING(ch_input, ch_reference, ch_bed, ch_exonwise_bed, ch_dbsnp, ch_mills)
    ch_final_bam     = PREPROCESSING.out.final_bam      // [meta, bam, bai]
    ch_hsmetrics     = PREPROCESSING.out.hsmetrics       // [meta, hs_metrics.txt]
    ch_exon_coverage = PREPROCESSING.out.exon_coverage   // [meta, exon_coverage.tsv]

    // ----- 2. Variant calling: 8 callers + U2AF1 rescue ----------------
    VARIANT_CALLING(ch_final_bam, ch_reference, ch_bed, ch_pindel_bed, ch_gnomad, ch_gnomad_tbi)

    // ----- 2b. SomaticSeq ensemble (8-caller) --------------------------
    // Join all 8 per-caller VCF channels on meta. Each .out.X_vcf is
    // [meta, path]; .join(by: 0) accumulates the paths keyed on meta.
    ch_somaticseq_in = VARIANT_CALLING.out.mutect2_vcf
        .join(VARIANT_CALLING.out.vardict_vcf,     by: 0)
        .join(VARIANT_CALLING.out.varscan_vcf,     by: 0)
        .join(VARIANT_CALLING.out.strelka_vcf,     by: 0)
        .join(VARIANT_CALLING.out.freebayes_vcf,   by: 0)
        .join(VARIANT_CALLING.out.platypus_vcf,    by: 0)
        .join(VARIANT_CALLING.out.pindel_vcf,      by: 0)
        .join(VARIANT_CALLING.out.deepsomatic_vcf, by: 0)
        .join(ch_final_bam,                        by: 0)
    // Result tuple shape: [meta, mutect2, vardict, varscan, strelka,
    //                     freebayes, platypus, pindel, deepsomatic,
    //                     bam, bai]

    SOMATICSEQ_ENSEMBLE(
        ch_somaticseq_in,
        ch_reference,
        ch_bed,
        ch_dbsnp_vcf,
    )

    // Post-process: sort/bgzip/index/concat/rename in gatk4 container
    // (somaticseq's own container lacks bcftools/bgzip/tabix on PATH).
    SOMATICSEQ_POSTPROCESS(
        SOMATICSEQ_ENSEMBLE.out.consensus_snv
            .join(SOMATICSEQ_ENSEMBLE.out.consensus_indel)
    )
    ch_somaticseq_vcf = SOMATICSEQ_POSTPROCESS.out.vcf

    // ----- 3. FLT3-ITD 4-tool ensemble (Pindel added 2026-05-19, D1) -----
    FLT3_ITD(
        ch_final_bam,
        VARIANT_CALLING.out.pindel_vcf,
        params.flt3_region
    )
    ch_flt3_consensus = FLT3_ITD.out.consensus_tsv

    // ----- 4. CNV calling (CNVKit + Z-score + concordance) --------------
    // nf-core CNV wiring v1 (apply_nfcore_cnv_wiring_part1)
    CNV_CALLING(
        ch_final_bam,
        ch_reference,
        ch_bed,
        ch_cnv_pon_male,
        ch_cnv_pon_female,
        ch_cnv_loo_summary,
        ch_cnv_noisy_bins,
        ch_cnv_noise_profile,
        ch_cytoband,
        ch_clingen,
        ch_scatter_regions,
    )

    // ----- 5. SV calling -----------------------------------------------
    // SV_CALLING(ch_final_bam, ch_reference, ch_bed)

    // ----- 6. Annotation: VEP -> ANNOVAR -> filter -> validator -> oncovi
    ANNOTATION(
        ch_somaticseq_vcf,
        ch_flt3_consensus,
        VARIANT_CALLING.out.u2af1_tsv,
        ch_blacklist,
        ch_reference,
    )

    // ----- 6b. IGV_REPORTS: per-sample HTML for clinical review (D2) -----
    IGV_REPORTS(
        ANNOTATION.out.clinical_tsv.join(PREPROCESSING.out.final_bam),
        ch_reference
    )

    // ----- 7. ORGANIZE_OUTPUT: build clinical/ deliverable tree --------
    //
    // Optional-channel handling via driver-pattern. Nextflow's
    // .join(remainder: true) is symmetric: it keeps unmatched items
    // from BOTH sides, which causes right-only emits when an optional
    // channel fires before its upstream mandatory siblings. Those
    // right-only emits collapse the LEFT tuple into a single `null`,
    // producing a malformed input tuple downstream.
    //
    // Instead: build always-emitting versions of each optional channel
    // by joining a meta-only driver (derived from a guaranteed-present
    // channel) against the optional, with remainder: true, and
    // null-filling missing slots with NO_FILE_* placeholder files.
    // The main organize chain then uses plain .join() everywhere -- no
    // remainder, no ordering surprises -- and bin/organize_output.py
    // detects the NO_FILE_ prefix to skip absent optionals.

    ch_meta_driver = PREPROCESSING.out.final_bam.map { meta, _bam, _bai -> meta }

    def no_u2af1_report = file("${projectDir}/assets/NO_FILE_u2af1_pileup_report.txt", checkIfExists: true)
    def no_u2af1_rescue = file("${projectDir}/assets/NO_FILE_u2af1_rescue.tsv",        checkIfExists: true)

    ch_u2af1_report = ch_meta_driver
        .join(VARIANT_CALLING.out.u2af1_report, remainder: true)
        .map { meta, f -> [meta, f ?: no_u2af1_report] }

    ch_u2af1_rescue = ch_meta_driver
        .join(VARIANT_CALLING.out.u2af1_tsv,    remainder: true)
        .map { meta, f -> [meta, f ?: no_u2af1_rescue] }

    ch_organize = PREPROCESSING.out.final_bam                                // tuple(meta, bam, bai)
        .join(ANNOTATION.out.clinical_tsv)                                   // + clinical_tsv
        .join(ANNOTATION.out.filtered_tsv)                                   // + filtered_tsv
        .join(ch_u2af1_report)                                               // + u2af1_report  (always emits; sentinel if missing)
        .join(ch_u2af1_rescue)                                               // + u2af1_rescue  (always emits; sentinel if missing)
        .join(FLT3_ITD.out.consensus_tsv)                                    // + flt3_consensus
        .join(PREPROCESSING.out.hsmetrics)                                   // + hsmetrics
        .join(PREPROCESSING.out.exon_coverage)                               // + exon_coverage
        .join(PREPROCESSING.out.fastp_html)                                  // + fastp_html
        .join(IGV_REPORTS.out.html)                                           // + igv_report (D2)
        .join(PREPROCESSING.out.dashboard)                                   // + dashboard
        .join(CNV_CALLING.out.clinical_report)                               // + cnv_clinical_tsv
        .join(CNV_CALLING.out.cnvkit_diagram_pdf)                            // + cnvkit_diagram
        .join(CNV_CALLING.out.cnvkit_scatter_png)                            // + cnvkit_scatter
        .join(CNV_CALLING.out.plots_dir)                                     // + cnvkit_plots_dir

    ORGANIZE_OUTPUT(ch_organize)

    // ----- 8. DASHBOARD: cohort HTML index + per-sample reports --------
    ch_dashboard_in = ORGANIZE_OUTPUT.out.clinical
        .map { meta, clin -> [ meta.id, clin ] }
        .collect(flat: false)
        .multiMap { rows ->
            sample_ids:    rows.collect { it[0] }
            clinical_dirs: rows.collect { it[1] }
        }

    DASHBOARD(
        ch_dashboard_in.sample_ids,
        ch_dashboard_in.clinical_dirs,
    )
}
