# 2026-09-08 afternoon memo 11 — A18: ANNOVAR annotation lost on indels (merge-key mismatch)

## Finding
While characterising the NON_REPORTABLE_CONSEQUENCE fails for D14, ~730 rows per run8 sample
(~12% of the filtered table; 19.3% of raw ANNOVAR rows, 1,016 of 5,264 on 26CGH1250) had
`Consequence == -1` and `VariantCaller_Count == -1`, plus ~18 with ANNOVAR-vocabulary terms
(`frameshift deletion`, `stopgain`). These were caller-less ANNOVAR rows that never merged with
their VEP/SomaticSeq record: `bin/annotate.py` keys each source on chr:pos:ref:alt, and ANNOVAR
writes indels in its own representation (start past the anchor base, `-` allele:
`chr11 119278646 ATG -`) while the VCF record is `chr11 119278645 TATG T`. The orphan rows were
correctly discarded downstream, but the primary indel rows lacked ClinVar, COSMIC_ID and the
ANNOVAR gnomAD/1KG columns. `Max_AF` and rsID come from VEP, so COMMON_POLYMORPHISM was not
affected; the ClinVar P/LP override could never fire on an indel.

## Fix (commit de7e2fe; ANNOVAR_KEY_V1, V1b)
`table_annovar.pl` runs with `-vcfinput`, which appends the original VCF record to every
multianno row as Otherinfo columns. `parse_annovar_txt()` now keys rows on those fields
(CHROM/POS/REF/ALT located by pattern: the first Otherinfo column equal to the row's Chr,
followed by a positive integer, with REF and ALT matching `[ACGTN]+|*`; V1b added the allele
check after a bookkeeping column produced 77 mis-keys). Old key as fallback when Otherinfo is
absent. `merge_annotations()` logs matched / orphan / unannotated counts and warns above 2%
orphans. `modules/local/vep_annotate.nf` bumped. Offline checker
`tools/patches/2026-09-08/check_annovar_key.py` runs old vs new keying on a cached
VEP_ANNOTATE task: 26CGH1250 19.3% → 1.5% (V1) → 0.0% (V1b), 0 VCF records without ANNOVAR.

## Run8 (resume 58 succeeded / 360 cached: VEP_ANNOTATE, VARIANT_FILTER, VV, ONCOVI,
FLT3_TO_VARIANTS, IGV_REPORTS, ORGANIZE ×8; DASHBOARD; BUNDLE)
- Orphans 0 on all eight; filtered tables 5,165–5,346 rows (were 5,927–6,118).
- clinical.final unchanged: 6/10/11/11/17/10/6/13 PASS. No call changed.
- Indels gained annotation, e.g. CBL chr11:119278645:TATG:T (PASS) → ClinVar
  Uncertain_significance (Noonan-like/JMML, multiple submitters); ANKRD26 5'UTR
  chr10:27066474:CCATAG:C → VUS (a D13 spike-in region); PTEN/other polymorphic indels → Benign,
  already filtered by frequency.

## Register
- A18 closed.
- D15 (new): ClinVar Benign / Likely_benign demotion in `variant_filter.py` — 26CGH132
  chr10:87864102:GC:G is PASS with ClinVar Benign; decide with D14.
- A19 (new, small): `COSMIC_ID` on indels renders as `10` / `11` — looks like the occurrence
  count rather than the identifier; check the cosmic103 field parsing in `annotate.py`.
- Operating rule: any change to `annotate.py` or `variant_filter.py` is verified with
  `check_annovar_key.py` on a cached task before a resume; the merge log line
  ("ANNOVAR merge: … orphan") is the regression tripwire.
- Note: terminal pastes of `sed -n` output can drop blank lines; patcher anchors must not
  span blank lines (the first A18 patcher aborted for this reason).
