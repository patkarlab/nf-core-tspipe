# Handoff brief — BUILD_PON_TWIST scaffold session (supersedes 2026-08-31 handoff)

**Paste this into a new chat and attach `2026-09-01_audit_memo.md` alongside
it.** The memo carries the evidence chain; this brief carries the build spec.

> Context written by you (Claude) at the end of the 2026-09-01 session. Read
> it as background, not as your own prior turn. Nothing in it has been
> re-checked in the new session.

---

## What this session builds

`BUILD_PON_TWIST`: a sex-stratified panel-of-normals workflow in
`nf-core-tspipe` for the Twist myeloid panel (TE-99430185), replacing the
legacy `BUILD_PON`. **Immediate build scope is the male stratum only** (24
conforming normals). The female arm is gated: the 24 female normals were
captured at 12-plex (males 8-plex, the validated condition) and are unusable
for reference purposes; re-hybridisation is pending a wet-lab inventory of
pre-capture library material. Architecture must support both strata; only
one is populated now.

Working style: Nikhil reviews and executes, Claude writes all code, outputs
pasted back, one major step at a time. Professional tone, no emojis.
Python 3.6-safe conventions for anything that could run in old containers;
this path is conda-only so host Python applies, but house style stands
(dry-run default, timestamped backups, [ok]/[warn]/[write]/[error], loud
assertions). Never suggest scp; Nikhil moves files via `~/inbox/from_claude`
and tarballs with repo-relative paths.

## Machines and execution

- **gandalf** (10.100.95.36, user hemat): 192 cores, 1.5 TB RAM, local
  executor. Repo `/goast/hemat_data/nf-core-tspipe/`. Conda env
  `/home/hemat/anaconda3/envs/targeted-seq`. This is where the PoN is built.
- **clinical-23** (10.100.95.23, ln1, user patkarlab-clinical): PBS Pro; repo
  `/home/patkarlab-clinical/pipelines/nf-core-tspipe/`. Where the PoN is
  eventually applied. Containers broken on compute nodes (no squashfuse);
  `conf/clinical23.config` exists for later application runs.
- **Everything in this workflow runs from conda, no containers**: cnvkit
  0.9.12, GATK 4.6.2.0, versions matched on both machines. PoN must be built
  and applied with the same versions.
- Long runs on gandalf: `setsid bash -c '...' < /dev/null > /tmp/x.log 2>&1 &`
  then `tail -f`. Never plain nohup (suspends), never screen -r.
- Lustre: keep `NXF_CACHE_DIR` on local disk; work dir on shared storage.

## Asset state (verified 2026-09-01, byte-identical on both machines;
## cross-machine manifest digest 7b3d3a537f37d95364d3f6157a746192)

`assets/twist_myeloid/` — key files:
- `panel.combined.filtered.bed` (8,821 rows, md5 01d8e8ce...): **the single
  target artifact for this workflow.** Both the CNVkit targets and the GATK
  interval list derive from this one file. It is panel.combined minus 10
  probes (8 measured-excluded exon labels) minus 71 backbone tiles. Do not
  use CNVkit exclude mechanics or GATK XL lists — the filter lives in the
  BED.
- `exclusions.exons.tsv` / `exclusions.backbone.tsv`: panel-definition data
  with criterion and provenance headers. Regenerable via
  `tools/derive_exclusion_list.py`.
- `snp_sites.baf.bed` (374 rows: 370 x 17p + 4 autosomal): `-L` input for
  CollectAllelicCounts. Sites are 120 bp probe windows; the informative SNP
  subset is determined empirically from the normals, not from rsID.
- `targets.exonwise.bed` (1,795), `backbone.hg38.bed` (3,047): reporting and
  QC spaces; the excluded exons deliberately REMAIN in exonwise (coverage
  reporting still sees them) and in the variant-calling BEDs.
- `bin/build_panel_assets.py` (md5 7b550a5d..., patched, identical on both
  machines).

## Input data

- **BAMs staged**: `/goast/hemat_data/pon_twist/bams/` — 48 x `*.final.bam`
  + 48 indexes (hardlinks; safe from work-dir cleanup). Index naming may be
  either `X.final.bam.bai` or `X.final.bai`; glob for both.
- Sex: filename prefix (Female*/Male*) verified against two orthogonal
  genomic signals; `/goast/hemat_data/pon_twist/pon/cnvkit_pon_sex_assignment.tsv`
  also exists from the legacy run. 24F/24M, no discordants.
- Legacy PoN (pooled, post-hoc split) at `/goast/hemat_data/pon_twist/pon/`
  — baseline for comparison only. `cnvkit_pon_male.cnn` is also the spread
  source for the exclusion criterion.
- FASTQs archived: `s3://hemat/FastqArchival2026/` (gandalf s3cfg only).

## The two decisions the session opens with

1. **Samplesheet entry**: recommend a sheet accepting BAM or FASTQ rows;
   BAM rows bypass PREPROCESSING entirely. Current build then starts from
   the staged BAMs in minutes instead of ~7 h, and future criteria changes
   make PoN re-derivation cheap. FASTQ path reuses PREPROCESSING unchanged.
   Sheet needs a `sex` column (source above).
2. **CollectAllelicCounts cohort**: males-only (consistent capture, but ~12
   informative samples per het site) vs all 48 with a per-site depth filter
   (allelic ratio is plausibly less plex-sensitive than depth). Genuinely
   open; decide before coding that module, not by reflex.

## What the workflow must contain (male stratum now, female-ready)

- New workflow + entry point; nothing in the `myeloid` / `myeloid_cnv`
  clinical path modified. Clean switch only after validation.
- CNVkit reference per stratum from `panel.combined.filtered.bed`; no `-y`,
  `params.male_reference` retired for this panel. 24/stratum is comfortable.
- GATK chain per stratum: PreprocessIntervals (from the same filtered BED)
  -> CollectReadCounts per sample -> CreateReadCountPanelOfNormals.
  (AnnotateIntervals GC correction: decide at module time.)
- CollectAllelicCounts over `snp_sites.baf.bed` per sample + an aggregation
  step producing the per-site reference-bias background table (cohort per
  decision 2).
- Per-stratum CNV_LOO_QC with `--panel twist_myeloid` passed explicitly
  (its default is `myeloid`). Known quirk: its publishDir creates an empty
  `references/<panel>/` in outdir while work-dir files are correct — keep
  the seed-script workaround.
- Optional scope if time allows: per-sample capture-conformity gate
  (NPM1_exon_11 depth, JAK2_exon_15 depth, mean insert size) — three
  numbers per library, the cheap batch-QC this month's failure would have
  been caught by.

## Nextflow footguns (all previously paid for)

- `conf/modules.config` `withName:` selectors override in-module container
  directives. **Every new process needs an explicit withName block with
  conda handling** or it silently inherits container settings that break on
  clinical-23. This exact failure cost hours on 31 Aug.
- Reference files: `Channel.value(file(...))`, never `Channel.fromPath()`.
- `.join(remainder:true)` chains start from a driver channel that has every
  sample by construction.
- Panel BEDs are FAI-sorted with contiguous chromosomes; the filtered BED
  already satisfies this — do not re-sort with `sort -k1,1`.
- Nextflow does not hash `bin/` script content into resume keys.
- mosdepth anywhere in QC: `--flag 772` (duplicates INCLUDED, lab
  convention; default 1796 excludes them).

## Carried-forward ledger (not this session's scope)

Female arm re-hybridisation decision (wet-lab inventory pending); Twist
correspondence draft (male 8-plex claims only; ~70 tiles not 830; exon list
per criterion; multi-mapping tiles like bb.chr9.64881493 cited as
sequence-context); `backbone_depth_qc.py` BAM-discovery fix before any
rerun; Male12 (shortest insert, 131.8 bp) watch item in the LOO; male pool
membership + whether Male1-8 are the validation-arm libraries; chrX
per-stratum filtered-BED question (12/71 excluded tiles are chrX; the 30x
male floor is ~60x diploid-equivalent) — deferred to the female
re-derivation; audit memos for future sessions go to `docs/audit/<date>/`.
