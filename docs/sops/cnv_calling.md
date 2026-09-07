# SOP: CNV_CALLING (V2) and the retired legacy CNV chain (7b)

## What the subworkflow does now

`subworkflows/local/cnv_calling.nf` runs CNVKIT only: batch against the
sex-stratified PoN, call, genemetrics. It emits `cnvkit_calls` (.call.cns),
`cnvkit_cnr`, `cnvkit_cns` and `cnvkit_genemetrics`. Consumers:
CNV_CONSENSUS_MULTI (arm K), RECONCNV, CHROM_PAGES/EXON_PLOTS through the
consensus JSON.

Inputs: BAM, reference, panel BED, male and female PoN, LOO summary and
noisy-bins BED per stratum. No longer inputs of the pipeline:
`loo_bin_noise_profile.tsv` (ZSCORE_CNV), `cytoBand_hg38.txt` and the
ClinGen list (CNV_ANNOTATE), `cnv_scatter_regions.txt` (CNV_PLOTS). The
asset files stay in the repo; `params.cnv_noise_profile`, `params.cytoband`
and `params.clingen` are accepted and ignored.

## Retired on 2026-09-07 (CNV_RETIRE_7B)

Processes and scripts removed from the DAG and the tree:

    modules/local/zscore_cnv.nf            bin/zscore_cnv.py
    modules/local/cnv_plots.nf             bin/cnv_plots.py
    modules/local/cnv_concordance.nf       bin/cnv_concordance.py
    modules/local/cnv_clinical_report.nf   bin/cnv_clinical_report.py
    modules/local/cnv_annotate.nf          bin/cnv_annotate.py
    bin/dashboard_builder/parsers/cnv.py

Why: the two-caller (CNVkit + Z-score) concordance, its tiered clinical
report and its plot layout were superseded by the six-arm consensus
(CMX_V2), the target-space chromosome pages, exon plots and reconCNV, and
by the dashboard CNV tab built on the consensus table (DASH_CNV_V1). The
annotated table (cytoband, ClinGen HI/TS, gene role, heme significance) was
no longer rendered anywhere; its useful columns are to be added to the
consensus `genes.tsv` in `cnv_consensus_multi.py` (follow-up).

Downstream changes:
- CNV_CONSENSUS_MULTI no longer takes the concordance table; `--concordance`
  in `cnv_consensus_multi.py` is optional and ignored.
- ORGANIZE_OUTPUT no longer receives the clinical/annotated tables or the
  CNVkit plot outputs; `organize_output.py` lost those five arguments and
  `<sample>/cnv_consensus/` and `<sample>/cnvkit_plots/` are no longer
  created under clinical/. Everything CNV lives under `clinical/cnv/`.
- `conf/modules.config`: the five publishDir blocks are gone, so
  `<outdir>/<sample>/cnv/{zscore,plots,concordance,report,annotated}` are
  no longer produced. `cnv/cnvkit` remains.
- Dashboard: `build.py` reads `parsers/cnv_v2.py` only.

Task-hash effect: CNV_CONSENSUS_MULTI (input tuple changed) and ORGANIZE_OUTPUT
re-execute for every sample on a resume; EXON_PLOTS, CHROM_PAGES, DASHBOARD and
REPORT_BUNDLE follow. CNVKIT and the other arms stay cached.

## Rollback

Patcher `tools/patches/2026-09-07/patch_cnv_retire_7b.py` leaves
`.bak_cnv_retire_7b_<ts>` copies of every edited file; the deleted files
are in git history at a2bc0b1.
