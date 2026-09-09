# Memo 16 — Pipeline hardening from the audit: Q3–Q6 (HARDEN_Q3Q6_V1)

Date: 2026-09-09. Repo `/goast/hemat_data/nf-core-tspipe`. Source: ChatGPT audit findings
verified against f830536 on 8 Sep (handoff v3 §3d). Patcher and checks in
`tools/patches/2026-09-09/`.

## 1. Scope

| Id | Finding | Change |
|---|---|---|
| Q3 | No samplesheet gate although `assets/schema_input.json` exists; FASTQ `checkIfExists` fires lazily mid-run | `validateSamplesheet()` in `workflows/tspipe.nf`, called after the `--input` param checks and before any channel is built. Mirrors the schema without the nf-schema plugin: required columns, non-empty whitespace-free unique ids, `.fq.gz`/`.fastq.gz` suffix and existence for both FASTQs, sex in male/female/unknown/empty. All problems reported in one message. Channel/meta code unchanged, so task hashes are stable. |
| Q4 | `pipefail` in 8 of 75 modules | `process.shell = ['/bin/bash', '-euo', 'pipefail']` in `nextflow.config` (after the includes). New `BAM_QUICKCHECK` process (`modules/local/bam_quickcheck.nf`, samtools 1.18 container) on the final BAM, its own process so no cached task is invalidated; publishes `<sample>/qc/<sample>.quickcheck.txt`. |
| Q4 (safety) | Scripts that tolerated a failing producer | `\|\| true` on `VAR=$(ls glob 2>/dev/null \| head -1)` in `reconcnv.nf` (5 lines; the HETVCF line lists two patterns and fails whenever either is empty) and on the `ls \| wc -l` / `ls \| sort \| tr` counts in `bpt_cnvkit_reference.nf`, `bpt_cnv_loo_qc.nf`, `bpt_gatk_create_rc_pon.nf`, `cnvkit_pon_build.nf`. `somaticseq.nf` L197 reviewed: guarded by the `N_PURGE -eq 0 → continue` check and the module already sets pipefail; no change. Version-capture pipes inside `versions.yml` heredocs are unaffected (exit status is `cat`'s). |
| Q5 | ANNOVAR failure non-fatal → ClinVar/COSMIC/gnomAD/avsnp silently `-1`, CLINVAR_BENIGN demotion off | `bin/annotate.py`: non-zero ANNOVAR exit → exit 1; exit 0 with missing/empty multianno → exit 1; a missing ANNOVAR database → return 1 (`--annovar-allow-missing-db` restores the old skip-with-warning). |
| Q6 | `max(hits)` on `(overlap, dict)` tuples, TypeError on equal overlaps | `max(hits, key=lambda h: h[0])` at both sites in `cnv_consensus_multi.py`. First segment wins a tie (pre-existing semantics; run8 never tied). |

Deferred: Q1 (sex_check exceptions → INDETERMINATE, exit 0) and Q2 (MISMATCH keeps samplesheet
sex) await the policy decision. Recommendation on record: Q1 hard fail; Q2 forced REVIEW with
samplesheet sex retained (meta.sex is in every task hash; switching to inferred sex re-executes
the sample end to end).

## 2. Verification

- `check_annovar_fatal.py` on the cached VEP_ANNOTATE task `work/cd/a39e70a6…` (26CGH1250,
  8 Sep 22:35, CAVA_V1b2 vintage) with `run_vep`/`run_annovar` stubbed: A (ANNOVAR rc 1) exit 1;
  B (multianno absent) exit 1; C (success path) output byte-identical to the cached
  `annotated.tsv` (md5 cb0fd5c3…); D (empty `--annovar-db`) rc 1 strict and lenient. PASS.
  First attempt against the 7 Sep task failed C by construction (older code); `nextflow log` for
  session abea2914 does not list the 8 Sep runs (missing index files) — see §4.
- Q6 tie test: equal-overlap segments raise `TypeError: '>' not supported between instances of
  'dict' and 'dict'` on the old code, return `('GAIN', 1, -0.9)` on the new.
- `-preview` with a constructed bad samplesheet: four problems reported (duplicate id, whitespace
  id, bad FASTQ suffix, sex `M`); with `twist_val_8_fastq.csv`: `8 sample(s) validated`,
  `BAM_QUICKCHECK` present in the DAG.
- run8 resume (session abea2914, run `special_austin`, 08:31–08:45, 13m58s): 98 executed, 352
  cached. Executed set exactly as predicted: BAM_QUICKCHECK, VEP_ANNOTATE + VARIANT_FILTER +
  VARIANT_VALIDATOR + ONCOVI + FLT3_TO_VARIANTS + IGV_REPORTS, CNV_CONSENSUS_MULTI + EXON_PLOTS +
  CHROM_PAGES, RECONCNV, ORGANIZE_OUTPUT (8 each), DASHBOARD, REPORT_BUNDLE. Preprocessing and
  all callers cached: `process.shell` is not part of the task hash.
- `samtools quickcheck` OK on all eight final BAMs (2.6–3.8 GB).
- 26CGH1250 `annotated.tsv`, new task vs 22:35 task: 5301 rows both, 40 columns, staged inputs
  and ANNOVAR multianno identical; 19 rows differ, all in `Consequence`, all the order of the
  equal-rank pair `splice_region_variant` / `splice_polypyrimidine_tract_variant`. VEP output
  itself differs (md5), ANNOVAR does not. See Q7.

## 3. Learnings

- `bin/` scripts invoked by bare name (annotate.py, cnv_consensus_multi.py) are in the task hash
  (Nextflow bin-entries rule); only scripts referenced by directory path (dashboard_builder)
  escape it. A `bin/annotate.py` change costs a ~60-task resume every time.
- `process.shell` is not hashed; enabling pipefail globally invalidates nothing.
- VEP is not byte-reproducible run to run: equal-rank consequence terms come out in Perl
  hash-iteration order, randomised per process.

## 4. Follow-ups

- **Q7 (new):** run VEP with `PERL_HASH_SEED=0 PERL_PERTURB_KEYS=0` in `run_vep()`'s env so two
  runs of the same input produce identical `Consequence` strings. One line; fold into the next
  `annotate.py`-touching commit (N4) to avoid a resume of its own.
- N10: `nextflow log abea2914…` warns `Missing cache index file … index.silly_bardeen` and does
  not list the 8 Sep runs; the two `-preview` sessions from today and
  `/goast/hemat_data/twist_val/preview_q3q6/` join the cleanup list. Locate work dirs by
  `ls -t work/*/*/<sample>.<file>` and `readlink -f` when the log is unreliable.
- `BAM_QUICKCHECK` writes samtools' "verbosity set to 2" banner into the report (`-vv`);
  cosmetic, leave unless the module is touched for another reason.
- N15 (test suite): `check_annovar_fatal.py` and `compare_annotated.py` are the first two
  pieces; a stub-mode DAG test and the `-preview` bad-samplesheet case are natural next entries.
- SOP: `docs/sops/` needs a line on the preflight (what a `[PREFLIGHT]` failure means and how
  to fix the samplesheet) and on `--annovar-allow-missing-db`.
