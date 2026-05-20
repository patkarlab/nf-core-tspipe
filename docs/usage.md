# Usage

How to run nf-core-tspipe once it's installed. For install, prerequisites,
and site configuration, see [`docs/INSTALL.md`](INSTALL.md).

## Introduction

The pipeline takes paired-end FASTQ from a samplesheet through preprocessing,
parallel variant calling, FLT3-ITD ensemble, CNV calling, annotation, and IGV
report generation. It outputs a per-sample clinical deliverable tree at
`<outdir>/<sample>/clinical/`. The full output layout is documented in
[`docs/output.md`](output.md).

Two entry workflows are defined in `main.nf`:

- `TSPIPE` (default) — per-sample analysis
- `BUILD_PON` — one-off panel-of-normals construction (see
  [`docs/usage_pon.md`](usage_pon.md))

## Quick start

```bash
nextflow run . \
    --input /path/to/samplesheet.csv \
    --outdir /path/to/results \
    -profile <yoursite>,singularity \
    -resume
```

`<yoursite>` is the profile you registered when copying
`conf/site_template.config` to `conf/<yoursite>.config` (see
[`docs/INSTALL.md#site-configuration`](INSTALL.md#site-configuration)).
On the development server the profile is `gandalf`.

## Samplesheet

A CSV validated against `assets/schema_input.json`. Header is mandatory and
case-sensitive.

```csv
sample,fastq_1,fastq_2,sex
25NGS1307,/data/fastqs/25NGS1307_R1.fastq.gz,/data/fastqs/25NGS1307_R2.fastq.gz,unknown
26CGH40,/data/fastqs/26CGH40_R1.fastq.gz,/data/fastqs/26CGH40_R2.fastq.gz,female
25NGS336,/data/fastqs/25NGS336_R1.fastq.gz,/data/fastqs/25NGS336_R2.fastq.gz,male
```

Column rules:

| Column | Required | Allowed values | Notes |
|---|---|---|---|
| `sample` | yes | no whitespace | Used as the per-sample output directory name |
| `fastq_1` | yes | path ending in `.fq.gz` or `.fastq.gz` | Must resolve from where Nextflow runs |
| `fastq_2` | yes | path ending in `.fq.gz` or `.fastq.gz` | Same |
| `sex` | no (defaults to `unknown`) | `male`, `female`, `unknown` | Selects the sex-stratified CNV panel-of-normals |

`tools/make_samplesheet.sh` scans a FASTQ directory and emits a samplesheet
CSV. Common invocation:

```bash
tools/make_samplesheet.sh /path/to/fastq_dir \
    --output /tmp/today.csv \
    --exclude 25NGS336,26CGH14 \
    --min-size 500 \
    --sex 25NGS1307=male,26CGH40=female
```

See `tools/make_samplesheet.sh --help` for the full flag set.

## Parameters reference

The source of truth for every parameter is `nextflow.config`. Defaults come
from one of three places:

1. `nextflow.config` itself (in `params { ... }`).
2. Your active site config (e.g. `conf/gandalf.config` or
   `conf/<yoursite>.config`).
3. `${projectDir}/assets/<panel>/` for the CNV PoN and annotation
   reference files, defaulted in by `workflows/tspipe.nf` when not set in
   the active config.

Any parameter listed here can be overridden on the command line with
`--<param> value`.

### Required (workflow validates at start)

The workflow refuses to launch if any of these are unset.

| Parameter | Description |
|---|---|
| `--input` | Samplesheet CSV (see "Samplesheet" above) |
| `--reference` | hg38 masked FASTA. Must have `.fai`, `.dict`, and the five bwa-mem2 index files (`.amb`, `.ann`, `.pac`, `.bwt.2bit.64`, `.0123`) sitting alongside |
| `--bed` | Panel BED file |
| `--exonwise_bed` | Exon-collapsed BED for `MOSDEPTH` per-exon coverage |

`--outdir` is not validated but defaults to
`/goast/hemat_data/nfcore_runs/default`. Set it explicitly for every run.

### Reference data

| Parameter | Default | Description |
|---|---|---|
| `--pindel_bed` | `${projectDir}/references/pindel_targets_flt3_ubtf.bed` | Pindel target subset (FLT3 + UBTF region) for the FLT3-ITD ensemble |
| `--adapters` | `null` (fastp auto-detect) | Illumina adapter FASTA |
| `--dbsnp_vcf` | site config | dbSNP VCF (+ `.tbi`) for BQSR and SomaticSeq |
| `--mills_vcf` | site config | Mills indel gold-standard VCF (+ `.tbi`) for BQSR |
| `--gnomad_af_only` | site config | gnomAD AF-only VCF (+ `.tbi`) for Mutect2 germline filtering |

### Panel and CNV resources

The pipeline ships CNV PoN artefacts under `assets/<panel>/` and falls back
to them when not overridden. The deprecated mixed-sex `cnv_pon` is kept for
back-compat only.

| Parameter | Default | Description |
|---|---|---|
| `--panel` | `'myeloid'` | Panel namespace under `assets/`; controls which PoN directory is read |
| `--panel_name` | `'MYOPOOL hg38'` | Human-readable panel label used in reports |
| `--male_reference` | `true` | Pass `-y` (haploid X reference) to CNVKit. Set `false` for a female-only PoN |
| `--cnv_pon_male` | `assets/${panel}/cnvkit_pon_male.cnn` | Male-normal CNVKit PoN |
| `--cnv_pon_female` | `assets/${panel}/cnvkit_pon_female.cnn` | Female-normal CNVKit PoN |
| `--cnv_loo_summary` | `assets/${panel}/cnvkit_loo_summary.tsv` | Leave-one-out QC summary |
| `--cnv_noise_profile` | `assets/${panel}/loo_bin_noise_profile.tsv` | Per-bin LOO noise profile |
| `--cnv_noisy_bins` | `assets/${panel}/cnvkit_noisy_bins.bed` | Bins to exclude from CNV calls |
| `--cnv_pon` | (deprecated) | Old mixed-sex PoN. Ignored when `meta.sex` is set in the samplesheet, which is always. **Do not use** for new sites. |

### Annotation references

Shipped under `assets/references/` and defaulted in by the workflow if not
overridden.

| Parameter | Default | Description |
|---|---|---|
| `--cytoband` | `assets/references/cytoBand_hg38.txt` | UCSC cytoband table for CNV annotation |
| `--clingen` | `assets/references/ClinGen_gene_curation_list_GRCh38.tsv` | ClinGen gene curation list |
| `--vep_cache` | site config | VEP cache directory (matching the VEP version in the active container) |
| `--annovar_script` | site config | Path to ANNOVAR's `table_annovar.pl` perl entrypoint |
| `--annovar_db` | site config | ANNOVAR `humandb/` directory |
| `--snv_blacklist` | site config (optional) | Hand-curated TSV of recurrent SNV/indel artefacts; defaults to no blacklist filtering |

### FLT3 ensemble

| Parameter | Default | Description |
|---|---|---|
| `--flt3_container` | `'docker'` | One of `'docker'` or `'singularity'`. Must match your runtime profile |
| `--flt3_region` | `'chr13:28003000-28101000'` | hg38 FLT3 transcript + flanking; used by the Pindel-FLT3 region filter |

### Resource limits

`check_max()` in `conf/base.config` clamps every per-process request at
these ceilings.

| Parameter | Default in `nextflow.config` | Default in `conf/gandalf.config` | Description |
|---|---|---|---|
| `--max_memory` | `'128.GB'` | `'512.GB'` | Per-process memory ceiling |
| `--max_cpus` | `16` | `96` | Per-process CPU ceiling |
| `--max_time` | `'240.h'` | (inherits) | Per-process time ceiling |

For finer control over the executor's parallelism (how many tasks run at
once), edit the `executor { ... }` block in your site config — not these
params.

### nf-core conventions

| Parameter | Default | Description |
|---|---|---|
| `--outdir` | `/goast/hemat_data/nfcore_runs/default` | Output root |
| `--publish_dir_mode` | `'link'` | One of `'symlink'`, `'rellink'`, `'link'`, `'copy'`, `'copyNoFollow'`, `'move'`. `'link'` uses hardlinks where possible; falls back to symlinks across filesystems |
| `--monochrome_logs` | `false` | Disable ANSI colour in log output |
| `--help` | `false` | Reserved for future help text |
| `--version` | `false` | Print version and exit |

### Deprecated and no-effect parameters

Declared in `nextflow.config` but should not be used:

| Parameter | Status | Notes |
|---|---|---|
| `--cnv_pon` | Deprecated | Replaced by `--cnv_pon_male` / `--cnv_pon_female`. Ignored when samplesheet sets `meta.sex`. |
| `--keep_intermediates` | No effect | Leftover from the Python pipeline's `cleanup_intermediates.py`. The Nextflow pipeline uses `publish_dir_mode` and `work/` cleanup instead. |
| `--skip_from` | No effect | Leftover from the Python runner's `--skip-from N`. Replaced by Nextflow's `-resume`. |

## Profiles

Profiles compose left-to-right. Pass them with a single `-profile`
followed by a comma-separated list.

| Profile | What it sets | When to use |
|---|---|---|
| `standard` | `process.executor = 'local'` | Default fallback |
| `gandalf` | Includes `conf/gandalf.config` (gandalf-specific paths, conda-on-host shortcut, 192-core executor envelope) | On gandalf only |
| `<yoursite>` | Includes `conf/<yoursite>.config` (paths and resource ceilings for your server) | Any other server |
| `singularity` | `singularity.enabled = true; docker.enabled = false; singularity.autoMounts = true` | Production runtime; recommended on HPC |
| `docker` | `docker.enabled = true; singularity.enabled = false; docker.userEmulation = true` | Workstation, or hosts without Singularity |
| `conda` | `conda.enabled = true` | Slowest, most fragile. Not recommended for production |
| `slurm` | `process.executor = 'slurm'; process.queue = 'normal'` | SLURM cluster |

Combine a site profile and a runtime profile: `-profile gandalf,singularity`
or `-profile mysite,slurm,singularity`.

## Running the pipeline

### Direct invocation

```bash
cd /path/to/nf-core-tspipe
nextflow run . \
    --input /path/to/samplesheet.csv \
    --outdir /path/to/results \
    -profile <yoursite>,singularity \
    -resume
```

The `-resume` flag is safe and recommended every time. Nextflow's work-dir
hashing reuses cached process outputs when inputs and code are unchanged;
if nothing has changed, the run completes in seconds.

### Production launcher

`tools/run_pipeline.sh` is the production wrapper. It prompts for inputs,
runs preflight checks (samplesheet readable, FASTQs exist, no other
`tspipe` run active, VV REST stack responding, output filesystem has
enough free space), then launches Nextflow with `nohup` so the run
survives SSH disconnect.

```bash
tools/run_pipeline.sh
```

Environment variables override the defaults:

| Variable | Default | Purpose |
|---|---|---|
| `TSPIPE_REPO` | `/goast/hemat_data/nf-core-tspipe` | Repo location |
| `TSPIPE_SAMPLES` | (prompt) | Samplesheet CSV path |
| `TSPIPE_PROFILE` | `gandalf,singularity` | Nextflow `-profile` string |
| `TSPIPE_OUTDIR_BASE` | `/goast/hemat_data/nfcore_runs` | Parent of per-run output dirs |
| `TSPIPE_SKIP_PREFLIGHT` | `0` | Set to `1` to skip preflight (not recommended) |

Extra Nextflow flags pass through after the script's own arguments:
`tools/run_pipeline.sh -stub -resume` works.

### Resuming

`-resume` reuses cached process outputs. It is always safe. If a run
fails partway through, fix whatever caused the failure (network, disk,
parameter), then re-run the same command with `-resume` to pick up
where it left off:

```bash
nextflow run . --input today.csv --outdir results/ -profile gandalf,singularity -resume
```

If a process succeeds but you want to force it to re-run (e.g. because
you changed something not in the process inputs), delete its work-dir
hash directory and re-run with `-resume`:

```bash
# Find the work-dir of the task you want to re-run
grep -l "<sample>" work/*/.command.sh | head -5
rm -rf work/<hash>/
nextflow run . ... -resume
```

### Stubs

The `-stub` flag runs each process with its `stub:` block instead of
the real `script:` block. Stub blocks `touch` the expected output
files and emit placeholder versions. Useful for:

- Validating the workflow topology end-to-end without running tools
- Testing a samplesheet without committing CPU time
- Reproducing an output structure for downstream-tool development

```bash
nextflow run . --input today.csv --outdir results_stub/ -profile <yoursite>,singularity -stub
```

A stub run completes in seconds. The outputs are empty placeholders;
do not use them clinically.

### Running a subset of samples

Trim the samplesheet to the rows you want, or build a fresh
samplesheet with `tools/make_samplesheet.sh --exclude ...`. There is
no CLI flag to filter samples at runtime — Nextflow consumes the
samplesheet wholesale.

### Per-run output directory

Always pass `--outdir` explicitly with a per-run timestamp:

```bash
--outdir /data/nfcore_runs/$(date +%Y%m%d_%H%M%S)
```

The default (`/goast/hemat_data/nfcore_runs/default`) is a shared
fallback that will collide with previous runs.

### Pipeline information

Each run writes Nextflow's standard reporting suite to
`${outdir}/pipeline_info/`:

- `execution_report_<timestamp>.html` — full HTML execution report
- `execution_timeline_<timestamp>.html` — Gantt timeline
- `execution_trace_<timestamp>.txt` — per-task tab-separated trace
- `pipeline_dag_<timestamp>.svg` — DAG visualisation

For postmortem analysis of a failed run, the trace TXT is the most
useful artefact.

## BUILD_PON entry workflow

To build a panel-of-normals, run with `-entry BUILD_PON`:

```bash
nextflow run . -entry BUILD_PON \
    --input /path/to/normals.csv \
    --reference /path/to/hg38_masked.fasta \
    --bed /path/to/panel.bed \
    --outdir /path/to/pon_run \
    -profile <yoursite>,singularity \
    -resume
```

Samplesheet format for `BUILD_PON` adds an optional `exclude` column
to mark normals to skip after leave-one-out QC. See
[`docs/usage_pon.md`](usage_pon.md) for the full walkthrough.

Outputs:

- `${outdir}/pon/cnvkit_pon_male.cnn`, `cnvkit_pon_female.cnn`,
  `cnvkit_pon_sex_assignment.tsv`, `loo_qc/`
- `${outdir}/references/<panel>/cnvkit_loo_summary.tsv`,
  `cnvkit_noisy_bins.bed`

Wire them into `TSPIPE` either by copying them into `assets/<panel>/`
in the repo, or by passing `--cnv_pon_male`, `--cnv_pon_female`,
`--cnv_loo_summary`, `--cnv_noise_profile`, `--cnv_noisy_bins`
explicitly.

## Output

The clinical deliverable tree is at
`${outdir}/<sample>/clinical/`. Full layout, intermediate stages, and
the BUILD_PON output layout are in [`docs/output.md`](output.md).

## Troubleshooting

For installation-time issues (VV REST stack, missing fixtures,
cross-filesystem hardlink errors), see
[`docs/INSTALL.md#troubleshooting`](INSTALL.md#troubleshooting). For
the known FLT3_ITD_EXT failure on FLT3-ITD-negative specimens, see
the same section.
