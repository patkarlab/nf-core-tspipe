# tools/build_artefacts/

One-off build scripts that produce tracked reference data elsewhere in
the repository. Each script is the source of truth for a specific
artefact: if you change the panel BED, the reference build, or any other
input these scripts consume, re-run the relevant script and commit the
updated output.

## Scripts

| Script                              | Produces                                              | Input                                            |
|-------------------------------------|-------------------------------------------------------|--------------------------------------------------|
| `collapse_to_exonwise.py`           | `assets/myeloid/MYOPOOL_240125_UBTF_Exonwise_hg38.bed` (or wherever your panel exonwise BED lives) | Segment-level panel BED                          |
| `regenerate_cnv_scatter_regions.py` | `assets/myeloid/cnv_scatter_regions.txt`              | Panel BED (the same one CNVKit runs against)     |
| `scatter_chr_gene_standalone.py`    | Per-chromosome exon-level CNV scatter PDF (run-time)  | CNVKit `.cnr` and `.cns` outputs                 |

## When to re-run

### `collapse_to_exonwise.py`

Collapses a segment-level panel BED into one row per exon by grouping
contiguous segments sharing the same `(chrom, exon_label)`. Re-run when:

- The panel BED changes (new genes added, hotspots updated, panel
  redesign).
- The exon-naming convention changes upstream and the canonical
  labels shift.

```bash
python tools/build_artefacts/collapse_to_exonwise.py \
    --bed   path/to/MYOPOOL_240125_UBTF_hg38.bed \
    --out   path/to/MYOPOOL_240125_UBTF_Exonwise_hg38.bed
```

Then commit the new BED.

### `regenerate_cnv_scatter_regions.py`

Builds the per-page scatter region list (`cnv_scatter_regions.txt`)
directly from the panel BED. The legacy `chrwise_list.txt` was
hand-curated against hg19 coordinates; running CNVKit on hg38 and
plotting against hg19 regions produces empty scatter pages because
nothing overlaps. This script keeps the regions in sync with whatever
panel + reference build the pipeline currently runs against.

Re-run when:

- The panel BED changes (any reason).
- You switch reference build (hg19 ↔ hg38, masked ↔ unmasked) — the
  regions list bakes in genomic coordinates, so a build switch
  invalidates the file.

```bash
python tools/build_artefacts/regenerate_cnv_scatter_regions.py \
    --bed path/to/MYOPOOL_240125_UBTF_hg38.bed \
    --out assets/myeloid/cnv_scatter_regions.txt
```

Then commit the new regions file.

### `scatter_chr_gene_standalone.py`

Per-chromosome exon-level CNV scatter PDF generator. A port of
patkarlab/MyOPool's `custom_scatter_chrwise.py`, restructured to read
`.cnr` and `.cns` once via pandas (5-10x faster than the original
line-by-line implementation), use logging instead of print, be
importable as a function, and handle missing files gracefully.

This is a runtime tool — invoked per-sample on demand rather than
producing a tracked output file. Kept here alongside the other CNV
plotting tooling for discoverability. Consider folding into
`bin/12b_cnv_plots.py` (or wherever the pipeline's CNV plotting
module lives) if the two scripts converge.

## Provenance

These scripts were carried over from the production
`targeted-seq-pipeline` tree during the nf-core port. They produce
artefacts the pipeline depends on, but they themselves are build-time
tools rather than runtime modules — they don't run during `nextflow
run`, only when a maintainer needs to regenerate one of the outputs.
