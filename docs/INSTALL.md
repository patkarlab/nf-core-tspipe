# nf-core-tspipe — installation

A targeted-sequencing pipeline for myeloid leukaemia panels, built on
Nextflow and following nf-core conventions. This document walks a
bioinformatician through standing the pipeline up from the GitHub
repository on a Linux host, configuring it for a new site, and
running it on a real sample.

For operational reference once the pipeline is installed, see
`docs/usage.md` (parameters), `docs/output.md` (output tree), and
`docs/usage_pon.md` (panel-of-normals build). For the gandalf-flavoured
move-from-here checklist, see `docs/deployment.md`.

## Pipeline summary

Per sample, in order:

1. **Preprocessing** — fastp adapter trim → bwa-mem2 align → Picard
   MarkDuplicates → GATK4 BQSR → ABRA2 indel realignment
2. **QC** — Picard HsMetrics + mosdepth per-exon coverage + a fastp/QC
   summary dashboard
3. **Variant calling** — 8 callers in parallel (Mutect2, VarDict,
   VarScan, Strelka2, FreeBayes, Platypus, Pindel, DeepSomatic) plus a
   U2AF1 paralog-rescue pass
4. **SomaticSeq ensemble** — 8-caller consensus
5. **FLT3-ITD ensemble** — 4 callers (FLT3_ITD_EXT, Pindel-region,
   filt3r, getITD) with a consensus TSV
6. **CNV calling** — CNVKit with sex-stratified PoN, z-score, plots,
   concordance with the LOO PoN, and an annotated clinical TSV
7. **Annotation** — VEP + ANNOVAR → variant filter (against a curated
   blacklist) → VariantValidator HGVS verification → OncoVI
   oncogenicity scoring
8. **IGV reports** — per-sample HTML pileup viewer for clinical review
9. **Organise output** — assembles `<sample>/clinical/` for sign-out

Two entry workflows live in `main.nf`:

- `TSPIPE` (default) — the per-sample analysis above
- `BUILD_PON` — one-off panel-of-normals construction (see
  `docs/usage_pon.md`)

## Quick start

For a reader who already has Nextflow, Singularity, Docker, and a
reference tree:

```bash
# 1. Clone
git clone git@github.com:patkarlab/nf-core-tspipe.git
cd nf-core-tspipe

# 2. Copy the template site config and edit it
cp conf/site_template.config conf/mysite.config
$EDITOR conf/mysite.config            # set paths for your server

# 3. Register the profile in nextflow.config (add a mysite { ... } block)

# 4. Bring up the VariantValidator REST stack (see section "VariantValidator
#    REST stack" below; required for the annotation pipeline)
cd /path/to/rest_variantValidator && docker compose up -d

# 5. Build a samplesheet
tools/make_samplesheet.sh /path/to/fastq_dir --output /tmp/today.csv

# 6. Run
nextflow run . \
    --input /tmp/today.csv \
    --outdir /data/nfcore_runs/$(date +%Y%m%d_%H%M%S) \
    -profile mysite,singularity \
    -resume
```

The rest of this document expands each of those steps.

---

## Prerequisites

### Hardware

Sized against the 2026-05-19 16-sample validation run on gandalf
(2 h 19 min wall time, full pipeline, all stages):

| Resource | Minimum (16 samples) | Tested (gandalf) |
|---|---|---|
| CPU cores | 32 | 192 |
| RAM | 128 GB | 1.5 TB |
| Output filesystem free space | 25 GB × samples | 760 GB free |
| Singularity image cache | 30–50 GB (one-time) | — |

The pipeline scales linearly at the sample boundary. With
`executor.queueSize ≥ samples`, wall time approaches single-sample
runtime.

### Software

| Component | Tested on gandalf | Minimum |
|---|---|---|
| Operating system | Rocky Linux 9.6 (kernel 5.14, glibc 2.34) | RHEL-family 9.x or equivalent; Debian/Ubuntu likely works |
| bash | 5.1.8 | 4.x |
| Java | OpenJDK 23.0.2-internal | Java 21 LTS recommended (Nextflow 25.10 supports 17 / 21) |
| Nextflow | 25.10.4 | 25.10.4 |
| Singularity / Apptainer | singularity-ce 4.3.2-1.el9 | 4.x recommended, 3.8+ minimum |
| Docker | 28.3.3 | 20.10+ (required for the VV REST stack) |
| Docker Compose | v2.39.1 | v2.x (compose plugin, not legacy `docker-compose`) |
| Python 3 | 3.13.11 (host) / 3.10.14 (conda env) | 3.10+ for the conda env |
| Git | 2.51.0 | 2.x |

Docker and Singularity coexist on the same host: Singularity launches
Nextflow process containers; Docker hosts the VV REST stack.

Install Nextflow if it is not already present:

```bash
curl -s https://get.nextflow.io | bash
sudo mv nextflow /usr/local/bin/
nextflow -version
```

### Network endpoints

Outbound network is required at install time and intermittently at
runtime. For air-gapped sites, see "Pre-pulling images" below.

| Endpoint | When |
|---|---|
| `get.nextflow.io` | Nextflow installer (one-time) |
| `quay.io/biocontainers/*` | Singularity image pulls on first run |
| `docker.io/{broadinstitute,google,lethalfang}/*` | Singularity image pulls on first run |
| `cdn.jsdelivr.net` | igv.js, loaded by per-sample IGV HTML at view time |
| Ensembl, NCBI, Broad mirror | VEP cache, ANNOVAR DBs, dbSNP/Mills/gnomAD VCFs (one-time) |

The IGV report HTML is the only network dependency at clinical
review time — every reviewer's browser needs jsdelivr access.

---

## Get the pipeline

```bash
git clone git@github.com:patkarlab/nf-core-tspipe.git
cd nf-core-tspipe
git checkout main
```

The repository is currently private. There are no git submodules and
no tagged releases as yet; the head of `main` is the working
baseline. The current commit is `dd0a3c6`.

### Pin a commit for reproducibility

Until releases are tagged, pin a specific commit SHA when running:

```bash
git checkout <commit-sha>
```

and record that SHA alongside the run's `pipeline_info/` directory.
Nextflow reports the working tree state to
`pipeline_info/execution_report_<timestamp>.html`.

### Panel-of-normals and panel assets

The repo ships six panel-specific files under `assets/myeloid/`,
git-tracked:

```
assets/myeloid/cnvkit_pon_male.cnn        1.8 MB
assets/myeloid/cnvkit_pon_female.cnn      1.8 MB
assets/myeloid/cnvkit_loo_summary.tsv      10 KB
assets/myeloid/cnvkit_noisy_bins.bed      812 KB
assets/myeloid/loo_bin_noise_profile.tsv  1.7 MB
assets/myeloid/cnv_scatter_regions.txt     43 KB
```

For sites running this myeloid panel as-is, these are usable
out-of-the-box. For sites running a different panel, regenerate them
via the `BUILD_PON` workflow (see `docs/usage_pon.md`) and
`tools/regenerate_cnv_scatter_regions.py` from the production tree.

The repo also ships under `assets/references/`:

```
assets/references/cytoBand_hg38.txt
assets/references/ClinGen_gene_curation_list_GRCh38.tsv
```

These are reference-genome-tied, not panel-tied, and rarely need
updating.

---

## Reference data

Beyond what ships in the repo, the pipeline reads ten external files
or directories. All are bound to Nextflow parameters that can be set
on the command line or in your site config.

| Parameter | What | Source | Approximate size |
|---|---|---|---|
| `--reference` | hg38 masked FASTA + `.fai` + `.dict` + bwa-mem2 index | Broad Institute hg38 bundle, then locally masked (see `docs/clinical_decisions.md` for masking rationale) | 3.1 GB FASTA |
| `--bed` | Panel BED | Ships under `bedfiles/` (gandalf path: `${pipeline_root}/bedfiles/MYOPOOL_240125_UBTF_hg38.bed`) | 264 KB |
| `--exonwise_bed` | Exon-collapsed BED for mosdepth | Same source as `--bed` | 100 KB |
| `--pindel_bed` | Pindel target subset (FLT3 + UBTF) | Ships at `references/pindel_targets_flt3_ubtf.bed` in the repo | <1 KB |
| `--adapters` | Illumina adapter FASTA | Standard Illumina | <1 KB |
| `--dbsnp_vcf` (+ `.tbi`) | dbSNP for BQSR + SomaticSeq | Broad bundle | ~10 GB |
| `--mills_vcf` (+ `.tbi`) | Mills indel gold-standard for BQSR | Broad bundle | ~100 MB |
| `--gnomad_af_only` (+ `.tbi`) | gnomAD AF-only for Mutect2 germline filter | Broad bundle | ~4 GB |
| `--vep_cache` | Ensembl VEP cache | VEP installer | ~25 GB |
| `--annovar_script` + `--annovar_db` | ANNOVAR perl entrypoint + `humandb/` directory | ANNOVAR upstream (licensed) | 50–200 GB |
| `--snv_blacklist` | Hand-curated SNV/indel artefact TSV | Site-curated; gandalf has a starter at `${pipeline_root}/references/blacklist_snvs_hg38.tsv` | small |

`workflows/tspipe.nf` validates `--input`, `--reference`, `--bed`,
and `--exonwise_bed` at workflow start. All other paths default from
the active site config.

### Building reference indexes

The pipeline uses **bwa-mem2**, not classic bwa — the index files
differ. After downloading the FASTA:

```bash
REF=/path/to/Homo_sapiens_assembly38.masked.fasta
samtools faidx $REF
gatk CreateSequenceDictionary -R $REF
bwa-mem2 index $REF
```

This produces `<ref>.fai`, `<ref>.dict`, and the five bwa-mem2 index
files (`.amb`, `.ann`, `.pac`, `.bwt.2bit.64`, `.0123`).
`subworkflows/local/preprocessing.nf:29-35` looks for these
specifically; classic-bwa indexes will not work.

For each VCF, ensure its `.tbi` index sits alongside:

```bash
tabix -p vcf <vcf.gz>
```

### Downloading the Broad bundle

The dbSNP, Mills, and gnomAD VCFs are part of the Broad's hg38
resource bundle. On a fresh server:

```bash
gsutil -m cp 'gs://genomics-public-data/references/hg38/v0/Homo_sapiens_assembly38.dbsnp138.vcf*' /data/refs/
gsutil -m cp 'gs://genomics-public-data/references/hg38/v0/Mills_and_1000G_gold_standard.indels.hg38.vcf.gz*' /data/refs/
gsutil -m cp 'gs://genomics-public-data/references/hg38/v0/af-only-gnomad.hg38.vcf.gz*' /data/refs/
```

Alternatively, `rsync` from gandalf if you have access (see
`docs/deployment.md` for the rsync recipe).

### VEP cache

Use the VEP `INSTALL.pl` to fetch the cache matching the VEP version
shipped in your active container. The pipeline does not pin a VEP
version explicitly; check the container catalogue (below) and align.

### ANNOVAR

ANNOVAR is license-bound and not redistributable. Obtain it from
the upstream maintainers, then download the databases your panel
needs (`refGene`, `cosmic`, `clinvar`, etc.) into the directory
pointed at by `--annovar_db`.

### Helper scripts under `assets/training/`

The repo ships two download helpers that simplify the steps above
when you have outbound network access from the install host:

| Script | What it fetches |
|---|---|
| `assets/training/download_hg38_resources.sh` | Broad hg38 FASTA + dbSNP + Mills + gnomAD VCFs |
| `assets/training/download_annovar_db.sh` | ANNOVAR databases (post-install, after you have the ANNOVAR perl install) |

Read each script before running — they write to paths under the
caller's working directory. For sites doing a full reference rebuild
(rare; only needed when retargeting the hg38 masking strategy),
`assets/training/run_masked_realign.sh` regenerates the masked
reference from the unmasked Broad bundle.

The four older PoN-building scripts in the same directory
(`build_sex_pon.py`, `build_sex_matched_pons.sh`, `cnv_loo_qc.py`,
`run_masked_realign_cnv_negatives.sh`) are superseded by the
`BUILD_PON` Nextflow workflow described in `docs/usage_pon.md`. Use
the workflow rather than the bash scripts for new PoN builds.

---

## Site configuration

Two configs ship in `conf/` that are relevant to a new install:

- **`conf/site_template.config`** — purpose-built starting point for a
  new server. Has placeholder paths, sensible conservative defaults
  (`max_cpus=16`, `max_memory=128.GB`), and walks through both
  containers-only (Strategy A) and local-install (Strategy B)
  configurations as commented blocks. This is what to copy.
- **`conf/gandalf.config`** — the working site config for the
  development host. Useful as a reference example (sized for
  192 cores / 1.5 TB, with the local-install Strategy B fully wired
  up), but not what you want to copy verbatim onto a new server.

To create a new site config:

```bash
cp conf/site_template.config conf/mysite.config
$EDITOR conf/mysite.config
```

Register the new profile in `nextflow.config` `profiles { ... }`:

```groovy
profiles {
    ...
    mysite {
        includeConfig 'conf/mysite.config'
    }
}
```

The placeholder paths in `site_template.config` are grouped by purpose,
each with a `// ----` comment header. Fill in each block in order:

| Block | What to set |
|---|---|
| Root directory | `pipeline_root` — base for your `references/`, `bedfiles/`, `software/` subtrees |
| Reference + panel | `reference`, `bed`, `exonwise_bed`, `pindel_bed`, `adapters` |
| Broad-bundle VCFs | `dbsnp_vcf`, `mills_vcf`, `gnomad_af_only` (with their `.tbi` indexes alongside) |
| Annotation databases | `vep_cache`, `annovar_script`, `annovar_db` |
| SNV blacklist | `snv_blacklist` — optional, defaults to no blacklist filtering |
| CNV resources | Leave commented out unless overriding the shipped `assets/<panel>/` PoN |
| Annotation references | Leave commented out unless overriding the shipped `assets/references/` files |
| FLT3 ensemble | `flt3_container` — `'singularity'` or `'docker'` to match your runtime |
| Resource ceilings | `max_memory`, `max_cpus`, `max_time` — `check_max()` in `conf/base.config` clamps requests at these |
| Executor envelope | `executor { cpus, memory, queueSize }` — should match your hardware |
| Container runtime | Leave `singularity { ... }` enabled; flip to `docker { enabled = true }` and disable singularity if Docker is your runtime |

For a worked example, see `conf/gandalf.config` — the local-install
Strategy B is fully wired there (conda envs, per-process tool-path
overrides for VARDICT/STRELKA/PLATYPUS/GETITD/FILT3R).

### Conda-on-host vs all-containers

`conf/site_template.config` ships as Strategy A (containers-only) by
default: every module's `container` directive is picked up by
Singularity (or Docker), and there is no `process.beforeScript` or
host-path machinery. **This is the recommended path for a new site.**

If your host already has the conda envs installed (the
`targeted-seq` env with fastp, bwa-mem2, samtools, gatk4, abra2,
cnvkit, freebayes, vardict, varscan, somaticseq, plus a py2 env for
Strelka and Platypus), Strategy B is faster on first run because no
containers need to be pulled. To switch to Strategy B in your site
config:

- Uncomment the `conda { enabled = false }`, `env { ... }`, and
  `process { ... }` block at the bottom of `site_template.config`.
- Fill in the conda env paths and the per-tool helper paths
  (`vardict_helpers_dir`, the FLT3 `getitd_path` / `filt3r_bin` /
  `filt3r_ref` ext-vars).

Reference: `conf/gandalf.config` is a complete Strategy B example.

### Modules that genuinely need host execution

Three modules cannot be containerised today and must run on host:

| Module | Why |
|---|---|
| `VARIANT_VALIDATOR` | Needs to reach `http://localhost:5001` (the VV REST stack) |
| `ONCOVI` | Needs `${pipeline_root}/software/oncovi/` on the host filesystem |
| `FLT3_TO_VARIANTS` | Grouped with the above for consistency |

`conf/modules.config:278-284` pins these three to `executor =
'local'`. They invoke three scripts from the production
`targeted-seq-pipeline` tree:

```
${TARGETED_SEQ_ENV}/bin/python
${PRODUCTION_TREE}/scripts/15_oncovi.py
${PRODUCTION_TREE}/scripts/17_variant_validator.py
${PRODUCTION_TREE}/scripts/17b_flt3_to_variants.py
```

`tools/run_pipeline.sh:120-128` checks all four paths in preflight.
The launcher's hardcoded path is `/home/hemat/targeted-seq-pipeline/`,
which on gandalf is a symlink resolving to
`/goast/hemat_data/targeted-seq-pipeline`. On a new server, either
clone the production tree and recreate the symlink, or edit the
launcher to point at your install location.

The pipeline cannot complete without these three modules; building
a containerised replacement is a known TODO at
`conf/modules.config:277`.

---

## VariantValidator REST stack

Required for the annotation pipeline. The stack is a four-container
Docker Compose project that lives in the production tree at
`${pipeline_root}/software/rest_variantValidator/`. The compose
file's canonical contents:

| Service | Built from | Host:container ports | Notes |
|---|---|---|---|
| `rv-vdb` | `db_dockerfiles/vdb/Dockerfile` | `33061:3306` | MySQL (VDB) |
| `rv-vvta` | `db_dockerfiles/vvta/Dockerfile` | `54322:5432` | PostgreSQL (VVTA), `shm_size: 2g` |
| `rv-seqrepo` | `db_dockerfiles/seqrepo/Dockerfile` | (internal) | seqrepo sequence server |
| `rest-variantvalidator` | repo root `Dockerfile` | `5001:5000`, `5050:5050`, `8000:8000`, `9000:9000` | REST API frontend. Entrypoint is `bash -c "sleep infinity"` — gunicorn is launched into it manually (see below). |

Volumes:

| Volume | Type | Backs | Host path |
|---|---|---|---|
| `vvta-data` | named docker volume | `/var/lib/postgresql/data` in `rv-vvta` | docker-managed |
| `vdb-data` | named docker volume | `/var/lib/mysql` in `rv-vdb` | docker-managed |
| `seqdata` | bind mount | shared by `rv-seqrepo` and `rest-variantvalidator` | `/home/hemat/variantvalidator_data/seqdata` |
| `vv-logs` | bind mount | `/usr/local/share/logs` in `rest-variantvalidator` | `/home/hemat/variantvalidator_data/logs` |

**Named volumes are non-optional.** The pre-2026-05-19 setup used
anonymous Docker volumes which orphaned silently on `docker compose
down` cycles, causing data loss (see
`docs/audit/2026-05-19/morning_findings.md` for the migration record).
Do not run `docker compose down -v` or `docker volume prune` against
this project.

### Standing the stack up on a new server

```bash
# 1. Copy the compose project from gandalf (or wherever you maintain it)
cp -r /goast/hemat_data/targeted-seq-pipeline/software/rest_variantValidator \
      /opt/rest_variantValidator

# 2. Create the bind-mount host directories (adjust paths in compose
#    yaml if your site uses different ones)
sudo mkdir -p /home/hemat/variantvalidator_data/{seqdata,logs}
sudo chown -R hemat:hemat /home/hemat/variantvalidator_data

# 3. Restore the two database volumes from tarballs
docker volume create rest_variantvalidator_vvta-data
docker volume create rest_variantvalidator_vdb-data

docker run --rm \
    -v rest_variantvalidator_vvta-data:/target \
    -v /path/to/vv_backups:/backup \
    alpine sh -c 'cd /target && tar xzf /backup/vvta_data.tgz'

docker run --rm \
    -v rest_variantvalidator_vdb-data:/target \
    -v /path/to/vv_backups:/backup \
    alpine sh -c 'cd /target && tar xzf /backup/vdb_data.tgz'

# 4. Bring up the stack
cd /opt/rest_variantValidator
docker compose up -d --remove-orphans

# 5. Wait for postgres/mysql, then launch gunicorn inside the REST
#    container. Use 1 worker x 5 threads; 3-worker boots fail with
#    100% CPU during VV library initialization.
sleep 20
docker exec -d rest_variantvalidator-rest-variantvalidator-1 \
    gunicorn -b 0.0.0.0:5000 --workers 1 --threads 5 --timeout 600 \
    wsgi:app --chdir ./rest_VariantValidator/

# 6. Wait for VV library init, then health-check
sleep 90
curl -i -m 60 \
    "http://localhost:5001/VariantValidator/variantvalidator/GRCh38/NM_000088.4%3Ac.589G%3ET/all" \
    | head -10
```

Expect HTTP 200 with JSON for COL1A1 annotations. The compose maps
host port 5001 to container port 5000; the nf-core port hardcodes
`http://localhost:5001` in `modules/local/variant_validator.nf`. Both
ports are part of the install contract.

Database tarballs are produced by the gandalf maintainer; current
location on gandalf is `/goast/hemat_data/vv_migration_20260519/`.
Sizes: ~876 MB compressed for VVTA (4 GB raw), ~81 MB for VDB
(713 MB raw).

### Bind-mount paths and sudo

The compose file hardcodes the seqdata and vv-logs bind paths under
`/home/hemat/variantvalidator_data/` because `$HOME` resolves to
`/root` when compose is run via sudo. On a new server, either keep
the same path (create `/home/hemat/...` even if your user is
different) or hardcode your own absolute paths into the compose file
before `docker compose up`.

---

## Container catalogue

The pipeline uses 12 distinct container images (9 pulled from
public registries; 3 locally built):

| Image | Used by |
|---|---|
| `broadinstitute/gatk:4.5.0.0` | GATK4_BQSR, GATK4_MUTECT2, HSMETRICS, SOMATICSEQ_POSTPROCESS, PARSE_EXON_COVERAGE |
| `google/deepsomatic:1.10.0` | DEEPSOMATIC |
| `lethalfang/somaticseq:3.7.4` | SOMATICSEQ_ENSEMBLE |
| `quay.io/biocontainers/bcftools:1.20--h8b25389_0` | bcftools-based steps |
| `quay.io/biocontainers/cnvkit:0.9.10--pyhdfd78af_0` | CNVKIT and the four pandas-bearing CNV modules |
| `quay.io/biocontainers/fastp:0.23.4--h5f740d0_0` | FASTP |
| `quay.io/biocontainers/igv-reports:1.12.0--pyh7cba7a3_0` | IGV_REPORTS |
| `quay.io/biocontainers/mosdepth:0.3.10--h4e814b3_1` | MOSDEPTH |
| `quay.io/biocontainers/samtools:1.18--h50ea8bc_1` | samtools steps |
| `local/filt3r:v0.1` | FILT3R |
| `local/getitd:v0.1` | GETITD |
| `local/flt3_itd_ext:v0.2` | FLT3_ITD_EXT (overlays `zhkddocker/flt3_itd_ext:v1.1` with a wrapper script) |

The three `local/*` images need to be available before the FLT3-ITD
ensemble can run. Quickest path on a new server is `docker save` on
gandalf → `docker load` on the new host:

```bash
# On gandalf
docker save local/filt3r:v0.1 local/getitd:v0.1 local/flt3_itd_ext:v0.2 \
    | gzip > flt3_images.tar.gz

# On the new server (after copying)
gunzip -c flt3_images.tar.gz | docker load

# Then convert to SIF for Singularity
mkdir -p $SINGULARITY_CACHEDIR
for img in filt3r:v0.1 getitd:v0.1 flt3_itd_ext:v0.2; do
    singularity build $SINGULARITY_CACHEDIR/local-${img/:/-}.sif \
        docker-daemon://local/$img
done
```

### Pre-pulling remote images

By default Nextflow pulls images on first run. To pre-pull (useful
for air-gapped sites or to remove first-run latency):

```bash
mkdir -p $SINGULARITY_CACHEDIR
grep -rhE "container\s+'" modules/local/*.nf \
    | sed -E "s/.*container\s+'([^']+)'.*/\1/" | sort -u \
    | grep -v '^local/' \
    | while read img; do
        singularity pull --dir $SINGULARITY_CACHEDIR docker://${img#docker://}
      done
```

Total cache size after pulling everything is typically 25–40 GB. Set
`singularity.cacheDir` in your site config to a persistent, roomy
filesystem.

---

## Samplesheet

The pipeline reads a CSV samplesheet validated against
`assets/schema_input.json`:

```csv
sample,fastq_1,fastq_2,sex
25NGS1307,/data/fastqs/25NGS1307_R1.fastq.gz,/data/fastqs/25NGS1307_R2.fastq.gz,unknown
26CGH40,/data/fastqs/26CGH40_R1.fastq.gz,/data/fastqs/26CGH40_R2.fastq.gz,female
25NGS336,/data/fastqs/25NGS336_R1.fastq.gz,/data/fastqs/25NGS336_R2.fastq.gz,male
```

Rules:

- `sample` — no whitespace, required.
- `fastq_1`, `fastq_2` — required, must end in `.fq.gz` or
  `.fastq.gz`, paths must resolve from where Nextflow runs.
- `sex` — one of `male`, `female`, `unknown`. Defaults to `unknown`.
  Drives CNV PoN selection downstream: `male` uses
  `cnvkit_pon_male.cnn`, `female` uses `cnvkit_pon_female.cnn`,
  `unknown` falls back to the female PoN with a `log.warn`.

### Building one

`tools/make_samplesheet.sh` scans a FASTQ directory and emits a CSV.
It handles two naming conventions on gandalf (sequencer-style and
stripped-style):

```bash
tools/make_samplesheet.sh /path/to/fastq_dir \
    --output /tmp/today.csv \
    --exclude 25NGS336,26CGH14 \
    --min-size 500 \
    --sex 25NGS1307=male,26CGH40=female
```

- `--exclude` — skip the listed sample IDs.
- `--min-size MB` — skip samples whose R1 is smaller than the
  threshold (defends against truncated uploads).
- `--sex ID=value` — override per-sample sex (default is `unknown`).

For the `BUILD_PON` workflow, samplesheets take one extra column
(`exclude`) — see `docs/usage_pon.md`.

---

## Running the pipeline

### Direct invocation

```bash
cd /path/to/nf-core-tspipe
nextflow run . \
    --input /tmp/today.csv \
    --outdir /data/nfcore_runs/$(date +%Y%m%d_%H%M%S) \
    -profile mysite,singularity \
    -resume
```

Profiles compose left-to-right. `mysite` brings paths and host-tuned
resources; `singularity` selects the container runtime.

### Production launcher

`tools/run_pipeline.sh` is the production wrapper. It prompts for
inputs, runs preflight checks, launches Nextflow in the background
with `nohup`, and writes a PID file so the run survives SSH
disconnect.

```bash
tools/run_pipeline.sh
```

Env variables that override the defaults:

| Variable | Default | Purpose |
|---|---|---|
| `TSPIPE_REPO` | `/goast/hemat_data/nf-core-tspipe` | Repo location |
| `TSPIPE_SAMPLES` | (prompt) | Samplesheet CSV path |
| `TSPIPE_PROFILE` | `gandalf,singularity` | Nextflow `-profile` string |
| `TSPIPE_OUTDIR_BASE` | `/goast/hemat_data/nfcore_runs` | Parent of per-run output dirs |
| `TSPIPE_SKIP_PREFLIGHT` | `0` | Set to `1` to skip preflight (not recommended) |

Preflight checks (run unless `TSPIPE_SKIP_PREFLIGHT=1`):

1. Samplesheet exists and has at least one data row.
2. Every FASTQ in the samplesheet exists on disk.
3. No other `nextflow ... tspipe` run is active.
4. VV REST: 4 containers up AND `http://localhost:5001` returns HTTP 200.
5. The four host-side paths (conda Python + three production
   scripts) are present.
6. Output filesystem has at least `samples × 25 GB` free (warns, does
   not abort).

Extra Nextflow flags forward verbatim after the script's own
prompts: `tools/run_pipeline.sh -stub -resume` works.

### Profiles

| Profile | Sets | When to use |
|---|---|---|
| `gandalf` | gandalf-specific paths and conda-on-host shortcut | On gandalf only |
| `<yoursite>` | Your site config | Any other server |
| `singularity` | `singularity.enabled=true` | Production runtime |
| `docker` | `docker.enabled=true` | Workstation, or no Singularity |
| `slurm` | `process.executor='slurm'` | SLURM cluster |
| `conda` | `conda.enabled=true` | Slowest, most fragile; not recommended |

Combine site + runtime: `-profile mysite,singularity` or
`-profile mysite,slurm,singularity`.

There is also a `test` profile, but it references missing
`assets/test/` fixtures and is broken. Use `gandalf,singularity -stub`
(or `mysite,singularity -stub`) for structural validation instead.

### Resuming and stubbing

- `-resume` reuses cached process outputs. Always safe.
- `-stub` runs every process with its `stub:` block (touches outputs,
  emits placeholder versions). Useful for topology validation
  without exercising real tools.

### BUILD_PON entry workflow

Run once per panel/reference combination:

```bash
nextflow run . -entry BUILD_PON \
    --input /tmp/normals.csv \
    --reference /data/refs/Homo_sapiens_assembly38.masked.fasta \
    --bed /data/bedfiles/MYOPOOL_240125_UBTF_hg38.bed \
    --outdir /data/nfcore_runs/pon_$(date +%Y%m%d_%H%M%S) \
    -profile mysite,singularity \
    -resume
```

Outputs land under `${outdir}/pon/` and
`${outdir}/references/<panel>/`. Copy them into `assets/<panel>/` or
wire them via `--cnv_*` flags. See `docs/usage_pon.md`.

---

## Output

### Per-sample clinical tree

The clinical deliverable lives at
`${params.outdir}/<sample>/clinical/` and is what should be copied
to clinical SFTP for sign-out:

```
<sample>/clinical/
├── <sample>_dashboard.html                # QC + variant summary HTML
├── <sample>_exon_coverage.tsv             # Per-exon coverage table
├── <sample>_fastp.html                    # fastp QC HTML
├── <sample>.final.bam                     # ABRA2-realigned BAM
├── <sample>.final.bam.bai
├── <sample>_flt3_consensus.tsv            # 4-tool FLT3-ITD consensus
├── <sample>_hsmetrics.txt                 # Picard HsMetrics
├── <sample>_igv_report.html               # IGV.js variant pileup report
├── <sample>.somaticseq.clinical.final.tsv # Final clinical variant TSV
├── <sample>.somaticseq.filtered.tsv       # All variants with FILTER populated
├── cnv_consensus/                         # Per-gene CNV calls
└── cnvkit_plots/                          # Per-chromosome scatter plots
```

`ORGANIZE_OUTPUT` forces byte-copy mode (not symlinks) for everything
under `clinical/` so the directory SFTPs cleanly and survives `work/`
cleanup.

The intermediate per-stage tree (`trimmed/`, `aligned/`, `markdup/`,
`bqsr/`, `abra2/`, `variant_callers/...`, `cnv/`, `annotation/`)
also lives under `<sample>/`. It is useful for debugging but not
part of the clinical deliverable.

`docs/output.md` describes an earlier per-stage layout; note that
SV calling is currently not part of the active pipeline (the
`SV_CALLING` subworkflow is included but commented out in
`workflows/tspipe.nf:183`), so no `sv/` outputs are produced.

### Run-level outputs

`${params.outdir}/pipeline_info/` contains:

- `execution_report_<timestamp>.html` — full Nextflow report
- `execution_timeline_<timestamp>.html` — per-task timeline
- `execution_trace_<timestamp>.txt` — tab-separated trace (status,
  runtime, peak memory, exit code)
- `pipeline_dag_<timestamp>.svg` — DAG visualisation

The trace file is the most useful artefact for postmortem analysis.

### work/ cleanup

The `work/` directory contains per-process scratch dirs and grows
large during execution. Keep it while debugging; delete it once
clinical outputs are signed out.

---

## Reproducibility

For runs that may need to be reproduced or audited later:

1. **Pin the pipeline commit.** Record `git rev-parse HEAD` alongside
   the run. `pipeline_info/` captures this implicitly via the
   execution report, but a separate note is wise.
2. **Pin Nextflow.** Record `nextflow -version`.
3. **Pin the container cache.** Keep `singularity.cacheDir`
   filesystem-snapshotted, or at minimum keep a manifest of SIF
   files and their checksums.
4. **Pin reference data.** The Broad bundle, VEP cache, and ANNOVAR
   `humandb/` are versioned upstream. Record which versions you
   downloaded.
5. **Pin the VV REST stack.** Tag the database tarballs by date and
   keep them — `vvta-data` and `vdb-data` change as VariantValidator
   releases new transcript and database snapshots.
6. **Pin the panel artefacts.** The six files under `assets/myeloid/`
   are git-tracked and move with the repo commit. If you ran
   `BUILD_PON` and used the local outputs instead of the shipped
   ones, record that and keep the run output.

The `pipeline_info/execution_report_*.html` already captures Nextflow
version, command line, parameters, and per-process container images
and runtimes.

---

## Troubleshooting

### VV REST not responding

```bash
docker ps --format '{{.Names}}\t{{.Status}}' | grep rest_variantvalidator
docker logs rest_variantvalidator-rest-variantvalidator-1 --tail 30
```

If gunicorn is not listening, relaunch it:

```bash
docker exec -d rest_variantvalidator-rest-variantvalidator-1 \
    gunicorn -b 0.0.0.0:5000 --workers 1 --threads 5 --timeout 600 \
    wsgi:app --chdir ./rest_VariantValidator/
sleep 90
curl -i -m 60 \
    "http://localhost:5001/VariantValidator/variantvalidator/GRCh38/NM_000088.4%3Ac.589G%3ET/all" \
    | head -10
```

If postgres logs show `FATAL: role "vvta_admin" does not exist` or
matview population errors, the named volume is empty — restore from
tarball (see "Standing the stack up" above).

### FLT3_ITD_EXT task FAILED on negative samples

For FLT3-ITD-negative specimens, `FLT3_ITD_EXT` exits with `NO ITD
CANDIDATE CLUSTERS GENERATED` and Nextflow records the task as
FAILED. `FLT3_CONSENSUS` then emits a header-only consensus TSV for
that sample. The other modules complete normally.

This is a known behaviour; the fix (treat "no ITD found" as a
successful task with an empty/sentinel output) is on the backlog
(`docs/audit/2026-05-19/multisample_validation.md`). Until then, for
affected samples consult the per-caller outputs under `work/`
(filt3r, getitd, pindel) directly.

### Test profile is broken

`-profile test` references `${projectDir}/assets/test/*` files that
do not exist. Use `gandalf,singularity -stub` (or
`mysite,singularity -stub`) with a real 1-sample samplesheet for
structural validation. Stubs short-circuit the missing-data
dependency.

### Cross-filesystem hardlink errors

`params.publish_dir_mode = 'link'` uses hardlinks where possible.
Crossing filesystem boundaries silently falls back to symlinks,
which then break the `clinical/` byte-copy assumption. Keep `outdir`
and `work/` on the same filesystem.

---

## Open items

Four items not yet fully resolved at the time of writing:

1. **Dockerfiles for the three `local/*` FLT3 images** are not
   currently in the repo. A fresh-server installer needs either the
   Dockerfiles or a `docker save` archive from gandalf. Durable fix:
   vendor the Dockerfiles under `containers/<tool>/`.
2. **`conf/test.config`** references missing `assets/test/`
   fixtures. Either restore the fixtures or remove the broken
   profile from `nextflow.config`.
3. **SNV blacklist column layout** below the `##` comment header is
   not documented here. The file's preamble describes the format as
   "tab-separated, one variant region per row"; `bin/14_variant_filter.py`
   is the authoritative consumer.
4. **Production-tree symlink convention.** The launcher's preflight
   expects `/home/<user>/targeted-seq-pipeline` to exist and resolve
   to the production tree. Recreate on each new server, or patch the
   launcher to use a configurable path.
