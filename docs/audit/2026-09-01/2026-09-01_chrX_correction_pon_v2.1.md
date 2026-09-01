# Correction: chrX reference semantics and male PoN v2.1 rebuild

Date: 2026-09-01 (evening; corrects part of the same-day execution memo)
Scope: Twist myeloid panel (TE-99430185), male CNVkit PoN
Marker: BPT_HAPLOID_X_V1

## What was wrong

Two related errors in the v2 build, both mine (Claude):

1. Design decision. The scaffold encoded "no -y anywhere; sex handled by
   stratification." CNVkit sex-normalises each input sample to the
   reference's target scale, so a flagless `cnvkit.py reference` from 24
   male inputs silently produced a DIPLOID-X reference -- the opposite of
   the design intent. Against that reference, the application layer
   (cnvkit_wrapper.py, which passes -y for male samples per production
   convention) would have produced systematic false chrX loss calls on
   every male sample.

2. Memo interpretation. The execution memo attributed the 409 blacklisted
   chrX bins to "hemizygous half-depth variance ... mean log2 stays
   centered." The claim was written without checking chrX rows. The data
   say otherwise: LOO chrX mean_log2 -0.947 with fp_loss_rate 0.916
   (per-tile rows at -1.00 / fp_loss 1.000) -- a systematic hemizygous
   offset flagged as deep loss in every iteration, not variance. The
   execution memo's open item 1 (chrX masking vs male sensitivity) was a
   downstream symptom of this build defect.

## Evidence (build_v2)

ref chr1 mean log2 -0.113 (430 bins) vs ref chrX +0.111 (416 bins):
diploid-X scale. LOO chrX (101 gene/tile rows): mean -0.947, fp_loss
0.916. Blacklist: 409/416 chrX bins.

## Fix

Per-stratum haploid-X flag (patch_bpt_haploid_x.py, applied 2026-09-01,
backups *.bak_bpt_haploid_x_*): the male stratum reference AND its LOO QC
are built with -y; the female stratum stays flagless (diploid-X). This
replaces the "no -y ever" doctrine and aligns build semantics with the
application layer and production convention. GATK RC-PoN, BAF background,
allelic counts, conformity, intervals: sex-flag-free, unchanged, carried
forward from v2 unmodified.

Rebuild: -resume into /goast/hemat_data/pon_twist/build_v2.1; 200 tasks
cached, 2 executed (reference, LOO), 2 m 40 s.

## Verification (build_v2.1)

- ref chr1 -0.079 vs chrX -0.844: haploid-X scale as intended.
- LOO chrX: mean_log2 -0.013, fp_loss 0.017 -- centered.
- Blacklist: 933 -> 549 bins. chrX 409 -> 15. X-linked driver-gene bins
  (SMC1A/STAG2/BCOR/KDM6A/DDX3X/UBA1/PHF6/ZRSR2/ALAS2/GATA1/PIGA/BTK)
  ~328 -> 5: male chrX CNV sensitivity recovered; execution-memo open
  item 1 is CLOSED for the male stratum.
- Autosomes: 35 gained / 25 lost (net +10 on ~530). Sampled gains are all
  backbone tiles at the thresholds (stdev 0.29-0.34 vs 0.30 cutoff;
  fp_any 0.125-0.167 vs 0.10) -- re-centering flicker (chr1 ref mean
  moved -0.113 -> -0.079), not new signal.
- chrY: 2 of the panel's 3 Y bins blacklisted; Y is not a callable target
  on this panel.

## Disposition

- v2 CNVkit artifacts: superseded, never consumed by any application run
  (no clinical exposure). build_v2 tree retained on disk for audit.
- assets/twist_myeloid reseeded from v2.1 (4 CNVkit files); manifest
  pon_male_v2.1.md5 + pon_male_v2.1.stats.txt replace the v2 pair.
- Doctrine for the female arm, when re-hybridised normals land: build
  flagless (diploid-X); the per-stratum yflag in the modules already
  encodes this.
