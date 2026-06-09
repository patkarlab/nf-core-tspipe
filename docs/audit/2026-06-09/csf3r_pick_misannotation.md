# CSF3R missed in all known positives — VEP `--pick` misannotation

**Date:** 2026-06-09
**Component:** `bin/annotate.py` (nf-core-tspipe)
**Severity:** High — clinically relevant variants silently dropped from final reports
**Status:** Fixed, validated on 9/9 known positives, committed.

---

## Summary

CSF3R mutations were absent from the final clinical table in every known
CSF3R-positive sample. The variants were called correctly (PASS, multi-caller
support) but were **mislabelled at the annotation stage**: VEP was run with
`--pick`, which collapses all transcript consequences to a single block and, at
loci where a panel gene overlaps a neighbour, could select the neighbour's
non-coding consequence. CSF3R T618I was recorded as an `MRPS15
upstream_gene_variant` with an empty HGVSp, then correctly down-filtered as
low-impact — so it never reached the clinical output.

The defect was gene-agnostic: any panel gene overlapping a neighbour that won
the `--pick` tie-break was affected. The fix selects the consequence by
severity rather than by `--pick`, treating every gene equally.

A second, independent bug surfaced during validation: under `gandalf.config`
the VEP subprocess inherited a PATH that shadowed its own Perl, aborting VEP
compilation. Fixed separately by scoping a sanitized environment to the VEP
call.

---

## Root-cause trail

The miss was traced through every stage for CSF3R T618I
(GRCh38 chr1:36,467,833 G>A, minus strand, c.1853C>T):

1. **Gene on panel** — CSF3R present in BED, driver-gene list, and hotspots. Not the cause.
2. **Position tiled** — 36,467,833 falls inside an exonic interval. Not a coverage gap.
3. **Coverage** — hundreds to >1000x at the locus. Adequate.
4. **Blacklist** — not present in `blacklist_snvs_hg38.tsv`. Not suppressed there.
5. **Calling** — variant called PASS, 6 callers, ~48% VAF in the SomaticSeq consensus VCF.
6. **Annotation** — recorded as `Gene=MRPS15`, `Consequence=upstream_gene_variant`,
   `HGVSp` empty. This is the failure point.

Cause: `run_vep()` passed `--pick`. With `--everything`, VEP returns many
transcript consequences per variant; `--pick` emits only one, chosen by VEP's
default `--pick_order`. At this locus the overlapping MRPS15
`upstream_gene_variant` (MODIFIER) was selected over the CSF3R
`missense_variant` (MODERATE). With `Gene=MRPS15` and no HGVSp, the variant
failed the CSF3R hotspot match (keyed on the amino-acid change) and was
down-filtered as low-impact, never reaching `clinical.final.tsv`.

Confirmed by re-running VEP without `--pick`: 13 consequence blocks returned,
including 5 CSF3R missense on MANE Select NM_000760.4, ranked above MRPS15.

---

## Fix 1 — severity-based consequence selection (gene-agnostic)

`bin/annotate.py`:

- `run_vep()`: `--pick` -> `--flag_pick`. VEP now emits every transcript
  consequence and tags one with `PICK=1`; nothing is discarded.
- New `CONSEQUENCE_RANK` constant (Ensembl consequence severity ordering) and a
  `_pick_csq()` helper.
- `parse_vep_csq()`: parse all CSQ blocks and select one by
  **(1) consequence severity, (2) MANE Select, (3) VEP PICK flag, (4) input order**.

No gene list, no panel awareness: a coding consequence wins over a co-located
non-coding MODIFIER for every gene on the panel. CSF3R T618I now resolves to
`CSF3R missense_variant`, MANE NM_000760.4, p.Thr618Ile.

## Fix 2 — VEP subprocess environment isolation

`bin/annotate.py`:

- `gandalf.config`'s `beforeScript` prepends the targeted-seq env bin to PATH
  (required for ANNOVAR's Perl). This shadowed VEP's own Perl, causing
  `BEGIN failed--compilation aborted` in `Bio::EnsEMBL::VEP` for any VEP run
  under the pipeline (it only worked from a clean interactive shell).
- `run()` gained an optional `env=` parameter. `run_vep()` builds a sanitized
  environment (drops `envs/targeted-seq/bin` from PATH, clears `PERL5LIB`,
  `PERL_LOCAL_LIB_ROOT`, `PERL_MM_OPT`, `PERL_MB_OPT`) scoped to the VEP
  subprocess only. ANNOVAR is unaffected and keeps the Perl it requires.

---

## Validation — 9/9 known positives

Re-ran 9 known CSF3R-positive samples end-to-end (`--panel myeloid_cnv`,
outdir `test_run/20260609_145828`). All nine now carry a correctly-annotated
CSF3R variant on NM_000760.4 in `clinical.final.tsv`, across both lesion classes:

| Sample      | CSF3R consequence (post-fix)              |
|-------------|-------------------------------------------|
| 25RSEQ475   | missense  p.Thr618Ile                     |
| 26CGH400    | missense  p.Thr618Ile; frameshift p.Phe792SerfsTer10 |
| 25NGS238    | missense  p.Gly687Ser                     |
| 25RSEQ631   | missense  p.Leu720Arg                     |
| 25RSEQ664   | missense  p.Ser611Asn                     |
| 26CGH620    | missense  p.Ser624Leu                     |
| 26CGH124    | missense  chr1:36,467,645 (PASS, 6 callers, 48% VAF) |
| 25NGS134    | stop_gained  p.Gln749Ter                  |
| 26CGH705    | stop_gained  p.Gln749Ter                  |

All were previously mislabelled MRPS15 and absent from clinical output.

Single-sample old-vs-new diff (26CGH400): 118 loci changed gene/consequence,
including RIT1 (frameshift/missense, previously `KHDC4 downstream_gene_variant`)
and KMT2A (start_lost/missense, previously `-1 intron_variant`).

---

## Blast radius (historical sweep)

`audit_pick_misannotation.py` flags supported calls recorded as a non-coding
`*_gene_variant` or `Gene=-1` — the `--pick` signature. Per exonic-panel
(MyOPool) sample, the fix reduced suspicious rows by roughly 70-90%:

| Sample    | pre-fix (run 122226) | post-fix (run 145828) |
|-----------|----------------------|-----------------------|
| 25NGS134  | 103 (CUX1 29, MRPS15 7, ...) | 12 |
| 25NGS238  | 21                   | 5  |
| 25RSEQ475 | 39 (ALAS2 9, MRPS15 3) | 14 |
| 25RSEQ631 | 46                   | 12 |
| 25RSEQ664 | 42                   | 12 |
| 26CGH124  | 76 (MRPS15 3)        | 7  |
| 26CGH400  | 50 (MRPS15 5)        | 8  |
| 26CGH620  | 65                   | 22 |
| 26CGH705  | 72                   | 15 |

The pre-fix `MRPS15`/`CUX1` rows are the overlapping-neighbour signature; the
post-fix residual is genuine intergenic/UTR or pseudogene calls (e.g. ALAS2,
RN7SL568P), not mismasked drivers.

**Caveat — CNV-backbone panels:** the raw audit also flags ~1,500-2,000 rows per
MYCNV sample, almost all `Gene=-1`. These are the genome-wide CNV backbone tiles,
which legitimately fall in intergenic space and are expected to be `-1`. They are
**not** the `--pick` bug and must be excluded when estimating clinical impact.
The audit heuristic cannot distinguish a backbone tile correctly in intergenic
space from a real coding variant mismasked, so the headline totals
(244,459 rows) are dominated by benign backbone tiles and overstate impact.

**Reports needing re-review:** exonic (MyOPool) clinical reports issued from the
nf-core port before 2026-06-09. CNV-backbone (MYCNV) reports are not implicated
by this defect.

---

## Open / follow-up (not part of this fix)

- `FLT3_ITD_EXT` continues to fail to emit `final_FLT3_ITD.vcf` (errorStrategy
  ignores it). Separate open item.
- VariantValidator REST died mid-batch during validation (gunicorn timeout),
  failing one sample (26CGH124); recovered via the launch wrapper and resumed.
  Consider a periodic VV liveness check or raising the VV container timeout/threads
  so long batches do not lose a sample.

## Artifacts

- `tools/patches/2026-06-09/patch_annotate_flagpick.py`
- `tools/patches/2026-06-09/patch_runvep_env.py`
- `tools/patches/2026-06-09/audit_pick_misannotation.py`
- `/tmp/pick_audit_20260609.csv` (per-file audit output)
