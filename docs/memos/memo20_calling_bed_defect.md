# Memo 20 — Calling interval list omitted three probe categories

**Date:** 12 September 2026
**Pipeline:** nf-core-tspipe, Twist myeloid panel TE-99430185
**Affects:** all cases analysed on the Twist myeloid assay before 12 September 2026
**Resolved in:** v1.0.2 (commits 5760d34, 0902748, 4edd46d)
**Status:** fixed and verified on both hosts; clinical re-check scope outstanding

---

## 1. Summary

`params.bed`, the interval list handed to every variant caller, was set to a
derived asset that had been assembled from only two of the five categories in
the Twist Main probe file. Three categories — 15 hotspot tiles, 370 17p SNP
windows and 4 BAF autosomal sites — were never merged in.

IDH1 exon 4, IDH2 exon 4 and BRAF exon 15 are present on the panel **only** as
hotspot-category tiles. Losing that category removed them entirely from the
callable space. These regions were captured and sequenced normally at
900–1700x, coverage QC reported them as 100% covered at every threshold, and
no caller ever examined them. No variant was called there, and none was
filtered — the regions were simply absent from the question being asked.

Consequently, **no IDH1, IDH2 or BRAF variant could be detected in any case
reported on this assay** up to 12 September 2026.

## 2. How it was discovered

A fellow compared eight validation cases against results from the previous
MIPS-derived panel and reported that IDH1 was missing in 26CGH0799 and IDH2 in
26CGH0885. Comparison of real cases against the predicate assay was the only
control capable of detecting this: coverage QC read from a complete file and
reported no problem, and the golden regression compared two runs that shared
the same defective interval list, so neither looked where the other did not.

## 3. Root cause

The Twist Main probe BED (6,244 rows) partitions exactly into five derived
category files:

| File | Rows |
|---|---|
| targets.exonic.bed | 5,838 |
| targets.hotspot.bed | 15 |
| targets.17p_snp.bed | 370 |
| targets.baf_autosomal.bed | 4 |
| targets.focal_cnv.bed | 17 |

`panel.combined.bed` (8,902 rows) was built as `targets.exonic.bed` +
`targets.focal_cnv.bed` + `backbone.hg38.bed` (3,047). The three remaining
categories, 389 intervals, were omitted. `panel.combined.filtered.bed` (8,821
rows) is that file minus 81 intervals removed by the CNV panel-of-normals
noise filter, and it was the file `conf/twist_apply.config` named as
`params.bed`.

Two distinct defects therefore applied:

1. **Category omission.** Nine regions lost: IDH1 exon 4, IDH2 exon 4,
   BRAF exon 15, ANKRD26 5'UTR, MLH1 5'UTR, KLHDC8B 5'UTR, DKC1 5'UTR,
   GATA3 intronic, FANCI intron 31. Also the five germline risk-SNP probes
   (GATA3 rs3781093 and rs3824662, ARID5B rs10994982 and rs10821936,
   IKZF1 rs11978267) and the 370 17p SNP windows.

2. **Wrong file for the purpose.** The PoN noise filter is correct for CNV
   and wrong for variant calling. It additionally removed AKT1 exon 1,
   PTEN exon 3, CCNC exons 6 and 7, and ANKRD26 exons 5, 19, 28 and 29.

The backbone probe file is supplied in probe-space coordinates
(`CNVbb_chr10_10019761_range=chr10_10019761_10019880  0  120  .`) and required
a conversion step, which is the likely reason the build worked from the derived
category files rather than from the Main probe BED directly.

## 4. Clinical impact

Regions that could not be examined in any reported case:

| Region | Clinical significance |
|---|---|
| IDH1 R132 | ivosidenib, olutasidenib eligibility |
| IDH2 R140, R172 | enasidenib eligibility |
| BRAF V600 | hairy cell leukaemia, entity-defining |
| AKT1 exon 1, PTEN exon 3 | reportable coding exons |
| ANKRD26 5'UTR and exons 5/19/28/29 | thrombocytopenia 2 predisposition |
| DKC1, MLH1, KLHDC8B 5'UTRs; FANCI intron 31; GATA3 intronic | germline predisposition and risk spike-ins |

The sequencing data is unaffected and retained, so remediation is re-analysis
from stored BAMs, not re-sequencing.

## 5. The fix

`assets/twist_myeloid/panel.calling.bed` — the merged capture space: Main probe
BED plus CNV backbone probe BED, probe-space rows decoded from the `range=`
suffix, non-primary contigs removed, FAI-sorted, overlapping intervals merged.

- 5,375 intervals, 1,052,904 bp
- md5 `4b7e123966079266e83ce7baf7642ef5`, 215,491 bytes
- `conf/twist_apply.config` `params.bed` repointed
- `panel.combined.filtered.bed` unchanged and retains its CNV role

Applied by `tools/patches/2026-09-12/patch_panel_calling_v1.py`, which verifies
before writing that all 12,336 probe intervals are contained, that named
hotspots are callable, and that **no interval callable under the previous BED
becomes uncallable**. An earlier iteration of the patcher silently discarded the
entire CNV backbone; that regression check is what caught it, and it is the
reason the check exists.

Effect: 462 intervals and 56,071 bp restored across 443 regions.

## 6. Verification (run9, gandalf, 12 September 2026)

Outdir `/goast/hemat_data/twist_val/tspipe_run9`, full re-run (params.bed is in
every task hash), 24 samples' predecessor cohort of 8.

**Both flagged cases now call:**

| Sample | Variant | Position | VAF | Callers | ClinVar | Filter |
|---|---|---|---|---|---|---|
| 26CGH0799 | IDH1 c.394C>T p.Arg132Cys | chr2:208248389 | 25.4% | 6 | Pathogenic/Likely_pathogenic | PASS |
| 26CGH0885 | IDH2 c.418C>G p.Arg140Gly | chr15:90088703 | 28.1% | 5 | Pathogenic | PASS |

Six independent callers on 26CGH0799 agreed within 1.4 percentage points
(FreeBayes 25.3%, Platypus 24.6%, Strelka 25.5%, VarDict 24.8%, VarScan 25.2%,
DeepSomatic 26.0%). Base depth at IDH1 R132 in 26CGH0060: 1,695x.

**No collateral effect:**

- Clinical table row counts: +1 in each of the two positive samples, +0 in the
  other six. No spurious calls introduced.
- Zero IDH/BRAF rows in the six negative samples.
- All eight sex inferences reproduce run8 exactly.
- BAF arm verdicts identical except 26CGH1250 17p GAIN f-estimate 0.256 → 0.251
  (more informative sites on 17p; verdict, confidence and scope unchanged).
- CNV assets are independent of `params.bed`: GATK CNV uses
  `cnv_gatk_intervals`, DECoN `decon_exons_bed` plus a fixed sex-matched pool,
  PureCN `purecn_intervals`, PURPLE/AMBER/COBALT `hmf_target_bed`, BAF
  `snp_sites.baf.bed`. CNVKIT is staged the BED but does not reference it;
  its bins come from the PoN `.cnn`.

`compare_runs.py` run9 vs run8: 981 identical, 189 real text differences,
18 cosmetic, 206 binary, 1 file on each side only.

## 7. New control

`tools/check_panel_completeness.py`, wired into `verify_install.sh` as
section 7. Asserts that every manufactured probe interval is inside
`params.bed` and that ten named clinical hotspots are callable. Verified
against a reconstruction of this defect: it fails and names the regions.

Current state on both hosts: 12,336 probe intervals contained, 10 of 10
hotspots callable, VERIFY PASSED.

`verify_install.sh` previously checked file existence and checksums only. A
checksum proves a file is the one expected; it does not prove the file is
correct. This defect was an intact file that was wrong.

**Scope limit:** the gate proves the calling BED covers the manufactured
capture space. It does not assess whether the panel design is clinically
complete — a gene absent from the probe file entirely would still pass. That
remains a design-review question.

## 8. Findings examined and dismissed

**Apparent coverage gaps are not design defects.** 82 intervals of
`targets.exonwise.bed` (14,128 bases) are not fully covered by the capture
space. Of these, 2,197 bases fall in coding sequence, and 2,048 of those are
ZNF91 exon 4 — a zinc-finger repeat array that cannot be uniquely tiled
(observed mean 76x, min 1x, max 1000x). The remaining 149 bases across 21 genes
are 1–4 bp seams at the 120 bp probe tiling period and are covered in practice:
CUX1 chr7:102,201,479, nominally uncovered, reads at 2,092x. Everything else is
3'UTR of terminal exons, expected for a coding-focused design. No coverage
complaint to the vendor arises. ZNF91 is not myeloid-relevant and is a
candidate for removal at the next design revision.

**NPM1 VAF difference is an assay characteristic.** NPM1 exon 11 insertion VAF
reads approximately 0.67 of the value from the comparator panel across four
cases. The comparator is a MIPS-derived probe expansion whose probe placement
is arranged around defined variant positions, unlike generic exon tiling, so a
systematic difference is expected. Not a pipeline defect and not a vendor
issue. NPM1 insertion VAF is not directly comparable between the two assays,
which matters for patients monitored across the platform transition.

## 9. Outstanding actions

1. **Clinical re-check scope** (decision required): every case reported on the
   Twist assay was signed out with IDH1, IDH2 and BRAF unexaminable. Stored
   BAMs are intact; this is re-analysis.
2. **A3 — re-run the 48 normals and rebuild the variant blacklist.** The
   existing 1,602-row blacklist was derived from normals processed with the
   defective BED and therefore has no entries anywhere in the restored regions.
   Two named candidates already observed: KLHDC8B c.-142A>C (8 of 8 samples,
   3.1–4.3%, currently caught only by LOW_IMPACT) and ANKRD26 5'UTR
   chr10:27100508 (4.62% in one sample).
3. **SOP-TSPIPE-001** revision entry; `tspipe_run9` replaces `tspipe_run8_c23`
   as the reference run for re-qualification.
4. **WI-TSPIPE-002 Part D** updated to the new reference.
5. **docs/RELEASE_NOTES.md** v1.0.2 section.
6. **IDH limit of detection has never been characterised**, the assay having
   had no IDH sensitivity at any VAF until today. No IDH dilution control
   exists; the NPM1 5% dilution in batch 2 covers NPM1 only.

## 10. References

| Item | Value |
|---|---|
| Fix commit | 5760d34 |
| Gate commit | 0902748 |
| CDS audit commit | 4edd46d |
| Tag | v1.0.2 |
| panel.calling.bed | md5 4b7e123966079266e83ce7baf7642ef5, 215,491 B |
| Superseded bed row | panel.combined.filtered.bed, 01d8e8ceae9dd708cff7d26ccd999649, 341,153 B |
| Reference run | /goast/hemat_data/twist_val/tspipe_run9 |
| Comparison | docs/audit/2026-09-12/ (run9 vs run8) |
| Patcher | tools/patches/2026-09-12/patch_panel_calling_v1.py |
| CDS audit | tools/patches/2026-09-12/cds_gap_audit.py |
| Gate | tools/check_panel_completeness.py |
