# 2026-09-06 evening session -- memo addendum

Repo: /goast/hemat_data/nf-core-tspipe (gandalf). Session start HEAD b84d8b1;
session end HEAD 84486d1 plus the female PureCN asset commit (see 6).
Companion documents: docs/audit/2026-09-06/gap_register_2026-09-06.md,
docs/sops/{sex_check,sexstrat,cnv_consensus_cmx_v2,purecn_sex}.md.

## 1. Course change

The eight-case validation run (twist_val_8_fastq.csv, all cases sex=male)
was launched at 18:0x and stopped by decision minutes later (SIGTERM,
Nextflow cancelled 8 tasks): module work first, validation once the CNV
arms are complete. A sweep of every project chat since February produced
the gap register (17 items not in the handoff). Sequencing decided from its
dependency graph: sex inference -> sex-stratified references -> consensus
tiering -> PureCN by sex; visualization, DECoN module and dashboard follow.

Nikhil holds: validation-case sex and known findings, Twist redesign
letter (A9, removed from the register), curation of driver/hotspot tables.

## 2. SEX_CHECK (SEX_CHECK_V1) -- commit 07228a8

- bin/sex_check.py infers sex from MOSDEPTH regions.bed.gz (already run at
  MAPQ 20, flag 772): each region normalised to the autosomal median of its
  own class (exon vs backbone), chrX/chrY medians of the normalised depths
  give X/A and Y/A; PARs excluded on both chromosomes; non-canonical
  contigs skipped. targets.exonwise.bed has 227 chrX regions and no chrY,
  so the call rests on X/A; Y/A reports NA. Thresholds: male X/A <= 0.70,
  female >= 0.80, Y present >= 0.15, absent < 0.05.
- Real data before wiring: Male24 X/A 0.563, Female15 (AT-dropout pool)
  1.023. In-pipeline: 26CGH60-TwistMyVal X/A 0.543 -> male.
- PREPROCESSING: SEX_CHECK after MOSDEPTH; withResolvedSex() rewrites
  meta.sex on every PREPROCESSING emit. Samplesheet male/female always
  wins; 'unknown' takes the inference; MISMATCH is logged and written to
  the TSV, never applied. meta's key set is unchanged, so -resume hashes
  move only when the value moves. Output <outdir>/<sample>/sex_check/.
- The script never fails a sample (indeterminate row on error).
- Observation: log.info inside the map closure appeared 13-14 times in the
  console log; .nextflow.log carries it once. Console repeats are the
  non-TTY progress redraw. A per-sample gate (V1a) was added anyway.
- Samplesheets: twist_val_8_fastq.csv now sex=unknown for all eight cases;
  twist_val_1_fastq.csv (26CGH60) for smoke tests.

## 3. Sex-stratified references (SEXSTRAT_V1) -- commit e24099b

- Live now: gatk_rc_pon_female.hdf5 (GATK_CNV_DENOISE);
  cnvkit_loo_summary_female.tsv (CNVKIT, CNV_ANNOTATE, CNV_CONSENSUS_MULTI);
  cnvkit_noisy_bins_female.bed (CNVKIT).
- Pattern: each module takes the female file as a second input staged
  under female_stratum/ (no filename collision when a legacy panel's
  "female" file is the male one) and picks the stratum from meta.sex.
- Decision: params.cnv_sex_fallback = 'male' for samples whose sex is not
  male/female. CNVKIT previously fell back to female while GATK was
  male-only; the arms now agree, and male is the better-characterised
  reference (23 normals, three pools). chrX is not interpretable for such
  samples; CNVKIT warns to stderr and every task echoes [SEXSTRAT] to
  .command.log.
- tspipe.nf: sexstratFemale() resolves each female asset and falls back
  to the male file with one log.warn when the panel has none, so myeloid
  and myeloid_cnv are unchanged.
- Deliberately not wired: ZSCORE_CNV and CNV_PLOTS (both retire; 7b and 12).
- Task hashes of the four modules changed; -resume on older runs
  re-executes the CNV block only.

## 4. Consensus arms and tier rule (CMX_V2) -- commit a253bc4 (item 7a)

- Z-score is no longer an arm. Depth arms K (CNVkit) and G (GATK) are
  one vote family; independent arms B (17p BAF verdict: DEL_17P -> LOSS,
  CNLOH_17P -> CNLOH), P (PureCN, status OK and unflagged; C==2 with loh
  true supports cnLOH), E (DECoN via optional --decon-genes TSV with
  columns gene, e_call, e_bf; NA until the DECON module exists).
- Tier: REVIEW on any contradiction; with a depth direction, TIER_1 when
  an independent arm agrees and LOO fp_any_rate < 0.10 (fraction; unknown
  counts as not ok), TIER_2 when K and G agree with fp ok or an independent
  arm agrees without fp ok, else TIER_3; independent-only agreement TIER_3;
  cnLOH TIER_1 with two allelic arms, TIER_2 with one.
- genes.tsv: z_call removed; b_call, e_call, e_bf, tier added. JSON schema
  twist_cnv_consensus4/v3; tracks.cnr_bins now carries depth and weight
  (first half of gap register A3; noisy-bin flag and het_sites pending).
- Synthetic fixture covered every branch and a flagged PureCN fit.
- 7b (with item 12): delete ZSCORE_CNV, CNV_CONCORDANCE, CNV_CLINICAL_REPORT;
  cnv_annotate.py and the dashboard CNV tab read the consensus table.
  Not done now because the dashboard CNV tab is built on the legacy tiered
  table and making Z optional in the legacy scripts would demote every
  call it shows.
- Nextflow does not hash bin/: the running 26CGH60 case picks CMX_V2 up
  at its consensus task; it is the first real-data exercise.

## 5. PureCN NormalDB by sex (PCN_SEX_V1) -- commit 84486d1 (item 5)

- tools/build_purecn_normaldb.sh --sex male|female; sheet-driven BAM
  selection and coverage list; per-stratum NormalDB dir and assay
  (twist_myeloid_female); coverage files shared between strata.
- purecn.nf second input staged under female_stratum/; tspipe.nf
  ch_purecn_normaldb_female via sexstratFemale(); twist overlay
  purecn_normaldb_female. Stub run confirmed the male-file fallback while
  the female RDS did not yet exist.
- Decision: stratified, not combined. PureCN's own handling of sex inside
  a mixed NormalDB was not verified; the other arms are stratified.
- Female build from the 8 conforming 8-plex normals with --force. Caveat:
  n=8 gives less stable interval weights than the male 23; a pooled
  mixed-sex autosomal reference (handoff item 8) remains a later option.

## 6. Female PureCN asset -- commit 989ac26

assets/twist_myeloid/normalDB_twist_myeloid_female_hg38.rds,
interval_weights_twist_myeloid_female_hg38.png, purecn_normaldb_female.md5.
Build log /tmp/purecn_female_build.log; workdir
/goast/hemat_data/pon_twist/purecn_normaldb/normaldb_female.

## 7. Run in progress

One-case run 26CGH60-TwistMyVal (sex=unknown), outdir
/goast/hemat_data/twist_val/tspipe_run1, log /tmp/twist_val_1.log. Launched
before SEXSTRAT_V1 and PCN_SEX_V1 were applied, so its DAG uses the
pre-patch CNVKIT / GATK_CNV_DENOISE / PURECN definitions (male references,
which for a male case is the correct answer anyway); its consensus task
runs CMX_V2. The eight-case run is the first to exercise every change.
Aborted 8-case run and three stub runs left work directories; clean with
nextflow log -q / nextflow clean -f -k <name> when nothing is running.

## 8. Untracked files awaiting a decision

tools/verify_s3_archived.py (referenced by the handoff; should be
committed), normals_twist.csv, pon_samplesheets/twist_males_24_fastq.csv,
probes_ok_ACTREC_Myeloid_TE-99430185_{CNV_Backbone_Spikein,hg38_Main}_*.bed,
qc/, references/backups/.

## 9. Open items after this session (delta to the handoff)

Done: A1 (sex inference); item 4 for its four consumers; item 5; item 7a.
Next by dependency: A5 DECON module (R container, per-sex pool, filter ->
--decon-genes contract) then item 6; item 12 with A2/A4 (reconCNV +
styled scatter wiring, dashboard CNV tab rebuilt on the consensus table)
and 7b; items 2/3 conformity gate; item 9 BAF_V2 with the rest of A3;
then items 10/11. Unchanged: 13-18 and the remaining register entries.

## 10. Lessons

- gate_*.mosdepth outputs from the PoN build are sentinel-only (2 rows);
  never a test input for anything that needs the panel.
- grep -o on config values drops the ${projectDir} prefix; resolve
  relative to the repo before testing paths.
- A log.info inside a channel closure looks replayed in a non-TTY console
  log; the count in .nextflow.log is the truth.
- Patchers that touch several files should compute every edit first and
  write nothing unless all anchors match (patch_sexstrat_v1.py pattern).
