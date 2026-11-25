# Changelog

All notable changes are documented in this file. The format is loosely
based on [Keep a Changelog](https://keepachangelog.com/) and the project
follows [semantic versioning](https://semver.org/).

## [Unreleased]

The v1.1 working line. Nothing here is part of a tagged release. Items deferred from 1.0.0 are
listed under "Deferred to 1.1" below.

### Fixed

Per-arm B-allele detector, marker `BAF_HETLOSS_V1`. An arm whose loss of heterozygosity was
present in more than about 80 percent of the cells, or whose deletion was present in more than
about 89 percent, came out `INDETERMINATE`: the detector looked only at sites with an allele
fraction between 0.10 and 0.90, and such an arm has none left. A heterozygosity-loss test now
judges every autosomal arm on its heterozygous loci against the number expected from the normals,
and on its residual sites. The arm is called with its clonal fraction where the residual sites
account for the missing heterozygous loci; it is reported as `ROH`, without a vote in the
consensus, where nothing is left to measure; and a run over part of an arm is reported with its
coordinates as a low-confidence call. An arm the existing statistic calls keeps its result unless
its heterozygous loci are significantly depleted. Checked on synthetic samples only; validation on
patient data is outstanding. See `docs/memos/memo21_high_fraction_loss_of_heterozygosity.md`,
`docs/sops/baf_het_loss.md` and `docs/audit/2026-11-25/`.

Site configuration, marker `PORTABLE_V1`. The hmftools reference paths were written into the panel
overlay with their location on the development server, where no site profile could redirect them;
`nextflow.config` carried paths of that server as defaults; and a further server had to register
its profile in `nextflow.config`, a file of the release. The site profile now names the hmftools
resource bundle in `hmf_root`, the defaults are neutral, and the new profile `site` reads
`conf/site.config`, which git ignores, so that a server is configured without editing a tracked
file. A parameter file written for v1.0.x keeps working. See
`docs/memos/memo22_site_paths_and_review_findings.md`.

A launch without a panel overlay stopped with a workflow construction error. It now stops before
any task with a message that names `conf/twist_apply.config`.

`launch_tspipe.sh` tested the local VariantValidator stack although the pipeline uses the public
service; it now tests the endpoint the pipeline uses. The launchers default to the checkout they
are in.

### Changed

`<sample>.baf.summary.tsv` keeps its 18 columns in place and gains 14; `verdict` can read `ROH` and
`scope` can read `segment`. `<sample>.baf.sites.tsv` gains `site_class`, and the site rows of the
consensus JSON gain the same value as a seventh element. The consensus gives a verdict of the
heterozygosity-loss test only to genes inside its run. The dashboard (builder 0.5.4-hetloss), the
genome-wide figure, the chromosome pages and the 17p page show the basis of such a call, and the
dashboard warns when a sample carries a second genome. The parameter `baf_het_loss`, default
`true`, switches the test; `false` restores the previous verdicts.

Golden regression: because of the added columns the B-allele summaries of two runs are no longer
identical line by line. `tools/compare_baf_arms.py` compares them on the columns that existed
before and fails on any difference the new test does not account for.

The default output directory is `results` under the place of launch; it was a path of the
development server. `tools/launch_clinical23.sh` passes the site parameter file when it exists and
no longer requires it.

### Added

`tests/baf/`: a simulator of synthetic samples, a regression test, a module test, a fuzz test and
a clone-fraction titration of the per-arm detector, with a mode that plants events in a real
sample. `tests/stub/run_stub_site.sh`: a throw-away site built from the template and a stub run of
the whole workflow. `tools/rescan_baf_arms.py`: the current detector over the stored files of
earlier runs, for a look-back. The profile `site` and a rewritten `conf/site_template.config`.

### On main since v1.0.2 without an entry

Recorded here from the code on 25 November 2026 so that they are not overlooked at the next
release; see section 5 of memo 22. Commit 438d308, labelled as documentation, also changed the
variant filter (marker `HOTSPOT_EXEMPT_V1`: `LOW_CALLERS` and `LOW_DEPTH` exempt every hotspot
residue of `assets/myeloid_hotspots.tsv` with a non-synonymous consequence, where only the U2AF1
hotspots were exempt), the NPM1 line of that table, and the variant browser of the dashboard
(marker `DASH_CEBPA_BZIP_V1`, builder 0.5.3-cebpa). These have no audit record and are in no
release. Releases v1.0.1 and v1.0.2 have no entry in this file either.

## [1.0.0] — 2026-09-10

Clinical freeze. Frozen on the development host on 2026-09-10, deployed to the clinical HPC and
accepted on 2026-09-11 after a cross-host golden regression. This is the version used for
reporting on the Twist myeloid panel. `docs/RELEASE_NOTES.md` holds the release definition;
`docs/sops/SOP-TSPIPE-001.md` governs installation, operation and change control.

### Added — release engineering

- **Full containerisation.** `local/tspipe-host:v1.1` (`containers/tspipe-host/`) carries the
  seven validated conda environments under `/opt/envs/` and Strelka2, ANNOVAR, OncoVI and the
  VarDict helpers under `/opt/`. No process depends on a conda environment, a `beforeScript` PATH
  export or a host tool. `conf/containers.config` assigns the image and the per-process `PATH`;
  site profiles carry only paths, executor settings and resources.
- **Release artefacts.** `docs/release/image_checksums.md5` (17 images) and
  `docs/release/reference_manifest.tsv` (44 reference entries with size and md5).
- **Second site.** `conf/clinical23.config` (PBS Pro), `tools/make_sandboxes.sh`,
  `tools/verify_install.sh` (installation qualification) and `tools/compare_runs.py` (content-aware
  run comparison, the golden-regression method).
- **Controlled documentation.** `docs/sops/SOP-TSPIPE-001.md` and its PDF render: dependencies,
  installation from nothing, IQ/OQ, routine operation, troubleshooting, frozen configuration and
  change control, porting, backup and restore, plus a site annex.
- Nextflow pinned at `!>=25.10.4`; `manifest.version` set to `1.0.0`.

### Added — annotation

- **CAVA 2.0.15** against the MANE 1.5 GRCh38 RefSeq catalog, for clinical HGVS nomenclature.
  Card and report nomenclature preference is VariantValidator, then CAVA, then VEP.
- **MANE-Select-first consequence selection** in VEP output, replacing severity-first selection.
- **MNV merge**: multi-nucleotide variants decomposed by the callers are reconstructed (gap
  <= 2 bp) and added alongside their tagged components, with caller support restored.
- **Alternative-transcript table**: every VEP transcript block retained in a `VEP_Transcripts`
  column and shown in the variant detail view.
- **External annotators**: GeneBe, MobiDetails and CancerVar on by default; OncoKB opt-in with a
  token supplied through an untracked credentials file.
- **Spike-in sites**: genotyping and coverage of the panel's regulatory and germline-risk spike-in
  targets, with their own report tab.

### Added — copy number

- Six-arm sex-stratified consensus: CNVkit, GATK ModelSegments, DECoN (exon level), PureCN,
  PURPLE (hmftools AMBER/COBALT, tumour-only targeted) and a per-chromosome-arm B-allele-frequency
  detector for cnLOH and allelic imbalance.
- Consensus gene table annotated with cytoband, ClinGen haploinsufficiency and triplosensitivity,
  and driver role; CNV gene blacklist asset.
- Visualisation: genome-wide overview (depth, BAF arm medians, PURPLE copy number), target-space
  chromosome pages with cytoband strip and per-gene exon panels, a dedicated 17p page, and
  reconCNV as an interactive view. CNV report tab reorganised into sub-tabs.

### Added — QC and filtering

- **Genotype-based sex check** from chrX heterozygosity with depth confirmation. A mismatch
  against the samplesheet forces a `REVIEW` verdict; it never stops the run.
- **QC page rewrite**: median of per-exon coverage as the headline metric, a 200x reportability
  tier above the 100x floor, a known-low-capture exon asset derived from the normals, read-level
  limits from fastp, and an explicit verdict (`PASS` / `PASS WITH LIMITATIONS` / `REVIEW`).
- **Cohort variant panel-of-normals blacklist** built from the 48 capture normals
  (`tools/build_variant_pon_blacklist.py`): 1,602 automatically derived entries across four tiers,
  with hotspot residues exempt. Recurrent artefacts that previously reached the clinical table are
  now filtered.
- Coding synonymous variants are reportable and tagged rather than dropped; ClinVar
  benign / likely-benign calls are demoted unless at a hotspot; blacklisted calls have their own
  report tab with reason and evidence.

### Changed

- **Hardening**: samplesheet validation before any task is scheduled; `pipefail` on every task
  shell; a BAM integrity check on the final alignment; ANNOVAR failures and missing databases are
  fatal, with an explicit escape flag.
- **Determinism**: `PERL_HASH_SEED=0` and `PERL_PERTURB_KEYS=0` for VEP, making its output
  byte-reproducible across runs.
- **COSMIC identifiers** are taken from VEP's `Existing_variation`; the ANNOVAR `cosmic103` table
  carries occurrence counts, not identifiers.
- **Caller thresholds moved out of the site profile.** `ext.min_var_freq` for VarScan now lives in
  `conf/modules.config`, which both sites load. A clinically meaningful threshold in a site profile
  had produced different variant sets on the two hosts.
- Legacy CNV modules retired from the DAG (z-score, concordance, annotated tables, the old CNV
  clinical report); `clinical/cnv/` is the only copy-number deliverable.
- README rewritten for this release; `docs/INSTALL.md`, `docs/deployment.md` and `docs/testing.md`
  are retained as historical records of the pre-containerisation layout.

### Fixed

- **ANNOVAR / VEP merge key**: differing indel representation left roughly one row in eight without
  caller attribution and stripped ClinVar and COSMIC from indels. Keys are now built from the
  `table_annovar` `-vcfinput` columns; orphan rows went to zero.
- **ALT-aware alignment**: the bwa-mem2 index was missing its `.alt` file, producing MAPQ-0
  alignments at paralogous loci.
- **CSF3R misannotation** from VEP `--pick` selecting a neighbouring gene's transcript.
- **reconCNV in the container**: missing `libtiff.so.5` for PIL via bokeh, fixed in image v1.1.
- **`nextflow config` on the container profile**: a closure in `conf/containers.config` resolved at
  run time but broke static config inspection; replaced with literal strings.
- **PBS resource requests**: `clusterOptions` suppressed Nextflow's own `-l select=` line, so tasks
  ran with the queue default and were killed.
- U2AF1 rescue, FLT3 tab IGV links, report column widths and several dashboard layout defects.

### Known findings

- **PURPLE segmentation depends on the C library.** AMBER and COBALT outputs are byte-identical
  across hosts, but the PCF step returns a slightly different segment set between an el9 host and
  the Ubuntu 22.04 image, with purity and ploidy unchanged and copy numbers shifted by about 0.005.
  The image, not the host, is therefore the reference for regression.
- **reconCNV** writes a placeholder HTML on failure rather than failing the run; it is a QC view.
- **FLT3_ITD_EXT** does not write `final_FLT3_ITD.vcf`; its directory output is optional and the
  other three detectors carry the ensemble.
- **17p haplotype phasing (MoChA)** was built and evaluated end to end, then parked: the panel's
  17p SNP spacing leaves phase between consecutive informative sites near random. The container
  and inputs are retained.

### Validation

- Eight-sample Twist validation cohort on the frozen image: 451 tasks, no failures, 2 h 33 min.
- Image-to-image regression: 1,233 files identical; every clinical, consensus, PURPLE and BAF
  output identical (`docs/audit/2026-09-11/run8_v1_vs_v11.md`).
- Cross-host regression, development host against clinical HPC on the same image: clinical tables
  identical on all eight samples, BAM records byte-identical, remaining differences confined to
  timestamped logs and files embedding a creation time
  (`docs/audit/2026-09-11/run8_gandalf_vs_clinical23_v2.md`).

### Deferred to 1.1

Re-run of the 48 normals through the current pipeline with a blacklist and `baf_background`
rebuild; BAF segmentation with a beta-binomial detector; female normals re-capture and a female
panel of normals; capture conformity gate; asset reconciliation; ClinVar refresh; FLT3_ITD_EXT
final VCF; per-run calibration of the 17p window depth.

## [0.1.0-dev] — 2026-05-19

The pre-1.0 working line, superseded by 1.0.0. Recorded here as the state at the end of the
initial port from the Python orchestrator.

### Per-sample workflow (TSPIPE)

- **Preprocessing**: fastp → bwa-mem2 → Picard MarkDuplicates → GATK4 BQSR → ABRA2 indel realignment.
- **QC**: Picard HsMetrics, mosdepth (with duplicates included per clinical convention), per-sample dashboard.
- **8-caller somatic ensemble**: Mutect2, VarDict, VarScan, FreeBayes, Strelka2, Platypus, Pindel, DeepSomatic. Consensus via SomaticSeq.
- **U2AF1 paralog rescue**: dedicated module recovers calls in the U2AF1 region that paralog collapse would otherwise drop.
- **4-caller FLT3-ITD ensemble**: FLT3_ITD_EXT, getITD, filt3r, Pindel-region. Pindel-region added 2026-05-19, raising consensus confidence on real ITDs.
- **CNV calling**: CNVKit against a sex-stratified panel-of-normals selected per-sample from `meta.sex`. Leave-one-out QC, scatter plots, concordance, and annotated clinical CNV TSV.
- **Annotation**: VEP + ANNOVAR → curated SNV blacklist filter → VariantValidator HGVS verification → OncoVI oncogenicity scoring.
- **IGV pileup reports**: per-sample interactive HTML for case review, patched in place by the cohort dashboard step to support hash-router deep links from the per-sample report.
- **Cohort HTML dashboard**: static dashboard at `<outdir>/cohort_index.html` with a row per sample, linking to a tabbed per-sample report at `<outdir>/<sample>/clinical/<sample>_report.html`. Tabs: Overview, QC (HsMetrics + per-exon coverage), Variants — Clinical, Variants — All Filtered, FLT3, CNV (CNVkit plots + clinical TSV), IGV, Reporting, Files. Vendored Bootstrap/jQuery/DataTables/Chart.js under `<outdir>/assets/`; no external CDN dependencies. Source: `dashboard_builder` v0.4.6 vendored at `bin/dashboard_builder/`. Runs on the host via `executor='local'`, reusing the same conda env as VARIANT_VALIDATOR/ONCOVI/FLT3_TO_VARIANTS (`params.legacy_python_env`, override via `params.dashboard_python`). See `docs/dashboard.md` for the full reference.
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

[Unreleased]: https://github.com/patkarlab/nf-core-tspipe/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/patkarlab/nf-core-tspipe/releases/tag/v1.0.0
