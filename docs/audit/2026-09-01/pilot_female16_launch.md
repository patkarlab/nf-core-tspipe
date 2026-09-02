# Pilot launch -- Female16 (Phase 5 specificity)

2026-09-01, HEAD 9ad7f6d. Stub-validated launch pattern, real sheet.

- Sample: Female16 (held-out; males are all PoN constituents).
  Inputs byte-verified vs archive; gzip -t OK.
- ID drops -TwistMy suffix (hyphen safety in downstream tools).
- sex=male in sheet: routes CNVkit to the male PoN, same footing as
  GATK/PureCN/BAF. chrX +1 log2 expected everywhere -> haploid-X
  sensitivity check; specificity scored on autosomes only.
- PureCN FAILED sentinels expected (copy-flat normal).
- Noted: purecn.nf consumes raw Mutect2 VCF -> hard dependency;
  any future --cnv-only mode = alignment + Mutect2 + CNV chain.
- Log: /tmp/pilot_female16_run.log. Launch time: (fill in)
