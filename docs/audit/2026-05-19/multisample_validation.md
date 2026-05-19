mkdir -p /goast/hemat_data/nf-core-tspipe/docs/audit/2026-05-19
mv ~/inbox/from_claude/multisample_validation.md \
   /goast/hemat_data/nf-core-tspipe/docs/audit/2026-05-19/multisample_validation.md# Multi-sample validation run — 2026-05-19

## Context

First multi-sample run of the nf-core-tspipe port after today's D1
(Pindel as 4th FLT3-ITD caller), D2 (IGV_REPORTS), and Pindel GT
filter changes landed. Goal was to exercise the pipeline on a
batch of real specimens and surface any operational issues before
declaring the port production-ready.

Scope of this session was validation only. No source changes
were made. Issues found are filed as follow-up items at the end
of this memo.

D2 visual inspection of 25NGS1307's IGV HTML (from the 1-sample
run earlier today, outdir `d1d2_real_20260519_104440`) was
performed at the start of this session and signed off.

## Run identifiers

| Item                  | Value                                                                |
| --------------------- | -------------------------------------------------------------------- |
| Outdir                | /goast/hemat_data/nfcore_runs/multi_d1d2_20260519_100426             |
| Log                   | /tmp/multi_d1d2_20260519_100426.log                                  |
| Samplesheet           | /tmp/multisample_validation.csv (17 lines: header + 16 samples)      |
| tmux session          | d1d2_multi                                                           |
| Start (UTC)           | 2026-05-19 10:04:26                                                  |
| Start (IST)           | 2026-05-19 15:34:26                                                  |
| End (IST, approx)     | 2026-05-19 17:53 (latest sample directory mtime)                     |
| Wall time             | ~2 h 19 min                                                          |
| Sample selection      | random.sample(seed=20260519, k=16) from 35 available FASTQ pairs     |
| Sex assignments       | all unknown (female PoN fallback, by current pipeline default)       |

## Resource verification (pre-launch)

```
/goast: 7.0T, 6.3T used, 761G avail, 90%
/home:  372G, 333G used,  39G avail, 90%
1-sample footprint (25NGS1307 outdir): 1.4G
nproc: 192
RAM: 1.5 TB
gandalf.config: per-process memory 32 GB; executor cpus 160,
                memory 1280 GB, queueSize 32
```

Headroom for 16 samples at 1.4G each was ~34x over the 761G
available on /goast. No pressure during the run.

## Wall-time planning vs actual

Planned band 90 min – 3 h with best estimate 2 h. Actual 2 h 19 min.
Inside band, close to the central estimate. With queueSize=32 ≥ 16
samples, the pipeline ran all samples in parallel through each stage.

## Artifact inventory

All 16 samples produced the same set of 12 entries in their
`<outdir>/<sample>/clinical/` directory:

```
<sample>_dashboard.html
<sample>_exon_coverage.tsv
<sample>_fastp.html
<sample>.final.bam
<sample>.final.bam.bai
<sample>_flt3_consensus.tsv
<sample>_hsmetrics.txt
<sample>_igv_report.html
<sample>.somaticseq.clinical.final.tsv
<sample>.somaticseq.filtered.tsv
cnv_consensus/    (dir)
cnvkit_plots/     (dir)
```

Per-sample entry counts (all 16 show 12 entries):

```
25NGS1319  25NGS336   25RSEQ146  25RSEQ415   26CGH169   26CGH238
25NGS1736  25NGS52    25RSEQ342  26CGH14     26CGH174   26CGH260
25NGS1860  25NGS980   25RSEQ360  26CGH57
```

## Trace summary

`pipeline_info/execution_trace_2026-05-19_15-34-28.txt`: 625 task rows.

- COMPLETED: 615
- FAILED: 9

All 9 failures are in a single process: `TSPIPE:FLT3_ITD:FLT3_ITD_EXT`.
No failures in any other process. No VV hiccups, no resumes, no
infrastructure errors.

Failed samples and corresponding consensus TSV row counts:

| Sample      | FLT3_ITD_EXT status | flt3_consensus.tsv rows |
| ----------- | ------------------- | ----------------------- |
| 25NGS1319   | FAILED              | 0                       |
| 25NGS1736   | FAILED              | 0                       |
| 25NGS1860   | FAILED              | 0                       |
| 25NGS52     | FAILED              | 0                       |
| 25RSEQ146   | FAILED              | 0                       |
| 25RSEQ360   | FAILED              | 0                       |
| 26CGH14     | FAILED              | 0                       |
| 26CGH238    | FAILED              | 0                       |
| 26CGH260    | FAILED              | 0                       |
| 25NGS336    | COMPLETED           | 1                       |
| 25NGS980    | COMPLETED           | 1                       |
| 25RSEQ342   | COMPLETED           | 1                       |
| 25RSEQ415   | COMPLETED           | 2                       |
| 26CGH169    | COMPLETED           | 1                       |
| 26CGH174    | COMPLETED           | 1                       |
| 26CGH57     | COMPLETED           | 2                       |

Empty consensus correlates with FLT3_ITD_EXT failure with no
exceptions.

## Evidence for the failure mode

`.command.err` from work dir `work/6b/542af1c7ab8e2e304e548d713b8274/`
(26CGH260, FLT3_ITD_EXT FAILED), tail:

```
[main] CMD: bwa mem -k 6 -M -O 6 -T 9 ...
[main] Real time: 0.040 sec; CPU: 0.007 sec
NO ITD CANDIDATE CLUSTERS GENERATED. Exiting...
```

This is the FLT3_ITD_ext tool reporting that no candidate ITDs were
found in the reads. For a FLT3-ITD-negative specimen this is the
expected biological outcome, not an error. The wrapper currently
treats this as a task failure (Nextflow records the task as FAILED
with no output file produced).

The high peak_vmem values reported in the trace for some of these
tasks (up to 26 GB) are JVM virtual-address-space allocations from
the bbduk preprocessing step; peak_rss stays under 300 MB. Not
relevant to the failure.

## Outstanding follow-ups

These are filed for a future session; no patches were applied in
this session per the scope rule.

1. **FLT3_ITD_EXT module treats "no ITD found" as task failure.**
   Module wrapper exits in a way Nextflow records as FAILED when
   FLT3_ITD_ext reports no candidate clusters. Expected behaviour
   for FLT3-ITD-negative specimens is a successful task with an
   empty/sentinel output file. Affects an estimated majority of
   clinical specimens. Evidence: work dirs for the 9 failed tasks
   listed above. Representative .command.err:
   `work/6b/542af1c7ab8e2e304e548d713b8274/.command.err`.

2. **FLT3_CONSENSUS produces header-only TSV when FLT3_ITD_EXT
   output is missing.** When the FLT3_ITD_EXT task fails (item 1),
   the consensus module emits a 162-byte header-only TSV rather
   than running consensus across the remaining three callers
   (filt3r, getitd, pindel). All 9 affected samples in this run
   have row=0 consensus TSVs despite having intact outputs from
   the other three callers in their respective work dirs. Until
   resolved, the consensus TSV is unreliable for any sample where
   FLT3_ITD_EXT does not call.

3. **Operational note: workflow.onComplete summary missing from
   piped log.** The standard Nextflow "Completed at / Succeeded /
   Failed" block did not appear in
   `/tmp/multi_d1d2_20260519_100426.log` after the run finished.
   The custom `Cleanup complete. Final per-sample layout: ...`
   message is the last line. Likely interaction between
   `-ansi-log false`, the `tee` pipe, and the workflow's onComplete
   handler. Not blocking — the trace file has the same data — but
   worth fixing for log readability.

## Usability of this run's outputs

- All 16 samples produced complete clinical artifact sets except
  for the FLT3 consensus TSV in the 9 failed samples.
- SNV outputs (somaticseq.clinical.final.tsv,
  somaticseq.filtered.tsv), CNV outputs (cnvkit_plots/,
  cnv_consensus/), coverage (exon_coverage.tsv, hsmetrics.txt),
  alignment (final.bam), and IGV (igv_report.html) are intact for
  all 16 samples.
- For FLT3 review on the 9 affected samples, per-caller outputs
  in the work dirs and in the corresponding production results
  directories should be consulted directly until follow-up
  items 1 and 2 are resolved.

## References

- Execution trace: `pipeline_info/execution_trace_2026-05-19_15-34-28.txt`
- Execution report: `pipeline_info/execution_report_2026-05-19_15-34-28.html`
- Execution timeline: `pipeline_info/execution_timeline_2026-05-19_15-34-28.html`
- Pipeline DAG: `pipeline_info/pipeline_dag_2026-05-19_15-34-28.svg`
- Run log: `/tmp/multi_d1d2_20260519_100426.log`
- Samplesheet: `/tmp/multisample_validation.csv`
- Sample selection seed: 20260519
- Failed task work dir (example): `work/6b/542af1c7ab8e2e304e548d713b8274/`
- Previous session reference: `docs/audit/2026-05-19/d1d2_real_data_findings.md`
