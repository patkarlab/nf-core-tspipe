# Porting status (historical snapshot)

> **This document is a historical snapshot from the port-era of nf-core-tspipe.**
>
> It was last updated at git tag `stage1-verified` (commit `a7c640e`,
> "preprocessing parity with production on 25NGS1307"). The information
> below describes the state of the port at that time. The port is now
> complete: every module marked "stub" below is wired and operational,
> as verified by the 2026-05-19 16-sample validation run.
>
> Do not use this document for current operational status. For current
> status, see `README.md` and `docs/INSTALL.md` in the repo root.
>
> Kept under `docs/audit/` for historical reference only.

---

# Porting status

Per-module status. "Faithful" = command-line is translated from the original
Python wrapper and the module should run as-is once tools are on PATH or
containers are pulled. "Stub" = module structure is correct but `script:` block
is a placeholder; copy the command line out of the source script in scripts/.

## Preprocessing

| module                    | status   | source script              |
| ------------------------- | -------- | -------------------------- |
| fastp.nf                  | faithful | scripts/01_trim_adapters.py |
| bwa_mem.nf                | faithful | scripts/02_align.py        |
| markduplicates.nf         | faithful | scripts/03_mark_duplicates.py |
| bqsr.nf                   | faithful | scripts/04_bqsr.py         |
| abra2.nf                  | faithful | scripts/05_abra2.py        |

## Variant calling

| module                    | status   | source script              |
| ------------------------- | -------- | -------------------------- |
| mutect2.nf                | faithful | scripts/06_variant_callers.py (Mutect2 section) |
| vardict.nf                | stub     | scripts/06_variant_callers.py (VarDict section) |
| varscan.nf                | stub     | scripts/06_variant_callers.py (VarScan section) |
| strelka.nf                | stub     | scripts/06_variant_callers.py (Strelka section) |
| freebayes.nf              | stub     | scripts/06_variant_callers.py (FreeBayes section) |
| platypus.nf               | stub     | scripts/06_variant_callers.py (Platypus section) |
| deepsomatic.nf            | stub     | scripts/06_variant_callers.py (DeepSomatic section) |
| somaticseq.nf             | faithful | scripts/07_somaticseq.py    |
| pindel.nf                 | stub     | scripts/08_pindel.py        |
| u2af1_rescue.nf           | stub     | scripts/u2af1_rescue.py     |

## FLT3-ITD ensemble

| module                    | status   | source script               |
| ------------------------- | -------- | --------------------------- |
| bam_to_flt3_fastq.nf      | faithful | scripts/bam_to_flt3_fastq.py |
| flt3_itd_ext.nf           | faithful | scripts/09_flt3_itd.py      |
| filt3r.nf                 | faithful | scripts/09_flt3_itd.py      |
| getitd.nf                 | faithful | scripts/09_flt3_itd.py      |
| flt3_consensus.nf         | faithful | scripts/09b_flt3_consensus.py |

## QC

| module                    | status   | source script              |
| ------------------------- | -------- | -------------------------- |
| hsmetrics.nf              | stub     | scripts/10_hsmetrics.py    |
| exon_coverage.nf          | stub     | scripts/10b_exon_coverage.py |

## CNV

| module                    | status   | source script              |
| ------------------------- | -------- | -------------------------- |
| cnvkit.nf                 | stub     | scripts/12_cnv_calling.py  |
| exon_cnv.nf               | stub     | scripts/12g_exon_cnv.py    |
| zscore_cnv.nf             | stub     | scripts/12d_zscore_cnv.py  |
| cnv_plots.nf              | stub     | scripts/12b_cnv_plots.py   |
| cnv_concordance.nf        | stub     | scripts/12e_cnv_concordance.py |
| cnv_clinical_report.nf    | stub     | scripts/12f_cnv_clinical_report.py |
| cnv_annotate.nf           | stub     | scripts/18_cnv_annotate.py |

## SV

| module                    | status   | source script              |
| ------------------------- | -------- | -------------------------- |
| sv_callers.nf             | stub     | scripts/11_sv_callers.py   |
| sv_annotate.nf            | stub     | scripts/19_sv_annotate.py  |

## Annotation

| module                    | status   | source script              |
| ------------------------- | -------- | -------------------------- |
| vep_annotate.nf           | stub     | scripts/13_annotate.py     |
| variant_filter.nf         | faithful | scripts/14_variant_filter.py |
| variant_validator.nf      | stub     | scripts/17_variant_validator.py |
| oncovi.nf                 | stub     | scripts/15_oncovi.py       |
| flt3_to_variants.nf       | stub     | scripts/17b_flt3_to_variants.py |

## Reporting

| module                    | status   | source script              |
| ------------------------- | -------- | -------------------------- |
| igv_reports.nf            | stub     | scripts/16_igv_reports.py  |
| organize_output.nf        | stub     | scripts/20_organize_output.py |

## PoN build (BUILD_PON workflow)

| module                    | status   | source script              |
| ------------------------- | -------- | -------------------------- |
| cnvkit_pon_build.nf       | faithful | run_masked_realign.sh (cnvkit batch step) |
| cnv_loo_qc.nf             | faithful | scripts/12c_cnv_loo_qc.py  |
| build_sex_pon.nf          | faithful | scripts/12c_build_sex_pon.py |

## How to convert a stub to faithful

1. Open the stub (e.g. `modules/local/vardict.nf`) and the source script
   (`scripts/06_variant_callers.py`).
2. Find the function that builds the command line (search for `VARDICT` /
   `VarDict` in the source).
3. Copy the command into the stub's `script:` block, replacing the `echo "STUB"`
   line.
4. Replace input paths with the variable names defined in the `input:` block
   (e.g. `${bam}`, `${fasta}`, `${bed}`).
5. Make sure outputs match the `output:` declarations exactly -- both the
   filename pattern and the channel emit name.
6. Replace any hardcoded conda env path (`/home/hemat/anaconda3/envs/targeted-seq/bin/...`)
   with either a bioconda package name in a `conda` directive, or a container
   URI in a `container` directive.

There is no automated way to do this conversion -- the source scripts call
tools via Python subprocess wrappers with quite a lot of glue code, so each
module needs a human read of the original to extract the actual command.

## Suggested porting order

For a working end-to-end MVP, fill in stubs in this order:

1. `vep_annotate.nf` + the remaining variant callers (so variant_calling and
   annotation subworkflows run end-to-end)
2. `cnvkit.nf` (CNV subworkflow MVP -- the other CNV stubs depend on its outputs)
3. `hsmetrics.nf` + `exon_coverage.nf` (QC)
4. `sv_callers.nf` (SV)
5. `oncovi.nf` + `variant_validator.nf` (annotation polish)
6. `organize_output.nf` + `igv_reports.nf` (final deliverables)

Then iterate. The `-profile test` configuration will let you smoke-test as you go.
