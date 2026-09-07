# 2026-09-07 morning -- memo addendum 3 (eight-case validation, thresholds, blacklist)

Session end HEAD 9f1f089 (three commits this morning on top of 17 yesterday:
9b90d3b DECON_V1b, aaab395 DECON_V1b_FIX, 9f1f089 CNV_BLACKLIST_V1; plus the
early-morning d5c8757 CMX_V2_1 and 93020e0 EXON_PLOTS_V1 of 2026-09-06 night).

## 1. Eight-case run

twist_val_8_fastq.csv (all sex=unknown), outdir /goast/hemat_data/twist_val/
tspipe_run8, session abea2914-e2f9-44c0-961a-2f9c50eab4d9, 410 tasks OK
(22:31 on 09-06), then four resumes by session uuid (EXON_PLOTS + CMX_V2_1;
DECON_V1b failed on every case; DECON_V1b_FIX; CNV_BLACKLIST_V1), last at
05:54. Sexes inferred: 1043 M 0.538, 1250 F 0.898, 1292 F 1.039, 132 F 1.084,
1480 M 0.529, 60 M 0.543, 799 F 1.068, 885 M 0.528.

Final per-case consensus (non-neutral, non-blacklisted): see the summary
command in this memo's companion (docs/sops/*). Headline: 9p deletion at
TIER_1 in 60 and 1043 (all arms); ETV6/DNMT3A/ASXL2 losses at TIER_1 in
132; whole chr8 gain at TIER_1 in 799; hyperdiploid pattern in 1250 with
17p DISCORDANT (REVIEW); IKZF1 Delta4-7 in 60 (FISH 90%) and NRAS in 1043
now reported via DECoN at BF 9.9 / 10.6; KDM6A and PAX5 intragenic
deletions in 1292 on DECoN alone; BTG1 CNVkit-only loss of varying
magnitude in 1043, 1292, 1480 (clean in normals; sensitivity case for the
depth segmenters). Clinical comparison against findings: Nikhil.

## 2. Fixes found by the cases

- CMX_V2_1 (d5c8757): the consensus expected cn 2 everywhere; cnvkit call
  --sex male reports absolute cn, so a normal male chrX (cn 1) became 13
  TIER_3 losses. Now expected cn by chromosome and --sex (X/Y: 1 male,
  X 2 female, Y none; unknown -> NA on X/Y). Verified on 26CGH60, 1043,
  1480, 1250.
- Remaining chrX pattern: GATK's neutral band (copy ratio 0.9-1.1, log2
  -0.15..+0.14) is narrower than CNVkit's (-0.25..+0.20), so whole-chrX
  segments at -0.16 (1480) / -0.21 (1250 Xq) are GATK-only TIER_3. Left
  as review; BAF_V2 (item 9) is the adjudicator for low-amplitude
  chromosome-level shifts.
- DECON_V1b (9b90d3b): deletions of >= 2 exons reportable at BF >= 8
  (decision PASS_MULTIDEL), everything else at 12. Evidence: no
  multi-exon LOO call of any kind in 31 normals; real events at 9.9 and
  10.6; the only 8-12 artefacts were two-exon SUZ12 duplications.
  DECON_V1b_FIX (aaab395): the patcher had put "// MARKER" inside the
  shell script (argparse exit 2 on every sample). Lesson: markers go in
  Groovy comments, never inside a script string; the fix patcher now
  audits script blocks for '//'.
- CNV_BLACKLIST_V1 (9f1f089): assets/twist_myeloid/cnv_gene_blacklist.tsv
  (gene, reason, evidence, added); consensus_call BLACKLISTED, tier NA,
  arms kept for audit; EXON_PLOTS ignores blacklisted genes as triggers.
  Entries: SUZ12 (SUZ12P1 paralog; identical 2-exon duplication in 3/8
  cases, LOO calls both directions in 5/23 normals), ELANE (GC-rich;
  CNVkit-only +0.2 in 2/8 with GATK flat). BTG1 deliberately not listed.

## 3. Tools

- EXON_PLOTS module (93020e0): per-chromosome exon-level figures from the
  consensus bins with DECoN brackets, driven by consensus calls,
  sub-threshold DECoN calls (BF >= 5) and the focal-CNV list; index TSV.
  Published to <sample>/cnv_consensus_multi/exon_plots/.
- Resume discipline: always -resume <session uuid> from `nextflow log`
  (bare -resume and -resume <run name> both attached to a stub session).
  Two resumes of one session must never overlap.

## 4. Open after this morning

Item 12 with 7b (reconCNV + styled scatter wiring, dashboard CNV tab on
the consensus table and the exon-plot index, ORGANIZE_OUTPUT routing of
cnv_consensus_multi/, cnv_decon/, sex_check/ into clinical/, retirement of
ZSCORE_CNV / CNV_CONCORDANCE / CNV_CLINICAL_REPORT, CNVkit segmentation
sensitivity for short intragenic events); items 2/3 conformity gate;
item 9 BAF_V2 with the rest of A3; 10/11; DECoN follow-ups (PROBE_VARIANT
via the sample variant table, RECURRENT_IN_NORMALS from the pool LOO,
sex-aware low-power flag for the female DNMT3A exon). Cleanup:
nextflow clean for compassionate_sax, friendly_joliot, sad_lamarr and the
/tmp stub sessions. Untracked files list unchanged.
