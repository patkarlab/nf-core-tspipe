# 2026-05-19 — D1 and D2 real-data validation findings

Status: real-data run on 25NGS1307 completed successfully (after one
VV-port issue diagnosed and resolved mid-session). D1 is structurally
working and surfaces a follow-up filtering issue worth a separate commit
next session. D2 is structurally working pending a browser-level visual
inspection of the published HTML.

This memo replaces and supersedes the draft `d1_real_data_findings.md`
that was prepared during the resume run.

---

## Run summary

| Field        | Value                                                          |
|--------------|----------------------------------------------------------------|
| Outdir       | `/goast/hemat_data/nfcore_runs/d1d2_real_20260519_104440`      |
| Sample       | 25NGS1307                                                      |
| Profile      | `gandalf,singularity`                                          |
| Started      | 2026-05-19 10:44                                               |
| First fail   | ~11:20 (VARIANT_VALIDATOR cannot connect to localhost:5001)    |
| Resumed      | 2026-05-19 11:58 after VV restored on port 5001                |
| Completed    | 2026-05-19 11:59 (resume ran in <1 min thanks to 37 cache hits)|
| Exit         | success; clinical/ tree populated                              |

### Mid-run failure: VV port mismatch

VARIANT_VALIDATOR is hardcoded in `modules/local/variant_validator.nf`
to use `http://localhost:5001`. After today's morning VV-stack migration,
gunicorn was bound to host port 8000 (container port 8000), leaving the
host port 5001 mapping (container port 5000) with nothing listening.

Resolution: started a second gunicorn worker on container port 5000:

```bash
sudo docker exec -d rest_variantvalidator-rest-variantvalidator-1 \
    gunicorn -b 0.0.0.0:5000 --workers 1 --threads 5 --timeout 600 \
    wsgi:app --chdir ./rest_VariantValidator/
```

After ~30s of init time, `localhost:5001` returned HTTP 200 and a real
JSON response for `NM_000088.4:c.589G>T`. Pipeline `-resume` then picked
up from cache and completed.

**Open question** (not addressed today): should the morning VV migration
have launched gunicorn on container port 5000 from the start to match
the existing nf-core code, OR should the nf-core code be updated to use
port 8000 to match the migration choice? Either is defensible; the
choice affects whether the production runner remains compatible without
edits. Filed for next session.

---

## D1 — Pindel as 4th FLT3-ITD caller

### Comparison: nf-core (with D1) vs production (pre-D1)

**Production** (3-caller, byte-identical to backup at
`results/25NGS1307/flt3/25NGS1307_flt3_consensus.tsv`):

| status            | n_tools | tools                              | length |
|-------------------|---------|------------------------------------|--------|
| PASS_HIGH         | 3       | FLT3_ITD_EXT, filt3r, getITD       | 45     |
| REVIEW_REQUIRED   | 1       | FLT3_ITD_EXT                       | 39     |

**nf-core** (4-caller, this run):

| status            | n_tools | tools                                  | length | notes                  |
|-------------------|---------|----------------------------------------|--------|------------------------|
| PASS_HIGH         | 4       | FLT3_ITD_EXT, Pindel, filt3r, getITD   | 45     | UPGRADED from 3 callers|
| PASS_LOW          | 2       | FLT3_ITD_EXT, Pindel                   | 39     | UPGRADED from REVIEW   |
| REVIEW_REQUIRED   | 1       | Pindel                                 | 68     | NEW, likely noise      |
| REVIEW_REQUIRED   | 1       | Pindel                                 | 73     | NEW, likely noise      |

### Wins (the D1 success case)

1. **45 bp ITD upgraded from PASS_HIGH (3) → PASS_HIGH (4).** Pindel
   independently confirms the 3 existing callers. Pindel lead record at
   `chr13:28034132` is `GT:AD = 0/1:483,213`, ~30.6% VAF — well-supported.
   Higher clinical confidence on a real ITD.

2. **39 bp ITD upgraded from REVIEW_REQUIRED (1) → PASS_LOW (2).**
   Pindel confirms the FLT3_ITD_EXT call. This is the more interesting
   win: the previously-marginal call is now confidence-promoted. Worth
   re-curating the original case if it was signed out as negative or
   indeterminate.

### Issue surfaced: Pindel noise records

Two new REVIEW_REQUIRED rows (68 bp, 73 bp lengths) are Pindel-only
events with sub-1% VAF and `GT=0/0` genotype, e.g.:

```
chr13   28034268   ...  SVLEN=68   GT:AD  0/0:655,2     # 0.3% VAF, "not called"
chr13   28034159   ...  SVLEN=73   GT:AD  0/0:510,1     # 0.2% VAF, "not called"
```

Pindel emits these as *candidate* positions; `GT=0/0` indicates Pindel
itself did not call the indel at that read support level. They survive
the bcftools SVTYPE filter because they have `SVTYPE=INS` and SVLEN >= 6.

Production never produced these in its consensus because production has
not been wiring Pindel into the FLT3 consensus for this sample — the
production parser has the same lack of GT/VAF filter, but production
never gave it a Pindel VCF to parse.

Lesser issue, same root cause: the PASS_HIGH row's
`vaf_pct_mean = 2.7%` is misleadingly low. The real ITD is at 30.6% VAF
(the Pindel lead record). The mean is dragged down by 37 sub-1%
"candidate" records that the length-clustering folds into the same 45 bp
event. `vaf_pct_min = 0.19`, `vaf_pct_max = 30.6` — clinically the max
is the real signal, the min is noise. Not a blocker but ugly in a
clinical-facing TSV.

### Recommended next-session fix

Genotype filter in `bin/flt3_consensus.py:parse_pindel()`. After the
existing SVTYPE/length checks, skip records where `FORMAT/GT` is `0/0`,
`0|0`, or `./.`:

```python
fmt_keys   = parts[8].split(":") if len(parts) > 8 else []
sample_vals = parts[9].split(":") if len(parts) > 9 else []
fmt = dict(zip(fmt_keys, sample_vals))
gt = fmt.get("GT", "")
if gt in ("0/0", "0|0", "./."):
    continue
```

Expected effect on this sample: drops all 37 noise records on the 45 bp
event, drops the 73 bp pair, drops the 68 bp row. Final TSV would have
just the two upgraded real calls. PASS_HIGH row's `vaf_pct_mean` becomes
30.6% (the real value). Matches clinical intent.

The same fix should propagate to production's
`scripts/09b_flt3_consensus.py` in a paired commit.

---

## D2 — IGV_REPORTS wired into clinical tree

### Structural validation

The `clinical/` deliverable tree at
`<outdir>/25NGS1307/clinical/`:

```
total 1386084
-rw-r--r-- 25NGS1307_dashboard.html               203 KB
-rw-r--r-- 25NGS1307_exon_coverage.tsv             76 KB
-rw-r--r-- 25NGS1307_fastp.html                   490 KB
-rw-r--r-- 25NGS1307.final.bam                   1.4 GB (hardlinked)
-rw-r--r-- 25NGS1307.final.bam.bai               4.5 MB
-rw-r--r-- 25NGS1307_flt3_consensus.tsv            2 KB
-rw-r--r-- 25NGS1307_hsmetrics.txt                 5 KB
-rw-r--r-- 25NGS1307_igv_report.html             5.9 MB    <-- D2
-rw-r--r-- 25NGS1307.somaticseq.clinical.final.tsv 7.6 KB
-rw-r--r-- 25NGS1307.somaticseq.filtered.tsv     388 KB
drwxr-sr-x cnv_consensus/
drwxr-sr-x cnvkit_plots/
```

- IGV HTML at expected path, present, 5.9 MB.
- Within 4% of production's IGV HTML (5.7 MB).
- HTML opens with valid igv-reports template (proper `<html>`, `<head>`,
  igv.js script reference at jsdelivr CDN, expected stylesheets).
- ORGANIZE_OUTPUT consumed IGV's output via the new join slot. No
  channel-shape errors. The fact that the `clinical/` tree is fully
  populated proves the input tuple's positional ordering survived the
  D2 wiring change.

### Pending visual validation

Browser-based inspection of the HTML still required to fully sign off
on D2. Cannot be done from the command line because igv-reports embeds
variant data inside base64-encoded JavaScript blobs (so grep on
"Gene=" or "FLT3" returns nothing useful even on a working HTML).

**To validate visually**:

1. Copy or SFTP the HTML to a local machine:
   ```
   /goast/hemat_data/nfcore_runs/d1d2_real_20260519_104440/25NGS1307/clinical/25NGS1307_igv_report.html
   ```
2. Open in a modern browser (Chrome/Firefox/Safari).
3. Confirm the variant table loads with the expected ~18 clinical
   variants from `25NGS1307.somaticseq.clinical.final.tsv`.
4. Click a variant. IGV.js should embed-load the pileup for that region.
5. Spot-check the FLT3 ITD region (chr13:28034132 ± 500 bp from
   `--flanking`) — should show a clear ~30% alt-allele pileup
   consistent with the consensus row.

### Side note: clinical TSV row counts diverge

```
nf-core: 19 lines (18 variants + header)
production: 23 lines (22 variants + header)
```

This is the same B1-style schema/row divergence flagged in this
morning's audit. NOT a D1 or D2 issue. Worth re-investigating
separately; today's audit closed B1 as a phantom based on per-caller
VCF identity, but the *post-annotation* TSV row counts now differ on
the same sample. Either production's row count includes upstream
information nf-core doesn't, or vice versa. Out of scope for D1/D2;
file separately.

---

## Combined finalization status

| Item                                            | State        |
|-------------------------------------------------|--------------|
| D1 (Pindel as 4th caller) committed             | done (`d5ff1e4`) |
| D1 stub validation                              | done         |
| D1 real-data validation                         | done — works + 1 finding |
| D1 Pindel noise filter (next session)           | pending      |
| D2 (IGV reports wired) committed                | done (`d1c491c`) |
| D2 stub validation                              | done         |
| D2 real-data structural validation              | done         |
| D2 visual HTML inspection                       | pending — needs browser |
| Combined audit memo                             | this file    |

---

## Open audit items rolled forward

From earlier today: B4 (KMT2A-PTD), IGV duplicate-handling alignment,
REPORTING subworkflow cleanup, mystery zero-byte files at repo root,
`assets/test/` restoration, VV REST 3-worker boot, `$HOME → /root` under
sudo.

New items from today's D1/D2 validation:

- **D1 Pindel noise filter (genotype-based).** Highest priority of the
  follow-ups. ~10 lines of code, same patching pattern used today.
- **D2 visual HTML inspection.** Manual step, takes 5 minutes in a
  browser. Should happen before any clinical use of nf-core output.
- **VV port allocation decision.** Either restart the morning's
  migration choice (move gunicorn to container port 5000 so the host
  port 5001 mapping makes sense) or update the nf-core code to point
  at port 8000. Today's "second gunicorn" workaround works but is
  fragile — it depends on docker-restart preserving the manual exec.
- **Clinical TSV row-count divergence.** nf-core 18, production 22.
  Re-investigate before declaring B1 fully closed.

---

## Commit roadmap from here

To finalize the production version:

1. **This memo committed and pushed** (next step, this session).
2. **Visual D2 inspection in browser** (5 min, can be done any time).
3. **Next session — D1 Pindel noise filter** (~30 min including
   commit + push).
4. **Next session — D1 noise filter re-validation** (resume the same
   outdir; -resume picks up cache for everything except FLT3_CONSENSUS;
   ~5 min runtime).
5. **Next session — production version of D1 fix** for parity with
   `scripts/09b_flt3_consensus.py` (paired commit on the production
   repo).
6. **Future sessions — B4 (KMT2A-PTD), REPORTING cleanup, etc.**

After steps 1-5 land, D1 and D2 are clinically production-ready.

---

## Addendum 2026-05-19 (post-resume reconciliation)

This addendum is written after `apply_pindel_gt_filter.py` was applied
to `bin/flt3_consensus.py` and the validation run was resumed against
25NGS1307. It reconciles two predictions in the **Recommended
next-session fix** block above with the actual post-patch consensus
TSV, and documents the reasoning for future test maintenance.

### Actual post-patch consensus TSV (25NGS1307)

| status            | n_tools | tools                                  | length_bp | pos_hg38   | vaf_pct_min | vaf_pct_max | vaf_pct_mean |
|---|---|---|---|---|---|---|---|
| `PASS_HIGH`       | 4       | FLT3_ITD_EXT, Pindel, filt3r, getITD   | 45        | 28034132   | 9.89        | 30.60       | 18.21        |
| `REVIEW_REQUIRED` | 1       | FLT3_ITD_EXT                           | 39        | 28034145   | 0.58        | 0.58        | 0.58         |

This is the correct clinical output. The two deviations from the
original prediction are explained below.

### Deviation 1: `vaf_pct_mean` 18.21 (predicted ~30)

The memo's "~30%" anticipated **Pindel's VAF in isolation**, not the
4-caller cluster mean. The four callers in the lead cluster report
VAFs across a 9.89–30.6 range; getITD and Pindel sit at the high end,
FLT3_ITD_EXT and filt3r at the low end. Arithmetic mean across the
four is 18.21, which is what `vaf_pct_mean` is defined to report.

Pindel-specific VAF (`AD=483,213` → 30.60%) appears as
`vaf_pct_max`. The lead-record VAF is unchanged from earlier
analyses; only the column being read off was different.

### Deviation 2: second row is `REVIEW_REQUIRED` 1-caller, not `PASS_LOW` 2-caller

The pre-patch Pindel VCF for 25NGS1307 contains 42 records: 1
genotyped 0/1 (the real ITD at chr13:28034132, AD=483,213) and 41
genotyped 0/0. Distribution of the 0/0 noise by SVLEN and alt-read
count:

| SVLEN | n records | alt reads (max) | clinical interpretation       |
|---|---|---|---|
| 45    | 38        | 24              | shoulder noise around the true ITD |
| 39    | 2         | 14              | one record at pos 28034145, AD=471,14 |
| 73    | 2         | 1               | sub-percent stray events           |
| 68    | 1         | 2               | distal stray                       |

The 39-bp record at pos 28034145, AD=471,14 is the source of the
predicted "PASS_LOW, 2 callers at 39 bp" row. Pre-patch, it cast a
second vote alongside the FLT3_ITD_EXT 39-bp call, lifting the
cluster from 1 caller (REVIEW_REQUIRED) to 2 callers (PASS_LOW).
This is precisely the failure mode the GT filter was added to
correct.

The memo's "post-fix" prediction was therefore internally
inconsistent: it expected all 0/0 records to be dropped **and**
expected the 39-bp cluster to retain its second caller. Only one
of those can be true; removing the 0/0 record is the correct
behaviour, and `REVIEW_REQUIRED, 1 caller, 0.58% VAF` is the
clinically correct post-patch call.

**Implication for test maintenance:** the standalone test
`tools/patches/2026-05-19/test_pindel_gt_filter.py` deliberately
does **not** assert on the second cluster's status, length, or
caller count. Future maintainers should not "correct" the test to
reproduce the pre-patch 2-caller prediction. The 1-caller
REVIEW_REQUIRED row is the intended outcome of the filter on this
fixture.

### Why GT-only outperforms `altreads >= N` on this data

A reasonable alternative was considered: layer an alt-read floor
(e.g. `altreads >= 10`) on top of, or in place of, the GT check.
On this specimen that would have kept the following 0/0 noise
records, all of which the GT filter correctly drops:

| pos      | SVLEN | alt reads | impact if kept                                     |
|---|---|---|---|
| 28034145 | 39    | 14        | restores the false 2-caller PASS_LOW at 39 bp        |
| 28034156 | 45    | 24        | drags lead-cluster `vaf_pct_min` to ~4.7%            |
| 28034158 | 45    | 10        | drags `vaf_pct_min` further                          |
| 28034163 | 45    | 12        | drags `vaf_pct_min` further                          |
| 28034164 | 45    | 12        | drags `vaf_pct_min` further                          |
| 28034166 | 45    | 11        | drags `vaf_pct_min` further                          |
| 28034171 | 45    | 10        | drags `vaf_pct_min` further                          |

Pindel's per-record GT call already integrates strand bias, soft-clip
evidence, mapping quality, and per-position error context — signals
that a flat alt-read threshold ignores. The 14 alt reads at
pos 28034145 look meaningful at first glance, but Pindel's full model
genotypes the locus as homozygous reference, and the independent
FLT3_ITD_EXT reading of the same position at 0.58% VAF agrees that
the signal is sub-clonal noise rather than a real low-burden ITD.

Trusting GT therefore means trusting Pindel's own decision boundary,
which is more biologically informed than any single numeric
threshold available downstream.

### Independent evidence the filter is doing its job

The cleanest single number confirming this is the lead cluster's
`vaf_pct_min = 9.89`. That value comes from FLT3_ITD_EXT or filt3r;
the Pindel contribution to the cluster reports VAF near 30%. If any
of the 38 GT=0/0 SVLEN=45 records had leaked through, they would have
contributed alt fractions in the 0.2–4.7% range, collapsing
`vaf_pct_min` to a fraction of a percent. `9.89` is consistent with
all four callers reporting the same true heterozygous ITD and nothing
else.

### Outstanding follow-ups (not blocking)

- The reconciliation above is panel- and specimen-specific. If a
  future specimen produces a low-burden ITD that Pindel itself calls
  as 0/0, the GT filter would drop it. This is acceptable for the
  current panel because three independent callers (FLT3_ITD_EXT,
  filt3r, getITD) cover the low-burden range; a single-caller
  REVIEW_REQUIRED row would still flag it for human review. If a
  future audit shows this assumption breaking, the right response is
  to revisit Pindel's calling parameters upstream, not to relax the
  GT filter downstream.
- The 0.58% VAF REVIEW_REQUIRED row stays in the output for human
  review, as intended; no further filtering is added here.

### References

- Patch: `tools/patches/2026-05-19/apply_pindel_gt_filter.py`
- Test: `tools/patches/2026-05-19/test_pindel_gt_filter.py`
- Fixture used for analysis: `/tmp/d1_pindel_real.vcf`
  (extracted from work dir `work/ca/5b8dfc*/25NGS1307.pindel_flt3.vcf`)
- Backup of pre-patch script:
  `bin/flt3_consensus.py.bak_pindel_gt_filter_20260519_124207`
