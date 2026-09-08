# CHROM_PAGES_V1 -- per-chromosome CNV pages in the pipeline -- 2026-09-07

bin/plot_targets_trio.py (v2.7) as a module: for every sample, one page per
chromosome with targets: depth per exon/backbone/SNP window (TITAN colours),
BAF from the v2-catalog allelic counts (grey balanced, green deviated),
PURPLE copy number per target, gene bands, and one exon panel per gene
(all exons labelled, DECoN brackets, PURPLE CN). Index TSV for the dashboard.
Published to <sample>/cnv_consensus_multi/chrom_pages/ beside exon_plots/.

Files
    bin/plot_targets_trio.py          (git mv tools/plot_targets_trio.py bin/ then overwrite)
    modules/local/chrom_pages.nf
    tools/patches/2026-09-07/patch_chrom_pages_v1.py   tspipe.nf + twist_apply.config

Placement (repo root)
    git mv tools/plot_targets_trio.py bin/plot_targets_trio.py
    cp <bundle>/bin/plot_targets_trio.py bin/ && chmod +x bin/plot_targets_trio.py
    cp <bundle>/modules/local/chrom_pages.nf modules/local/
    cp <bundle>/tools/patches/2026-09-07/patch_chrom_pages_v1.py tools/patches/2026-09-07/
    python3 tools/patches/2026-09-07/patch_chrom_pages_v1.py [--apply]

Inputs joined per sample: consensus JSON, GATK allelic counts, DECoN filtered
(placeholder when off), PURPLE dir (placeholder when off). Assets as values:
panel.combined.filtered.bed, snp_sites.baf.base.bed, baf_background.tsv.
Next: ORGANIZE_OUTPUT routing into clinical/cnv/ and the dashboard CNV tab
(item 12).

## Addendum 2026-09-08 — cytoband strip (IDEO_V1) and DECoN bracket rule (DECON_BRACKET_V1)

Cytoband strip. `bin/plot_targets_trio.py --cytoband <cytoBand_hg38.txt>` (optional;
passed by CHROM_PAGES from `ch_cnv_cytoband`) adds a fifth row under the targets track
on every `--every-chrom` page. The strip is drawn in target space: consecutive targets
whose midpoints fall in one band form one block spanning those targets' x range, so it
stays aligned with the panels above; bands without targets collapse to nothing, and a
dotted divider before a block marks that untargeted bands were skipped. Shading follows
Giemsa stain (gneg white, gpos25..gpos100 greys, acen red, gvar/stalk light grey); the
band name is written inside the block when it is wide enough (rotated when narrow,
omitted when very narrow). Physical Mb ranges remain in the targets footer. The
grouped and genes styles are unchanged.

Band labels. Gene footer: `9p21.3  21.97-21.99 Mb`. Backbone runs of >= 10 targets
that are wide enough to label: `9q21.33-q34.3 backbone (n=59)` (first-last band of the
run). Gene-panel titles: `CDKN2A (3 ex)  9p21.3`.

DECoN brackets in the gene panels. DECoN reports a call spanning several genes once per
gene: identical `CNV.ID`, `Start`, `End`, with `Gene` naming the gene and `Start.b`/`End.b`
the exon indices within it. Brackets are therefore matched on `Gene` when the column is
present (fallback: coordinate overlap when it is empty) and drawn once per `CNV.ID` per
panel. Before this rule every gene inside a multi-gene deletion drew one bracket per row
(CDKN2A/CDKN2B/PAX5 on 26CGH60, CNV.ID 6, 15 exons).

Cache. Both are `bin/` changes; the module bash comment carries
`IDEO_V1 ... DECON_BRACKET_V1`. A CHROM_PAGES change re-executes CHROM_PAGES (8),
ORGANIZE_OUTPUT (8), DASHBOARD and REPORT_BUNDLE: 18 tasks. Patchers:
`tools/patches/2026-09-08/patch_chrom_pages_ideogram_v1.py`, `patch_decon_bracket_v1.py`.

Offline check without Nextflow: locate the cached task with
`nextflow log <uuid> -f process,tag,status,workdir | grep CHROM_PAGES | grep <meta.id>`,
take the image from `grep -o "/[^ ]*\.\(img\|sif\)" .command.run`, copy the
`plot_targets_trio.py` invocation from `.command.sh` with `--every-chrom` replaced by
`--chrom chrN` and `--out` pointed at /tmp, call the script by absolute path, and run
`singularity exec -B /goast,/tmp $IMG bash run.sh` with `MPLCONFIGDIR` under /tmp.
