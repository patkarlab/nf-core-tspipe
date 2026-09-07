# 2026-09-07 morning, part 2 -- memo addendum 4 (BAF catalog v2, hmftools arm H)

Session end HEAD a83218e. Commits this part: 0ba8e6d BAF_CATALOG_V1, 29b33a0
catalog v2 assets + V1a fix, 4512a6f HMF_PANEL_V1, 2b8a0c0 HMF_PURPLE_V1,
18fd637 V1a, 7c27551 V1b, 2e6d5c4 V1c, a83218e CMX_V2_4.

## 1. Genome-wide BAF site catalog (item 9, catalog half)

Evidence: one normal carries 1,550 het SNPs at >= 50x across the panel's
incidental SNPs (19-127 per chromosome). BUILD_PON_TWIST gained
BPT_DISCOVER_HETS (bcftools per sample, per chromosome in parallel) and
BPT_MERGE_HET_SITES (het in >= 3 include_in_pon normals at >= 50x; chrX from
females; PARALOG_LIMITED exons excluded; unioned with the 17p windows).
Assets v2 (baf_catalog_v2.md5): snp_sites.baf.bed 4,193 intervals (374 base
+ 3,819 discovered, chrX 76), het_catalog.tsv, baf_background.tsv over all
48 rows (cohort 'all', 48,699 positions). Base 17p catalog preserved as
snp_sites.baf.base.bed.
Incident: the merge task staged the base catalog under its output's name and
wrote through the staged symlink into the asset; recovered from git.
Rule: an input is never staged under an output's filename (stageAs).
The eight-case session was resumed on the v2 catalog; the V1 17p detector
runs unchanged with autosomal controls. Detector v2 is the next step.

## 2. hmftools stack (item 11)

Setup (tools/hmftools/setup_hmftools.sh): conda env 'hmftools' with AMBER
4.3, COBALT 3.0, PURPLE 4.4 on OpenJDK 21; WiGiTS bundle
hmf_pipeline_resources.38_v3.0.0--8 at /goast/hemat_data/references/hmftools
(md5 ce78ad7f...). Panel resources (tools/hmftools/build_panel_resources.sh,
assets/twist_myeloid/hmftools/): sorted primary-contig target BED (8,821
rows), COBALT target-regions normalisation trained on the 31 normals (5,318
usable windows; the sample-id CSV carries Gender, so AMBER is not needed to
train), driver gene panel for every gene named in the BED (HMF rows copied,
missing genes templated by role; reportGermline* columns are enums, never
empty). Per sample: HMF_AMBER -> HMF_COBALT -> HMF_PURPLE tumour-only
targeted, host env, published under <sample>/cnv_hmftools/ with logs;
purple_gene_table.py -> arm H (sex-aware vs expected cn; LOH from minor
allele CN; FAIL_ or WARN_LOW_PURITY -> advisory). Consensus schema v4.
Option names that differ from the docs: COBALT -target_region_norm_file;
PURPLE -amber_dir/-cobalt_dir, no -target_regions_ratios; QC file is
<id>.purple.qc as key-value.

PURPLE on the eight: 1043 PASS 0.92/1.96 M; 1250 PASS 0.65/2.24 MALE; 1292
WARN_LOW_PURITY 0.15/2.0 F; 132 PASS 0.87/2.02 F; 1480 PASS 0.91/2.02 M; 60
PASS 0.90/2.00 M; 799 FAIL_NO_TUMOR (panel-mode tumour-detection threshold,
not a sample statement); 885 PASS 1.0/2.0 M.

## 3. CMX_V2_4 tier refinements (from the PURPLE run)

WARN_LOW_PURITY makes H advisory (1292 at 0.15 had produced 30 H-only cnLOH
calls at TIER_2; now 3 TIER_3); single-arm cnLOH is TIER_2 only from B (direct
17p BAF against the cohort background), P or H alone TIER_3; two independent
arms agreeing without depth are TIER_2 (IKZF1 Delta4-7 in 60: E + H).
The module carries a bash comment with the rule version so a consensus-only
change re-executes on resume (Nextflow does not hash bin/).

Final tiers: 1043 T1=6 T3=5; 1250 T1=30 T2=1 REVIEW=9 T3=5; 1292 T3=3; 132
T1=3; 1480 T2=1 T3=14; 60 T1=3 T2=1 T3=3; 799 T1=4 T3=2; 885 T3=1.

## 4. Findings for the register

- A1b: depth-based sex inference is confounded by X aneuploidy. 1250 is
  MALE by AMBER and COBALT (heterozygosity and X/Y ratios) while SEX_CHECK
  said female at X/A 0.898; a male hyperdiploid B-ALL with +X at 65% purity
  gives exactly that X/A. Consequence: Xq reads as a loss against the female
  PoN, PURPLE calls X gained, nine chrX genes at REVIEW. SEX_CHECK must use
  heterozygosity on chrX (v2 catalog, 76 sites) or AMBER's gender.
- PURPLE's FAIL_NO_TUMOR on 799 (whole chr8 gain on G/K/P) is its
  tumour-detection threshold on panels; advisory handling is right.
- BTG1: K-only in three cases with different magnitudes, clean in normals;
  GATK and DECoN miss two-exon events at ratio 0.66-0.80 (sensitivity item
  with IKZF1 for item 12's segmentation pass).

## 5. Next

A1b sex from heterozygosity; BAF_V2 detector (genome-wide arms/segments on
the v2 catalog; consensus B genome-wide); then item 12 with 7b (reconCNV,
styled scatter with BAF panel, dashboard CNV tab on consensus + exon plots +
PURPLE summary, ORGANIZE_OUTPUT routing, retire ZSCORE/CONCORDANCE/CLINICAL
report, CNVkit segmentation sensitivity). Untracked files list unchanged;
nextflow clean for the aborted stub sessions still pending.
