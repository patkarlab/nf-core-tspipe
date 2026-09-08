# CMX_V2 -- consensus arms K/G/B/P/E, tier rule, Z-score dropped (item 7a) -- 2026-09-06

Patcher: tools/patches/2026-09-06/patch_cnv_consensus_multi_cmx_v2.py
Target:  bin/cnv_consensus_multi.py (one MARKER CMX_V2; compiles-check and
         z-score leftover check before anything is written)

Arms: depth K (CNVkit) and G (GATK) are one vote family; independent arms
B (17p BAF verdict: DEL_17P -> LOSS, CNLOH_17P -> CNLOH), P (PureCN when
status OK and not flagged; C==2 with loh true is cnLOH support), E (DECoN,
optional --decon-genes TSV with columns gene, e_call, e_bf; NA until the
DECON module exists). Z-score is not an arm; the legacy concordance table
still rides through into the JSON for reference.

Tier rule (fp_ok = LOO fp_any_rate < --loo-fp-max, default 0.10; unknown =
not ok): REVIEW on any contradiction; with a depth direction: TIER_1 if an
independent arm agrees and fp_ok, TIER_2 if K and G agree and fp_ok or an
independent arm agrees without fp_ok, else TIER_3; without a depth call:
independent-only agreement TIER_3, cnLOH TIER_1 with two arms / TIER_2 with
one; NEUTRAL otherwise.

Outputs: genes.tsv columns gene chrom start end k_call k_cn k_log2 g_call
g_seg_log2 g_n_bins b_call p_call p_C p_loh e_call e_bf support flags
consensus_call tier loo_fp_any allelic_state (z_call removed). JSON schema
twist_cnv_consensus4/v3; tracks.cnr_bins now [chrom,start,end,gene,log2,
depth,weight].

Unchanged: modules/local/cnv_consensus_multi.nf (no new inputs yet);
ZSCORE_CNV, CNV_CONCORDANCE, CNV_CLINICAL_REPORT keep running until 7b
(with item 12) retires them and switches the dashboard to this table.

Nextflow does not hash bin/ scripts: a running pipeline picks the new
script up when its CNV_CONSENSUS_MULTI task starts; -resume does not
re-execute an already completed consensus task.

## Addendum 2026-09-08 — CMX_ANNOT_V1 annotation columns (C1)

Seven columns are appended after `allelic_state` in `<sample>.cnv_consensus4.genes.tsv`
and as keys on every `genes[]` row of the JSON. The first 27 columns are unchanged;
downstream readers select by header name.

| column | source | value |
|---|---|---|
| `cytoband` | UCSC `cytoBand_hg38.txt` | band(s) overlapping the gene span: `17p13.1`; `7q22.1-q22.3` when the gene straddles bands; `NA` without the asset |
| `clingen_hi` | ClinGen gene curation list (GRCh38) | Haploinsufficiency Score as published (0, 1, 2, 3, 30, 40); `NA` when the gene is not curated |
| `clingen_ts` | ClinGen gene curation list | Triplosensitivity Score, same scale |
| `driver_role` | hmftools DriverGenePanel `likelihoodType` | `ONCO` or `TSG`; `NA` when absent from the panel |
| `driver_report_del` | DriverGenePanel `reportDeletion` | `TRUE`/`FALSE`/`NA` |
| `driver_report_amp` | DriverGenePanel `reportAmplification` | `TRUE`/`FALSE`/`NA` |
| `driver_amp_ratio` | DriverGenePanel `amplificationRatio` | only when `reportAmplification` is TRUE, else `NA` |

Assets and wiring. `bin/cnv_consensus_multi.py --cytoband --clingen --driver-panel`,
all optional (missing asset -> column `NA`). `modules/local/cnv_consensus_multi.nf`
takes three `path` inputs after `gene_blacklist`; `workflows/tspipe.nf` resolves them:
`params.cytoband` -> `assets/references/cytoBand_hg38.txt`;
`params.clingen` -> `assets/references/ClinGen_gene_curation_list_GRCh38.tsv`;
`params.hmf_driver_panel` (set in `conf/twist_apply.config`) ->
`assets/<panel>/hmftools/DriverGenePanel.<panel>.38.tsv`; each becomes an empty list
when the file does not exist. The ClinGen file has several leading `#` comment
lines; its header line begins `#Gene Symbol` and is detected by that prefix.

Known gaps. Non-gene targets (`*_intronic`, `*_5UTR`) have no driver role by design.
IDH1, IDH2, BRAF and FANCI are real genes absent from the 127-row DriverGenePanel
(register N8). Matching is by exact gene symbol on all three assets.

Cache. The annotation is a `bin/` change; the module bash comment carries
`annotation CMX_ANNOT_V1` to bust the task cache. Patcher:
`tools/patches/2026-09-07/patch_cmx_annot_v1.py`. Verified on run8: 135 genes per
sample, 0 cytoband NA, first 27 columns byte-identical to the pre-patch table.
