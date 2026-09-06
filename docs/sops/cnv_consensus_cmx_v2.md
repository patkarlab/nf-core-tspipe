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
