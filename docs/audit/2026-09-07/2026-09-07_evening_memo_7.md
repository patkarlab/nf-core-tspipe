# 2026-09-07 evening -- memo 7 (A1b: sex inference from chrX heterozygosity, SEX_CHECK_V2)

Start HEAD 17d7884. Patcher tools/patches/2026-09-07/patch_sex_check_v2.py.
Resume target: tspipe_run8, session abea2914-e2f9-44c0-961a-2f9c50eab4d9.

## 1. Problem

SEX_CHECK_V1 was depth-only (X/A ratio; the Twist myeloid BED has no chrY, so
n_y = 0 and the Y vote never exists). 26CGH1250, a male hyperdiploid B-ALL
with +X at PURPLE purity 0.65, reads X/A 0.898 and was inferred female. Every
CNV arm then used the female stratum: Xq as a loss against the female PoN,
PURPLE (which knew the sample was MALE from heterozygosity) calling X gained,
nine chrX genes at REVIEW. The depth ratio cannot be tuned out of this: it is
the correct value for the biology.

## 2. Calibration (existing GATK allelic counts at het_catalog.tsv positions,
depth >= 30, het if 0.15 < AF < 0.85, PAR excluded)

    sample      PURPLE  X/A    chrX sites  chrX het  X_hetfrac  auto sites  A_hetfrac
    26CGH1043   MALE    0.538  76          0         0.000      3729        0.400
    26CGH1250   MALE    0.898  76          0         0.000      3730        0.414
    26CGH1292   FEMALE  1.039  76          31        0.408      3733        0.414
    26CGH132    FEMALE  1.084  76          29        0.382      3736        0.413
    26CGH1480   MALE    0.529  76          1         0.013      3740        0.421
    26CGH60     MALE    0.543  76          0         0.000      3734        0.407
    26CGH799    FEMALE  1.068  76          33        0.434      3739        0.419
    26CGH885    MALE    0.528  76          0         0.000      3733        0.437

All 76 chrX catalog sites reach depth 30 in every case. Separation is
complete and does not depend on chrX copy number.

## 3. Design (SEX_CHECK_V2)

- SEX_CHECK now takes the final BAM (ABRA2), the reference and
  assets/<panel>/het_catalog.tsv (override --sex_check_het_catalog), and
  runs CollectAllelicCounts at the 4,193 catalog positions inside the GATK
  container it already used. Panels without a catalog stage [] and keep the
  V1 depth-only behaviour (HET_VOTE_UNAVAILABLE).
- Vote 1, heterozygosity, decides: chrX het fraction <= 0.10 male, >= 0.25
  female; needs >= 20 chrX sites at depth and an autosomal het fraction
  >= 0.25 (AUTOSOMAL_HET_LOW otherwise; contamination or a bad library hands
  the decision back to depth).
- Vote 2, depth, confirms; disagreement is X_DEPTH_CONFLICT, logged with both
  values (the 1250 pattern: chrX gain or loss in the tumour).
- Samplesheet male/female still wins; 'unknown' takes the inference;
  MISMATCH stays a flag. The sixteen V1 columns are unchanged; seven are
  appended (method, het_inferred_sex, depth_inferred_sex, x_het_frac,
  auto_het_frac, n_x_het_sites, n_auto_het_sites), so header-keyed consumers
  (preprocessing.nf splitCsv, dashboard parsers) are unaffected.
- The allelic counts are published beside the sex_check TSV
  (conf/modules.config pattern, MARKER SEX_CHECK_MODULES_V2).
- SOP docs/sops/sex_check.md rewritten.

## 4. Expected effect on the resume

SEX_CHECK re-runs for all eight (new inputs). meta.sex changes only for 1250
(female -> male), so the CNV block re-executes for 1250 alone; ORGANIZE_OUTPUT,
DASHBOARD and REPORT_BUNDLE re-run for all because the sex_check TSV changed.
For 1250: chrX arms against the male PoN, PURPLE and consensus sex agree, the
nine chrX REVIEW rows resolve to a +X gain (TIER_1 expected: depth + H).

## 5. Result (resume of abea2914, run serene_feynman, completed 16:22)

64 tasks executed, 394 cached, no errors. Stub run (sexcheck_v2_stub2) green
before launch; note that a stub with --outdir on /tmp fails at the first
publishDir because link mode cannot cross filesystems from /goast.

sex_check rows (inferred, resolved, flags, method, X het, autosomal het):
all eight decided by heterozygosity and concordant with PURPLE; only 1250
carries X_DEPTH_CONFLICT (male, X het 0.000, X/A 0.898). The log.warn fired
once with both votes.

1250 chrX consensus (cnv_consensus4.genes.tsv): every chrX gene GAIN TIER_1.
Xp genes (PIGA, ZRSR2, BCOR, DDX3X) on G+H+K, CNVkit cn 3 at log2 1.0-1.3,
PURPLE CN 2.88; Xq genes (KDM6A .. PHF6) on G+H, PURPLE CN 1.86, CNVkit
NEUTRAL cn 1 at log2 0.67-0.70. The nine chrX REVIEW rows from the previous
run are gone; PURPLE (sex MALE, purity 0.65, PASS) and the consensus agree.
Report header: PURPLE status PASS, purity 0.65, sex MALE.

Two things learned on the way:
- meta.sex is part of every task hash, so a sex change re-executes the
  sample end to end from SEX_CHECK (Mutect2 and the whole variant block
  included), not only its CNV arms. A sex correction on a clinical sample
  is a full per-sample re-run.
- CNVkit call thresholds undercall a single-copy gain on a male chrX
  (haploid reference, +1 copy = log2 +1.0, but Xq here sits at 0.67-0.70
  and is called NEUTRAL cn 1). Add to the CNVkit segmentation/threshold
  sensitivity item alongside IKZF1 and BTG1.

## 6. Closes

A1b. With it the CNV module is closed as a calling and reporting stack;
remaining CNV items (BAF_V2 genome-wide, 7b legacy retirement, CNVkit
segmentation sensitivity, DECoN follow-ups, MoChA optional, identity
checker, cell-line control) are extensions and cleanup, tracked in the
reconciled register.
