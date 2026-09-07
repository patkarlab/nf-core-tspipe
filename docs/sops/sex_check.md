# SOP: SEX_CHECK (V2) -- sample sex inference

Module `modules/local/sex_check.nf`, script `bin/sex_check.py`, wired in
`subworkflows/local/preprocessing.nf` (MARKER SEX_CHECK_V1 / SEX_CHECK_V2).
Runs once per sample after MOSDEPTH and ABRA2, before any CNV arm, and
writes `<outdir>/<sample>/sex_check/<sample>.sex_check.tsv` (one row) plus
`<sample>.sexcheck.allelicCounts.tsv` when a het catalog exists.

## Inputs

- mosdepth `regions.bed.gz` (exon-collapsed BED, `--mapq 20 --flag 772`).
- Final BAM (ABRA2) with index; reference FASTA, .fai, .dict.
- Het catalog `assets/<panel>/het_catalog.tsv` (columns `chrom pos ref alt
  n_het n_het_male n_het_female median_af source`). Override with
  `--sex_check_het_catalog <path>`. A panel without the file stages `[]`
  and gets the depth-only inference with `HET_VOTE_UNAVAILABLE`.

## Two votes

1. Heterozygosity (decides). `gatk CollectAllelicCounts` at every catalog
   position (single-base BED built in the task). At sites with ref+alt
   depth >= 30 a site is heterozygous if 0.15 < AF < 0.85. chrX het
   fraction (PAR excluded) <= 0.10 male, >= 0.25 female, between
   `CHRX_HET_AMBIGUOUS`. Needs >= 20 chrX sites at depth
   (`TOO_FEW_HET_SITES`) and an autosomal het fraction >= 0.25
   (`AUTOSOMAL_HET_LOW`, e.g. contamination or a bad library); either
   failure hands the decision to the depth vote.
2. Depth (confirms). Median chrX depth over median autosomal depth per
   region class, PAR excluded: X/A <= 0.70 male, >= 0.80 female, between
   `CHRX_RATIO_AMBIGUOUS`. chrY is used where the BED has it (the Twist
   myeloid BED has none, so `y_status` is NA).

When both votes are present and disagree the het vote wins and
`X_DEPTH_CONFLICT` is set: the usual cause is a somatic chrX gain or loss
(26CGH1250, male +X hyperdiploid B-ALL, X/A 0.898, chrX het 0.000).

Calibration, tspipe_run8, 2026-09-07 (76 chrX sites, depth >= 30):
males 0.000-0.013, females 0.382-0.434, autosomal 0.400-0.437.

## Resolution into meta.sex

`resolved_sex` = samplesheet value if male/female, else the inference.
Samplesheet always wins; `MISMATCH` is logged (`log.warn`) and flagged,
never applied. `X_DEPTH_CONFLICT` is logged as a warning with both votes.
Every downstream channel from PREPROCESSING carries the resolved meta.sex;
CNVkit, GATK, PureCN, DECoN, PURPLE and the consensus select the stratum
from it (`params.cnv_sex_fallback` for anything else).

## Columns

V1 (unchanged): sample, sheet_sex, inferred_sex, resolved_sex, status,
x_auto_ratio, y_auto_ratio, y_status, n_auto, n_x, n_y, auto_median_exon,
auto_median_backbone, n_par_excluded, n_noncanonical_skipped, flags.
V2 (appended): method (heterozygosity | depth | none), het_inferred_sex,
depth_inferred_sex, x_het_frac, auto_het_frac, n_x_het_sites,
n_auto_het_sites.

## Checks after a run

    awk -F'\t' 'FNR==2' <outdir>/*/sex_check/*.sex_check.tsv | cut -f1-5,16,17,20,21

Any `X_DEPTH_CONFLICT` should correspond to a chrX call in the CNV
consensus; any `AUTOSOMAL_HET_LOW` needs a look at contamination before
the sample's CNV results are read.

## Standalone use

    python3 bin/sex_check.py --regions <sample>.regions.bed.gz \
        --allelic-counts <counts.tsv> --het-catalog assets/twist_myeloid/het_catalog.tsv \
        --sample <id> --sheet-sex unknown --out <id>.sex_check.tsv

Any CollectAllelicCounts file covering the catalog positions works
(the GATK_CNV_COLLECT_ALLELIC output does).

## History

- SEX_CHECK_V1 (2026-09-06): depth-only. Failed on 26CGH1250 (see above).
- SEX_CHECK_V2 (2026-09-07): heterozygosity vote added and made decisive;
  patcher `tools/patches/2026-09-07/patch_sex_check_v2.py`.
