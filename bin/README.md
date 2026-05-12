# bin/

Python helpers copied verbatim from `scripts/` in the original pipeline. These are
on `$PATH` inside every Nextflow process automatically (this is how nf-core
exposes custom logic to its modules).

## What's here and why

Scripts that wrap a third-party tool (fastp, BWA, GATK, ABRA2, CNVKit...) do NOT
live here -- the tool itself is called directly from the module's `script:` block.
What lives here is logic that's genuinely *your* code: filtering rules, consensus
clustering, blacklist matching, output organization.

| bin script              | comes from                | called by module        |
| ----------------------- | ------------------------- | ----------------------- |
| apply_blacklist.py      | scripts/apply_blacklist.py        | variant_filter (library)  |
| flt3_consensus.py       | scripts/09b_flt3_consensus.py     | flt3_consensus.nf         |
| flt3_to_variants.py     | scripts/17b_flt3_to_variants.py   | flt3_to_variants.nf       |
| u2af1_rescue.py         | scripts/u2af1_rescue.py           | u2af1_rescue.nf           |
| variant_filter.py       | scripts/14_variant_filter.py      | variant_filter.nf         |
| cnv_concordance.py      | scripts/12e_cnv_concordance.py    | cnv_concordance.nf        |
| cnv_clinical_report.py  | scripts/12f_cnv_clinical_report.py| cnv_clinical_report.nf    |
| zscore_cnv.py           | scripts/12d_zscore_cnv.py         | zscore_cnv.nf             |
| exon_cnv.py             | scripts/12g_exon_cnv.py           | exon_cnv.nf               |
| cnv_plots.py            | scripts/12b_cnv_plots.py          | cnv_plots.nf              |
| cnv_annotate.py         | scripts/18_cnv_annotate.py        | cnv_annotate.nf           |
| sv_annotate.py          | scripts/19_sv_annotate.py         | sv_annotate.nf            |
| organize_output.py      | scripts/20_organize_output.py     | organize_output.nf        |
| oncovi.py               | scripts/15_oncovi.py              | oncovi.nf                 |
| variant_validator.py    | scripts/17_variant_validator.py   | variant_validator.nf      |
| igv_reports.py          | scripts/16_igv_reports.py         | igv_reports.nf            |
| exon_coverage.py        | scripts/10b_exon_coverage.py      | exon_coverage.nf          |

## What needs adapting before you `nextflow run`

These scripts were written to be called by `run_sample_pipeline.py` and assume
a specific directory layout under `results/{sample}/...`. Two changes per script
are usually needed:

1. **Replace fixed input paths with CLI flags.** Most already use argparse, so
   this is straightforward: add `--input`, `--output` flags instead of computing
   paths from `--sample` and `--results-dir`.
2. **Remove `PIPELINE_DIR` discovery.** Several scripts walk up from
   `os.path.dirname(__file__)` to find the pipeline root for resources. In nf-core
   resources are staged into the work directory by the module, so accept them as
   CLI args instead.

A search-and-replace pass for these patterns:

```python
# Pattern to remove:
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PIPELINE_DIR = os.path.dirname(SCRIPT_DIR)

# Pattern to remove:
def find_input(sample, results_dir):
    return os.path.join(results_dir, sample, ...)

# Replace with: explicit --input flag wired in from the module's script: block.
```

`apply_blacklist.py` is already a clean library + CLI -- it can be used as-is.
`flt3_consensus.py` is also close to clean.

The rest will each need ~10 minutes of cleanup. Best done incrementally: port one
subworkflow at a time, run the test config, and only adapt the bin scripts the
test exercises.
