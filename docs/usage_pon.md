# Building a CNV Panel-of-Normals

`BUILD_PON` is the nf-core entry point that consumes a samplesheet of normal
samples and produces all the CNV reference artifacts the main per-sample
`TSPIPE` workflow needs:

- A sex-stratified pair of CNVkit references (`cnvkit_pon_male.cnn`,
  `cnvkit_pon_female.cnn`).
- A per-bin noise profile from leave-one-out (LOO) cross-validation, used
  downstream as the noisy-bin blacklist.
- A gene-level LOO false-positive summary for QC.
- A sex-assignment audit table.

These artifacts are panel-namespaced. A separate `BUILD_PON` invocation is
required for each panel (e.g. the legacy MYOPOOL exonic panel and the
MYOPOOL+backbone hybrid live under different `--panel` values).

## When to (re)build the PoN

Rebuild when **any** of the following change in a way that shifts coverage
distributions:

- The panel BED (new targets, new probes, new backbone).
- The capture chemistry or library prep protocol.
- The sequencing instrument or run mode in a way that affects coverage
  uniformity.
- The reference fasta (e.g. masked-vs-unmasked, or a new build).

If you just want a fresh PoN from new normals on an existing panel, the
samplesheet changes but everything else is identical.

## Inputs you must have

| Input | Notes |
|---|---|
| Samplesheet CSV | One row per normal; columns `sample,fastq_1,fastq_2,sex,exclude` |
| Reference fasta | hg38 masked, with `.fai` and `.dict` sidecars at the standard paths |
| Panel BED | Sorted, hg38, with the panel name in the path |
| Known-sites VCFs | dbSNP and Mills (default-wired in `conf/gandalf.config`) |

`BUILD_PON` also runs the same `PREPROCESSING` subworkflow that the main
pipeline uses (fastp → BWA → MarkDuplicates → BQSR → ABRA2 → coverage). So
on top of the inputs above, you need the same `--exonwise_bed` that TSPIPE
needs for mosdepth. On gandalf this is set automatically by
`-profile gandalf`; on other sites add it explicitly.

## The samplesheet

Schema:

```csv
sample,fastq_1,fastq_2,sex,exclude
BNC1F,/data/normals/BNC1F-MYCNV_R1.fastq.gz,/data/normals/BNC1F-MYCNV_R2.fastq.gz,female,false
BNC10M,/data/normals/BNC10M-MYCNV_R1.fastq.gz,/data/normals/BNC10M-MYCNV_R2.fastq.gz,male,false
```

- `sample` — unique identifier; appears in per-sample work-dir names and in
  the sex-assignment TSV. Keep it short and free of whitespace.
- `fastq_1`, `fastq_2` — absolute paths; both must exist.
- `sex` — `male`, `female`, or `unknown`. Used only as ground-truth label
  for the sex-assignment audit (the actual sex classification is
  data-driven, see "Sex assignment").
- `exclude` — `true` for normals to skip (cell lines like OCIAML3,
  known-aberrant samples, sequencing failures). Excluded samples never
  enter the PoN.

For panels with sex encoded in the FASTQ filenames (e.g. `BNC1F`, `BNC10M`),
the helper at `tools/make_bnc_pon_samplesheet.py` generates a samplesheet
automatically, validates each R1 has a paired R2, and warns if either sex
cohort falls below 10 normals:

```bash
python3 tools/make_bnc_pon_samplesheet.py \
    --fastq-dir /goast/hemat_data/BNC_fastqs \
    --output /goast/hemat_data/nf-core-tspipe/pon_samplesheets/my_pon.csv
```

## Cohort size guidance

| Cohort range per sex | Quality |
|---|---|
| 5–9   | Acceptable for proof-of-concept; expect noisy CNV calls on real samples |
| 10–19 | Usable for production with documented caveats |
| 20+   | Recommended; CNVKit's per-bin variance estimates stabilize here |

The 2026-05-24 build used 13 male + 12 female and produced a working PoN.
Below 10 per sex, `tools/make_bnc_pon_samplesheet.py` emits a warning.

## Required parameters

| Param | Purpose |
|---|---|
| `--input` | Samplesheet CSV |
| `--reference` | hg38 masked fasta (`.fai` and `.dict` sidecars resolved automatically) |
| `--bed` | Panel BED |
| `--panel` | Panel name; drives output namespacing (`references/<panel>/`, `assets/<panel>/`) |

## Optional parameters

| Param | Default | Purpose |
|---|---|---|
| `--male_reference` | `true` | Passes `-y` to CNVkit (haploid X reference). Set `false` only for female-only PoNs. |
| `--chrx_threshold` | derived | chrX log2 cutoff for sex classification in `BUILD_SEX_PON`. If null (default), derived from `--male_reference`: `+0.5` when `-y` is in effect, `-0.5` otherwise. Override only if your data shows a non-standard chrX distribution. |
| `--outdir` | `/goast/hemat_data/nfcore_runs/default` | Run output root |
| `--keep_intermediates` | `false` | Preserves scratch per sample. Useful when debugging. |

The threshold derivation matters: a PoN run with `--male_reference=true` but
the legacy hardcoded threshold of `-0.4` will misclassify every sample as
female (the chrX cluster centers shift to ~0 and ~+1 under `-y`, both above
`-0.4`).

## Profile

On gandalf:

```
-profile gandalf,singularity
```

The `gandalf` profile sets `exonwise_bed`, `dbsnp_vcf`, `mills_vcf`, and
container engine paths. Other sites must override these in a site-specific
config and use that instead.

## End-to-end recipe

The example below builds a PoN for the `myeloid_cnv` panel from 25 BNC
normals on gandalf, mirroring the 2026-05-24 build.

### 1. Stage inputs

The panel BED lives under `targeted-seq-pipeline/bedfiles/`:

```bash
ls /goast/hemat_data/targeted-seq-pipeline/bedfiles/myeloid_CNVbackbone_HG38_nf-core-tspipe.bed
md5sum /goast/hemat_data/targeted-seq-pipeline/bedfiles/myeloid_CNVbackbone_HG38_nf-core-tspipe.bed
```

### 2. Generate the samplesheet

```bash
mkdir -p /goast/hemat_data/nf-core-tspipe/pon_samplesheets
python3 /goast/hemat_data/nf-core-tspipe/tools/make_bnc_pon_samplesheet.py \
    --fastq-dir /goast/hemat_data/BNC_fastqs \
    --output /goast/hemat_data/nf-core-tspipe/pon_samplesheets/bnc_mycnv_25.csv
```

Verify the row counts and per-sex split match expectations.

### 3. Stub run (always do this first)

```bash
cd /goast/hemat_data/nf-core-tspipe

RUN_TAG="pon_myeloid_cnv_$(date +%Y%m%d_%H%M%S)"

nextflow run main.nf -entry BUILD_PON \
    --input     /goast/hemat_data/nf-core-tspipe/pon_samplesheets/bnc_mycnv_25.csv \
    --reference /goast/hemat_data/targeted-seq-pipeline/references/hg38_broad/Homo_sapiens_assembly38.masked.fasta \
    --bed       /goast/hemat_data/targeted-seq-pipeline/bedfiles/myeloid_CNVbackbone_HG38_nf-core-tspipe.bed \
    --panel     myeloid_cnv \
    --outdir    /goast/hemat_data/nfcore_runs/${RUN_TAG}_stub \
    -profile    gandalf,singularity \
    -stub \
    -resume
```

Stub mode resolves the DAG and runs each process as `touch`/`mkdir`, so a
clean stub completion confirms channel topology before burning compute.
Expect ~1–2 min total.

### 4. Real run

```bash
RUN_TAG="pon_myeloid_cnv_$(date +%Y%m%d_%H%M%S)"

nextflow run main.nf -entry BUILD_PON \
    --input     /goast/hemat_data/nf-core-tspipe/pon_samplesheets/bnc_mycnv_25.csv \
    --reference /goast/hemat_data/targeted-seq-pipeline/references/hg38_broad/Homo_sapiens_assembly38.masked.fasta \
    --bed       /goast/hemat_data/targeted-seq-pipeline/bedfiles/myeloid_CNVbackbone_HG38_nf-core-tspipe.bed \
    --panel     myeloid_cnv \
    --outdir    /goast/hemat_data/nfcore_runs/${RUN_TAG} \
    -profile    gandalf,singularity \
    -resume \
    -with-trace -with-report -with-timeline \
    2>&1 | tee /tmp/${RUN_TAG}.log
```

For 25 normals on gandalf's 192-core box, expect 1.5–3h total. The dominant
serial cost is `CNV_LOO_QC`, which builds N N-1 references and runs
fix+segment on the held-out sample for each.

### 5. Seed assets/<panel>/

The PoN files in `<outdir>/pon/` and the LOO outputs in the `CNV_LOO_QC`
work directory need to be copied to `assets/<panel>/` for TSPIPE to pick
them up via asset-default fallback:

```bash
# Locate the CNV_LOO_QC work directory from the trace file
RUN_DIR=/goast/hemat_data/nfcore_runs/${RUN_TAG}
WORK_LOO=$(awk -F'\t' '$4 ~ /CNV_LOO_QC/ { print $5; exit }' \
    "$RUN_DIR/pipeline_info/execution_trace.txt")

python3 tools/patches/2026-05-24/seed_myeloid_cnv_assets.py \
    --outdir   "$RUN_DIR" \
    --work-loo "$WORK_LOO"
```

If `cnv_scatter_regions.txt` is unchanged from the parent panel, copy it:

```bash
cp assets/<parent_panel>/cnv_scatter_regions.txt \
   assets/<new_panel>/cnv_scatter_regions.txt
```

If the panel's gene content changed (new genes, new exon coordinates),
regenerate it from the new BED — see
`tools/regenerate_cnv_scatter_regions.py` in the production tree.

## What outputs you get

After a successful run:

```
<outdir>/
    pon/
        cnvkit_pon_male.cnn               # BUILD_SEX_PON
        cnvkit_pon_female.cnn             # BUILD_SEX_PON
        cnvkit_pon_sex_assignment.tsv     # BUILD_SEX_PON
        pon_reference.cnn                 # CNVKIT_PON_BUILD (combined, not used downstream)
        loo_qc/                           # CNV_LOO_QC informational artifacts
            loo_iterations/
            plots/
    references/<panel>/                   # CNV_LOO_QC consumer artifacts (note: see "Known publishDir issue")
        cnvkit_loo_summary.tsv
        cnvkit_noisy_bins.bed
    pipeline_info/
        execution_trace.txt
        execution_report.html
        execution_timeline.html
```

After seeding, `assets/<panel>/` contains:

```
assets/<panel>/
    cnvkit_pon_male.cnn
    cnvkit_pon_female.cnn
    cnvkit_loo_summary.tsv
    cnvkit_noisy_bins.bed
    loo_bin_noise_profile.tsv
    cnv_scatter_regions.txt
    cnvkit_pon_sex_assignment.tsv         # provenance, not consumed
    MANIFEST.tsv                          # generated by seed script
```

## Sex assignment

`BUILD_SEX_PON` reads each sample's `.cnr` file from the LOO output,
computes the mean chrX log2 ratio, and applies `--chrx_threshold` to
assign sex. The samplesheet's `sex` column is **not** used for
classification — it appears in the sex-assignment TSV alongside the
data-driven call for audit, so you can spot mismatches.

When `--male_reference=true`:
- Males cluster around chrX log2 ≈ 0 (haploid X matches the reference).
- Females cluster around chrX log2 ≈ +1 (diploid X vs haploid reference).
- Threshold `+0.5` separates them cleanly when the cohort isn't pathological.

When `--male_reference=false`:
- Males cluster around chrX log2 ≈ -1.
- Females cluster around chrX log2 ≈ 0.
- Threshold `-0.5` separates them.

In the 2026-05-24 build, the 13M vs 12F clusters were at `[0.07, 0.13]` vs
`[0.92, 0.99]` — a 0.85 log2 gap. Any threshold in the gap classifies
correctly; the `+0.5` default has ~3.5× safety margin on the closer side.

## Validation gates

After the seed script writes `MANIFEST.tsv`, sanity-check the PoN before
trusting it on real samples:

1. **Sex-assignment vs samplesheet**: the classifier should agree with the
   samplesheet `sex` column for every sample. The seed script reports
   per-sex counts in the validation column of `MANIFEST.tsv`; if they
   match your filename-derived expectation, you're good.

2. **Bin count parity** between male and female PoNs: both should have the
   same number of bins (same target/antitarget grid).

3. **LOO blacklist rate** ("noisy_bins as fraction of total bins"): for
   exon-only panels expect 5–15%. For panels with a CNV backbone, expect
   30–45% (backbone tiles in low-coverage regions are inherently noisier).

4. **MANIFEST.tsv md5 trail** — keep it; it's the audit record of which
   `BUILD_PON` run produced which asset. When you build a future PoN
   against another panel variant, the MANIFEST is what lets you reason
   about reproducibility.

## Known limitations

### Sex-mixed LOO noise profile

`CNV_LOO_QC` currently runs with a single reference type (controlled by
`--male_reference`), so the LOO noise profile and the gene-level FP rates
mix both sexes' contribution to the chrX/chrY signal. This inflates
chrX/chrY FP rates in `cnvkit_loo_summary.tsv` — they're not real noise,
they're the reference-mismatch artifact.

The **sex-stratified PoN files** (`cnvkit_pon_male.cnn`,
`cnvkit_pon_female.cnn`) are correctly built per-sex by `BUILD_SEX_PON`
and are unaffected. Only the LOO QC summary has this caveat.

A proper sex-stratified LOO refactor is tracked as an open item.

### Known publishDir issue (workaround: seed script)

As of the 2026-05-24 build, `CNV_LOO_QC`'s `publishDir` for the panel-
namespaced artifacts (`cnvkit_loo_summary.tsv`, `cnvkit_noisy_bins.bed`)
sometimes creates an empty `references/<panel>/` in the outdir without
the files. The seed script (`seed_myeloid_cnv_assets.py`) works around
this by sourcing those files directly from the `CNV_LOO_QC` Nextflow
work directory.

### onComplete sweep

The `workflow.onComplete` handler in `main.nf` is shaped for TSPIPE's
per-sample outdir layout. For BUILD_PON it's a no-op for `pon/` and
`references/<panel>/` (those names aren't in the scratch-subdirs list),
but the line `Final per-sample layout: <outdir>/<sample>/clinical/`
that prints at the end is misleading for BUILD_PON. Ignore it.

## Troubleshooting

### `Workflow BUILD_PON:PREPROCESSING declares 6 input channels but 3 were given`

`build_pon.nf` is out of date relative to the `PREPROCESSING` subworkflow.
Apply `tools/patches/2026-05-24/apply_build_pon_preprocessing_fix.py`.

### `Missing output file(s) references/<panel>/cnvkit_loo_summary.tsv`

`cnv_loo_qc.py` is writing outputs PIPELINE_DIR-relative instead of
CWD-relative. Apply
`tools/patches/2026-05-24/apply_cnv_loo_qc_cwd_relative_paths_fix.py`.

### `Missing output file(s) cnvkit_pon_male.cnn`

Two possible causes:

1. The script writes `cnvkit_hg38_pon_male.cnn` (legacy production name)
   but the module expects `cnvkit_pon_male.cnn`. Apply
   `tools/patches/2026-05-24/apply_build_sex_pon_filename_and_threshold_fix.py`.

2. Sex classification failed and 0 samples landed in the male cohort. Check
   `cnvkit_pon_sex_assignment.tsv`: if all samples are one sex, the
   threshold doesn't match the `--male_reference` setting. The same patch
   above fixes the threshold derivation.

### All samples classified as one sex despite balanced cohort

`--chrx_threshold` is hardcoded or out of step with `--male_reference`.
The fix is to either rely on the auto-derivation (don't set
`--chrx_threshold`) or set it explicitly to a value inside the chrX log2
gap your data shows. Inspect `loo_iterations/<sample>/<sample>.cnr` to
see where your data's chrX cluster centers actually are.

### Empty `references/<panel>/` in outdir

See "Known publishDir issue" above. Run the seed script with `--work-loo`
pointing to the `CNV_LOO_QC` work directory to recover the files.
