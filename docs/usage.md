# Usage

## Prerequisites

- Nextflow >= 23.04
- Either Docker, Singularity, or Conda for tool environments
- Reference resources built by `assets/training/` (see that directory's README)

## Quick start

```bash
nextflow run main.nf \
    --input samplesheet.csv \
    --reference references/hg38_broad/Homo_sapiens_assembly38.masked.fasta \
    --bed bedfiles/MYOPOOL_240125_UBTF_hg38.bed \
    --cnv_pon references/cnvkit_pon/pon_reference.cnn \
    --snv_blacklist references/blacklist_snvs_hg38.tsv \
    --outdir results \
    -profile docker
```

## Samplesheet format

A CSV with header `sample,fastq_1,fastq_2,sex`:

```csv
sample,fastq_1,fastq_2,sex
25NGS1307,/data/25NGS1307_R1.fastq.gz,/data/25NGS1307_R2.fastq.gz,unknown
26CGH40,/data/26CGH40_R1.fastq.gz,/data/26CGH40_R2.fastq.gz,female
```

`sex` is optional (defaults to `unknown`) and is used downstream by the CNV step
to pick the sex-matched PoN. The columns replace what `run_sample_pipeline.py`
used to derive from filename pattern-matching in a fastq directory.

## Parameters

All parameters can be set on the command line (`--param value`) or in a config
file. Key ones:

| param | required | description |
| ----- | -------- | ----------- |
| `--input` | yes | Path to samplesheet CSV |
| `--outdir` | yes | Where results go (one subfolder per sample) |
| `--reference` | yes | hg38 masked FASTA. Must have `.fai` and `.dict` alongside |
| `--bed` | yes | Panel BED file |
| `--pindel_bed` | no | Subset BED for Pindel; defaults to `--bed` |
| `--adapters` | no | Illumina adapter FASTA (defaults to fastp's auto-detect) |
| `--cnv_pon` | for CNV | CNVKit panel-of-normals `.cnn` file |
| `--cnv_loo_summary` | for CNV | LOO summary TSV from `cnv_loo_qc.py` |
| `--cnv_noise_profile` | for CNV | Per-bin noise profile TSV |
| `--cnv_noisy_bins` | no | BED of bins to exclude from CNV calls |
| `--snv_blacklist` | no | TSV of recurrent SNV/indel artifacts; defaults empty |
| `--vep_cache` | for annotation | VEP cache directory |
| `--annovar_db` | for annotation | ANNOVAR humandb directory |
| `--flt3_container` | no | `docker` or `singularity` (default: docker) |
| `--max_memory`, `--max_cpus`, `--max_time` | no | Resource caps |

## Profiles

- `-profile docker` — uses Docker for all containerized steps
- `-profile singularity` — uses Singularity (recommended on HPC)
- `-profile conda` — uses Conda environments (slowest, most fragile)
- `-profile slurm` — uses SLURM for process execution
- `-profile test` — minimal smoke test, mostly for CI

Profiles can be combined: `-profile slurm,singularity`.

## Resuming

Nextflow caches every successful process. If a run dies partway through, just
re-run the same command with `-resume`:

```bash
nextflow run main.nf ... -resume
```

This replaces the `--skip-from N` flag from the old Python runner -- you no
longer have to remember which step you got to.

## Running a subset of samples

Filter the samplesheet, or use Nextflow's `--input` with a smaller CSV. There's
no need for the old `--samples 25NGS1307 26CGH40` flag.

## Output layout

See `docs/output.md`.
