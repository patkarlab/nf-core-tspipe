# nf-core-tspipe

Targeted-sequencing pipeline for leukemia / myeloid malignancies, ported from
the original `scripts/run_sample_pipeline.py` Python orchestrator to Nextflow
following nf-core conventions.

> Status: **scaffold + select modules**. The structure, the seven subworkflows,
> all 38 module files, and the bin/ helpers are in place. Preprocessing,
> SomaticSeq, the four FLT3-ITD tools, and the variant filter are written
> faithfully; ~24 other modules are stubs with TODOs pointing back at the
> original Python source. See `docs/PORTING_STATUS.md`.

## What's here

```
nf-core-tspipe/
├── main.nf                     # Two entry workflows: TSPIPE (default) and BUILD_PON
├── nextflow.config             # Params + profiles
├── workflows/
│   ├── tspipe.nf               # Per-sample analysis (replaces run_sample_pipeline.py)
│   └── build_pon.nf            # PoN builder (replaces run_masked_realign*.sh + 12c_*)
├── subworkflows/local/         # preprocessing, variant_calling, flt3_itd, cnv_calling, sv_calling, annotation, reporting
├── modules/local/              # 41 process definitions
├── conf/                       # base / modules / test config
├── assets/                     # samplesheet schemas, training scripts
├── bin/                        # Python helpers (on PATH inside processes)
└── docs/                       # usage, output, usage_pon, porting status
```

## Quick start (per-sample analysis)

```bash
nextflow run main.nf \
    --input samplesheet.csv \
    --reference references/hg38_broad/Homo_sapiens_assembly38.masked.fasta \
    --bed bedfiles/MYOPOOL_240125_UBTF_hg38.bed \
    --cnv_pon references/cnvkit_pon/pon_reference.cnn \
    --snv_blacklist references/blacklist_snvs_hg38.tsv \
    --outdir results \
    -profile docker -resume
```

See `docs/usage.md` for full parameter reference, `docs/output.md` for the
output layout, and `docs/PORTING_STATUS.md` for what's done and what isn't.

## Quick start (PoN build)

Run once before the main pipeline, with a samplesheet of normal samples:

```bash
nextflow run main.nf -entry BUILD_PON \
    --input normals_samplesheet.csv \
    --reference references/hg38_broad/Homo_sapiens_assembly38.masked.fasta \
    --bed bedfiles/MYOPOOL_240125_UBTF_hg38.bed \
    --outdir pon_results \
    -profile docker -resume
```

Outputs go to `pon_results/pon/` -- wire those into the main pipeline's
`--cnv_pon`, `--cnv_loo_summary`, `--cnv_noise_profile`, `--cnv_noisy_bins`.

See `docs/usage_pon.md` for details on how this replaces the bash chain in
`assets/training/`.

## Testing on gandalf

`docs/testing.md` walks through a phased plan: verify Nextflow installation,
parse the config, run one sample through preprocessing, compare against your
existing Python-runner output, then incrementally fill in stubs. Don't skip
phases — each phase isolates one possible failure mode.

To start:

```bash
nextflow run main.nf -profile gandalf --input test_samplesheet.csv --outdir test_run -preview
```

## Moving to another server

`docs/deployment.md` has a 7-step checklist. The short version: copy
`conf/site_template.config` to `conf/<yoursite>.config`, fill in the paths,
register it as a profile, and run.

## Differences from the Python runner

1. **No `run_batch_preprocessing.py`.** Nextflow channels parallelize across
   samples automatically. Just put more rows in the samplesheet.
2. **No `--skip-from N`.** Use `-resume`; Nextflow caches every successful
   process.
3. **No `cleanup_intermediates.py`.** Set `cleanup = true` in nextflow.config
   or rely on `publishDir` to copy only what you want to keep.
4. **Sex column in samplesheet** replaces per-sample sex inference from the
   CNV PoN. Set `sex` to `male`, `female`, or `unknown` in the CSV.
5. **Step 14 → 17 → 15 ordering** is preserved in `subworkflows/local/annotation.nf`.
   The numbers reflect when scripts were added to the original pipeline, not
   execution order — which Nextflow's DAG model makes explicit anyway.
6. **FLT3-ITD Docker volume-mount workaround is gone.** Nextflow stages files
   into the process work dir and mounts that automatically; the original
   orchestrator's absolute-path hack is no longer needed.
7. **getITD CWD-collision workaround is gone.** Each process gets its own
   work dir.

## What was dropped

- `12d_cn_mops.R`, `12d_panelcn_mops.R`, `12d_ifcnv*.py` — alternative CNV
  callers that never made it into the production runner. `12e_cnv_concordance.py`
  explicitly marks `--ifcnv-genes` deprecated.
- `lymphoma_fusion_scanner.py`, `run_batch_fusion_scan.py`, `build_fusion_pon.py`,
  `run_lymphoma_batch.sh` — lymphoma-panel work, out of scope.
- `run_sample_pipeline.py`, `run_batch_preprocessing.py`, `cleanup_intermediates.py`
  — replaced by Nextflow itself.

Training/setup scripts (build_sex_pon, cnv_loo_qc, download_*, run_masked_realign)
moved to `assets/training/` — they're one-off resource builders, not part of the
per-sample DAG.
