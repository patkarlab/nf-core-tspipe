# 2026-05-18 - End-of-day summary

## Commits planned

Single feature commit to nf-core-tspipe:

    feat(organize): add ORGANIZE_OUTPUT module + scratch cleanup hook

    - bin/organize_output.py: hardlink-based clinical/ tree builder
    - modules/local/organize_output.nf: process with explicit channel inputs
    - workflow.onComplete cleanup in main.nf
    - publishDir mode flip 'copy' -> 'link' across all modules
    - emit edits in fastp, flt3_itd_ext, cnv_plots, annotation subwf,
      variant_calling subwf for clean channel handles into organize
    - nextflow.config: anchored outdir default, keep_intermediates param
    - tools/run_pipeline.sh: interactive launcher
    - audit notes under docs/audit/2026-05-18/

## Disk math

Before (per sample, current):
- BAM doubled in abra2/ and ... -- ~6.3 GB total
- Scratch dirs persist: bqsr/, markdup/, mosdepth/, ... -- ~1.3 GB

After (per sample, with this patch):
- Single BAM inode; clinical/ paths are hardlinks -- ~5 GB
- Scratch dirs deleted in onComplete; work/ retains for debug

## Files touched

NEW (6):
- bin/organize_output.py
- modules/local/organize_output.nf
- tools/run_pipeline.sh
- docs/audit/2026-05-18/SESSION_NOTES.md
- docs/audit/2026-05-18/end_of_day_summary.md
- tools/patches/2026-05-18/manual_edits_required.md

EDITED in place (6, with .bak):
- nextflow.config
- modules/local/fastp.nf
- modules/local/flt3_itd_ext.nf
- modules/local/cnv_plots.nf
- subworkflows/local/annotation.nf
- subworkflows/local/variant_calling.nf

SED-PASSED (variable count, all modules/local/*.nf with publishDir copy):
- mode: 'copy' -> mode: 'link'

MANUAL (2 -- not auto-edited):
- workflows/tspipe.nf -- ORGANIZE_OUTPUT wiring
- main.nf -- workflow.onComplete block

## What to validate next

1. `nextflow run . -profile test,singularity --input /tmp/cnv_wiring/validation_samplesheet.csv -stub` -- DAG validates
2. Real run on 25NGS1307 with default outdir; confirm clinical/ structure matches expected layout
3. `du -shL` on the outdir -- physical bytes should be ~5 GB, not ~10 GB
4. After-cleanup directory listing should show only clinical/ and pipeline_info/ under each sample
