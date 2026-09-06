# DECON_V1 -- exon-level CNV arm E (DECoN / ExomeDepth) -- 2026-09-06

Gap register A5; unblocks handoff item 6 and arm E of CMX_V2.

## Files in this bundle (repo-relative)

    bin/decon_call_sample.R          one test sample vs a stratum pool; QC gate; DECoN *_all.txt layout
    bin/decon_gene_table.py          CMX_V2 --decon-genes contract (gene, e_call, e_bf, ...)
    modules/local/decon.nf           DECON process (host 'decon' env)
    tools/decon/build_decon_pool.sh  per-stratum pool asset builder (--sex male|female)
    tools/patches/2026-09-06/patch_decon_v1.py   wiring: twist_apply.config, tspipe.nf, cnv_consensus_multi.nf

Two files are copied on gandalf from tools/decon (unchanged content, new home):
    cp tools/decon/ReadInBams.R           bin/decon_ReadInBams.R
    cp tools/decon/filter_decon_calls.py  bin/filter_decon_calls.py
    cp tools/decon/twist_myeloid_exons.bed assets/twist_myeloid/decon_exons.bed
    cp tools/decon/twist_myeloid_exon_numbering.tsv assets/twist_myeloid/decon_exon_numbering.tsv

## Design

Pool per stratum (asset): decon_ReadInBams.R over the sheet's include_in_pon
normals (23 male, 8 female) -> decon_pool_<sex>.RData; IdentifyFailures.R
(pool exon/sample failures) and makeCNVcalls.R within-pool LOO calls kept
as TSV assets (recurrence list; not yet used by the filter).

Per sample (DECON): ReadInBams on the test BAM alone; decon_call_sample.R
appends that column to the sex-matched pool and runs select.reference.set
+ CallCNVs for the test sample only; QC gate = max correlation with the
pool >= 0.98 and median count >= 100 (D7 thresholds); filter_decon_calls.py
(BF >= 12, paralog and low-power classes; PROBE_VARIANT needs the sample's
variant table and is not wired in v1); decon_gene_table.py writes the
contract with every gene NA when QC fails so arm E abstains.

Consensus: DECON.out.genes joins the CNV_CONSENSUS_MULTI input as
--decon-genes. When decon_pool_male is unset or the asset does not exist
yet, an empty placeholder is joined and the argument is omitted (log.warn).

Female pool from 8 normals: ExomeDepth selects a correlated subset; power
is lower than the male pool. Pool for the other stratum is staged under
female_stratum/ and never read.

## Order of operations

1. Copy the four files above; place the bundle files; chmod +x bin/*.R bin/*.py.
2. Build the male pool (serial ReadInBams over 23 BAMs, roughly 30-60 min):
       setsid bash -c 'cd /goast/hemat_data/nf-core-tspipe; bash tools/decon/build_decon_pool.sh --sex male' > /tmp/decon_pool_male.log 2>&1 & disown
   then the female pool the same way (8 BAMs).
3. Apply the patcher (dry run first). Safe before the pool exists: the gate
   disables arm E with a warning until decon_pool_male.RData appears.
4. -stub-run; then a real one-sample run. On the 26CGH60 run directory a
   -resume adds DECON and re-executes only the consensus and what follows.

## Outputs per sample (<outdir>/<sample>/cnv_decon/)

<id>.decon_all.txt (DECoN layout + N.exons.gene), <id>.decon_filtered.tsv,
<id>.decon_qc.tsv, <id>.decon.genes.tsv (contract), <id>.decon.RData.
[SEXSTRAT] line in .command.log names the pool used.
