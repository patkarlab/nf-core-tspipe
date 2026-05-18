# 2026-05-18 - ORGANIZE_OUTPUT module + scratch cleanup

## Session goal

Land the final per-sample organization step for the nf-core port:
a single `clinical/` subdirectory containing only deliverables, with
intermediate scratch dirs removed at run end. ~5 GB per sample, down
from ~6.3 GB.

## Design decisions

### Option B chosen for output organization

Trade-off table compared three approaches:

| Option | Mechanism | Pro | Con |
|---|---|---|---|
| A | ORGANIZE_OUTPUT reaches into outdir, hardlinks + deletes | Matches bootstrap sketch | Non-idiomatic; resume semantics fragile |
| **B** | publishDir mode 'link' everywhere + workflow.onComplete cleanup | One inode end-to-end; cleanup separated from data flow | Requires flipping every publishDir |
| C | publishDir only on ORGANIZE_OUTPUT; nothing else publishes | Cleanest; no cleanup step | Mid-pipeline debugging requires work/ navigation |

B selected. C is the longer-term destination but a bigger refactor than
this session.

### IGV_REPORTS dropped from deliverables

The IGV_REPORTS module is currently a stub (`echo "STUB: IGV_REPORTS"`).
Publishing its 0-byte HTML output as a "clinical IGV review report" would
be actively misleading. Added to carry-forward backlog.

### pindel_flt3.vcf descoped

No PINDEL_FLT3 module exists in the port. PINDEL emits genome-wide
calls; FLT3-region filtering needs a separate tiny bcftools-view
module. Added to carry-forward backlog.

### U2AF1 deliverables route directly from VARIANT_CALLING, not via ANNOTATION

ANNOTATION consumes the U2AF1 rescue TSV as input; it doesn't produce it.
Surfacing the report and rescue TSV through ANNOTATION would muddy the
data-flow semantics. Routed both directly from VARIANT_CALLING by adding
a `u2af1_report` emit (already had `u2af1_tsv`).

### Filesystem-mismatch handling

`publishDir mode: 'link'` silently degrades to copy when source and dest
are on different mounts. Two safeguards:

1. `nextflow.config` outdir default changed from `"results"` (relative)
   to `/goast/hemat_data/nfcore_runs/default` (anchored to xfs mount).
2. `workflow.onComplete` performs a `stat -c %d` mount comparison;
   warns (does not fail) on mismatch.

## Module emit edits

Five upstream emit edits required to give ORGANIZE_OUTPUT clean handles:

| Module | Edit |
|---|---|
| `fastp.nf` | html and json emits keyed on meta (were bare path) |
| `flt3_itd_ext.nf` | add `summary` emit (was glob-only) |
| `cnv_plots.nf` | split `diagram_pdf` and add `scatter_png` (exact filenames) |
| `subworkflows/local/annotation.nf` | add `filtered_tsv` emit (was internal-only) |
| `subworkflows/local/variant_calling.nf` | add `u2af1_report` emit |

## Files added

- `bin/organize_output.py` - hardlink orchestrator, Python 3.6 stdlib only
- `modules/local/organize_output.nf` - process with ~20 explicit inputs
- `tools/run_pipeline.sh` - interactive launcher prompting for outdir/samplesheet
- `docs/audit/2026-05-18/` - this session log

## Manual integration required

The apply script does not auto-edit `workflows/tspipe.nf` or `main.nf`
because both are integration points where automated splice is risky.
Exact text to paste into both lives in
`tools/patches/2026-05-18/manual_edits_required.md`.

## Validation expectations (25NGS1307)

After integration, on the validation sample the run should produce:

```
<outdir>/25NGS1307/clinical/
    25NGS1307.final.bam                            (hardlink, ~5 GB)
    25NGS1307.final.bam.bai
    25NGS1307.somaticseq.clinical.final.tsv
    25NGS1307.somaticseq.filtered.tsv
    25NGS1307_u2af1_pileup_report.txt
    25NGS1307_flt3_consensus.tsv
    25NGS1307_exon_coverage.tsv
    25NGS1307_hsmetrics.txt
    25NGS1307_fastp.html
    25NGS1307_dashboard.html
    cnv_consensus/
        25NGS1307_cnv_clinical.tsv
    cnvkit_plots/
        25NGS1307.final-diagram.pdf
        25NGS1307.final-scatter.png
        combined/ overview/ per_chromosome/ per_gene/
    flt3_itd/
        25NGS1307.final_FLT3_ITD.vcf
        25NGS1307.final_FLT3_ITD_summary.txt
        25NGS1307_filt3r.results.vcf
        25NGS1307_filt3r.results.json
        getitd/                                    (out_needle excluded)
```

Coverage numbers should not change from yesterday:
- Mean coverage: 2,994x
- Low-cov exons: 5
- Selected / off-bait: 64.7% / 35.3%

If they drift, an upstream channel was renamed inadvertently.

## Carry-forward (unchanged from yesterday)

- B1 - per-caller VCF discrepancy on 25NGS1307
- B2 - 69-entry annotated-tier port-only residual
- B3 - Phase 1 stubs (VARIANT_VALIDATOR, ONCOVI, FLT3_TO_VARIANTS, IGV_REPORTS)
- B4 - KMT2A-PTD detection
- B5 - Rescue_Note column missing
- C1-C5 - cosmetic polish batch

## New carry-forward items from this session

- D1 - PINDEL_FLT3_FILTER module: tiny bcftools-view module to extract
  FLT3-region calls from PINDEL.out.vcf, then wire into ORGANIZE_OUTPUT
- D2 - IGV_REPORTS real implementation (currently stub); when real,
  add channel back into ORGANIZE_OUTPUT join chain
- D3 - Consider Option C migration (strip publishDir from non-organize
  modules entirely) once the team is comfortable debugging from work/
