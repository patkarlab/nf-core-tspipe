# Memo 19 — session 2026-09-10 (nf-core-tspipe)

## 1. TP53 / 17p observation block (TP53_OBS_V1, then TP53_ON_17P_V1)

`bin/dashboard_builder/parsers/tp53.py` (stdlib) puts every reportable TP53 row of the clinical table
(HGVS VariantValidator → CAVA → VEP, transcript from the same source, VAF with counts, callers,
verdict, ClinVar, OncoVI) beside the 17p allelic evidence at TP53 (consensus call/tier/arms,
allelic_state, CNVkit, GATK, BAF_V2 17p arm, PURPLE total/minor CN and LOH, PureCN C and LOH, PURPLE
and PureCN purity). The interpretation line is looked up in
`assets/twist_myeloid/tp53_interpretation_rules.tsv` (condition → wording, first match wins, grammar
and 34 fields in the header, each card shows the sample's values); no rule is active, the line reads
"per reporting pathologist"; malformed rules are reported on the card. Builder 0.5.2-tp53,
`--tp53-rules`, dashboard.nf passes the asset when present. Placement moved twice at Nikhil's
request: first at the head of the CNV tab, finally inside the 17p chromosome page (a template macro;
fallback to the end of the CNV tab on runs without a 17p page). A one-line mirror sits on the
Reporting tab. Run8 carries no real TP53 variant; the variant half was checked on synthetic rows
(`tools/patches/2026-09-10/check_tp53_block.sh`).

## 2. BAF_V2 in-silico 17p cnLOH dilution (docs/audit/2026-09-10/baf_v2_17p_dilution/)

Base 26CGH60 (diploid 17, 139 het sites, 1,342×); ALT counts redrawn at each het site as
Binomial(depth, observed AF ± f/2), random sign, 20 replicates per level, detector unchanged;
four clean samples run unmodified. At production parameters (noise-mult 2.5) a 17p cnLOH is called
from f ≈ 0.15 (LOW, no vote) and HIGH from ≈ 0.22; f_estimate unbiased above the floor; zero false
calls. Counting noise alone would give a null f_estimate of 0.020; the real one is 0.071, so 17p
site-level noise (≈ 3.5 × binomial) sets the floor, not depth — A3 site classes and BAF_V2c per-site
dispersion are the remedies. noise-mult 2.0: 0.10–0.12 / 0.20 with one LOW false call in eight; 1.5:
0.08 / 0.15 with four. Reproduced byte for byte on gandalf (CHECKSUMS.md5). Suggested wording:
"about 15 % any call, about 22 % high confidence, limited by 17p site noise rather than depth,
validated in silico only". Decision pending: keep 2.5 (recommended).

## 3. The 17p page (ARM17P_V1 → V2)

`bin/plot_arm_17p.py` in CHROM_PAGES writes `chrom_pages/<S>.17p.png` and registers it in
`chrom_pages.tsv` as `chr17p` (pill "17p" after "17", own Include checkbox, in the bundles). Tracks:
SNP-window depth ratios along the arm (as on the chromosome pages, sample-normalised on the backbone
catalog positions) with the CNVkit segment and the exon-bin arm median as lines; raw ALT fraction of
every catalog site with heterozygous sites in the BAF_V2 verdict colour and the 0.5 ± f/2 band;
PURPLE total/minor CN; gene strip. Eight-sample check
(`docs/audit/2026-09-10/17p_window_depth_medians.md`): raw window ratios do not measure copy number;
backbone-normalised ones put the seven neutral samples at −0.18 ± 0.03 and the 26CGH1250
chromosome-17 gain at +0.31 above that, equal to its exon-bin median; the −0.18 is a run-level
probe-batch offset of the 17p supplementary windows (needs per-run calibration or matched control
windows — Twist letter).

## 4. Run-level bundle (RUN_BUNDLE_V1)

`tools/make_run_bundle.py` + `modules/local/run_bundle.nf` (cohort-level, beside REPORT_BUNDLE):
`<outdir>/<run>_reports.zip` → cohort index with working links, `assets/` once, one folder per sample
(report with rewritten paths, dashboard, fastp, IGV, `cnv/`). Per-sample bundles unchanged.

## 5. Housekeeping and lessons

26CGH1043 genome-wide figure checked by Nikhil (OK). `singularity exec` needs `-B /goast`; launches
must be gated on the pre-flight. `snp_sites.baf.base.bed` holds only the SNP windows, not the
catalog. Nextflow 25.10 progress lines read `[hash] NAME | n of m`.

## 6. Decision taken at the end of the day

Freeze the pipeline to a final version on gandalf (A1 containerisation + A10 release engineering,
feature freeze otherwise), then port to clinical-23 with a detailed SOP for Vishram. See
HANDOFF_FREEZE_v1.md. A3 / BAF_V2c / PoN rebuild are v1.1.
