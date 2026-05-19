# `assets/training/`

These scripts are **not** part of the per-sample pipeline DAG. They are
one-off setup utilities for building reference resources, or historical
artefacts kept for reference. Run them outside `nextflow run`.

## Inventory

| Script | Purpose | Status |
|---|---|---|
| `download_hg38_resources.sh` | Fetches the Broad hg38 reference FASTA and the dbSNP / Mills / gnomAD known-sites VCFs | Current — recommended setup script |
| `download_annovar_db.sh` | Fetches ANNOVAR annotation databases into a `humandb/` directory | Current — recommended setup script |
| `run_masked_realign.sh` | Realigns the BNC normals against masked GRCh38 (one-off reference build) | Current — needed only for a full reference rebuild |
| `run_masked_realign_cnv_negatives.sh` | Same, for the cnv_negatives normals | Current — needed only for a full reference rebuild |
| `build_sex_pon.py` | Classifies normals by chrX log2, builds male/female CNV PoNs | **Superseded** by the `BUILD_PON` Nextflow workflow |
| `build_sex_matched_pons.sh` | Wrapper around `build_sex_pon.py` | **Superseded** by the `BUILD_PON` Nextflow workflow |
| `cnv_loo_qc.py` | Leave-one-out CNV noise assessment; emits noise profile + blacklist BED | **Superseded** by the `CNV_LOO_QC` module in the `BUILD_PON` workflow |

## Current path for new PoN builds

To build a panel-of-normals from a samplesheet of normals, **use the
`BUILD_PON` Nextflow workflow** rather than the bash scripts above:

```bash
nextflow run . -entry BUILD_PON \
    --input normals.csv \
    --reference /path/to/hg38_masked.fasta \
    --bed /path/to/panel.bed \
    --outdir /path/to/pon_outputs \
    -profile <yoursite>,singularity \
    -resume
```

See `docs/usage_pon.md` for the full walkthrough and `docs/INSTALL.md`
for the install context.

## When the bash scripts here are still useful

- `download_hg38_resources.sh` and `download_annovar_db.sh` save time
  on a fresh install. `docs/INSTALL.md` "Reference data" points at
  these as the easier path to grab the Broad bundle and ANNOVAR DBs
  on a host with outbound network access.
- `run_masked_realign.sh` is needed only when rebuilding the masked
  reference itself — i.e. when changing the masking strategy or
  retargeting to a different genome build. The pipeline does not use
  it at runtime.
- The four superseded scripts are kept because they document the
  exact pre-Nextflow PoN-building procedure and can be useful when
  reproducing legacy results. They should not be used for new builds.

## Outputs

Once built (via either the workflow or these scripts in legacy mode),
the PoN artefacts live under `assets/<panel>/` (git-tracked) or
wherever the `--outdir` of `BUILD_PON` points. They feed back into
the per-sample workflow via the `cnv_pon_male`, `cnv_pon_female`,
`cnv_loo_summary`, `cnv_noise_profile`, and `cnv_noisy_bins`
parameters (defined in `nextflow.config` and defaulted from
`${projectDir}/assets/${params.panel}/` by `workflows/tspipe.nf`).
