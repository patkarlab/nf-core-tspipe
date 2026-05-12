# assets/training/

These scripts are NOT part of the per-sample pipeline DAG. They are setup /
training utilities that build the reference resources the pipeline consumes.
You run them once (or whenever you retrain), outside of `nextflow run`.

## Inventory

| script                                    | purpose                                                       | run when                              |
| ----------------------------------------- | ------------------------------------------------------------- | ------------------------------------- |
| download_hg38_resources.sh                | fetches Broad's hg38 reference + known-sites VCFs             | once, before first use                |
| download_annovar_db.sh                    | fetches ANNOVAR annotation databases                          | once, before first use                |
| build_sex_pon.py (was 12c_build_sex_pon.py)| classifies normals by chrX log2, builds male/female CNV PoNs | when normals are re-aligned           |
| build_sex_matched_pons.sh                 | wrapper around build_sex_pon.py                              | "                                     |
| cnv_loo_qc.py (was 12c_cnv_loo_qc.py)     | leave-one-out CNV noise assessment; emits noise profile + blacklist BED | when normals are re-aligned |
| run_masked_realign.sh                     | realign the 25 BNC normals against masked GRCh38, rebuild PoN | one-off reference rebuild             |
| run_masked_realign_cnv_negatives.sh       | same for the 30 cnv_negatives normals                         | one-off reference rebuild             |

Outputs from these feed back into the pipeline as `params.cnv_pon`,
`params.cnv_loo_summary`, `params.cnv_noise_profile`, etc. — defined in
`nextflow.config`.

If you want to port these to Nextflow as well, build them as a SEPARATE
"training" workflow (e.g. `workflows/build_pon.nf`) with its own entry point.
Don't fold them into the per-sample DAG — they have completely different inputs
(a directory of normals, not a single sample) and run on a different cadence.
