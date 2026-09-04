# Memo: Twist myeloid CNV reference set rebuilt on alt-aware alignments

Sessions 2026-09-03 (evening) and 2026-09-04. nf-core-tspipe HEAD at close: 134cf3e.
Decisions and evidence only. Procedures are in the commit messages and in
`tools/patches/2026-09-04/`.

## 1. Decisions

D1 (corrected twice). The bwa-mem2 index was not alt-aware. Installing the
`.alt` file (09-02) was insufficient for nf-core-tspipe because Nextflow stages
index files from an explicit list; `.alt` staging was added to PREPROCESSING
(412f223, MARKER alt_staging). Production pipeline aligns against the reference
path directly and was fixed by the install alone.

D1 scope (corrected 09-04). The alt-contig bug affected four genes, not six:
HRAS, PRPF8, PARN, ELANE (78 exons). The STAT5B (exons 7, 8) and SUZ12 (exon 3)
losses in `docs/audit/2026-09-02/evidence/mapq_loss_exons.tsv` are a separate,
permanent limitation caused by primary-assembly paralogs (STAT5A at
chr17:42.3 Mb; SUZ12P1 in NF1-REP-A at chr17:30.7 Mb). See section 3.

D3 (done). All 24 male normals re-aligned alt-aware through full TSPIPE
(realign_v4). CNVkit/GATK PoN, BAF background, PureCN normalDB and DECoN pool
rebuilt from those BAMs and committed. D4 retrospective is scoped on the four
alt-affected genes only.

D5 (unchanged). Male11 stays out of the CNVkit/GATK/PureCN reference
(constitutional KRAS duplication; DECoN BF 84.9 in the v4 pool, was 85).

VARIANT_VALIDATOR default (b4b6706). maxForks 1, errorStrategy retry,
maxRetries 3 promoted from `/tmp/vv_serial.config` to `conf/modules.config`.
Evidence: realign_v4 (24 samples) completed with three transient VV failures
recovered by retry; maxForks 2 previously hung the endpoint. The block comment
citing localhost:5001 as the reason for host-local execution is obsolete since
49a4bff (public REST endpoint); containerising VARIANT_VALIDATOR is no longer
blocked.

Female pilots run with `sex = male` by design so that CNV arms normalise
against the male PoN and chrX presents as a positive control. `cnvkit_pon_female.cnn`
(12-plex, non-conforming) must not be selected until the 8-plex female PoN exists.

## 2. Verification chain (all against v2.1 or the 09-01/09-02 evaluations)

realign_v4 (run magical_bell, resumed from stoic_montalcini after disk-full
MarkDuplicates): 8 h 50 m, 1113 succeeded, 61 cached, 4 ignored
(FLT3_ITD_EXT: Male1, Male6, Male21, Male24), 7 failed (3 VV retries + the 4
ignored). Male3 HRAS chr11:532240-532521 at MAPQ>=20: 9916 reads (0 before);
TP53 chr17:7675053-7675236: 7072.

BUILD_PON_TWIST build_v3 (09-04): 106 tasks, 12 m 33 s, 0 failures. Nine
assets seeded flat into `assets/twist_myeloid/`, checksums in
`pon_male_v3.md5` (4922e18). Same 6100 bins as v2.1;
`targets.preprocessed.interval_list` and `targets.gc.annotated.tsv`
byte-identical to v2.1 (BED- and reference-derived). PoN bin depth vs v2.1:

| gene | v2.1 | v3 | ratio |
|---|---|---|---|
| HRAS | 798.9 | 1449.3 | 1.81 |
| PRPF8 | 957.3 | 1725.5 | 1.80 |
| PARN | 804.4 | 1454.1 | 1.81 |
| ELANE | 827.3 | 1480.8 | 1.79 |
| STAT5B | 1603.0 | 1638.1 | 1.02 |
| SUZ12 | 1249.1 | 1278.6 | 1.02 |
| TP53 | 1606.7 | 1643.4 | 1.02 |
| NPM1 | 966.0 | 988.1 | 1.02 |

The 09-03 non-alt-aware build had shown +2% on HRAS; that is how the staging
bug was caught. Noisy bins 539 -> 523 (marginal-bin churn, not the rescued
genes); LOO genes 3103 and BAF sites 44885 unchanged.

PureCN normalDB (134cf3e): 23 males, PureCN 2.16.0, fresh workdir
`pon_twist/purecn_normaldb_v4`. Interval file 5782 rows, byte-identical to the
previous build. Male3 loess coverage vs non-alt-aware: HRAS intervals 1.71x
and 1.75x; TP53 intervals 1.00x. HRAS duplication rate 0.16 -> 0.28 (the
returning half of the reads), TP53 unchanged.

Females (run reverent_stone, 2 h 06 m, 100 tasks, 0 ignored, 0 failed;
FLT3_ITD_EXT held for both). Female16 HRAS MAPQ>=20: 7398.
Female16 v4 vs 09-01 pilot: 13 TIER_1 concordant, all chrX (log2 0.905-0.944,
z 8.5-12.5), identical; 0 autosomal concordant calls in either run. HRAS,
PRPF8, ELANE, TP53 neutral in both (the bug halved depth in sample and
reference alike, so MQ0-counting ratios were never wrong; coverage QC and
MAPQ-filtered callers were).
Female18 (2.2x Female16's reads): 13 chrX genes at log2 0.91, plus one
autosomal TIER_1, ZNF91 loss (section 4).

DECoN pool25_v4 (24 males + Female16, alt-aware): failures 79 -> 1 (Female16
whole-sample, correlation 0.970 from the chrX mismatch; expected). The 78
whole-exon failures, HRAS 725/726 among them, are gone. Male11 KRAS BF 84.9.
Female16 chrX duplications BF 14.3-29.9. New single-exon calls: HRAS exon 730
in four males, both directions (Male1 del ratio 0.53 BF 13.8; Male4 del 0.57
BF 8.5; Male11 dup 1.41 BF 4.3; Male19 dup 1.30 BF 2.9), expected ~240 reads;
ANKRD26 exons 664/676/684 deletions in Male23 (BF 12.6, 0.67), Male12
(BF 11.6, 0.53; BF 5.7, 0.65) and Female16 (0.49; 0.15).

## 3. STAT5B / SUZ12: paralog, not alt contig

Non-alt-aware evidence (total -> MAPQ>=20): SUZ12 exon 3 1375 -> 590; STAT5B
exon 8 1414 -> 499; exon 7 1777 -> 395. Alt-aware Male3, same regions:
3044 -> 1364 (45%), 4306 -> 1832 (43%), 5346 -> 1350 (25%). Unchanged
fractions. Every low-MAPQ read carries exactly one XA alternative hit, all on
chr17 primary: 30.7 Mb for the SUZ12 exon (SUZ12P1), 42.3 Mb for the STAT5B
exon (STAT5A). The `.cnn` depth comparison could not detect this because
CNVkit counts at MQ0 and total depth at these exons is unaffected; the MAPQ>=20
samtools count is the correct test for partial-paralog genes. Consequence:
CNV ratio calls at these exons remain interpretable (sample and reference are
filtered identically) but with reduced power; SNV sensitivity is reduced for
MAPQ-filtered callers, same class as U2AF1 S34F on chr21. DECoN's recurrent
SUZ12 false positives (09-02 findings, line 39) fit this.

## 4. ZNF91 in Female18: reference instability, not a deletion

Female18 ZNF91 log2 -0.374, z -3.81, concordance `cnvkit,zscore`, cn.mops and
ifCNV silent, LOO FP 0/23, no DECoN call in any male. Exon coverage at
MAPQ>=20 relative to sample median is identical in both females (exon 4
0.13 / 0.16; exon 3 0.60 / 0.65; exon 1 0.44 / 0.42), yet Female16's CNVkit
log2 is -0.015. The pooled reference's per-bin residual log2 for ZNF91 runs
from +0.46 to -0.63 within one 5 kb exon (depth 365-1824, GC 0.24-0.35), and
-0.60 at the GC-rich exon 1 (GC 0.60): the bias model does not fit this locus.
A sample from a different capture batch (both females are 12-plex) drifts off
these bins according to its own GC curve. Same-batch LOO cannot see it.

## 5. Corrections to earlier lessons

Lesson 2 (rewritten). Killed or backgrounded Nextflow runs leave task shells
*stopped* (`T` state), not dead. Nextflow runs `stty ... < /dev/tty`; without
`setsid` a backgrounded run receives SIGTTIN and its whole process group
stops. Stopped processes ignore SIGTERM, hold files open, show ~0% CPU, and
survive indefinitely. Found on 09-04: cohorts 112, 99 and 3 days old,
including a `fastp` on Female10 stopped since 08-31 18:12. Sweep after any
kill with `ps -u hemat -o pid,stat | awk '$2 ~ /^T/'` and use SIGKILL.

Lesson 4 (corrected). Publish mode is per publishDir. The global
`params.publish_dir_mode` is `link` (hardlinks; deleting work frees nothing
for those files). ORGANIZE_OUTPUT is an explicit `copy`: `<sample>/clinical/`
is independent of `work/` (link count 1, regular files; 79 GB for the 24
normals). Check `stat -c %h` before assuming either.

## 6. Disk and process hygiene

09-03 deletions (from the handoff, all patient FASTQ verified on S3 first):
nf-core test_run 81 G, nfcore_runs 60 G, production OCIAML3, BNC_fastq (first
run), results_masked, pon_coverage_masked, cnv_negatives 45 G, sequences 56 G,
sample_fastqs 23 G, reference_pipeline checkout, nf-core normals/ 177 G
(on S3), realign_v3, pon_twist/bams, work_v3, build_v3 (non-alt-aware).
/goast/Anand 77 G -> `s3://hemat/archive/Anand_backup_20260902.tar` (81.6 GB,
verified), then deleted.

09-04: `nextflow clean -f -k` on naughty_visvesvaraya, hungry_lumiere,
golden_mahavira, stoic_montalcini, magical_bell, reverent_stone freed 473 GB
(354 -> 827 GB free); `work/` residue 393 MB from the two killed runs whose
cache index was never written. Deleted `twist_pilot/altfix/aln` (3.6 G) and
`nxf_work_twist` (133 M, home of the stopped Female10 fastp). Kept: `work_v3`
(82 M, PoN build intermediates), `references/backups/twist_myeloid_v2.1/`
(untracked), the old `twist_pilot/decon/` evaluation for side-by-side.

## 7. Open items

New this session
1. DECoN exon exclusion list or depth-conditioned BF threshold. HRAS exon
   730 (~240 expected reads) produces single-exon calls in 4/24 normals, one
   above BF 12. First member of the list.
2. Paralog-limited exon table, panel-wide: MAPQ>=20 retained fraction per
   exon across the 24 v4 BAMs (mosdepth `--mapq 0` vs `--mapq 20`), flag
   below ~80%. Known members: STAT5B exons 7-8, SUZ12 exon 3; candidate
   ANKRD26. Half a day including the script. Feeds both CNV caveats and the
   U2AF1-style SNV rescue list.
3. Reference-instability exclusion axis: bins with |reference log2| > ~0.3
   in `cnvkit_pon_male.cnn` are loci the bias model failed on (ZNF91).
   Complements the two existing exclusion criteria.
4. TIER_1 concordance rule: `cnvkit` and `zscore` count the same reads against
   the same reference and should not constitute two independent votes.
5. TIER_2 ZSCORE_ONLY volume: ~1,200 rows per normal at |log2| < 0.1. Confirm
   the dashboard suppresses TIER_2; otherwise raise the z-score arm threshold.
6. FLT3_ITD_EXT non-fatal failures: reproducible inputs Male1, Male6, Male21,
   Male24 (realign_v4); none on the two females.
7. Containerise VARIANT_VALIDATOR (no longer blocked), then FLT3_TO_VARIANTS,
   then ONCOVI; retire params.legacy_python_env.
8. BUILD_PON_TWIST: four `first` operator warnings on value channels
   (cosmetic).

Carried
- D4 retrospective on HRAS/PRPF8/PARN/ELANE in archived cases.
- Female re-capture at 8-plex; female PoN build. ZNF91 (section 4) is a
  second argument for same-batch references.
- Positive controls on Twist (OCI-AML3 etc.).
- Production myeloid_cnv PoN alt-aware rebuild (BNC_fastqs).
- FASTP adapter fasta as staged path input.
- MoChA Route B.
- Asset-root split; archive production.
- oncoanalyser 3.0.0 evaluation (AMBER/COBALT/PURPLE as a sixth arm;
  needs Hartwig-reference re-alignment from FASTQ and ~200 GB): after the
  above, not before.
- MNV merging before annotation; CAVA integration (requested 09-03).

## Addendum (2026-09-04, later): paralog-limited exon table built

`tools/paralog_limited_exons.py` over the 23 v4 males, 1795 exons, mosdepth
MAPQ>=0 vs MAPQ>=20. Six exons are paralog-limited (median retained < 0.80,
all < 0.75; next on the panel NF1 exon 24 at 0.889): STAT5B exons 6, 7, 8
(retained 0.61, 0.23, 0.40; XA locus STAT5A chr17:42.2-42.3 Mb, 97-100%) and
SUZ12 exons 3, 6, 9 (0.44, 0.57, 0.73; SUZ12P1 chr17:30.7 Mb, 100%). ANKRD26
is not paralog-limited (retained 1.0 throughout); the withdrawn candidate in
open item 2. Its DECoN deletions, and HRAS exon 730's, come from low-depth
exons: HRAS exon 1 148x, ANKRD26 exons 5/14/28 at 170-320x, exons 19/29 at
10-16x (capture failures, with CCNC exons 6-7 and AKT1 exon 1). Open item 1
(DECoN exon exclusion) is therefore derivable from this table on
`median_depth_mq20` alone. Table seeded as
`assets/twist_myeloid/paralog_limited_exons.tsv` (+ per-sample matrix).

## Addendum 2: DECoN post-hoc filter (open item 1 closed)

`tools/decon/filter_decon_calls.py` classifies single-exon DECoN calls by
overlap with `paralog_limited_exons.tsv` and the sample's own variant table:
PARALOG_EXON (never reported), PROBE_VARIANT (PASS variant, VAF >= 30%,
inside the call interval; never reported), LOW_POWER_EXON (exon median
MAPQ>=20 depth < 300x; reported only at BF >= 20), else PASS at BF >= 12.
Multi-exon calls pass at BF >= 12. Male23 ANKRD26 exon 27 (ratio 0.67, BF
12.6) is a probe-variant dropout: two homozygous variants under the probe,
c.3972+3A>G and p.Val1305Ile, alt fraction 1.0 at 400+ reads. On
pool25_v4: 61 calls, 6 reportable (Male11 KRAS BF 84.9; Female16 chrX x5),
1 LOW_POWER_EXON (Male1 HRAS exon 1, BF 13.8), 1 PROBE_VARIANT, 53 below BF.
Zero false positives across 25 normals. Evidence table:
`decon_pool25_v4_filtered.tsv` alongside this memo.
