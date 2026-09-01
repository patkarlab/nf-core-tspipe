# BUILD_PON_TWIST execution record -- Twist myeloid panel (TE-99430185)

Date: 2026-09-01 (afternoon session; follows the exclusion-analysis memo of the same date)
Machine: gandalf, user hemat, repo /goast/hemat_data/nf-core-tspipe (HEAD f3fef83 pre-commit)
Operator: Nikhil (review/execute); code authored by Claude

## Scope

First production run of the new BUILD_PON_TWIST entry workflow: sex-stratified
panel-of-normals for the Twist myeloid panel, male stratum only (24 conforming
8-plex/16 hr normals). Female arm gated in data (include_in_pon=false, 24
nonconforming 12-plex captures) pending re-hybridisation.

## What was added

- workflows/build_pon_twist.nf (entry: `-entry BUILD_PON_TWIST`),
  subworkflows/local/bpt_stratum.nf, 13 modules/local/bpt_*.nf.
- bin/bpt_check_samplesheet.py, bin/aggregate_baf_background.py (per-position
  BAF aggregation), bin/capture_conformity_gate.py (report-only gate),
  tools/make_pon_twist_samplesheet.py.
- Patches (idempotent, anchor-based, applied 2026-09-01 15:59, backups
  main.nf.bak_bpt_entry_20260901_155938 and
  conf/modules.config.bak_bpt_modules_20260901_155938):
  - main.nf: one include line, marker BPT_ENTRY_V1.
  - conf/modules.config: marker BPT_MODULES_CONFIG_V1; umbrella
    `withName: 'BPT_.*' { conda = params.legacy_python_env; container = null }`
    plus per-module publishDir blocks. beforeScript deliberately untouched.
- Samplesheet pon_samplesheets/twist_normals_48.csv (48 rows; 24 male
  included, 24 female excluded with note).

## Key design decisions encoded

- Female gate lives in the samplesheet (include_in_pon), not in code.
  Per-sample steps run on all 48 rows; reference construction filters
  sex + include and fails loudly on an empty stratum.
- No `-y` anywhere; sex handled by stratification. params.male_reference
  retired for this panel.
- Conda-only execution: launch carries `-c conf/twist_pon_noncontainer.config`
  (gandalf profile alone would run singularity images with cnvkit 0.9.10 /
  GATK 4.5.0.0 and violate build/apply version parity).
- Fasta defaults to params.reference (hg38_broad masked) so the PoN is built
  on the alignment reference; --pon_fasta overrides for cross-site use.
- Antitargets empty by design (in-panel backbone provides genome-wide bins).
- GATK AnnotateIntervals GC track always computed; consumption by
  CreateReadCountPanelOfNormals gated by pon_gc_correction=true (this run: on).
- BAF cohort decision (handoff item 2) parameterised: this run
  pon_baf_cohort=male; flipping to 'all' re-runs only the aggregation.
- Conformity gate REPORT-ONLY: thresholds npm1_min=100, jak2_min=100,
  insert_min=150.

## Run record

- Launch: setsid/disown, NXF_CACHE_DIR=/home/hemat/.nextflow_cache_bpt,
  --keep_intermediates true (guards reference artifacts from the TSPIPE
  onComplete sweeper, whose tail is unreviewed for this layout).
- Nextflow 25.10.4. 202 tasks, 0 failures, 22 m 6 s wall, 46.9 CPU h.
  Completed 2026-09-01 16:23:23 IST.
- Outdir: /goast/hemat_data/pon_twist/build_v2 (publish mode link; hardlink
  counts confirmed all publish targets, including the triple-published
  loo_bin_noise_profile.tsv).

## Tool versions (build_versions.txt; parity invariant satisfied)

python 3.10.14 (targeted-seq env), cnvkit 0.9.12, GATK 4.6.2.0
(HTSJDK 4.2.0, Picard 3.4.0), mosdepth 0.3.10, samtools 1.21.
The PoN must be applied with cnvkit 0.9.12 / GATK 4.6.2.0.

## Conformity gate results (48 samples, report-only)

23 WARN, 25 PASS.
- Male12: insert 131.1 bp < 150 (known watch item; survey value 131.8).
- Male13: insert 148.9 bp < 150 (new marginal flag, 1.1 bp under a round
  threshold).
- 21/24 females WARN on sentinel depth (12-plex collapse signature).
- 3 females PASS the two-sentinel screen: Female11 (181.4x/104.2x),
  Female12 (351.0x/311.0x), Female18 (247.7x/204.1x). Within-pool
  competition variance at 12-plex; exclusion remains protocol-level via
  include_in_pon (backbone-tile evidence), not this gate. These three are
  natural paired comparators (same library, both protocols) when the
  re-hybridised female arm runs, and further support the kinetic mechanism
  for the Twist correspondence.

## LOO QC (male stratum, 24 iterations)

- 6,100 target bins (targets.split.bed); pooled reference
  cnvkit_pon_male.cnn.
- Noisy-bin blacklist: 933 bins (15.3%). Decomposition: chrX 409, of which
  ~328 are X-linked driver exons (SMC1A 47, STAG2 42, KDM6A 37, BCORL1 33,
  BCOR 30, UBA1 26, DDX3X 26, PHF6 21, BTK 20, PIGA 16, ZRSR2 12, ALAS2 11,
  GATA1 7) -- hemizygous half-depth variance in an all-male cohort, expected;
  remainder predominantly individually-named backbone tiles (~19-20% of the
  ~3,000 filtered tiles; exact split in assets/twist_myeloid/
  pon_male_v2.stats.txt). This variance blacklist is a stricter, different
  metric than the 90.6% depth-usability figure from the 16 hr validation arm.
  ~2,400 clean genome-wide tiles remain (~1 per 1.2 Mb), ample for
  segmentation. Example blacklisted tile bb.chr1.629966 (fp_any 25%) sits in
  chr1 pericentromeric segdup territory.
- Per-sample LOO false-positive segments: range 2-4 across the cohort
  (segment totals 46-49). Male12: 2 FP / 46 segments (mid-pack). Male13 below
  the top eight. No outlier; both retained. Heatmap reviewed without banding.

## BAF background (reference-bias catalog)

Per-position aggregation over snp_sites.baf.bed (md5 5528b7b1..., 374
intervals, 44,880 positions), cohort male n=24, min_depth 20, het band
0.20-0.80, min_het_samples 3. 298/374 probes informative (79.7%) --
sufficient het-SNP density for arm-level 17p cnLOH work.

## Artifacts seeded to assets/twist_myeloid/

cnvkit_pon_male.cnn, cnvkit_loo_summary.tsv, cnvkit_noisy_bins.bed,
loo_bin_noise_profile.tsv, gatk_rc_pon_male.hdf5, baf_background.tsv,
targets.preprocessed.interval_list, targets.gc.annotated.tsv,
pon_build_versions.txt, pon_male_v2.md5 (manifest), pon_male_v2.stats.txt.
Byte copies from the build tree; md5 parity verified at seeding.

## Open / carried items

1. chrX masking vs male CNV sensitivity: if TSPIPE hard-masks blacklisted
   bins, deletion sensitivity for STAG2/BCOR/ZRSR2-class events in male
   samples depends on segment-level integration across remaining X bins.
   Add to the TSPIPE-vs-production CNV comparison checklist. The female
   stratum (diploid X) will resolve this cleanly.
2. Female stratum: pending wet-lab inventory and re-hybridisation; rebuild is
   `--pon_strata female` (or male,female) on the updated samplesheet.
3. BAF cohort revisit: rerun aggregation with pon_baf_cohort=all once
   conforming female data exist.
4. clinical-23 mirror: replicate patches + scaffold, rerun builder, verify
   manifest md5 parity (pon_male_v2.md5 is the comparison target).
5. Cosmetic: remove five redundant .first() calls in
   workflows/build_pon_twist.nf (benign WARNs).
6. FASTQ samplesheet rows hard-fail by design in v1; PREPROCESSING wiring is
   a follow-up if ever needed.
7. Repo-root vendor BEDs (probes_ok_*.bed) and normals/, qc/ data dirs left
   uncommitted; decide placement later.
