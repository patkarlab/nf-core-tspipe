# Changelog

All notable changes are documented in this file. The format is loosely
based on [Keep a Changelog](https://keepachangelog.com/) and the project
follows [semantic versioning](https://semver.org/).

## [Unreleased] — 0.1.0-dev

The pre-1.0 working line. Features below are present and validated on
gandalf; the version stays at `0.1.0-dev` until the first tagged
GitHub Release.

### Per-sample workflow (TSPIPE)

- **Preprocessing**: fastp → bwa-mem2 → Picard MarkDuplicates → GATK4 BQSR → ABRA2 indel realignment.
- **QC**: Picard HsMetrics, mosdepth (with duplicates included per clinical convention), per-sample dashboard.
- **8-caller somatic ensemble**: Mutect2, VarDict, VarScan, FreeBayes, Strelka2, Platypus, Pindel, DeepSomatic. Consensus via SomaticSeq.
- **U2AF1 paralog rescue**: dedicated module recovers calls in the U2AF1 region that paralog collapse would otherwise drop.
- **4-caller FLT3-ITD ensemble**: FLT3_ITD_EXT, getITD, filt3r, Pindel-region. Pindel-region added 2026-05-19, raising consensus confidence on real ITDs.
- **CNV calling**: CNVKit against a sex-stratified panel-of-normals selected per-sample from `meta.sex`. Leave-one-out QC, scatter plots, concordance, and annotated clinical CNV TSV.
- **Annotation**: VEP + ANNOVAR → curated SNV blacklist filter → VariantValidator HGVS verification → OncoVI oncogenicity scoring.
- **IGV pileup reports**: per-sample interactive HTML for case review.
- **Clinical deliverable tree**: `<outdir>/<sample>/clinical/` assembled by the reporting subworkflow; scratch directories pruned by the `workflow.onComplete` hook.

### Resource and reference handling

- **Masked hg38** is used for every step including variant calling. See `docs/clinical_decisions.md` for the U2AF1 paralog rationale.
- **Panel-namespaced asset layout**: PoN, noise profile, and noisy-bin BED live under `assets/<panel>/` with an asset-default fallback at `${projectDir}/assets/${params.panel}/...` for every CNV input.
- **Sex declared per-sample** in the samplesheet (`sex` column: `male` / `female` / `unknown`); replaces production's coverage-based inference.
- **CNV input fallbacks**: `cnv_loo_summary`, `cnv_noise_profile`, `cnv_noisy_bins` resolve to asset defaults unless overridden on the CLI. The historical `--cnv_pon` flag is deprecated and has no effect.

### PoN-build workflow (BUILD_PON)

- Standalone workflow entry that replaces `12c_cnv_loo_qc.py`, `12c_build_sex_pon.py`, and the `run_masked_realign.sh` chain.
- Produces `cnvkit_pon_male.cnn`, `cnvkit_pon_female.cnn`, `cnvkit_loo_summary.tsv`, `loo_bin_noise_profile.tsv`, `cnvkit_noisy_bins.bed`, and `cnvkit_pon_sex_assignment.tsv`.
- Normals samplesheet supports an `exclude` column to keep a sample in preprocessing but drop it from the PoN aggregation (used for known clonally-aberrant lines like OCIAML3).

### Engineering and validation

- All 40 modules in `modules/local/` carry `stub:` blocks for DAG-level validation in `-stub` mode.
- Documented multi-sample baseline: **16 samples, 2 h 19 min wall time on gandalf** (192 cores, 1.5 TB RAM), 2026-05-19.
- Two-workflow architecture (TSPIPE and BUILD_PON) declared in `main.nf` with a post-run `workflow.onComplete` hook that prunes scratch directories and warns on filesystem-mismatch publishDir fallbacks.

### Known limitations

- `FLT3_ITD_EXT` exits with `NO ITD CANDIDATE CLUSTERS GENERATED` on ITD-negative samples, recorded by Nextflow as a task failure. All other modules complete normally.
- Bundled `test` profile references missing `assets/test/` fixtures and should not be used. Use `<yoursite>,singularity -stub` with a real samplesheet for structural validation.

### Documentation

- Comprehensive install reference at `docs/INSTALL.md`.
- Per-document references: `docs/usage.md`, `docs/output.md`, `docs/usage_pon.md`, `docs/clinical_decisions.md`, `docs/testing.md`, `docs/deployment.md`.

## Pre-release porting history

The pipeline was ported from the in-house Python orchestrator
`run_sample_pipeline.py` to Nextflow DSL2 over multiple sessions. The
work is recorded in detail under `docs/audit/` (per-session notes) and
in the git log; this summary covers the milestones.

- **Initial scaffold**: 7 subworkflows (preprocessing, variant_calling, flt3_itd, cnv_calling, sv_calling, annotation, reporting) and 38 module files, most as stubs. Python helpers copied into `bin/` for consensus, filter, and organize logic.
- **Module-by-module porting**: variant callers, FLT3-ITD ensemble, annotation, and reporting filled in across sessions.
- **CNV wiring (2026-05-15 / 2026-05-16)**: six previously-unwired CNV modules attached to the per-sample DAG; panel-namespaced asset layout established; `gandalf.config` cleaned of CNV-path overrides so asset-default fallbacks fire.
- **Stub-block sweep (2026-05-16)**: stub blocks added to all 40 modules in one pass, making `-stub` mode usable for DAG-level validation.
- **End-to-end validation (2026-05-19)**: 16-sample run completes in 2 h 19 min on gandalf with clean clinical deliverables across all samples.
- **Documentation hardening (2026-05-19 / 2026-05-20)**: README rewritten, `docs/INSTALL.md` authored as the canonical fresh-server reference, `docs/output.md` and `docs/usage.md` rewritten against current configs, `docs/PORTING_STATUS.md` archived to `docs/audit/2026-05-19/`.

### Dropped from the port

The following components from the production tree were intentionally
not ported:

- **Alternative CNV callers** never wired into the production runner: `12d_cn_mops.R`, `12d_panelcn_mops.R`, `12d_ifcnv.py`, `12d_ifcnv_precompute.py`.
- **Lymphoma-specific scripts** (out of scope for the current leukaemia focus): `lymphoma_fusion_scanner.py`, `run_batch_fusion_scan.py`, `build_fusion_pon.py`, `run_lymphoma_batch.sh`.
- **Orchestration scripts** replaced by Nextflow: `run_sample_pipeline.py`, `run_batch_preprocessing.py`, `cleanup_intermediates.py`.

[Unreleased]: https://github.com/patkarlab/nf-core-tspipe/compare/HEAD...HEAD
