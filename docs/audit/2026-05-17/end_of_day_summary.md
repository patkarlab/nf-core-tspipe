# 2026-05-17 — End of Day Summary

## What shipped today

Five commits across two repositories.

### Production (`patkarlab/targeted-seq-pipeline`, branch `main`)

| Commit | What |
|---|---|
| `9a4a91a` | feat(panel): Exonwise hg38 BED + collapse utility |
| `b14a346` | fix(coverage): include duplicates in mosdepth (`--flag 772`) |

### nf-core port (`patkarlab/nf-core-tspipe`, branch `main`)

| Commit | What |
|---|---|
| `15f912e` | feat(coverage): switch mosdepth to use Exonwise BED via `params.exonwise_bed` |
| `178cc08` | fix(coverage): include duplicates in mosdepth (`--flag 772`) [amended for +x bit] |
| (latest)  | feat(qc): per-sample HTML QC dashboard |

## Real-data validation on 25NGS1307

End-to-end output of the dashboard run:

| Metric | Value | Source |
|---|---|---|
| Mean coverage (per-exon mean of means) | **2,994×** | Computed from `25NGS1307_exon_coverage.tsv` |
| Low-coverage exons (<100×) | **5** | `Flag == LOW_COVERAGE` rows in TSV |
| Affected exons | MYB Ex_1 (0×), PHIP Ex_03 (4×), SF1 Ex_1 (27×), PTPN Ex_01 (46×), PRPF40B Ex_1 (72×) | TSV |
| Selected bases | **64.7%** | Picard `PCT_SELECTED_BASES` |
| Off-bait | **35.3%** | Picard `PCT_OFF_BAIT` |
| Sample's duplicate rate | 71.4% | samtools flagstat |
| Total exons | 1,153 | Exonwise BED row count |
| Total canonical genes | 120 (123 including 3 oddball labels) | Per-gene rollup |
| Dashboard HTML size | 200 KB self-contained | `du -h` |

End-to-end mean coverage shift: **435× → 2,994×** (6.88× boost from including duplicates in mosdepth's count). Boost is bigger than the flagstat-naive prediction (3.5×) because duplicates preferentially stack at panel target regions — that's how hybrid capture enrichment works.

## Why the coverage numbers landed where they did

Earlier in the day the headline figure was 435× (per-exon mean of means, dup-excluded) which seemed wrong vs the legacy hg19 framing of 3,819×. Three things were going on:

1. **Production already lost the 3,819× figure** when it migrated from hg19 to hg38. Its current hg38 TSV reports 455×, very close to our 435× port number. The legacy was hg19 + different aligner + different panel BED.
2. **Mosdepth was excluding duplicates** by default (`--flag 1796` excludes the DUP bit `0x400`). Clinical convention here is to include duplicates. Override to `--flag 772 = 1796 − 1024`.
3. **The Exonwise BED collapse** (segment-level 4,589 rows → exon-level 1,153 rows) produced cleaner per-gene rollups by giving each exon a canonical label instead of probe-prefixed tile labels.

Combined effect: clinically-meaningful coverage numbers at the level the legacy report led you to expect, with audit-traceable provenance (you can recompute the mean from the TSV in one awk line).

## Audit-trail patches

Six patch scripts archived in `tools/patches/2026-05-17/` on both repos. Each is self-contained, md5-fingerprinted, idempotent, and ships a `.bak` on every apply. Anyone tracing through the history can run them in dry-run mode to see exactly what they did.

### Production
- `apply_mosdepth_include_duplicates.py`

### Port
- `apply_mosdepth_exonwise_bed.py` — REPLACE strategy, segment BED → Exonwise BED for mosdepth only
- `apply_mosdepth_include_duplicates.py` — `--flag 772`
- `apply_dashboard_patch.py` — core dashboard deployment
- `apply_dateformat_fix.py` — `workflow.start` is `OffsetDateTime` in Nextflow 25.10.4+
- `apply_container_fix.py` — matplotlib-base biocontainer tag didn't exist; use GATK 4.5
- `apply_render_py36_fix.py` — strip 3.7+ syntax for the Python 3.6 in the GATK image

## Known issues recorded today (not blockers)

### Real correctness items

1. **Per-caller VCF discrepancy** (carry-forward from morning) — 3 variants on 25NGS1307 are missing one caller's vote each between port and production.
2. **69-entry annotated-tier port-only residual** — port produces 69 variants that production filters out. Could be benign threshold differences or real over-permissiveness.
3. **Phase 1 stubs** — `VARIANT_VALIDATOR`, `ONCOVI`, `FLT3_TO_VARIANTS` may still be stub-only (`touch`-based). Need verification.
4. **KMT2A-PTD not yet detected** — 25NGS1307 is clinically positive but the port hasn't surfaced it.
5. **Rescue_Note column gap** in annotated TSV vs production.

### Environment / tooling

6. **Picard `COVERAGE_CAP=200`** — current HSMETRICS invocation caps depth at 200×, making `MEAN_TARGET_COVERAGE`, `MEDIAN_TARGET_COVERAGE`, `MAX_TARGET_COVERAGE`, and `PCT_TARGET_BASES_NNNX` columns clinically useless. The dashboard avoids these fields (uses only `PCT_SELECTED_BASES` and `PCT_OFF_BAIT`, which are bases-on-bait ratios and unaffected by the cap). To recover the depth fields, re-run HSMETRICS with `--COVERAGE_CAP 100000`.
7. **`params.panel_name` warning** — `Access to undefined parameter panel_name` printed at workflow start. Benign (the `?:` fallback works), but trivially silenced by adding `panel_name = "MYOPOOL hg38"` to `nextflow.config`.

### Cosmetic (one-line regex fixes in `bin/parse_exon_coverage.py`)

8. **Oddball exon labels** — `ANKRD26_Ex_5'UTR`, `NOTCH1_Ex_3'UTR`, `NPM1_Ex_intr_10_part` parse as full-string genes.
9. **Leading-zero inconsistency** — `Ex_03` vs `Ex_3` from the source BED.
10. **`PTPN` shows as `PTPN`** — should be `PTPN11`. Non-greedy regex `(.+?)` stops too early.

### Output directory hygiene (next session's opener)

11. **Inside `<outdir>/<sample>/`** — pipeline scratch (`bqsr/`, `markdup/`, `mosdepth/`, `trimmed/`, `aligned/`, plus the variant-callers per-tool dirs) publishes alongside real deliverables. Port production's `scripts/20_organize_output.py` into a Nextflow `ORGANIZE_OUTPUT` module that:
    - hardlinks deliverables into a `clinical/` subdir (no doubled BAM)
    - deletes the intermediate scratch by default
    - keeps a `--keep_intermediates` flag for validation runs
    - **omits** SV calls / SV annotation from the deliverable list (this pipeline doesn't run SV callers; production does, but we don't port that)
12. **`nfcore_runs/` parent directory** — 17+ dated run directories from today's validation work. Nextflow doesn't manage retention; needs a run-naming convention + periodic cleanup script.

## Operational notes captured in memory

- User transfers files to gandalf by dropping them into `~/inbox/from_claude/`; never suggest scp.
- Coverage calculations include duplicates (`--flag 772` for mosdepth).
- GATK 4.5 container ships Python 3.6 + matplotlib 3.2.1 — no `from __future__ import annotations`, no PEP 585 generics, no walrus.
- Nextflow 25.10.4+ has `workflow.start` as `OffsetDateTime` — use `workflow.start.format('yyyy-MM-dd')`, not `SimpleDateFormat`.
