# SOP — sample QC tab and verdict (DASH_QC_V1–V2b, 2026-09-08)

## Purpose
The QC tab of `<sample>_report.html` answers one question for the signing pathologist: can the
negative results in this sample be trusted, and where not. Everything on it serves that.

## Layout (top to bottom)
1. Verdict pill and reasons. PASS / PASS WITH LIMITATIONS / REVIEW; the same pill sits in the
   report header and on the overview tab.
2. Sample identity (sex check): samplesheet sex; sex by chrX heterozygosity (deciding vote);
   sex by X/autosome depth (confirming); sex used; status and flags.
3. Low-coverage genes: median of the gene's non-known exons < 100x, lowest first, with worst
   exon, driver role, CNV consensus call.
4. Regions below 200x: every exon under the reportability tier, banded `< 100x` (red) or
   `100-200x`, with driver role, known-limitation flag, CNV call.
5. Known panel limitations: exons from `assets/<panel>/known_low_exons.tsv` present in the
   sample, with this sample's coverage and the cohort statistics.
6. Run metrics: mosdepth median per-exon coverage and % regions ≥ 200x first, then Picard
   CollectHsMetrics. A limit is shown only where the metric feeds the verdict.
7. Per-gene median coverage chart (log y, 100x line, low genes in red).
8. All genes table.
9. Read-level QC (fastp) table, with the fastp HTML as one link.
10. Per-exon coverage table, collapsed.

## Inputs (all under `<sample>/clinical/`)
`<S>_exon_coverage.tsv` (mosdepth per-exon mean, duplicates included), `<S>_hsmetrics.txt`,
`<S>_fastp.json` (ORGANIZE_OUTPUT hardlinks it beside the HTML since DASH_QC_V2),
`cnv/sex_check/<S>.sex_check.tsv` (via `parsers/cnv_v2.py`),
`cnv/consensus/<S>.cnv_consensus4.genes.tsv` (driver_role, consensus_call, tier),
`assets/<panel>/known_low_exons.tsv` (passed by `dashboard.nf` as `--known-low-exons`).

## Verdict rule (`parsers/coverage.py: verdict()`)
REVIEW if any run-level limit is broken: mosdepth median per-exon < 500x; regions ≥ 200x < 95%;
PCT_TARGET_BASES_100X < 0.95; PCT_TARGET_BASES_250X < 0.90; PCT_EXC_DUPE > 0.50; fastp Q30 after
filtering < 0.85; fastp insert-size peak < 120 bp; samplesheet sex contradicts chrX
heterozygosity.
Else PASS WITH LIMITATIONS if any gene's median over its non-known exons is < 100x, or any
driver gene has a non-known exon < 100x. A gene whose low coverage is explained by a consensus
LOSS is reported as a finding and does not count.
Else PASS. Findings (never limitations): CNV-explained low genes; sex not on the samplesheet;
X_DEPTH_CONFLICT (heterozygosity decides, depth suggests a chrX copy-number change).
Thresholds: `QC_THRESHOLDS` in `parsers/coverage.py`, `FASTP_THRESHOLDS` in `parsers/fastp.py`.
Their basis is in memo 10 §3; change them there and in this SOP together.

## Coverage statistic
Per exon: mosdepth region mean (duplicates included; the clinical convention). Gene and sample
aggregates: median (D8, 2026-09-08), robust to a single skewed exon. Picard
MEDIAN_TARGET_COVERAGE is capped at 200 by COVERAGE_CAP and is informational until N11.

## Known low-capture exons
Panel-design facts (GC-rich first exons, uncaptured CCNC/ANKRD26 exons). Asset built from the
PoN normals' per-exon coverage tables:

    awk -F, 'NR==1{print "sample,sex,exclude"; next} {print $1","$2","($6=="true"?"false":"true")}' \
        pon_samplesheets/twist_normals_48_v4.csv > /tmp/pon_normals_exclude.csv
    python3 tools/build_known_low_exons.py \
        --coverage /goast/hemat_data/pon_twist/realign_v4 --coverage /goast/hemat_data/pon_twist/realign_v4_female \
        --normals /tmp/pon_normals_exclude.csv \
        --out assets/twist_myeloid/known_low_exons.tsv --stats /tmp/known_low_exons.cohort_stats.tsv

Rule: < 100x in ≥ 50% of included normals. Use the PoN cohort (`include_in_pon == true`, 31),
never the full 48: the excluded females are globally low and produce a false tail. Rebuild
whenever the PoN or the panel changes; the asset header records date, cohort and md5.
Current list (2026-09-08): CCNC Ex__6/7, ANKRD26 Ex__19/29, AKT1 Ex__1, DNMT3A Ex__1.

## Re-rendering
Parsers and template are unhashed `bin/`: `-c /tmp/dash_nocache.config`. ORGANIZE_OUTPUT and
FASTP wiring are hashed: plain resume. After a nocache run the next plain resume re-executes
DASHBOARD and REPORT_BUNDLE once.

## Patchers
`tools/patches/2026-09-08/patch_dash_qc_v1.py … v1e.py, patch_dash_qc_v2.py, v2b.py`.
