/*
 * workflows/tspipe.nf
 *
 * Main workflow. Replaces run_sample_pipeline.py end-to-end.
 *
 * Step ordering matches the original runner:
 *     PREPROCESSING -> VARIANT_CALLING -> SOMATICSEQ_ENSEMBLE -> FLT3_ITD
 *                   -> CNV_CALLING -> ANNOTATION
 *                   -> IGV_REPORTS -> ORGANIZE_OUTPUT -> DASHBOARD -> REPORT_BUNDLE
 *
 * NOTE: SV_CALLING and REPORTING are intentionally not wired into the active
 * DAG. SV calling is disabled (no SV deliverable on this panel yet); final
 * assembly is done directly via IGV_REPORTS + ORGANIZE_OUTPUT below rather than
 * through the REPORTING subworkflow.
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
include { GATK_CNV_CALLING    } from '../subworkflows/local/gatk_cnv_calling'   // TGC_V1
include { CNV_CONSENSUS_MULTI } from '../modules/local/cnv_consensus_multi'   // CMX_V1
include { DECON               } from '../modules/local/decon'                 // MARKER DECON_V1a
include { EXON_PLOTS          } from '../modules/local/exon_plots'            // MARKER EXON_PLOTS_V1
include { HMF_AMBER           } from '../modules/local/hmf_amber'             // MARKER HMF_PURPLE_V1
include { HMF_COBALT          } from '../modules/local/hmf_cobalt'
include { HMF_PURPLE          } from '../modules/local/hmf_purple'
include { CHROM_PAGES         } from '../modules/local/chrom_pages'           // MARKER CHROM_PAGES_V1
include { RECONCNV            } from '../modules/local/reconcnv'
include { PURECN_COVERAGE     } from '../modules/local/purecn_coverage'   // PCN_V1
include { PURECN              } from '../modules/local/purecn'   // PCN_V1
include { ANNOTATION          } from '../subworkflows/local/annotation'
include { IGV_REPORTS         } from '../modules/local/igv_reports'
include { ORGANIZE_OUTPUT     } from '../modules/local/organize_output'
include { DASHBOARD           } from '../modules/local/dashboard'
include { REPORT_BUNDLE       } from '../modules/local/report_bundle'

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
    // MARKER CNV_RETIRE_7B: loo_bin_noise_profile.tsv (ZSCORE_CNV), cytoBand/ClinGen
    // (CNV_ANNOTATE) and cnv_scatter_regions.txt (CNV_PLOTS) are no longer pipeline
    // inputs; params.cytoband and params.clingen feed CMX_ANNOT_V1 (assets/references fallback); params.cnv_noise_profile is ignored.
    // MARKER SEXSTRAT_V1: female-stratum LOO artefacts. The male file is used when the panel
    // has no _female asset (legacy panels), with one log.warn. Selection by
    // meta.sex happens inside CNVKIT, CNV_CONSENSUS_MULTI and
    // GATK_CNV_DENOISE (params.cnv_sex_fallback for unknown/indeterminate).
    def sexstratFemale = { override, female_default, male_path ->
        def f = override ?: female_default
        if( file(f).exists() ) return file(f)
        log.warn "[SEXSTRAT] ${file(f).name} not found for panel ${params.panel}; female stratum uses ${file(male_path).name}"
        return file(male_path)
    }
    ch_cnv_loo_summary_female = Channel.value( sexstratFemale(
        params.cnv_loo_summary_female,
        "${projectDir}/assets/${params.panel}/cnvkit_loo_summary_female.tsv",
        params.cnv_loo_summary ?: "${projectDir}/assets/${params.panel}/cnvkit_loo_summary.tsv" ) )
    ch_cnv_noisy_bins_female  = Channel.value( sexstratFemale(
        params.cnv_noisy_bins_female,
        "${projectDir}/assets/${params.panel}/cnvkit_noisy_bins_female.bed",
        params.cnv_noisy_bins ?: "${projectDir}/assets/${params.panel}/cnvkit_noisy_bins.bed" ) )

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

    // ----- 4. CNV calling: CNVkit arm K (MARKER CNV_RETIRE_7B; legacy chain retired) -----
    CNV_CALLING(
        ch_final_bam,
        ch_reference,
        ch_bed,
        ch_cnv_pon_male,
        ch_cnv_pon_female,
        ch_cnv_loo_summary,
        ch_cnv_noisy_bins,
        ch_cnv_loo_summary_female,   // SEXSTRAT_V1
        ch_cnv_noisy_bins_female,    // SEXSTRAT_V1
    )

    // ----- 4b. GATK CNV calling (TGC_V1; twist_myeloid) ---------------
    // Gated on params.cnv_gatk_pon, defined only in conf/twist_apply.config.
    // Legacy panels never evaluate this block; the containsKey guard also
    // avoids undefined-parameter warnings.
    if( params.containsKey('cnv_gatk_pon') && params.cnv_gatk_pon ) {
        def gatk_ilist = "${projectDir}/assets/${params.panel}/targets.preprocessed.interval_list"
        if( params.containsKey('cnv_gatk_intervals') && params.cnv_gatk_intervals )
            gatk_ilist = params.cnv_gatk_intervals
        ch_gatk_rc_pon = Channel.value(file(params.cnv_gatk_pon, checkIfExists: true))
        // MARKER SEXSTRAT_V1: female GATK read-count PoN; male file when the panel has none.
        def gatk_pon_female = (params.containsKey('cnv_gatk_pon_female') && params.cnv_gatk_pon_female) ? params.cnv_gatk_pon_female : null
        ch_gatk_rc_pon_female = Channel.value( sexstratFemale(gatk_pon_female,
            "${projectDir}/assets/${params.panel}/gatk_rc_pon_female.hdf5", params.cnv_gatk_pon) )
        ch_gatk_ilist  = Channel.value(file(gatk_ilist,          checkIfExists: true))
        // BAF_V1: BAF SNP catalog + male-cohort background for the
        // allele-specific track (ModelSegments) and the 17p cnLOH detector.
        def baf_sites = "${projectDir}/assets/${params.panel}/snp_sites.baf.bed"
        if( params.containsKey('cnv_baf_sites') && params.cnv_baf_sites )
            baf_sites = params.cnv_baf_sites
        def baf_bg = "${projectDir}/assets/${params.panel}/baf_background.tsv"
        if( params.containsKey('cnv_baf_background') && params.cnv_baf_background )
            baf_bg = params.cnv_baf_background
        ch_baf_snp_bed    = Channel.value(file(baf_sites, checkIfExists: true))
        ch_baf_background = Channel.value(file(baf_bg,    checkIfExists: true))
        GATK_CNV_CALLING(
            ch_final_bam,
            ch_reference,
            ch_gatk_ilist,
            ch_gatk_rc_pon,
            ch_exonwise_bed,
            ch_baf_snp_bed,
            ch_baf_background,
            ch_gatk_rc_pon_female,   // SEXSTRAT_V1
        )

        // PCN_V1: PureCN purity/ploidy/integer-CN + LOH (fifth caller).
        // Reference set from the twist overlay params; NormalDB build:
        // tools/build_purecn_normaldb.sh --sex male|female (PureCN 2.16.0).
        ch_purecn_intervals = Channel.value(file(params.purecn_intervals, checkIfExists: true))
        ch_purecn_normaldb  = Channel.value(file(params.purecn_normaldb,  checkIfExists: true))
        // MARKER PCN_SEX_V1: female PureCN NormalDB; the male file until the female asset exists.
        def purecn_ndb_female = (params.containsKey('purecn_normaldb_female') && params.purecn_normaldb_female) ? params.purecn_normaldb_female : null
        ch_purecn_normaldb_female = Channel.value( sexstratFemale(purecn_ndb_female,
            "${projectDir}/assets/${params.panel}/normalDB_twist_myeloid_female_hg38.rds", params.purecn_normaldb) )
        PURECN_COVERAGE( ch_final_bam, ch_purecn_intervals )
        ch_mutect2_vcf_only = VARIANT_CALLING.out.mutect2_vcf
            .map { it -> tuple(it[0], it[1]) }
        ch_purecn_in = PURECN_COVERAGE.out.coverage
            .join( ch_mutect2_vcf_only, by: 0 )
        PURECN( ch_purecn_in, ch_purecn_normaldb, ch_purecn_intervals, ch_purecn_normaldb_female )   // PCN_SEX_V1

        // MARKER DECON_V1: exon-level arm E (DECoN); gated on params.decon_pool_male.
        // Without it, or while the pool asset is not built yet, the consensus
        // receives an empty placeholder and omits E (one log.warn).
        def decon_enabled = params.containsKey('decon_pool_male') && params.decon_pool_male && file(params.decon_pool_male).exists()
        if( params.containsKey('decon_pool_male') && params.decon_pool_male && !decon_enabled )
            log.warn "[DECON] pool not found: ${params.decon_pool_male}; arm E disabled for this run"
        if( decon_enabled ) {
            ch_decon_exons     = Channel.value(file(params.decon_exons_bed, checkIfExists: true))
            ch_decon_pool_male = Channel.value(file(params.decon_pool_male, checkIfExists: true))
            def decon_pool_female = (params.containsKey('decon_pool_female') && params.decon_pool_female) ? params.decon_pool_female : null
            ch_decon_pool_female = Channel.value( sexstratFemale(decon_pool_female,
                "${projectDir}/assets/${params.panel}/decon_pool_female.RData", params.decon_pool_male) )
            ch_paralog_exons = Channel.value(file("${projectDir}/assets/${params.panel}/paralog_limited_exons.tsv", checkIfExists: true))
            DECON( ch_final_bam, ch_reference, ch_decon_exons, ch_decon_pool_male, ch_decon_pool_female, ch_paralog_exons )
            ch_decon_genes = DECON.out.genes
            ch_decon_filtered = DECON.out.filtered   // EXON_PLOTS_V1
        } else {
            ch_decon_genes = ch_final_bam.map { m, _b, _i -> [ m, [] ] }
            ch_decon_filtered = ch_final_bam.map { m, _b, _i -> [ m, [] ] }   // EXON_PLOTS_V1
        }

        // HMF_PURPLE_V1: hmftools AMBER -> COBALT -> PURPLE (tumour-only, targeted) as
        // consensus arm H. Gated on the panel's COBALT normalisation asset existing.
        def hmf_norm_path = params.containsKey('hmf_target_norm') ? params.hmf_target_norm : "${projectDir}/assets/${params.panel}/hmftools/target_regions.cobalt_normalisation.twist_myeloid.38.tsv"
        def hmf_enabled = params.containsKey('hmf_resources') && params.hmf_resources && file(hmf_norm_path).exists()
        if( params.containsKey('hmf_resources') && params.hmf_resources && !hmf_enabled )
            log.warn "[HMF] normalisation asset not found: ${hmf_norm_path}; arm H disabled for this run"
        if( hmf_enabled ) {
            ch_hmf_loci      = Channel.value(file(params.hmf_loci,        checkIfExists: true))
            ch_hmf_gc        = Channel.value(file(params.hmf_gc_profile,  checkIfExists: true))
            ch_hmf_ensembl   = Channel.value(file(params.hmf_ensembl_dir, checkIfExists: true))
            ch_hmf_hotspots  = Channel.value(file(params.hmf_hotspots,    checkIfExists: true))
            ch_hmf_target    = Channel.value(file(params.hmf_target_bed,  checkIfExists: true))
            ch_hmf_norm      = Channel.value(file(hmf_norm_path,          checkIfExists: true))
            ch_hmf_drivers   = Channel.value(file(params.hmf_driver_panel, checkIfExists: true))
            HMF_AMBER( ch_final_bam, ch_reference, ch_hmf_loci, ch_hmf_target )
            HMF_COBALT( ch_final_bam, ch_reference, ch_hmf_gc, ch_hmf_norm )
            HMF_PURPLE( HMF_AMBER.out.dir.join( HMF_COBALT.out.dir, by: 0 ), ch_reference, ch_hmf_gc, ch_hmf_ensembl,
                        ch_hmf_drivers, ch_hmf_hotspots, ch_hmf_target, ch_hmf_norm )
            ch_purple_genes   = HMF_PURPLE.out.genes
            ch_purple_summary = HMF_PURPLE.out.summary
            ch_purple_dir     = HMF_PURPLE.out.dir   // CHROM_PAGES_V1
        } else {
            ch_purple_genes   = ch_final_bam.map { m, _b, _i -> [ m, [] ] }
            ch_purple_summary = ch_final_bam.map { m, _b, _i -> [ m, [] ] }
            ch_purple_dir     = ch_final_bam.map { m, _b, _i -> [ m, [] ] }   // CHROM_PAGES_V1
        }

        // CMX_V1: five-caller consensus + Phase-4 JSON payload.
        ch_consensus_in = CNV_CALLING.out.cnvkit_cnr                       // CNV_RETIRE_7B: no concordance input
            .join( CNV_CALLING.out.cnvkit_calls,         by: 0 )
            .join( GATK_CNV_CALLING.out.genes,           by: 0 )
            .join( GATK_CNV_CALLING.out.called,          by: 0 )
            .join( GATK_CNV_CALLING.out.denoised,        by: 0 )
            .join( GATK_CNV_CALLING.out.baf_summary,     by: 0 )
            .join( GATK_CNV_CALLING.out.baf_sites,       by: 0 )
            .join( PURECN.out.genes,                     by: 0 )
            .join( PURECN.out.summary,                   by: 0 )
            .join( ch_decon_genes,                        by: 0 )   // DECON_V1
            .join( ch_purple_genes,                       by: 0 )   // HMF_PURPLE_V1
            .join( ch_purple_summary,                     by: 0 )
        // MARKER CNV_BLACKLIST_V1: optional panel gene blacklist (consensus BLACKLISTED; no plot trigger)
        def gene_blacklist_path = "${projectDir}/assets/${params.panel}/cnv_gene_blacklist.tsv"
        ch_cnv_gene_blacklist = file(gene_blacklist_path).exists() ? Channel.value(file(gene_blacklist_path)) : Channel.value([])
        // CMX_ANNOT_V1: annotation assets -- params override, assets fallback, empty list when absent
        def cytoband_path     = params.cytoband ?: "${projectDir}/assets/references/cytoBand_hg38.txt"
        def clingen_path      = params.clingen  ?: "${projectDir}/assets/references/ClinGen_gene_curation_list_GRCh38.tsv"
        def driver_panel_path = params.hmf_driver_panel ?: "${projectDir}/assets/${params.panel}/hmftools/DriverGenePanel.${params.panel}.38.tsv"
        ch_cnv_cytoband     = file(cytoband_path).exists()     ? Channel.value(file(cytoband_path))     : Channel.value([])
        ch_cnv_clingen      = file(clingen_path).exists()      ? Channel.value(file(clingen_path))      : Channel.value([])
        ch_cnv_driver_panel = file(driver_panel_path).exists() ? Channel.value(file(driver_panel_path)) : Channel.value([])
        CNV_CONSENSUS_MULTI( ch_consensus_in, ch_cnv_loo_summary, ch_cnv_loo_summary_female, ch_cnv_gene_blacklist,
                             ch_cnv_cytoband, ch_cnv_clingen, ch_cnv_driver_panel )   // SEXSTRAT_V1 CNV_BLACKLIST_V1 CMX_ANNOT_V1
        // EXON_PLOTS_V1: per-chromosome exon figures from the consensus bins (+ DECoN brackets)
        def focal_bed = "${projectDir}/assets/${params.panel}/targets.focal_cnv.bed"
        ch_focal_bed = file(focal_bed).exists() ? Channel.value(file(focal_bed)) : Channel.value([])
        ch_exon_plots_in = CNV_CONSENSUS_MULTI.out.json
            .join( CNV_CONSENSUS_MULTI.out.genes, by: 0 )
            .join( ch_decon_filtered,             by: 0 )
        EXON_PLOTS( ch_exon_plots_in, ch_focal_bed, ch_cnv_gene_blacklist )   // CNV_BLACKLIST_V1
        // CHROM_PAGES_V1: per-chromosome CNV pages in target space (depth, BAF, PURPLE, gene exon panels)
        def cp_panel_bed = "${projectDir}/assets/${params.panel}/panel.combined.filtered.bed"
        def cp_snp_base  = "${projectDir}/assets/${params.panel}/snp_sites.baf.base.bed"
        def cp_baf_bg    = "${projectDir}/assets/${params.panel}/baf_background.tsv"
        ch_cp_panel_bed = Channel.value(file(cp_panel_bed, checkIfExists: true))
        ch_cp_snp_base  = file(cp_snp_base).exists() ? Channel.value(file(cp_snp_base)) : Channel.value([])
        ch_cp_baf_bg    = file(cp_baf_bg).exists()   ? Channel.value(file(cp_baf_bg))   : Channel.value([])
        ch_chrom_pages_in = CNV_CONSENSUS_MULTI.out.json
            .join( GATK_CNV_CALLING.out.allelic, by: 0 )
            .join( ch_decon_filtered,            by: 0 )
            .join( ch_purple_dir,                by: 0 )
        CHROM_PAGES( ch_chrom_pages_in, ch_cp_panel_bed, ch_cp_snp_base, ch_cp_baf_bg, ch_cnv_cytoband )   // IDEO_V1
        // VIZ_V1: reconCNV (styled scatters removed by MARKER VIZ_V1b; the genome overview lives in CHROM_PAGES)
        ch_viz_vcf = VARIANT_CALLING.out.mutect2_vcf.map { it -> [ it[0], it[1] ] }
        def reconcnv_tpl = params.containsKey('reconcnv_template') ? params.reconcnv_template : "${projectDir}/assets/reconcnv/reconcnv_config_twist_myeloid.json"
        ch_reconcnv_tpl = Channel.value(file(reconcnv_tpl, checkIfExists: true))
        ch_recon_in = CNV_CALLING.out.cnvkit_cnr
            .join( CNV_CALLING.out.cnvkit_calls, by: 0 )
            .join( ch_viz_vcf,                   by: 0 )
        RECONCNV( ch_recon_in, ch_reference, ch_reconcnv_tpl )
    }

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
        .join(PREPROCESSING.out.fastp_json)                                  // + fastp_json (DASH_QC_V2)
        .join(IGV_REPORTS.out.html)                                           // + igv_report (D2)
        .join(PREPROCESSING.out.dashboard)                                   // + dashboard
        .join(CNV_CONSENSUS_MULTI.out.genes)                                     // + cnv_consensus_genes (MARKER ORG_CNV_V1; MARKER ORG_CNV_V1a)
        .join(CNV_CONSENSUS_MULTI.out.segments)                                     // + cnv_consensus_segments
        .join(CNV_CONSENSUS_MULTI.out.json)                                     // + cnv_consensus_json
        .join(EXON_PLOTS.out.dir)                                            // + exon_plots_dir
        .join(CHROM_PAGES.out.dir)                                           // + chrom_pages_dir
        .join(ch_decon_filtered)                                             // + decon_filtered (placeholder when off)
        .join(ch_decon_genes)                                                // + decon_genes
        .join(ch_purple_summary)                                             // + purple_summary (placeholder when off)
        .join(ch_purple_genes)                                               // + purple_genes
        .join(ch_purple_dir)                                                 // + purple_dir
        .join(PREPROCESSING.out.sex_check)                                   // + sex_check
        .join(RECONCNV.out.dir)                                              // + reconcnv_dir
        .join(PREPROCESSING.out.spikein)                                     // + spikein (SPIKEIN_V1)

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

    // ----- 9. REPORT_BUNDLE: zip per-sample shareable bundles ---------
    // sample_ids inferred inside the module from clinical/ contents,
    // avoiding misalignment with DASHBOARD's glob-ordered output.
    REPORT_BUNDLE(
        DASHBOARD.out.clinical_dirs,
        DASHBOARD.out.assets,
    )
}
