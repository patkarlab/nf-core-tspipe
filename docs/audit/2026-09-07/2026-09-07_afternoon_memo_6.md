# 2026-09-07 afternoon, part 2 -- memo addendum 6 (CNV tab locked; item 12 done except 7b's DAG retirement)

Session end HEAD 591c341. Commits since memo 5: d703a62 DASH_CNV_V1a (legacy
views removed, clinical/cnv in the bundle), 69f4792 VIZ_V1 (styled scatters +
reconCNV), 80ac4d2 exec bits, b418463 VIZ_V1b (genome overview with arm
medians; STYLED_SCATTER removed; exon rows), eb171bd DASH_CNV_V1b (chromosome
sub-tabs), 591c341 EXON_PLOTS_V1a (cache bust).

## CNV tab, final order

summary line (PURPLE status/purity/ploidy/sex, sex check, tier counts,
blacklist) | consensus table (arms K G B P E H, tiers) | DECoN table |
genome-wide: per-bin log2 as faint points with ONE median line per chromosome
ARM (red < -0.25, green > +0.20; values under the labels), BAF, PURPLE CN |
reconCNV (bokeh, iframe + open link) | chromosome pages as 24 sub-tabs |
exon-level figures (chromosomes with a consensus call, a DECoN call at
BF >= 5, or a focal-CNV gene; rows of <= 120 exons wrapped at gene boundaries).
Nothing legacy. Every card keeps the "Include in report" selection.

## Pipeline pieces added today for this

CHROM_PAGES (pages + genome overview), RECONCNV (host env reconCNV from
tools/reconcnv/environment.yml; adapter prep_reconcnv_inputs.py + panel
config; placeholder HTML on failure), ORGANIZE_OUTPUT routing into
clinical/cnv/{consensus,exon_plots,chrom_pages,decon,purple,sex_check,reconcnv},
make_report_bundle.py copies clinical/cnv/, parsers/cnv_v2.py, template block.
STYLED_SCATTER was built and then removed the same day: its overview is
replaced by the arm-median genome figure and its per-chromosome/per-gene
views were redundant with the pages.

## Lessons

- bin/ scripts are not hashed by Nextflow: a renderer change needs a bash
  comment with a version in the module script (EXON_PLOTS_V1a, CMX_V2_4), and
  DASHBOARD needs `process.withName DASHBOARD cache=false` in a throwaway config.
- Scripts added to bin/ must carry the executable bit (git records it);
  prep_reconcnv_inputs.py and cnvkit_scatter_styled.py did not.
- Recon output cut with `cut -c1-N` truncates emit names; read anchors whole.
- The bundle script whitelists what ships; new clinical/ subtrees must be added there.

## Next (order proposed)

1. A1b: SEX_CHECK from chrX heterozygosity (v2 catalog, 76 sites) with the
   depth ratio as a second vote; 1250 is the test case.
2. BAF_V2 detector: genome-wide arms/segments on the v2 catalog; consensus B
   arm genome-wide; the 17p verdict kept as a field.
3. 7b in the DAG: retire ZSCORE_CNV, CNV_CONCORDANCE, CNV_CLINICAL_REPORT,
   CNV_PLOTS and the legacy ORGANIZE routes; re-point cnv_annotate.py at the
   consensus table; drop parsers/cnv.py's legacy fields.
4. CNVkit segmentation sensitivity (IKZF1, BTG1); SNP windows as CNVkit
   targets in the next PoN rebuild (clean depth on the 17p block).
5. Housekeeping: nextflow clean for the stub sessions; untracked-files decision.
