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


## Reference data formats

### SNV blacklist (`params.snv_blacklist`)

The SNV blacklist is a tab-separated file of variants that should be
flagged but not dropped. The annotation step (`bin/14_variant_filter.py`,
invoked from the variant-filter module) reads it and sets
`FILTER=BLACKLIST` on any matching variant. Matching variants remain in
the output for audit; they are not removed.

The format is a hybrid: most columns use BED-style 0-based half-open
coordinates, but the optional exact-match columns use 1-based VCF-style
coordinates. The split exists so each row can encode either a region
("any indel overlapping this window") or an exact substitution. Mind
the coordinate convention when adding rows.

#### Columns

| Column        | Required | Coord. base    | Description                                                                                                                |
|---------------|----------|----------------|----------------------------------------------------------------------------------------------------------------------------|
| `chrom`       | always   | -              | UCSC-style contig name with `chr` prefix, hg38. Example: `chr17`.                                                          |
| `start`       | always   | **0-based**    | Inclusive start of the region to match. BED-style.                                                                         |
| `end`         | always   | **0-based**    | Exclusive end of the region to match. BED-style.                                                                           |
| `match_mode`  | always   | -              | One of: `region_indel`, `exact`. See *Match modes* below.                                                                  |
| `pos_exact`   | exact only | **1-based**  | VCF-style position. Use `.` when `match_mode=region_indel`.                                                                 |
| `ref_exact`   | exact only | -              | REF allele. Use `.` when `match_mode=region_indel`.                                                                         |
| `alt_exact`   | exact only | -              | ALT allele. Use `.` when `match_mode=region_indel`.                                                                         |
| `gene`        | always   | -              | Gene symbol. Audit-only; not used for matching. Helps reviewers grep the file.                                              |
| `reason`      | always   | -              | One of: `ARTIFACT`, `POLYMORPHISM`, `RECURRENT_FP`. See *Reason vocabulary* below.                                          |
| `evidence`    | always   | -              | Free-text justification. Include sample IDs, LOVD identifiers, frequency in cohort, or anything else the next reviewer needs to re-evaluate the entry. |
| `date_added`  | always   | -              | ISO date (`YYYY-MM-DD`).                                                                                                    |

Comment lines start with `#` or `##`. Lines starting with `##` are
schema-documentation comments; lines starting with `#` (single hash)
are typically commented-out placeholder rows pending coordinate
resolution (see *Adding a placeholder*).

#### Match modes

- **`region_indel`** — flag any insertion, duplication, or deletion
  whose variant locus overlaps the half-open interval `[start, end)`.
  Use this for polyproline tracts, polynucleotide runs, and other
  recurrent-indel sites where the exact offset varies between callers.
  The `*_exact` columns should be `.`.

- **`exact`** — flag a variant only when `(chrom, pos_exact, ref_exact,
  alt_exact)` matches exactly. Use this for specific recurrent
  substitutions identified as artefacts or common polymorphisms. The
  `start` and `end` columns are still required (they should bracket
  the position) but `pos_exact / ref_exact / alt_exact` carry the
  actual match logic.

#### Reason vocabulary

- **`ARTIFACT`** — sequencing or alignment artefact (homopolymer
  slippage, paralog collapse not handled by the masked reference,
  polyproline-tract dup/del, 8-oxoG hotspots, etc.). Not real biology.
- **`POLYMORPHISM`** — common germline variant that recurs in the
  cohort and has been clinically reviewed as not actionable.
- **`RECURRENT_FP`** — recurrent false positive in the ensemble that
  doesn't fit cleanly into the first two categories (e.g. a
  consistently mis-aligned region that produces calls in one caller
  but no others).

#### Adding a new entry

Two cases.

**Case 1: a recurrent region you want to flag (region_indel).** You
have the contig and the genomic window; you don't need a specific
ALT. Example workflow:

1. Identify the region from the audit observation (sample ID, gene,
   coordinates from VEP output).
2. Convert any 1-based coordinates you have to 0-based half-open for
   the `start` / `end` columns. (Subtract 1 from a 1-based start; the
   1-based end is already the half-open exclusive end.)
3. Add the row with `match_mode=region_indel` and `.` for the three
   `*_exact` columns.
4. Populate `evidence` with sample IDs and any external identifiers
   (LOVD, ClinVar) you used.

**Case 2: a specific recurrent substitution (exact).** You have a
variant you've seen multiple times in cohort review.

1. Pull the exact `CHROM`, `POS`, `REF`, `ALT` from a VEP-annotated
   TSV for the affected sample. These are 1-based VCF-style and go
   into `pos_exact / ref_exact / alt_exact`.
2. Pick a small window around the position for the `start` / `end`
   columns (`pos_exact - 1` and `pos_exact`, in 0-based half-open
   terms, is sufficient).
3. Set `match_mode=exact`.
4. Same evidence and date-added requirements.

#### Adding a placeholder

When an audit flags a variant but you don't yet have the exact hg38
coordinates from a VEP TSV (because the affected sample needs to be
re-annotated, or because the audit happened off-platform), drop a
commented row at the bottom of the file so the next reviewer has the
context:

```
# --- placeholders requiring confirmation; do NOT enable until coordinates verified ---
# Pull from a VEP-annotated TSV for the affected sample and replace the '.' fields, then remove the leading '#'.
#chr17  .       .       exact   .       .       .       KDM6B   ARTIFACT        <evidence with sample IDs>      <date>
```

When the coordinates land, fill in `start`, `end`, `pos_exact`,
`ref_exact`, `alt_exact` and uncomment the row.

#### Filter behaviour

`bin/14_variant_filter.py` sets `FILTER=BLACKLIST` on any variant that
matches a row in this file. Matching variants are **kept**, not
dropped. The intent is that downstream clinical review can see what
was flagged and why, and can revisit the entry if the call turns out
to be real biology after all. Removal would be lossy and would break
audit trails; do not change this convention without a clinical-safety
review.

#### Cross-references

- [`docs/clinical_decisions.md`](clinical_decisions.md) — the
  blacklist is part of the conservative-by-default filtering strategy.
- The schema is also documented inline in the
  `##`-prefixed header of the TSV itself; the two should stay in
  sync. If you edit one, mirror the change to the other.
