# Testing

This is a phased smoke-test plan for verifying that a fresh install works end
to end. It assumes [`docs/INSTALL.md`](INSTALL.md) is complete: prerequisites
installed, site config written and registered, reference data in place,
VariantValidator REST stack running, container catalogue pulled.

Run the phases in order. Each one verifies one thing; skipping ahead produces
failures that are hard to debug.

| Phase | What it verifies                                       | Time      | Real data |
|-------|--------------------------------------------------------|-----------|-----------|
| 1     | Config parses, profiles resolve                        | 2 min     | No        |
| 2     | DAG topology and channel wiring (stub mode)            | 5 min     | Stubs     |
| 3     | One-sample real run, end to end                        | 30–45 min | Yes       |
| 4     | Multi-sample parallelism at production scale           | 2–4 h     | Yes       |
| 5     | Panel-of-normals build (only when rebuilding the PoN)  | varies    | Yes       |

Throughout this document, `<yoursite>` stands in for the profile name you
registered in `nextflow.config` (e.g. `gandalf`, `mysite`). All examples assume
you are at the repository root.

Cross-references:

- [`docs/INSTALL.md`](INSTALL.md) — install context and prerequisites
- [`docs/usage.md`](usage.md) — parameter reference and samplesheet format
- [`docs/output.md`](output.md) — expected outputs per sample
- [`docs/usage_pon.md`](usage_pon.md) — panel-of-normals build workflow
- [`docs/clinical_decisions.md`](clinical_decisions.md) — intentional differences from the upstream Python pipeline

## Phase 1 — Config parse check (2 min)

Verify that the configuration is syntactically valid and your site profile
resolves cleanly. This does not start any processes.

```bash
# Resolved configuration for your profile. Errors here mean a typo in
# conf/<yoursite>.config or in nextflow.config.
nextflow config -profile <yoursite>,singularity

# Help output exercises main.nf parsing without running anything.
nextflow run . -profile <yoursite>,singularity --help 2>&1 | head -60
```

Success criteria:

- `nextflow config` prints the merged config without errors.
- The help output lists pipeline parameters with sensible defaults.

If either fails, fix the config before moving on. Common causes: missing
required params (`dbsnp_vcf`, `mills_vcf`, `gnomad_af_only`, `exonwise_bed`,
`annovar_script`), unresolved `${...}` variables, or a profile name that does
not match the `profiles { ... }` block in `nextflow.config`.

## Phase 2 — Structural validation in stub mode (~5 min)

Every module in `modules/local/` has a `stub:` block that creates empty
declared outputs without invoking the underlying tool. Running the whole
pipeline in `-stub` mode therefore exercises:

- Channel construction and joins in `subworkflows/local/`
- DAG topology (every consumer finds a producer)
- Per-module output shape (declared emits match downstream consumers)
- Resolved file paths for all reference inputs

It does **not** exercise container pulls, the variant callers themselves, or
any tool-specific behaviour.

Build a one-sample samplesheet against any pair of FASTQs (the files are not
read in stub mode, but the paths must exist):

```bash
mkdir -p /tmp/tspipe_smoke
cat > /tmp/tspipe_smoke/samplesheet.csv <<'EOF'
sample,fastq_1,fastq_2,sex
SMOKE01,/absolute/path/to/SMOKE01_R1.fastq.gz,/absolute/path/to/SMOKE01_R2.fastq.gz,unknown
EOF
```

Samplesheet column reference is in [`docs/usage.md`](usage.md). `sex` accepts
`male`, `female`, or `unknown` (the CNV module falls back to the female PoN on
`unknown`, with a warning).

Run with `-stub`:

```bash
nextflow run . \
    -profile <yoursite>,singularity \
    -stub \
    --input /tmp/tspipe_smoke/samplesheet.csv \
    --outdir /tmp/tspipe_smoke/stub_$(date +%Y%m%d_%H%M%S) \
    -with-trace /tmp/tspipe_smoke/stub_trace.txt
```

Success criteria:

- Every process line ends with `1 of 1 ✔` (or `cached: 1 ✔` on a `-resume`).
- No `FAILED` or `ABORTED` rows in the trace.
- The output tree under `--outdir` mirrors the layout described in
  [`docs/output.md`](output.md), with empty placeholder files.

A reference clean run is the 2026-05-16 stub validation: 21 of 21 processes
green on a single CNV-calling sample.

## Phase 3 — One-sample real run (~30–45 min)

This is the first run that actually pulls containers and invokes the tools.

### Sample selection

Pick a sample with a **known FLT3-ITD** for the first smoke test if you have
one. The reason is documented in the README under *Status and known
limitations*: `FLT3_ITD_EXT` exits with `NO ITD CANDIDATE CLUSTERS GENERATED`
on ITD-negative specimens, which Nextflow records as a task failure. The
pipeline as a whole still completes (other modules are unaffected and the
clinical tree is assembled), but a first-time smoke test on an ITD-negative
sample will surface a red row in the execution report that looks like an
install problem and is not.

If you only have ITD-negative samples available, use one anyway and expect
exactly one `FLT3_ITD_EXT` failure per sample in the report.

### Run

```bash
mkdir -p /data/runs
RUN_DIR=/data/runs/$(date +%Y%m%d_%H%M%S)_smoke_1sample

nextflow run . \
    -profile <yoursite>,singularity \
    --input /tmp/tspipe_smoke/samplesheet.csv \
    --outdir ${RUN_DIR} \
    -resume \
    -with-report  ${RUN_DIR}/report.html \
    -with-trace   ${RUN_DIR}/trace.txt \
    -with-timeline ${RUN_DIR}/timeline.html \
    2>&1 | tee ${RUN_DIR}/nextflow.log
```

`-resume` is harmless on a first run and lets you retry from cache if a single
process fails for a transient reason.

### Verifying success

Inspect the run in this order:

1. **Execution report** — open `${RUN_DIR}/report.html` (or
   `${RUN_DIR}/pipeline_info/execution_report_*.html`). All processes should
   show exit code 0, with the documented FLT3_ITD_EXT exception above.
2. **Clinical deliverable tree** — `${RUN_DIR}/<sample>/clinical/` should
   contain the files listed in [`docs/output.md`](output.md): the final BAM,
   clinical TSV, FLT3 consensus TSV, CNV plots, IGV pileup HTML, and per-sample
   dashboard.
3. **Clinical TSV has rows** —
   `wc -l ${RUN_DIR}/<sample>/clinical/<sample>.clinical.tsv` should be
   greater than 1 (header plus variants).
4. **FLT3 consensus TSV is well-formed** —
   `${RUN_DIR}/<sample>/clinical/<sample>_flt3_consensus.tsv` exists. If the
   sample is ITD-positive, expect rows; if ITD-negative, expect header only.
5. **CNV outputs** — `${RUN_DIR}/<sample>/clinical/cnv/` contains the scatter
   PDF/PNG and the annotated CNV TSV.

### When something fails

```bash
# Find the failed task in the trace
grep -E "FAILED|ABORTED" ${RUN_DIR}/trace.txt

# Look at the task's work directory
ls -la work/<hash>/
cat work/<hash>/.command.sh    # the script Nextflow ran
cat work/<hash>/.command.err   # stderr from the tool
cat work/<hash>/.command.log   # Nextflow's wrapper log
cat work/<hash>/.exitcode      # non-zero exit code
```

For channel-join failures, `.command.err` is usually empty because no task
script ran; the error is in `.nextflow.log` at the repository root with a
traceback into the relevant subworkflow.

## Phase 4 — Multi-sample batch (production scale)

Once a one-sample run is green, the same command with a larger samplesheet
exercises Nextflow's per-sample parallelism. There is no separate command —
just more rows in the samplesheet.

The production baseline is the 2026-05-19 run on gandalf: **16 samples, 2 h 19
min wall time** on 192 cores and 1.5 TB RAM. Smaller hosts will see longer
wall times but the same per-sample work.

```bash
RUN_DIR=/data/runs/$(date +%Y%m%d_%H%M%S)_batch

nextflow run . \
    -profile <yoursite>,singularity \
    --input /path/to/multi_sample_samplesheet.csv \
    --outdir ${RUN_DIR} \
    -resume \
    -with-report  ${RUN_DIR}/report.html \
    -with-trace   ${RUN_DIR}/trace.txt \
    -with-timeline ${RUN_DIR}/timeline.html
```

What to watch:

- Multiple `RUNNING` rows in `${RUN_DIR}/trace.txt` early on confirm that the
  scheduler is parallelising across samples.
- The execution report's CPU utilisation gauge: if it sits low for long
  stretches, one process label is a bottleneck. Tune `withLabel:...`
  resource directives in your site config; see [`docs/INSTALL.md`](INSTALL.md)
  for the resource label conventions.
- Wall time on the timeline HTML, compared against the gandalf baseline,
  scales roughly linearly with `(samples / cores)`.

## Phase 5 — PoN build (one-off, only when rebuilding)

A separate workflow entry, only run when constructing a new CNV panel-of-
normals (different panel BED, different reference build, or a refreshed
normals cohort). Full reference is in
[`docs/usage_pon.md`](usage_pon.md); the smoke-test invocation is:

```bash
nextflow run . -entry BUILD_PON \
    -profile <yoursite>,singularity \
    --input /path/to/normals.csv \
    --outdir /path/to/pon_outdir \
    -resume
```

The normals samplesheet has the same columns as the per-sample samplesheet
plus an `exclude` column (true/false) to mark known-aberrant normals that
should be present in the input but absent from the final PoN. See
[`docs/usage_pon.md`](usage_pon.md).

## Common errors

| Error                                                  | Means                                                | Fix                                                                                    |
|--------------------------------------------------------|------------------------------------------------------|----------------------------------------------------------------------------------------|
| `nextflow: command not found`                          | Nextflow not on PATH                                 | Reinstall per [`docs/INSTALL.md`](INSTALL.md#nextflow)                                  |
| `Nextflow requires Java 17+`                           | Older Java in PATH                                   | Install Java 21 LTS per [`docs/INSTALL.md`](INSTALL.md#java)                            |
| `singularity: command not found`                       | Singularity/Apptainer not installed                  | Install per [`docs/INSTALL.md`](INSTALL.md#singularity-apptainer)                        |
| `Cannot find any reads matching: ...`                  | Samplesheet path wrong or file unreadable            | Check the absolute path and permissions; FASTQs must be readable by the run user        |
| `Reference dictionary file does not exist`             | `.dict` missing next to the reference FASTA          | `gatk CreateSequenceDictionary -R <fasta>`                                              |
| Process FAILED with exit status 247                    | Out of memory                                        | Bump `max_memory`, or the label-specific resource tier in your site config              |
| Process FAILED with exit status 137                    | OOM-killed by the OS (cgroup limit)                  | Same as 247; check the host's available memory                                          |
| `FLT3_ITD_EXT` failed with `NO ITD CANDIDATE CLUSTERS` | Sample has no detectable FLT3-ITD                    | Expected; the consensus TSV will be header-only. Not an install problem.                |
| `VariantValidator: connection refused`                 | The REST stack is not running                        | `docker compose up -d` in the rest_variantValidator directory; see [`docs/INSTALL.md`](INSTALL.md#variantvalidator-rest-stack) |
| Channel-join `EmptyChannelException`                   | An upstream process emitted nothing for a sample     | Check the trace for the upstream FAILED row; the missing output is the root cause       |
| `MANIFEST_UNKNOWN` from a `docker://` URI              | Container image was renamed or never published       | Check `conf/modules.config` for the offending `container` directive                     |

## Re-running and caching

`-resume` reuses cached results from the same `--outdir`. Two rules to remember:

- Same `--outdir` → cache is consulted. Change `--outdir` → cache is ignored,
  even with `-resume`.
- Cache keys hash the full container URI, input file content, and the script
  block. Changing any of these invalidates the downstream cache.

The `work/` directory grows quickly. After a clean validation run, prune with
`nextflow clean -f` (interactive) or remove the run-specific work hashes by
hand if you need to keep parallel runs around.
