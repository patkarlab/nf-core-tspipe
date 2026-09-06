# SEX_CHECK (SEX_CHECK_V1) -- 2026-09-06

Infers sample sex from the existing MOSDEPTH regions output (chrX/autosome
depth ratio, per-class normalised; chrY where the BED has it) and resolves
meta.sex when the samplesheet says `unknown`. Samplesheet male/female always
wins; a MISMATCH is logged and written to the TSV, never applied.

Validated on real data before wiring: Male24 X/A 0.563, Female15 X/A 1.023
(227 chrX exon regions each; targets.exonwise.bed has no chrY).

## Placement (repo root = /goast/hemat_data/nf-core-tspipe)

    bin/sex_check.py                                   (replaces the copy placed earlier today)
    modules/local/sex_check.nf                         (new)
    tools/patches/2026-09-06/patch_preprocessing_sex_check.py
    tools/patches/2026-09-06/patch_modules_config_sex_check.py
    pon_samplesheets/twist_val_8_fastq.csv             (all eight cases now sex=unknown)
    pon_samplesheets/twist_val_1_fastq.csv             (26CGH60 only, smoke test)

## Apply

    python3 tools/patches/2026-09-06/patch_preprocessing_sex_check.py          # dry run, read the preview
    python3 tools/patches/2026-09-06/patch_preprocessing_sex_check.py --apply
    python3 tools/patches/2026-09-06/patch_modules_config_sex_check.py --apply

## Validate

1. `nextflow inspect` / `-stub-run` on twist_val_1_fastq.csv: compiles, SEX_CHECK
   task present, no join errors.
2. Real run on twist_val_1_fastq.csv (sex=unknown). Expect
   `[SEX_CHECK] 26CGH60-TwistMyVal: samplesheet sex unknown; using inferred ...`
   in the log and `<outdir>/26CGH60-TwistMyVal/sex_check/26CGH60-TwistMyVal.sex_check.tsv`.
   CNVKIT must then pick the PoN for the inferred sex, not the unknown fallback.

## Output columns

sample, sheet_sex, inferred_sex, resolved_sex, status
(CONCORDANT | MISMATCH | SHEET_UNKNOWN | INDETERMINATE), x_auto_ratio,
y_auto_ratio, y_status (PRESENT | ABSENT | AMBIGUOUS | NA), n_auto, n_x, n_y,
auto_median_exon, auto_median_backbone, n_par_excluded,
n_noncanonical_skipped, flags (Y_DEPLETED, Y_UNEXPECTED, CHRX_RATIO_AMBIGUOUS,
TOO_FEW_CHRX_REGIONS, NO_USABLE_CLASS, ERROR:...).

## Thresholds (script arguments, defaults)

male X/A <= 0.70; female X/A >= 0.80; Y present >= 0.15; Y absent < 0.05;
class usable if >= 50 autosomal regions at median depth >= 20x.

## Follow-ups (not in this bundle)

- ORGANIZE_OUTPUT: copy the TSV into clinical/; dashboard QC card shows
  inferred sex and MISMATCH.
- docs/usage.md: samplesheet `sex` accepts male | female | unknown.
- Item 4 (sex-stratified GATK PoN / LOO selection) now keys on the resolved meta.sex.
