# 2026-05-17 — Morning session audit (QC modules + dashboard scoping)

## Outcome summary

Three QC modules ported and validated end-to-end against real
25NGS1307 data, all producing expected outputs in
${outdir}/${sample}/{hsmetrics,mosdepth,exon_coverage}/. The
exon-coverage path is now a two-stage pipeline (MOSDEPTH followed by
PARSE_EXON_COVERAGE) because the mosdepth biocontainer has no Python
interpreter and the parsing logic must run in a container that does.

Dashboard module deferred. The dashboard renderer was drafted and
unit-tested locally against synthetic fixtures, but a substantive
question about the right granularity for per-gene rollup surfaced
during validation and was not resolved this session.

## What landed (uncommitted on gandalf as of session end)

### Patches applied during the session

1. `apply_hsmetrics_port.py` (2026-05-17 04:48)
   Filled the HSMETRICS stub in modules/local/hsmetrics.nf with
   the GATK BedToIntervalList + CollectHsMetrics commands ported
   verbatim from scripts/10_hsmetrics.py. Container:
   docker://broadinstitute/gatk:4.5.0.0. Output:
   ${meta.id}_hsmetrics.txt. First-attempt OLD_BODY missed a blank
   line between the stub `"""` and `script:` declaration; re-shipped
   with corrected anchor.

2. `apply_exon_coverage_port.py` (2026-05-17 04:56)
   Filled the EXON_COVERAGE stub by calling bin/exon_coverage.py.
   Initially used the mosdepth biocontainer for the module. **This
   module was subsequently retired** in favor of the two-stage
   split below; the patch script remains in tools/patches/2026-05-17/
   for audit purposes.

3. `apply_preprocessing_qc_wiring.py` (2026-05-17 11:37)
   Added HSMETRICS and EXON_COVERAGE calls inside PREPROCESSING
   after ABRA2, with two new emit channels (hsmetrics,
   exon_coverage). Atomic across three anchors.

4. `apply_tspipe_qc_channels.py` (2026-05-17 11:39)
   Added two channel handles (ch_hsmetrics, ch_exon_coverage) in
   workflows/tspipe.nf after the PREPROCESSING call.

5. `apply_qc_publishdir_routing.py` (2026-05-17 11:42)
   Added withName: blocks for HSMETRICS and EXON_COVERAGE in
   conf/modules.config so outputs publish to
   ${outdir}/${sample}/{hsmetrics,exon_coverage}/.

6. **First validation run failed.** EXON_COVERAGE inherited the
   mosdepth biocontainer which has no python3. The Python script
   couldn't run. Exit code 127, work dir at
   /goast/hemat_data/nf-core-tspipe/work/83/107ebf5a... .

7. `apply_exon_coverage_split_bundle1.py` (2026-05-17 11:57)
   Installed three new files: bin/parse_exon_coverage.py (a pure-
   Python parser refactored from bin/exon_coverage.py, no mosdepth
   invocation, no samtools fallback); modules/local/mosdepth.nf
   (pure mosdepth invocation in the biocontainer); and
   modules/local/parse_exon_coverage.nf (parser invocation in the
   GATK container which has Python 3.6.10). Retired the obsolete
   modules/local/exon_coverage.nf to a .bak file.

8. `apply_exon_coverage_split_bundle2.py` (~2026-05-17 12:00)
   Rewired preprocessing.nf: replaced the single EXON_COVERAGE call
   with MOSDEPTH chained to PARSE_EXON_COVERAGE. Updated
   conf/modules.config: replaced the EXON_COVERAGE withName block
   with separate MOSDEPTH and PARSE_EXON_COVERAGE blocks (mosdepth
   intermediates publish to ${outdir}/${sample}/mosdepth/; final
   TSV publishes to ${outdir}/${sample}/exon_coverage/). Atomic
   across four anchors.

### Validation run: 25NGS1307_qc_20260517_120209

```
Workflow completed > WorkflowStats[
    succeededCount=3 (HSMETRICS, MOSDEPTH, PARSE_EXON_COVERAGE)
    failedCount=0
    cachedCount=32 (everything else, from yesterday's run)
]
```

Outputs verified:
- ${outdir}/${sample}/hsmetrics/25NGS1307_hsmetrics.txt: 4.8 KB,
  Picard METRICS CLASS block with real numbers.
- ${outdir}/${sample}/mosdepth/: 7 files including
  25NGS1307.regions.bed.gz (4589 regions),
  25NGS1307.thresholds.bed.gz, and three .mosdepth.*.txt audit
  files.
- ${outdir}/${sample}/exon_coverage/25NGS1307_exon_coverage.tsv:
  337 KB, 4590 rows (header + 4589 data).

### Real numbers from 25NGS1307 HsMetrics

```
MEAN_TARGET_COVERAGE:    422x
MEDIAN_TARGET_COVERAGE:  200x
PCT_SELECTED_BASES:      64.7%   (on-target rate)
PCT_TARGET_BASES_100X:   94.1%
PCT_TARGET_BASES_500X:   38.6%
ZERO_CVG_TARGETS_PCT:    1.0%
FOLD_ENRICHMENT:         4631x
TOTAL_READS:             20.5M
```

Mean of per-segment mosdepth means: 455x.

## Architectural decisions made this session

### Split EXON_COVERAGE into MOSDEPTH + PARSE_EXON_COVERAGE

Cause: the mosdepth biocontainer is single-tool by design and has
no python3 interpreter. The original combined-module approach
inherited that container and could not run its bin script. Three
options were considered:

- (A) Drop the container, run on host PATH (conda env). Rejected
  because it breaks containerization for one module and sets a
  precedent.
- (B) Build a custom multi-tool container. Rejected because the
  iteration loop is too slow for today.
- (C) Split into two modules, each using a container that has the
  tool it needs. **Chosen.** Cleaner architecture, matches nf-core
  conventions (one tool per process), no infrastructure debt.

User explicitly directed C: "option C (no shortcuts !!!)"

### Container choices

| Module               | Container                                                |
|---------------------|----------------------------------------------------------|
| HSMETRICS            | docker://broadinstitute/gatk:4.5.0.0                     |
| MOSDEPTH             | quay.io/biocontainers/mosdepth:0.3.10--h4e814b3_1        |
| PARSE_EXON_COVERAGE  | docker://broadinstitute/gatk:4.5.0.0 (Python 3.6.10)     |

The GATK container's Python 3.6.10 is sufficient for
parse_exon_coverage.py because the script uses only stdlib (gzip,
csv, re, pathlib, argparse, logging) and no 3.7+ features.

### bin/exon_coverage.py kept for redundancy

User decision: keep the combined script for standalone use (matches
production's scripts/10b_exon_coverage.py); only the .nf module was
retired. The new bin/parse_exon_coverage.py is the post-split
parser.

## Unresolved: per-gene rollup granularity (deferred)

Toward the end of the session, surfaced a real question about what
granularity the dashboard should use for per-gene coverage rollup.

The current state:
- `bin/parse_exon_coverage.py` emits one row per BED region (4589
  rows for 25NGS1307).
- The panel BED (MYOPOOL_240125_UBTF_hg38.bed) is segment-level:
  each `Target=N` site is covered by 1+ tiled probe segments.

The legacy clinical report (from the hg19 pipeline) reports:
- Mean coverage: 3819.5x
- 1156 probes total, 4 with suboptimal (<100x) coverage

Today's run reports (at segment level):
- Mean of per-segment means: 455x
- 4589 regions total, 205 with <100x mean

The gap is explained by:
1. Picard's MEAN_TARGET_COVERAGE excludes duplicates, low-MAPQ
   reads, low-baseQ bases, and overlap-clipped bases; legacy may
   use raw read counts.
2. The current panel BED (`MYOPOOL_240125_UBTF`) is approximately
   4x denser than the legacy BED (`MYOPOOL_231224_Rebalanced`)
   that the legacy report was generated against.
3. The legacy "1156 probes" appears to be a per-exon count: the
   collapsed Exonwise version of the same panel
   (`MYOPOOL_240125_Exonwise.bed`) has 1155 entries, matching
   legacy's framing.

The Exonwise BEDs found on disk are all hg19. There is no hg38
Exonwise BED. Generating one requires either liftover from hg19 or
collapsing the segment-level hg38 BED by `_Ex_N` label.

There is also a 179-vs-123 gene anomaly: parsing the Exonwise BED's
column-4 labels with the GENE_Ex_N regex yields 179 distinct gene
prefixes, but the panel is described as 123 genes. Either the
panel marketing number excludes some regions, or the parsing
catches non-gene labels (introns, control regions). Worth
investigating.

## What we did NOT ship today

- The SAMPLE_DASHBOARD Nextflow module
- The bin/render_dashboard.py script (drafted locally, unit-tested
  against synthetic fixtures, validated to render correctly; not
  yet transferred to gandalf)
- The ORGANIZE_OUTPUT module wiring (separate work, deferred)

The dashboard renderer is drafted at
/mnt/user-data/outputs/render_dashboard.py (in Claude's local
outputs; transferable on demand) but should not be shipped until
the granularity question is settled, because rendering against
segment-level data would produce coverage numbers that don't match
what your clinicians expect from the legacy report.

## Lessons codified for next session

1. **Whitespace in OLD_BODY anchors is fragile.** Patch 1
   (hsmetrics) missed a blank line on first attempt. After this,
   we standardized on:
   - Always run `cat -A` and `md5sum` on the target file before
     writing the patch.
   - Build fixtures via Python (heredoc fixtures via bash mangle
     apostrophes).
   - Use single-line OLD anchors when possible since they're more
     robust to surrounding-whitespace drift.

2. **Container compatibility check is a separate step from
   patch-applies-cleanly check.** Patch 2 applied cleanly to the
   .nf file but the chosen container could not run the script.
   Future patches should verify the container provides every tool
   the script invokes (Python, samtools, bedtools, etc.) before
   shipping.

3. **BED-row count is not the same as clinical-report "probe"
   count.** Two intermediate aggregation levels exist (Target=N
   sites, exon labels), and the legacy report's "1156 probes" is
   actually exons. Always cross-check counts before promising
   "matches legacy" semantics.

## File inventory (as of session end)

New files installed (committed-ready):
```
modules/local/mosdepth.nf
modules/local/parse_exon_coverage.nf
bin/parse_exon_coverage.py
tools/patches/2026-05-17/apply_hsmetrics_port.py
tools/patches/2026-05-17/apply_exon_coverage_port.py
tools/patches/2026-05-17/apply_preprocessing_qc_wiring.py
tools/patches/2026-05-17/apply_qc_publishdir_routing.py
tools/patches/2026-05-17/apply_tspipe_qc_channels.py
tools/patches/2026-05-17/apply_exon_coverage_split_bundle1.py
tools/patches/2026-05-17/apply_exon_coverage_split_bundle2.py
```

Files modified (committed-ready):
```
modules/local/hsmetrics.nf
subworkflows/local/preprocessing.nf
workflows/tspipe.nf
conf/modules.config
```

Files retired (.bak preserved):
```
modules/local/exon_coverage.nf  (moved to .bak_split_into_mosdepth_and_parse_*)
```

The validation run output remains at
/goast/hemat_data/nfcore_runs/25NGS1307_qc_20260517_120209/ for
reference.
