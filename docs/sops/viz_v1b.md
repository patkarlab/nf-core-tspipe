# VIZ_V1b -- genome overview with arm medians; STYLED_SCATTER removed; exon figures in rows -- 2026-09-07

- bin/plot_genome_overview.py (new): per-bin log2 as faint points with one median
  line per chromosome ARM (red < -0.25, green > +0.20, dark otherwise; values under
  the labels), BAF (grey/green), PURPLE CN. Run inside CHROM_PAGES -> chrom_pages/<id>.genome.png;
  shown as "Genome-wide" above reconCNV.
- STYLED_SCATTER removed end to end (module, wiring, config, ORGANIZE, parser, template):
  its overview is replaced by the above; per-chromosome and per-gene views were
  redundant with the chromosome pages.
- bin/plot_exon_ratio.py v1.3: exon figures wrapped into rows of <= 120 exons at gene
  boundaries, equal exon width across rows. EXON_PLOTS rule unchanged: a chromosome
  is drawn when it carries a non-neutral consensus gene, a DECoN call at BF >= 5, or a
  focal-CNV gene (assets/<panel>/targets.focal_cnv.bed).

Placement (repo root)
    cp <bundle>/bin/plot_genome_overview.py <bundle>/bin/plot_exon_ratio.py bin/ && chmod +x bin/plot_genome_overview.py bin/plot_exon_ratio.py
    cp <bundle>/tools/patches/2026-09-07/patch_viz_v1b.py tools/patches/2026-09-07/
    python3 tools/patches/2026-09-07/patch_viz_v1b.py [--apply]
    git rm modules/local/styled_scatter.nf
