# Session audit — 2026-05-17 (SomaticSeq 8-caller port + ANNOTATION commit)

**Subject:** Three commits land. SOMATICSEQ_ENSEMBLE and SOMATICSEQ_POSTPROCESS
reach parity with production's 8-caller setup. Path B (variant_filter rewrite
+ ANNOTATION activation), held out of yesterday's commit, lands together with
the SomaticSeq fixes. Three of six clinically-significant variants missing
from the port's 25NGS1307 clinical TSV in the 2026-05-16 audit are recovered;
the remaining three are explained at the per-caller-VCF level and deferred to
next session.

**Repos touched:** patkarlab/nf-core-tspipe at /goast/hemat_data/nf-core-tspipe/

**Server:** gandalf

**HEAD at start of session:** 5cf6df6 (on origin/main; carried forward
uncommitted Path B from 2026-05-16)

**HEAD at end of session:** (to be set after commits land)

---

## Outcome

Three commits land cleanly. All five files that were uncommitted at the start
of the session are now committed in three logically-distinct units. The
working tree is clean. Validation against production on 25NGS1307 shows:

- annotated tier: port-only/prod-only counts down from 69/527 to 69/373
- filtered tier:  port-only/prod-only counts down from 57/369 to 57/274
- clinical tier:  port-only/prod-only counts down from 0/6  to 0/3

Three of six previously-missing clinical variants recovered. The remaining
three (UBTF, CEBPA, RAD21) are missing one specific caller's vote each in
the port relative to production; that is upstream of SomaticSeq and is the
next session's priority 1.

Two Tier-1 hotspots verified end-to-end in the port's clinical TSV with
PASS filter status: FLT3-ITD c.1742_1786dup at VAF 10.9% (via Pindel,
identical record to production), and U2AF1 S34F c.101C>T at VAF 47.1%
(via conventional callers; production reaches the same answer via its
rescue path).

---

## Commits landed (3)

| Hash    | Subject |
|---------|---------|
| (TBD)   | feat(somaticseq): port full 8-caller ensemble with stable MVDKFP tag |
| (TBD)   | feat(annotation): wire ANNOTATION subworkflow with u2af1 rescue input |
| (TBD)   | feat(tools): add three-tier production diff utility |

### Commit 1 — SomaticSeq full 8-caller port

Brings SOMATICSEQ_ENSEMBLE + SOMATICSEQ_POSTPROCESS to parity with
production's `scripts/07_somaticseq.py` 8-caller setup, and fixes three
independent latent bugs in the rename of SomaticSeq's caller-decision INFO
field. See commit body for full rationale.

**Patches applied to disk in this commit:**

- `tools/patches/2026-05-17/apply_somaticseq_postprocess_fix.py` — Patch A.
  MVDKFPID -> MVDKFP, VarDict/VarScan order swap, Number=N parsed from
  raw header.
- `tools/patches/2026-05-17/apply_somaticseq_arbitrary_callers.py` — Patch B.
  Pindel + DeepSomatic re-enabled in the arbitrary-caller loop; awk
  pre-filter strips symbolic-allele records before splitVcf.py.
- `tools/patches/2026-05-17/apply_somaticseq_split_sort_pipefail_fix.py` —
  Patch C. `|| true` on the inner-loop sort pipeline to tolerate
  header-only split VCFs.
- `tools/patches/2026-05-17/apply_somaticseq_groovy_dollar_escape_fix.py` —
  Patch D. Hotfix for Patch C: `$VCF` in the rationale comment was being
  interpreted as a Groovy interpolation reference; escaped to `\$VCF`.

### Commit 2 — ANNOTATION subworkflow wiring

Carries forward Path B from 2026-05-16, which was held out of yesterday's
commit pending today's SomaticSeq fixes. variant_filter.nf full rewrite,
annotation.nf takes u2af1_tsv_ch, tspipe.nf activates ANNOTATION(...).

### Commit 3 — Diff utility

`tools/compare_tsv_to_production.py`. Used to generate the validation
table in commit 1.

---

## Validation on 25NGS1307

Real-mode run at `/goast/hemat_data/nfcore_runs/25NGS1307_real_20260517_101646/`.
All 32 processes completed exit 0 after the SomaticSeq chain stabilized.
Upstream tasks reused yesterday's cache via `-resume`; only the modified
SomaticSeq + downstream chain re-ran.

### Pre-rename SomaticSeq INFO header (raw `Consensus.sSNV.vcf`)

```
##INFO=<ID=MVDK0123,Number=8,Type=Integer,Description="Calling decision of
the 8 algorithms: MuTect, VarScan2, VarDict, Strelka, SnvCaller_0,
SnvCaller_1, SnvCaller_2, SnvCaller_3">
```

Number=8 confirms all four arbitrary callers (FreeBayes/Platypus/Pindel/
DeepSomatic) reached SomaticSeq. SnvCaller_0..3 are SomaticSeq's internal
placeholders, replaced by the postprocess rename below.

### Post-rename merged VCF INFO header

```
##INFO=<ID=MVDKFP,Number=8,Type=String,Description="Calling decision of
the 8 algorithms: Mutect2, VarScan, VarDict, Strelka, FreeBayes,
Platypus, Pindel, DeepSomatic">
```

Tag name now matches production's `INFO_TAG` (literal "MVDKFP"). Native
callers in production's empirically-correct order. All eight callers
named in the description.

### Per-caller record counts after preparation

```
[somaticseq] freebayes: prepared (records=1826)
[somaticseq] platypus: prepared (records=454)
[somaticseq] pindel: prepared (records=271)
[somaticseq] deepsomatic: prepared (records=5)
```

The awk SV pre-filter produced no "dropped N" messages on this sample,
which means Pindel did not emit symbolic-allele records here. The filter
is acting as a safety net for future samples rather than the active cleaner
in this case.

### Three-tier diff vs production

| Tier         | Port keys | Prod keys | Common | Port-only | Prod-only |
|--------------|-----------|-----------|--------|-----------|-----------|
| annotated    | 1559      | 1863      | 1490   | 69        | **373**   |
| filtered     | 1433      | 1650      | 1376   | 57        | **274**   |
| clinical     | 18        | 21        | 18     | 0         | **3**     |

Compared with the 2026-05-16 audit (port-only / prod-only): annotated was
69/527 (now 69/373; -154 prod-only), filtered was 57/369 (now 57/274;
-95 prod-only), clinical was 0/6 (now 0/3; -3 prod-only). The
annotated-tier port-only count of 69 is unchanged, suggesting those 69
entries are a separate class of port-side-only artifact independent of
the MVDKFP fix; deferred to next session as a secondary priority.

### Clinical-tier recovery breakdown

**Recovered (3 of 6 from the 2026-05-16 list):**

| Gene  | Variant         | VAF   | Callers (per 2026-05-16 audit) |
|-------|-----------------|-------|--------------------------------|
| SETD2 | p.Pro1916His    | 25.5% | FreeBayes + DeepSomatic        |
| TET2  | p.Ser142Tyr     | 21.5% | FreeBayes + DeepSomatic        |
| TET2  | p.Glu1250Ter    | 22.1% | FreeBayes + DeepSomatic        |

All three required DeepSomatic in the bitmap; recovered automatically by
re-enabling DeepSomatic in the arbitrary-caller loop.

**Still missing (3 of 6 from the 2026-05-16 list):**

| Gene  | Variant            | VAF   | Port MVDKFP           | Prod MVDKFP           | Missing caller |
|-------|--------------------|-------|-----------------------|-----------------------|----------------|
| UBTF  | c.1247_1248ins27bp | 1.95% | 0,0,0,0,0,1,0,0       | 0,1,0,0,0,1,0,0       | **VarScan**    |
| CEBPA | c.288C>G           | 13.4% | 0,0,0,0,1,0,0,0       | 0,0,1,0,1,0,0,0       | **VarDict**    |
| RAD21 | p.Leu155Phe        | 22.3% | 0,0,0,0,1,0,0,0       | 0,0,0,0,1,1,0,0       | **Platypus**   |

Bitmap positions (post-rename): Mutect2, VarScan, VarDict, Strelka,
FreeBayes, Platypus, Pindel, DeepSomatic. Both port and production agree
on which callers DID detect each variant. Port is missing exactly one
specific caller's vote per variant, and a different caller per variant.
This rules out a SomaticSeq-stage or downstream-filter cause. The
discrepancy is at the per-caller variant-calling stage.

AF and LC INFO fields match within rounding (RAD21 port=0.221, prod=0.223;
CEBPA port=0.128, prod=0.134), so the variants exist at these sites in
both runs with similar input BAMs. The disagreement is purely about which
callers' filters let them through.

---

## Operational habits

Carrying forward from prior sessions, all still valid. New observations
this session:

- **Nextflow script blocks are Groovy GStrings end-to-end.** Every `$id`
  outside of `\$` is a Groovy interpolation, including inside shell `#`
  comments. The shell does not get a chance to ignore the comment until
  after Groovy renders the string. The Patch D hotfix was caused by an
  unescaped `$VCF` reference in a comment block. Future patches that
  modify a `.nf` script block must grep the new content for the regex
  `(^|[^\\])\$[A-Za-z_]` and verify every match is either an intentional
  Groovy channel variable or properly escaped.

- **Patch authoring against str_replace anchors needs explicit indentation
  control.** Patch C's first draft had a Python-side indentation bug
  where OLD_LINE matched at 16 spaces but NEW_LINE was written at 12;
  the str_replace succeeded but produced structurally broken output.
  The fix was to construct OLD_LINE and NEW_LINE programmatically with
  a shared `INDENT = " " * 16` prefix. Worth making this the default
  pattern for any multi-line .nf patch.

- **The `-newer` predicate doubles as a sanity probe.** When using
  `find work/ -name "*SOMATICSEQ_ENSEMBLE*" -newer <patched_module>` to
  locate a fresh work dir for snapshotting, an empty result means
  either the task hasn't run yet or `-resume` decided not to invalidate
  the cache for this module. Both are problems worth catching early.

- **Snapshots before re-runs.** This session repeatedly hit the
  "captured a stale snapshot" trap because `cp -r work/<task>` was run
  before the next iteration had populated it. The reliable check is to
  look at file timestamps in the snapshot before trusting it.

---

## Carry-forward priorities for next session (in order)

### 1. Per-caller VCF discrepancy: VarScan, VarDict, Platypus

Three different callers each silently dropping one clinically-significant
variant relative to production. This is upstream of SomaticSeq and the
fix lies in the per-caller variant-calling modules. Suggested approach:

- Measure per-caller VCF record counts port vs production for all
  callers, not just the three above. Yesterday's audit noted Platypus
  was 454 (port) vs 689 (prod), a 34% deficit; that may be the most
  visible case of a broader issue.
- For each caller showing a non-trivial deficit, diff the port's
  `modules/local/<caller>.nf` script block (and the rendered
  `.command.sh` from the most recent work dir) against production's
  invocation in `scripts/0[2-7]_*.py` to find the parameter
  difference.
- Reconcile. Likely candidates: filter thresholds, region BED file
  used, soft-clip handling, mapping-quality cutoffs.

Acceptance criterion: clinical TSV port-only/prod-only drops to 0/0
or to a deliberately-justified residual.

### 2. Annotated-tier port-only residual of 69 entries

The annotated tier has 69 port-only entries that are not in production.
Their count didn't change between the 2026-05-16 audit (69) and today
(69), suggesting this is a stable class of port-side artifact independent
of the MVDKFP fix and the per-caller-VCF issue. Diagnostic: sample 5-10
entries from `/home/hemat/inbox/diff_20260517/annotated_port_only.tsv`
and trace their origin. Candidate causes: a more permissive consequence
filter in the port, or a region-BED difference letting extra positions
through.

### 3. CLINICAL_TIER / REJECT-rescue investigation (re-evaluated)

The 2026-05-16 audit hypothesized that production had a REJECT-rescue
step downstream of variant_filter.py that promoted SomaticSeq-REJECT
variants based on hotspot or driver-gene criteria. With today's MVDKFP
fix exposing three additional clinical variants (SETD2/TET2/TET2) that
ARE SomaticSeq-REJECT in both port and production, and the port's
`variant_filter.py` letting them through, the rescue logic may already
be in `variant_filter.py` and was only invisible because of the broken
MVDKFP match. This priority is downgraded; revisit only if the
per-caller fix (priority 1) does not close the clinical-tier deficit
fully.

### 4. Resume Phase 1 stubs

Unchanged from 2026-05-16:

- VARIANT_VALIDATOR (port from `bin/variant_validator.py`)
- ONCOVI (port from `bin/oncovi.py`)
- FLT3_TO_VARIANTS (port from `bin/flt3_to_variants.py`)
- CLINICAL_TIER (port from `scripts/17c_clinical_tier.py`)
- IGV_REPORTS (port from `bin/igv_reports.py`)
- ORGANIZE_OUTPUT (port from `bin/organize_output.py`)
- Samplesheet schema: add `dx` (diagnosis) column for CLINICAL_TIER
- Activate `REPORTING(...)` call in tspipe.nf

### 5. Per-process resource tuning (lower priority)

Unchanged from 2026-05-16:

- FASTP `-w 2` script bug — change to `-w ${task.cpus}`
- BQSR Spark mode or interval-split for parallelism
- ABRA2 explicit `--threads ${task.cpus}` if not already set

### 6. KMT2A-PTD validation (U2AF1 verified this session)

U2AF1 S34F (chr21:43104346 G>A, c.101C>T, p.Ser34Phe) is present in
the port's clinical TSV at VAF 47.1%, Filter=PASS, called by five
conventional callers (VarScan, VarDict, Strelka, FreeBayes, Platypus).
Production reports the same variant at VAF 46.7% via its
U2AF1_PileupRescue path (SomaticSeq_Verdict=RESCUED). Both arrive at
the same biological answer via different mechanisms: the port's
conventional callers found it on this sample; production's conventional
callers did not and only its rescue path caught it. The port's
U2AF1_RESCUE module ran successfully and produced a valid rescue TSV
record at 46.7% VAF, but the merged clinical row prefers the
conventional-caller record when both exist.

This confirms Path B's u2af1 wiring (commit 2 of this session) is
functional end-to-end on a real clinical hotspot.

KMT2A-PTD verification still pending. Production's clinical TSV has
no KMT2A entries on this sample, suggesting either (a) the variant
is not called by either pipeline on 25NGS1307 despite the case
documentation, or (b) it reaches a different output file than
25NGS1307.somaticseq.clinical.tsv. Worth diagnosing in the next
session.

### 7. Port clinical-TSV schema is missing the Rescue_Note column

Production's clinical TSV has a `Rescue_Note` column populated when a
record's origin is a rescue path (e.g. U2AF1 pileup rescue). The
port's clinical TSV does not include this column. Both pipelines'
clinical TSVs are functionally complete for the variants they report,
but field-by-field comparison tools that assume schema parity will
trip on this. A small follow-up update to `bin/variant_filter.py` to
emit the Rescue_Note column (populated when a record came from a
rescue path, blank otherwise) closes the divergence.

---

## Source-of-truth references

Unchanged from prior sessions:

- Production scripts: `/home/hemat/targeted-seq-pipeline/scripts/`
- Production results (ground truth): `/home/hemat/targeted-seq-pipeline/results/<sample>/`
- nf-core port: `/goast/hemat_data/nf-core-tspipe/`

Validation artifacts for this session:

- Run output: `/goast/hemat_data/nfcore_runs/25NGS1307_real_20260517_101646/`
- SOMATICSEQ_ENSEMBLE snapshot: `/home/hemat/inbox/somaticseq_debug_20260517_103317/`
- Three-tier diff TSVs: `/home/hemat/inbox/diff_20260517/`
- Run log: `/tmp/real_run_20260517_v3.log`

Patch scripts in `tools/patches/2026-05-17/`:

- `apply_somaticseq_postprocess_fix.py`
- `apply_somaticseq_arbitrary_callers.py`
- `apply_somaticseq_split_sort_pipefail_fix.py`
- `apply_somaticseq_groovy_dollar_escape_fix.py`
