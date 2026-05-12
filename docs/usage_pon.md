# Building the PoN

The CNV calls in the main pipeline are computed against a panel of normals
(PoN) built from a cohort of confirmed-non-cancer samples. The PoN must be
rebuilt whenever you:

- switch reference (e.g. unmasked GRCh38 -> masked GRCh38)
- change the panel BED
- add a large batch of new normals

The `BUILD_PON` workflow handles this end-to-end and replaces the bash chain
in `assets/training/run_masked_realign*.sh`.

## When to run

Once per reference/panel combination. The outputs go in `params.outdir/pon/`
and you wire them into the main pipeline via:

```
--cnv_pon            results/pon/pon_reference.cnn       (or pon_male / pon_female)
--cnv_loo_summary    results/pon/loo_summary.tsv
--cnv_noise_profile  results/pon/loo_bin_noise_profile.tsv
--cnv_noisy_bins     results/pon/cnvkit_noisy_bins.bed
```

## Inputs

A samplesheet of normal samples (`assets/normals_samplesheet_example.csv`):

```csv
sample,fastq_1,fastq_2,sex,exclude
BNC1,/data/normals/BNC1_R1.fastq.gz,/data/normals/BNC1_R2.fastq.gz,female,false
BNC2,/data/normals/BNC2_R1.fastq.gz,/data/normals/BNC2_R2.fastq.gz,male,false
OCIAML3,/data/normals/OCIAML3_R1.fastq.gz,/data/normals/OCIAML3_R2.fastq.gz,female,true
```

The `exclude` column lets you keep a normal in the preprocessing step but drop
it from the PoN itself. The original pipeline excluded OCIAML3 by default
(it carries known clonal aberrations and would contaminate the PoN baseline).

## Run

```bash
nextflow run main.nf -entry BUILD_PON \
    --input  normals_samplesheet.csv \
    --reference references/hg38_broad/Homo_sapiens_assembly38.masked.fasta \
    --bed bedfiles/MYOPOOL_240125_UBTF_hg38.bed \
    --outdir pon_results \
    -profile docker -resume
```

## What it does

```
   normals samplesheet
          |
          v
   PREPROCESSING (per-normal, in parallel)   <-- same subworkflow as the main pipeline
          |
          v
   collect all .final.bam files
          |
          v
   CNVKIT_PON_BUILD                          <-- cnvkit.py batch --normal *.bam --output-reference pon_reference.cnn
          |
          v
   CNV_LOO_QC                                <-- for each normal: build N-1 reference, fix+segment held-out sample,
          |                                      emit per-bin noise + per-gene FP rate + noisy-bin BED
          v
   BUILD_SEX_PON                             <-- classify normals by chrX log2, build pon_male.cnn / pon_female.cnn
          |
          v
   results/pon/                              <-- final artefacts
       pon_reference.cnn
       cnvkit_pon_male.cnn
       cnvkit_pon_female.cnn
       loo_summary.tsv
       loo_bin_noise_profile.tsv
       cnvkit_noisy_bins.bed
       cnvkit_pon_sex_assignment.tsv
```

## Things to watch

1. **Sample size matters.** CNVKit needs at least 10-20 normals for a stable
   PoN; the original pipeline used 25 BNC + 30 cnv_negatives = 55 normals.
   Fewer than 10 will give you a noisy PoN with poor CNV sensitivity.

2. **Reference must match the main pipeline.** If TSPIPE uses masked GRCh38
   and BUILD_PON uses unmasked, your CNV calls will be garbage. Same goes for
   the BED file -- they must be the same panel definition.

3. **The chrX log2 threshold for sex classification** defaults to -0.4
   (validated on hg38). If you change panels, validate this threshold on
   samples of known sex before trusting the male/female PoNs. Tweak it via
   `ext.chrx_threshold` in `conf/modules.config`.

4. **Excluding aberrant normals.** OCIAML3 is excluded by default in the
   original pipeline via `--exclude OCIAML3`. In the Nextflow port, this is
   per-row via the `exclude` column in the samplesheet -- more visible, easier
   to audit. Mark any cell-line or contaminated sample `exclude=true`.

5. **LOO QC takes a while.** N-1 reference builds for N=55 normals means ~55
   separate cnvkit runs. On 16 cores that's typically 4-6 hours. Run on
   `-profile slurm` if you have a cluster.
