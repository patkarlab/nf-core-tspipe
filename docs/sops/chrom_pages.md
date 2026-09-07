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
