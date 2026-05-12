# Changelog

## 0.1.0-dev (initial scaffold)

- Ported pipeline structure from `scripts/run_sample_pipeline.py` to Nextflow DSL2.
- 7 subworkflows: preprocessing, variant_calling, flt3_itd, cnv_calling,
  sv_calling, annotation, reporting.
- 38 module files. 13 fully faithful; 25 stubs with TODOs.
- Python helpers copied into `bin/` for processes that wrap custom logic
  (consensus, filter, organize).
- Training/setup scripts moved to `assets/training/` and excluded from the
  per-sample DAG.

### Dropped

- Alternative CNV callers never wired into the production runner: `12d_cn_mops.R`,
  `12d_panelcn_mops.R`, `12d_ifcnv.py`, `12d_ifcnv_precompute.py`.
- Lymphoma-specific scripts (out of scope per current focus on leukemia panel):
  `lymphoma_fusion_scanner.py`, `run_batch_fusion_scan.py`, `build_fusion_pon.py`,
  `run_lymphoma_batch.sh`.
- Orchestration scripts replaced by Nextflow: `run_sample_pipeline.py`,
  `run_batch_preprocessing.py`, `cleanup_intermediates.py`.
