# 2026-05-19 — Late-morning findings + finalization roadmap

Companion to `morning_findings.md`. Captures (1) the late-morning work
landing D1 and D2, (2) three observations made during that work that
deserve later cleanup, and (3) the path from here to "production-ready"
on the nf-core port.

---

## Late-morning commits

Four commits landed on `origin/main` today, two of them substantive
backlog closures:

| SHA       | Type    | Summary                                              |
|-----------|---------|------------------------------------------------------|
| `3268744` | audit   | Morning findings (VV REST volume migration)          |
| `5052360` | audit   | Detailed backlog spec for D1/D2/B4                   |
| `d5ff1e4` | feature | D1: Pindel as 4th caller in FLT3-ITD consensus       |
| `d1c491c` | feature | D2: IGV_REPORTS wired into clinical deliverable tree |

Both features structurally validated via stub-mode runs on 25NGS1307
under the `gandalf,singularity` profile. Both have pending real-data
validation gates (see "Pending validation" below).

---

## Three findings filed today (no fix in this commit)

### Finding 1 — `assets/test/` is missing

The `test` profile (`conf/test.config`) references:
- `${projectDir}/assets/test/chr13_chunk.fa`
- `${projectDir}/assets/test/test_panel.bed`
- `${projectDir}/assets/test/illumina_adapters.fa`
- `${projectDir}/assets/test/blacklist_snvs_hg38.tsv`

None of these files exist under `assets/`. They were either gitignored
at some point or never committed. Any attempt to use `-profile test`
will fail at preflight.

**Workaround in use today**: `-profile gandalf,singularity -stub` with
`/tmp/cnv_wiring/validation_samplesheet.csv` (a 1-sample real CSV with
real FASTQs). Stubs short-circuit the missing data dependency. This is
what the 2026-05-16 audit also used.

**Proper fix**: either restore the test assets (small synthetic
chunked references), or remove `conf/test.config` and switch all
stub-validation guidance to use the `gandalf` profile. The 2026-05-18
end-of-day notes also suggest the `test` profile was already broken at
that point; today's session simply re-confirmed it.

**Severity**: Low. Doesn't block any production work. Affects only
people coming to the repo without gandalf-specific paths.

### Finding 2 — Mystery zero-byte files at repo root

At session timestamp `10:00`, seven zero-byte regular files appeared
at the repo root:

```
ANNOTATION  CNV_CALLING  FLT3_ITD  REPORTING
SOMATICSEQ_ENSEMBLE  SV_CALLING  VARIANT_CALLING
```

These names match seven subworkflow names from `tspipe.nf` exactly.
The temporal coincidence with today's failed first stub run
(`--outdir /tmp/...`, which hit a cross-filesystem hardlink error in
PICARD_MARKDUPLICATES) is suggestive but the causal link could not be
identified:

- `grep` across all `.nf` files found no `file("UPPERCASE_TOKEN")` patterns.
- `main.nf`'s `workflow.onComplete` block only *deletes* directories
  (line 78: `if (target.exists()) target.deleteDir()`), never creates
  files.
- `scratchSubdirs` in `onComplete` does not contain any of the seven
  names.
- Nothing in `tools/` or `bin/` writes files matching these names.

The files were deleted, and `.gitignore` entries added defensively in
the D1 commit (`d5ff1e4`):

```gitignore
/ANNOTATION
/CNV_CALLING
/FLT3_ITD
/REPORTING
/SOMATICSEQ_ENSEMBLE
/SV_CALLING
/VARIANT_CALLING
```

**Action for next session**: on the next stub run with a cross-FS
outdir (or any failed stub), check whether these files reappear at
the repo root. If they do, isolate the producing code path by reading
`.nextflow.log` carefully. If they don't reappear, treat the
`.gitignore` as defense-in-depth and move on.

**Severity**: Low (files were zero-byte, no data loss possible) but
worth resolving because uncaught mystery state is a bad pattern.

### Finding 3 — REPORTING subworkflow is dead code

`subworkflows/local/reporting.nf` imports both `IGV_REPORTS` and
`ORGANIZE_OUTPUT` and defines a `workflow REPORTING { ... }` block.
But `workflows/tspipe.nf` never invokes it. D2's investigation found
that IGV_REPORTS was orphaned (not running on any sample in any
nf-core run since `3a2c4ce`, the stub-blocks commit on 2026-05-16),
and ORGANIZE_OUTPUT was being called directly from `tspipe.nf`
bypassing the REPORTING subworkflow.

D2's fix wired IGV_REPORTS directly into `tspipe.nf` to match the
existing ORGANIZE_OUTPUT pattern. REPORTING is now provably dead:

- `tspipe.nf` line 28: `include { REPORTING }` (orphan)
- `tspipe.nf` body: never calls `REPORTING(...)`.
- Nothing else references it.

**Cleanup proposal**: `git rm subworkflows/local/reporting.nf` and
remove the orphan include in `tspipe.nf`. One-line code change plus
a file deletion. Low risk; can be a single audit-only commit.

**Severity**: Code-hygiene only. Not blocking. Worth doing because
dead code is misleading to anyone reading the topology — a future
maintainer will see "REPORTING" in includes and look for it, finding
nothing.

---

## Pending validation gates before "production-ready"

D1 and D2 are both committed but neither has been exercised end-to-end
on real data in the nf-core port. The structural validation (stubs)
proves topology. Real-data validation proves behavior.

### D1 real-data gate

```bash
cd /goast/hemat_data/nf-core-tspipe
nextflow run . \
    -profile gandalf,singularity \
    --input /tmp/cnv_wiring/validation_samplesheet.csv \
    --outdir /goast/hemat_data/nfcore_runs/d1_real_$(date +%Y%m%d_%H%M%S) \
    -ansi-log false \
    -resume \
    2>&1 | tee /tmp/d1_real.log
```

Expected runtime: 4-8 hours for the single 25NGS1307 sample given
gandalf's typical throughput on this pipeline.

**Validation**: semantic diff of the FLT3 consensus TSV against
production. Byte-equal diff will fail — the nf-core port's schema has
extra `vaf_pct_*` and `ar_*` columns that production lacks. The
correct test:

```bash
NFCORE_TSV=<outdir>/25NGS1307/clinical/25NGS1307_flt3_consensus.tsv
PROD_TSV=/goast/hemat_data/targeted-seq-pipeline/results/25NGS1307/flt3/25NGS1307_flt3_consensus.tsv

# Compare the columns both schemas share, on rows defined by (sample, status, n_tools, tools, length_bp, pos_hg38)
# Quick visual diff:
diff \
    <(awk -F'\t' 'BEGIN{OFS="\t"} NR==1{for(i=1;i<=NF;i++) if($i~/^(sample|status|n_tools|tools|length_bp|pos_hg38)$/) cols[i]=1; print "sample\tstatus\tn_tools\ttools\tlength_bp\tpos_hg38"} NR>1{out=""; for(i=1;i<=NF;i++) if(i in cols) out=out (out?"\t":"") $i; print out}' "$NFCORE_TSV" | sort) \
    <(awk -F'\t' 'BEGIN{OFS="\t"} NR==1{for(i=1;i<=NF;i++) if($i~/^(sample|status|n_tools|tools|length_bp|pos_hg38)$/) cols[i]=1; print "sample\tstatus\tn_tools\ttools\tlength_bp\tpos_hg38"} NR>1{out=""; for(i=1;i<=NF;i++) if(i in cols) out=out (out?"\t":"") $i; print out}' "$PROD_TSV" | sort)
```

Expected outcome: identical rows. If the nf-core port detects an extra
ITD that production missed (because Pindel uniquely catches it), this
is actually a positive finding — file as a "D1 caught a real ITD that
production missed on this sample" win.

### D2 real-data gate

The D2 gate is opportunistic: the same real-data run that validates
D1 also produces a real IGV HTML at:

```
<outdir>/25NGS1307/clinical/25NGS1307_igv_report.html
```

**Validation**: open it in a browser. Walk the variant table and
confirm each variant's pileup view loads. Compare against:

```
/goast/hemat_data/targeted-seq-pipeline/results/25NGS1307/annotation/25NGS1307_igv_report.html
```

Same variants should appear in both, with similar pileup depth. Byte-
equal is impossible (embedded BAM blobs depend on the exact BAM, and
create_report timestamps differ). The validation is "does it open,
does it show the right variants, are the pileups sensible".

---

## Open audit items NOT addressed today

Carried forward to future sessions. Roughly in priority order:

1. **B4: KMT2A-PTD detection.** Still unimplemented in the nf-core
   port. Today's morning_findings has the full spec. Effort estimate
   half-day to two days depending on what production's
   `scripts/12g_exon_cnv.py` actually does (read it first).

2. **VV REST 3-worker boot failure.** Workaround in place (1 worker
   × 5 threads). Root cause not investigated. From morning_findings.

3. **`$HOME → /root` under sudo in VV REST compose.** Currently
   hardcoded `/home/hemat/` paths. Proper fix is a `.env` file. From
   morning_findings.

4. **IGV duplicate-handling alignment.** D2 inherited production's
   default of excluding duplicates (`--exclude-flags 1536`). This
   diverges from this site's coverage convention (mosdepth `--flag
   772` INCLUDES duplicates). Ask clinical reviewers whether the
   inclusion rule should apply to visual IGV review. If yes, the
   nf-core .nf module gains `--exclude-flags 512` (or similar);
   production stays as-is unless they want to align.

5. **REPORTING subworkflow cleanup** (Finding 3 above).

6. **`assets/test/` restoration or removal** (Finding 1 above).

7. **`/home` filesystem still at 94%.** Long-term remediation is
   Docker data-root migration to `/goast` or LVM expansion. Not on
   fire today. From morning_findings.

8. **Mystery zero-byte files at repo root** (Finding 2 above).

---

## Backup audit at session end

Files preserved from today's work (safe to delete after real-data
validation passes; preserve for now as rollback path):

```
bin/flt3_consensus.py.bak_20260519_095458         (D1: pre-patch original)
bin/flt3_consensus.py.bak_arfix_20260519_095650   (D1: pre-arfix)
bin/flt3_consensus.py.bak_tallyfix_20260519_095756 (D1: pre-tallyfix)
bin/igv_reports.py.bak_<ts>                       (D2: pre-refactor)
bin/organize_output.py.bak_d2_igv_<ts>            (D2: pre-igv-arg)
modules/local/flt3_consensus.nf.bak_*             (D1)
modules/local/igv_reports.nf.bak_<ts>             (D2: pre-real-module)
modules/local/organize_output.nf.bak_d2_*         (D2)
subworkflows/local/flt3_itd.nf.bak_*              (D1)
workflows/tspipe.nf.bak_*                         (D1 and D2)
nextflow.config.bak_*                             (D1)
```

Plus assorted older `.bak_*` files from earlier sessions, all left
in place.

---

## Suggested next session

If the day's energy allows:

1. **Start the D1+D2 real-data validation run** in a tmux/screen
   session. It'll run for 4-8 hours unattended.
   ```
   tmux new -s d1d2_validation
   # ... run command from "D1 real-data gate" above ...
   # Detach: Ctrl-b d
   ```
2. **While that runs, address Finding 3 (REPORTING cleanup).** Small,
   contained, safe.
3. **Or pick up B4 (KMT2A-PTD).** Start by reading
   `/goast/hemat_data/targeted-seq-pipeline/scripts/12g_exon_cnv.py`
   to learn what production does, before designing anything.

If energy doesn't allow: stopping here is fine. The day landed two
substantive features that will materially improve clinical output.
