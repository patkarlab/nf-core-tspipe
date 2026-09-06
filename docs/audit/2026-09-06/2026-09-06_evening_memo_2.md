# 2026-09-06 evening session -- memo addendum 2 (DECoN, publish fix, first case)

Continues 2026-09-06_evening_memo.md. Session end HEAD 006844b (14 commits
today, b84d8b1..006844b, all on origin/main). Nothing running at close
except nothing; two DECoN pool builds and the 26CGH60 resume all completed.

## 1. DECON_V1 -- exon-level arm E (commits 6598e35, afabcdd, 78fc149, 006844b)

- Per-stratum pool assets built by tools/decon/build_decon_pool.sh --sex:
  male 23 normals (Male11 excluded): no exon or sample failures (the
  alt-aware v4 BAMs removed the MAPQ-dead exons the 09-02 evaluation had to
  exclude); 25 within-pool LOO calls (1.1/sample), one at BF >= 12 (Male1
  HRAS exon 1 deletion, BF 13.8, the consistent-suppression exon).
  female 8 normals: one exon failure (BED row 127, a DNMT3A exon at
  median 48x); 3 LOO calls in 8 (Female18 BPGM single-exon duplication
  BF 54, Female24 GNB1 / NOTCH1 single-exon deletions BF 6).
  Assets: decon_pool_<sex>.RData, _failures.tsv, _loo_calls.tsv, .md5;
  decon_exons.bed (1,778 targets, 126 genes), decon_exon_numbering.tsv.
- modules/local/decon.nf: ReadInBams on the test BAM alone, then
  bin/decon_call_sample.R appends the column to the sex-matched pool and
  runs select.reference.set + CallCNVs for the test sample only, with the
  D7 QC gate (max correlation >= 0.98, median count >= 100); calls in
  DECoN's *_all.txt layout so bin/filter_decon_calls.py runs unchanged
  (BF >= 12, paralog / low-power classes); bin/decon_gene_table.py writes
  the CMX_V2 --decon-genes contract (every gene NA when QC fails). Host
  'decon' env via PATH override; pool of the other stratum staged under
  female_stratum/. Gated on params.decon_pool_male AND the asset existing
  (log.warn and empty placeholder otherwise). DECON.out.genes joined into
  CNV_CONSENSUS_MULTI (--decon-genes when present).
- V1a: the DECON include line was missing from tspipe.nf; stubs passed
  only because the gate was closed. Fixed (afabcdd).
- Not in v1: PROBE_VARIANT classification (needs the sample variant
  table), a recurrence blacklist from the pool LOO calls, plots, a
  sex-aware low-power flag (female DNMT3A exon).

## 2. Publish fix (cf8a7cf, 7a6c50f)

main.nf's onComplete sweep deletes <outdir>/<sample>/cnv_consensus (a
legacy scratch name) and the twist overlay published the CMX_V2 outputs
there; the 19:01 run lost its consensus table. First fix (V1) moved the
files under clinical/, which ORGANIZE_OUTPUT materialises whole and
thereby wiped them. V2: consensus, DECON and sex_check publish at sample
level in cnv_consensus_multi/, cnv_decon/, sex_check/ (not on the sweep
list, beside cnv_baf/, cnv_gatk/, purecn/). Routing through
ORGANIZE_OUTPUT into clinical/ (and therefore report.zip) is deferred to
item 12 where the clinical/ layout and the dashboard change together.

## 3. Resume lesson

Bare -resume and -resume <run-name> both attached to the last stub
session in this launch directory and re-ran the whole pipeline; only
-resume <session-uuid> (from `nextflow log -f name,session`) attached to
the real run. Always resume by session uuid here. Killed runs to clean:
compassionate_sax, friendly_joliot, sad_lamarr (their work/ is under the
repo work/ dir) plus the stub sessions in /tmp/sex_check_stub_work.

## 4. First validation case: 26CGH60-TwistMyVal (sex=unknown on the sheet)

Reported diagnosis (Nikhil, 09-06): B-cell precursor ALL; FISH
BCR::ABL1 95%, IKZF1 deletion del(7p12.2) 90%, CDKN2A deletion del(9p21) 90%.

Pipeline (evil_elion 17:57-19:01, 52 tasks; resume with DECON and the
stratified references 19:4x, cached through annotation):
- SEX_CHECK: male, X/A 0.543; PureCN's own sex_inferred M agrees.
- Variants: consequence filter first in-pipeline exercise, 986 rows
  NON_REPORTABLE_CONSEQUENCE, 10 clinical PASS (Nikhil's review).
- PureCN: OK, purity 0.36, ploidy 2.03, flagged HIGH AT/GC DROPOUT ->
  arm P advisory (its calls agree with the others).
- CDKN2A / CDKN2B: TIER_1 LOSS, flags EGK (CNVkit cn 0 log2 -2.78, GATK
  -2.92, PureCN C=0, DECoN 15-exon deletion BF 130 ratio 0.48).
  Homozygous core chr9:21.97-22.07 Mb; hemizygous 9p flank 23.4-39.1 Mb
  incl. PAX5 (cn 1, -0.67/-0.85, PureCN C=1). CNVkit-only cn 1 at
  17.4-20.6 Mb where GATK is neutral (segment boundary disagreement).
  NOTCH1 TIER_3 GAIN on CNVkit alone (cn 3, log2 0.22).
- IKZF1: DECoN deletion exons 4-7 (Delta4-7 / Ik6), ratio 0.61, BF 9.89,
  BELOW_BF under the D7 threshold of 12 -> not reportable, not in the
  consensus. CNVkit bins for exons 4-7 sit at log2 -0.92/-0.72/-0.68/-0.79
  (weights 0.99) yet CBS segmented through them (flat chr7 0.24-57.3 Mb);
  GATK likewise. A real, 90%-clonal finding missed by the threshold, with
  the signal present in every arm's raw data. IKZF1 is not in
  targets.focal_cnv.bed (17 rows).
- BCR::ABL1: out of scope for the DNA CNV arms (no SV calling wired);
  RNA fusion panel.
- Remaining DECoN calls: 15 single/few-exon duplications at BF 2-6, the
  expected noise floor.

Decisions pending (Nikhil): DECoN BF threshold (candidate rule: multi-exon
deletions at BF >= 8 in focal-CNV genes, else 12; the male pool LOO
table gives the false-positive cost of any rule); whether IKZF1 joins
targets.focal_cnv.bed. Infrastructure follow-up: CNVkit segmentation
sensitivity to short sub-gene events (segment threshold / HMM) under the
item 12 tuning.

## 5. tools/plot_exon_ratio.py (78fc149, 006844b)

Per-exon copy-ratio plot in genomic order from the consensus JSON
(tracks.cnr_bins with depth and weight) or a .cnr; guides at +/-0.5 and
+/-1.0, point size by weight, hollow below 0.5, gene blocks, one bracket
per DECoN call with BF, ratio and decision. Needs matplotlib: run with
/home/hemat/anaconda3/envs/targeted-seq/bin/python3. Figures for 26CGH60
(chr7 IKZF1 region, chr9 JAK2..NOTCH1) are in
<outdir>/26CGH60-TwistMyVal/cnv_consensus_multi/. Becomes the per-gene
view of the styled scatter under item 12.

## 6. Open items delta after this addendum

Done today: A1, item 4 (four consumers), item 5, item 7a, A5 (DECON) and
item 6 (female pool), first half of A3, the publish fix.
Next: the eight-case validation run (pon_samplesheets/twist_val_8_fastq.csv,
all sex=unknown) now exercises every change; then item 12 (reconCNV +
styled scatter wiring, dashboard CNV tab on the consensus table,
ORGANIZE_OUTPUT routing, CNVkit segmentation tuning) with 7b; items 2/3;
item 9 BAF_V2 with the rest of A3; 10/11. Threshold and focal-list
decisions after the eight cases.

Untracked files still awaiting a decision: tools/verify_s3_archived.py,
normals_twist.csv, pon_samplesheets/twist_males_24_fastq.csv, the two
probes_ok_*.bed files, qc/, references/backups/.
