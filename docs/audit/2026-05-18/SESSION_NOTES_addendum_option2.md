# 2026-05-18 - Addendum: Option 2 clinical/ trim

## Context

After apply_organize_output.py (part 1) landed, the user reviewed the
deliverable list and asked whether the per-tool FLT3-ITD VCFs (and
related raw outputs) were actually needed in clinical/, since the
pathologist-facing artifact is the consensus TSV alone.

## Decision

Trim clinical/ to Option 2: include the consensus TSV at top level,
drop the entire flt3_itd/ subdirectory. Keep CNVkit subdir plots
(combined/, overview/, per_chromosome/, per_gene/) -- those are
inspected during case review.

## Rationale

- flt3_consensus.tsv already contains the multi-caller call,
  classification (PASS_HIGH / PASS_LOW / REVIEW_REQUIRED), and
  per-tool agreement metadata. That is the report-driving artifact.
- The raw per-tool outputs (final_FLT3_ITD.vcf, filt3r.results.{vcf,json},
  getitd/ tree) are an audit trail. They live in Nextflow's work/
  directory after the run and are accessible there for the rare
  REVIEW_REQUIRED case that needs deep inspection.
- Removing the audit-trail subdir from clinical/ reduces cognitive
  load when browsing per-sample output. Disk impact is small in
  absolute terms (~few MB per sample) but the file count drops
  meaningfully.

## What clinical/ contains after part 2

```
<outdir>/<sample>/clinical/
    <sample>.final.bam                            (hardlink, ~5 GB)
    <sample>.final.bam.bai
    <sample>.somaticseq.clinical.final.tsv
    <sample>.somaticseq.filtered.tsv
    <sample>_u2af1_pileup_report.txt
    <sample>_u2af1_rescue.tsv                     (when >100 bytes)
    <sample>_flt3_consensus.tsv
    <sample>_exon_coverage.tsv
    <sample>_hsmetrics.txt
    <sample>_fastp.html
    <sample>_dashboard.html
    cnv_consensus/
        <sample>_cnv_clinical.tsv
    cnvkit_plots/
        <sample>.final-diagram.pdf
        <sample>.final-scatter.png
        combined/
        overview/
        per_chromosome/
        per_gene/
```

That is 11 top-level files + 2 subdirectories, vs the part-1 plan's
11 files + 3 subdirectories (the third being flt3_itd/).

## Changes in part 2

| Action | Path | Reason |
|---|---|---|
| Replaced | bin/organize_output.py | Dropped 5 CLI args + FLT3-ITD ensemble section |
| Replaced | modules/local/organize_output.nf | Dropped 5 input paths |
| Replaced | tools/patches/2026-05-18/manual_edits_required.md | New (simpler) join chain |
| Edited | subworkflows/local/preprocessing.nf | Added `fastp_html` emit |
| Edited | subworkflows/local/cnv_calling.nf | Added `cnvkit_diagram_pdf`, `cnvkit_scatter_png` emits |

## What part 1 left in place that is now unused

These are harmless and left as-is:

- modules/local/flt3_itd_ext.nf has a `summary` emit added in part 1.
  It is no longer consumed but may be useful for D2 (IGV_REPORTS real
  implementation) or future audit-trail features.
- The cnv_plots.nf module retains `diagram_pdf`, `scatter_png`, and
  `plots_dir` emits added in part 1 -- all three are still consumed
  via CNV_CALLING's new emit pass-throughs.

## Carry-forward implications

D2 (IGV_REPORTS real implementation) is unaffected -- IGV reports
were already descoped from clinical/ in part 1 because the module is
still a stub.

D1 (PINDEL_FLT3_FILTER) is unaffected -- pindel_flt3.vcf was already
descoped.

## Validation expectations on 25NGS1307 (unchanged)

- Mean coverage: 2,994x
- Low-cov exons: 5
- Selected / off-bait: 64.7% / 35.3%
