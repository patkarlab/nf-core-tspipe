# Building the PoN

The CNV calls in TSPIPE are computed against a panel of normals (PoN) built
from a cohort of confirmed-non-cancer samples. The PoN must be rebuilt
whenever you:

- switch reference (e.g. unmasked GRCh38 to masked GRCh38)
- change the panel BED
- add a large batch of new normals

The `BUILD_PON` workflow handles this end to end. It replaces the bash chain
in `assets/training/run_masked_realign*.sh` and the standalone `12c_*.py`
scripts that the upstream Python pipeline used.

Cross-references:

- [`docs/usage.md`](usage.md) — TSPIPE samplesheet format and CLI flag reference
- [`docs/INSTALL.md`](INSTALL.md) — install context (prerequisites, container catalogue, site config)
- [`docs/testing.md`](testing.md) — post-install smoke tests (Phase 5 covers BUILD_PON)
- [`docs/output.md`](output.md) — how the per-sample CNV tree consumes these PoN artefacts
- [`docs/clinical_decisions.md`](clinical_decisions.md) — masking strategy and other intentional differences from upstream

## When to run

Once per (reference, panel) combination, then again only when one of the
trigger conditions above is met. Outputs are published under `--outdir`;
see *Outputs and wiring* below for how TSPIPE consumes them.

## Inputs

A samplesheet of normal samples (template at
`assets/normals_samplesheet_example.csv`):

```csv
sample,fastq_1,fastq_2,sex,exclude
BNC1,/data/normals/BNC1_R1.fastq.gz,/data/normals/BNC1_R2.fastq.gz,female,false
BNC2,/data/normals/BNC2_R1.fastq.gz,/data/normals/BNC2_R2.fastq.gz,male,false
OCIAML3,/data/normals/OCIAML3_R1.fastq.gz,/data/normals/OCIAML3_R2.fastq.gz,female,true
```

Column reference:

- `sample`, `fastq_1`, `fastq_2` — as for the per-sample samplesheet (see
  [`docs/usage.md`](usage.md)).
- `sex` — `male`, `female`, or `unknown`. Drives sex-stratified PoN
  construction. Normals with `sex=unknown` are excluded from the
  sex-specific PoNs but can still contribute to the default reference.
- `exclude` — set to `true` to keep the normal in preprocessing (so its BAM
  exists in `work/`) but drop it from the PoN aggregation itself. Use this
  for known clonal-aberration samples; the lab marks OCIAML3 as
  `exclude=true` because its chromosome-level abnormalities would otherwise
  contaminate the baseline.

## Run

```bash
nextflow run . -entry BUILD_PON \
    -profile <yoursite>,singularity \
    --input normals_samplesheet.csv \
    --outdir pon_results \
    -resume
```

`<yoursite>` is the profile you registered when setting up the destination
(see [`docs/INSTALL.md`](INSTALL.md)). `params.reference` and `params.bed`
come from the site profile; to rebuild against a different reference or
panel BED for the same run, override them on the command line.

> **[verify against `workflows/build_pon.nf`]** Confirm that BUILD_PON
> reads `params.reference` and `params.bed` directly from the profile (as
> TSPIPE does) and does not require explicit `--reference` / `--bed` on
> the command line. If it does require them, restore them to the example
> above.

## What it does

```text
normals samplesheet
       |
       v
PREPROCESSING (per-normal, parallel)        <- same subworkflow as TSPIPE
       |
       v
collect all .final.bam files
       |
       v
CNVKIT_PON_BUILD                            <- cnvkit.py batch --normal *.bam
                                               --output-reference pon_reference.cnn
       |
       v
CNV_LOO_QC                                  <- per-normal N-1 reference,
       |                                       fix + segment held-out sample,
       |                                       emit per-bin noise + per-gene FP rate
       |                                       + noisy-bin BED
       v
BUILD_SEX_PON                               <- classify normals by chrX log2,
       |                                       build sex-stratified PoNs
       v
published outputs (see next section)
```

> **[verify against `workflows/build_pon.nf`]** Confirm `BUILD_SEX_PON` is
> still a distinct step in the workflow, vs being folded into
> `CNVKIT_PON_BUILD` or executed inline. The diagram above reflects the
> historical design.

## Outputs and wiring

The workflow publishes (paths shown relative to `--outdir`):

| File                              | Purpose                                                              |
|-----------------------------------|----------------------------------------------------------------------|
| `cnvkit_pon_male.cnn`             | Sex-stratified reference for male samples                            |
| `cnvkit_pon_female.cnn`           | Sex-stratified reference for female samples                          |
| `cnvkit_loo_summary.tsv`          | Per-normal LOO concordance summary                                   |
| `loo_bin_noise_profile.tsv`       | Per-bin noise quantiles across the LOO cohort                        |
| `cnvkit_noisy_bins.bed`           | High-noise bins flagged for masking in TSPIPE                        |
| `cnvkit_pon_sex_assignment.tsv`   | chrX log2 evidence for each normal's sex classification              |

> **[verify against `workflows/build_pon.nf` and `conf/modules.config`]**
> Confirm the exact published filenames and the `publishDir` target.
> The list above describes the canonical layout that the per-sample TSPIPE
> workflow expects under `assets/<panel>/`.

### Wiring the outputs into TSPIPE

There are two ways to make the PoN artefacts visible to TSPIPE.

**(a) Promote to the panel asset directory.** Copy the published files into
`assets/<panel>/` (e.g. `assets/myeloid/`). The per-sample pipeline's CNV
subworkflow uses an asset-default fallback at
`${projectDir}/assets/${params.panel}/...` for every PoN input, so once the
files are in place TSPIPE picks them up without any extra CLI flags. This
is the convention used on gandalf.

**(b) Point TSPIPE at the BUILD_PON output directory.** Pass the paths
explicitly on the TSPIPE invocation:

```bash
nextflow run . \
    -profile <yoursite>,singularity \
    --input samplesheet.csv \
    --outdir results \
    --cnv_loo_summary    pon_results/cnvkit_loo_summary.tsv \
    --cnv_noise_profile  pon_results/loo_bin_noise_profile.tsv \
    --cnv_noisy_bins     pon_results/cnvkit_noisy_bins.bed \
    -resume
```

The historical `--cnv_pon` flag is **deprecated** and has no effect: the
sex-stratified PoNs (`cnvkit_pon_male.cnn` / `cnvkit_pon_female.cnn`) are
now selected from the panel asset directory based on `meta.sex` per
sample. For `sex=unknown` samples, the CNVKit module falls back to the
female PoN with a warning. See [`docs/usage.md`](usage.md) for the
current TSPIPE flag set.

> Asset files (`cnvkit_pon_*.cnn`, `loo_bin_noise_profile.tsv`) are
> binary or large and are not currently tracked in the git repository.
> Either rsync them from a known-good site (see
> [`docs/deployment.md`](deployment.md)) or rebuild via `BUILD_PON` on the
> destination.

## Things to watch

1. **Sample size matters.** CNVKit needs at least 10–20 normals for a
   stable PoN; the lab's myeloid PoN uses 25 BNC + 30 cnv_negatives = 55
   normals. Fewer than 10 will give you a noisy PoN with poor CNV
   sensitivity.

2. **Reference and panel must match TSPIPE.** If TSPIPE uses masked
   GRCh38 and BUILD_PON uses unmasked, your CNV calls will be wrong
   silently — not a loud error. Same for the BED file: same panel
   definition on both sides.

3. **Sex classification threshold.** The chrX log2 cutoff for male vs
   female classification defaults to `-0.4` (validated on hg38 with the
   current myeloid panel). For a new panel, validate the cutoff on
   samples of known sex before trusting the male/female PoNs.

   > **[verify against `conf/modules.config` and the BUILD_SEX_PON
   > module]** Confirm the parameter name (historically `ext.chrx_threshold`)
   > and the default value (`-0.4`). The mechanics are correct; only the
   > exact override knob may have drifted.

4. **Excluding aberrant normals.** The upstream pipeline excluded
   OCIAML3 via a CLI flag (`--exclude OCIAML3`); in BUILD_PON this is
   per-row via the `exclude` column. More visible, easier to audit.
   Mark any cell-line or contaminated sample `exclude=true`.

5. **LOO QC takes a while.** N-1 reference builds for N=55 normals means
   ~55 separate CNVKit runs. On 16 cores expect 4–6 hours. On a cluster,
   use your site's executor profile (see [`docs/INSTALL.md`](INSTALL.md));
   on gandalf the executor is `local` and runs benefit from the host's
   192 cores.

6. **Sex-specific PoN ages can drift.** If a later realignment effort
   (e.g. masked-reference rebuild) updates only one of the two
   sex-stratified PoNs, calls for samples of the un-rebuilt sex inherit
   a subtly different background. Check the file dates on
   `assets/<panel>/cnvkit_pon_{male,female}.cnn` periodically and rebuild
   both together when one moves. As of writing, the female PoN at
   `assets/myeloid/cnvkit_pon_female.cnn` is older than the male PoN and
   is a candidate for rebuild against the masked reference.
