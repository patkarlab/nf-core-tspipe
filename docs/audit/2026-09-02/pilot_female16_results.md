# Pilot results -- Female16 through the twist overlay (2026-09-02)

End to end: 51 processes, REPORT_BUNDLE produced, four resume cycles.
43.7 CPU-h total; clean wall-clock deferred to the next sample.

## Fixes applied (tools/patches/2026-09-02/, all in bin/, backward compatible)
- cnvkit_wrapper: header-only annotated genemetrics on zero calls
  (module contract required the file; stub touch hid the gap).
- Exon token _Ex_ -> _(?:Ex|exon)_ in cnv_plots, cnv_concordance,
  cnv_clinical_report, zscore_cnv, cnvkit_wrapper. Legacy parsers
  fell through to raw twist names -> exon-level pseudo-genes in the
  K/Z arms; the consensus join would miss on any sample with calls.
- cnv_consensus_multi: PureCN flagged=TRUE -> P calls advisory, no
  support. Schema unchanged.
- 17_variant_validator: probe timeout 30 s -> 150 s.
- VV stack: root cause of SOP Failure Mode B found (SOP addendum).

## Readout (stress test, NOT a specificity number)
Female16 is batch B5, 12-plex, sentinel-WARN. 18% of autosomal bins
sit below -0.5 log2 in the standardized CR (pre-PCA), heaviest on
AT-rich chr4/5/6/13/18: the 12-plex collapse signature seen through
the CNV arms.
- K: 0 autosomal FP. Z: 1 (RAD51). BAF 17p: NEUTRAL (f_est 0.149 vs
  f_min 0.10; MAD gate held). G: 17 whole-chromosome losses, segment
  means 0.11-0.14 below bin medians against GATK's -0.152 floor.
  P: purity 0.46 spurious fit, flagged; 4 calls, now advisory.
- Consensus after the flagged-P patch: 0 reportable autosomal calls.
- chrX +0.94 in all ratio arms; K cn=2 neutral, Z/G GAIN -- as
  predicted for a female against the male reference.
- G and P errors are correlated on sex-discordant input (shared
  male reference set); the consensus cannot protect against that.

## Decisions and queue
- Next sample: Female18 (sentinel-passing). Definitive specificity
  needs protocol-matched normals (male LOO or the 8-plex arm).
- Wire a dropout gate into the overlay (standardized-CR tail
  fraction) before G/P are trusted; evaluate G neutral band at
  CNVkit's -0.25.
- BAF f_min: get the female cohort distribution before it decides alone.
- panel_gene_chroms.tsv: _5UTR/_intronic names; DKC1_5UTR has no data
  in any arm; GATA2_intron4 (5 tiles) falls through clean_gene.
- One gene-naming helper shared by the CNV scripts (replaces five
  regex copies).
- cnv_plots.load_gene_annotations gates on a clean_gene column the
  wrapper never writes: dead branch, LOO-summary fallback in use.
- --cnv-only mode = alignment + Mutect2 + CNV chain (PureCN consumes
  the Mutect2 VCF).
- 17_variant_validator: 5 x 120 s per variant is a two-hour hang on a
  dead stack; add a circuit breaker.
- VV: compose dns: pin pending (recreate + relaunch); launcher
  readiness wait 60 s < app load; verify worker CPU > 0 after launch.
