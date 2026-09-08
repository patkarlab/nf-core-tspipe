# SOP — MNV merge before annotation (MNV_MERGE_V1, N2)

Written 2026-09-08. Applies to nf-core-tspipe with the twist_apply.config overlay.

## Why

SomaticSeq decomposes every caller's multi-nucleotide variant into single-base records.
Two consequences: VEP annotates the SNVs separately (codon-level HGVS is wrong for a
dinucleotide substitution), and Mutect2's support is lost on the components — Mutect2 calls
the MNV as one record, so the split SNVs carry `MVDKFP` M = 0 while VarDict's MNV is split
with credit. A real somatic dinucleotide can therefore drop a caller and sink to LOW_CALLERS
on a technicality. In run8 no clinical-grade call was affected; the merge is a correctness
guard for the rare event.

## What

`MNV_MERGE` (modules/local/mnv_merge.nf, GATK container) runs between SOMATICSEQ_POSTPROCESS
and VEP_ANNOTATE on the consensus VCF, the Mutect2 FilterMutectCalls VCF
(`VARIANT_CALLING.out.mutect2_vcf`; keeps MNV records and PGT/PID phase sets) and the VarDict
VCF. `bin/mnv_merge.py` (stdlib, Python 3.6, reads the reference through the .fai index):

- candidate run: consecutive consensus SNVs on one chromosome whose positions differ by ≤ 2
  (adjacent, or one reference base between — same-codon scope);
- evidence, any of: a Mutect2 MNV record covering the run exactly (MUTECT2_MNV); a VarDict
  MNV record covering it exactly (VARDICT_MNV); every SNV of the run present in the Mutect2
  VCF with the same PID and PGT (MUTECT2_PID). Runs of three or more are tested whole, then
  as adjacent pairs;
- the merged record is ADDED, nothing is removed. REF/ALT span the run with gap bases from
  the reference (a consensus REF that disagrees with the reference aborts that merge);
  `MVDKFP` = AND of the components with M set when Mutect2 supports the MNV and D set when
  VarDict does; `NUM_TOOLS` recomputed; `AF` and the FORMAT/sample columns from the
  lowest-AF component; FILTER = worst of the components (PASS < LowQual < REJECT); INFO
  `MNV_OF` (component positions) and `MNV_EVIDENCE`;
- each component gets INFO `MNV_PARENT=chrom:pos:ref:alt`.

Downstream: `annotate.py` writes the column `MNV_Note` ("MNV of 95791956,95791957
(MUTECT2_MNV|VARDICT_MNV)" or "component of chr13:95791956:CT:TC"; -1 otherwise), placed
after Existing_variation — the Filter column moved from 35 to 36. `variant_filter.py`:

1. BLACKLIST stays priority 0 (a blacklisted component keeps its own BLACKLIST);
2. components get Filter `MNV_COMPONENT`;
3. an MNV row inherits BLACKLIST when any component is blacklisted
   (Blacklist_Reason `MNV|INHERITED_FROM_COMPONENT|<component reason, | → />`) and
   COMMON_POLYMORPHISM when every component has Max_AF > 0.01. The merged allele rarely
   matches a gnomAD record (its own Max_AF is −1), so without inheritance every germline
   dinucleotide would surface as a novel variant;
4. everything else as before.

## Run8 result (2026-09-08)

- 21–30 MNVs per sample from 85–108 candidate runs; 198 in total: 168 COMMON_POLYMORPHISM,
  29 LOW_IMPACT, 1 BLACKLIST, none PASS. Clinical tables unchanged (PASS 6/8/8/10/18/6/8/10).
- Evidence mix per sample: Mutect2+VarDict ~half, VarDict-only and VarDict+phase a quarter
  each, Mutect2-only or phase-only 1–4.
- Unmerged runs are the recurrent FreeBayes-only 4–7% clusters (EGLN1, RUNX1, SF1, NOTCH3,
  GATA2 …) and unsupported pairs — correctly left as separate SNVs.
- Example: chr13:95791956 CT>TC (DNAJC3 3'UTR) annotated as c.*926_*927delinsTC, 5 callers.

## Reading the tables

- Clinical table: an MNV appears once, as the merged record, with the codon-level HGVS.
- All Filtered: the components are present with Filter MNV_COMPONENT and the parent key in
  MNV_Note; the MNV row's MNV_Note lists the evidence.
- A PASS MNV in a future sample deserves a look at MNV_EVIDENCE: MUTECT2_MNV|VARDICT_MNV
  is the strong case; MUTECT2_PID alone means the two SNVs were phased but neither caller
  emitted the MNV itself.

## Cost and maintenance

- Any change to mnv_merge.py re-executes MNV_MERGE 8 + VEP 8 + the downstream chain (~66
  tasks on run8, ~20 min).
- Widening the window (`--max-gap`) is a module-level parameter; > 2 bp starts producing
  complex alleles that belong to N3/CAVA, not here.
- Read-level co-occurrence for unphased pairs is not implemented (V2 if ever needed).
- Offline check: `bin/mnv_merge.py` in the GATK image against the newest
  `<S>.somaticseq.vcf`, `<S>.mutect2.vcf.gz` and `<S>.vardict.vcf` under work/ (find by
  -type f and mtime; the VEP and VARIANT_FILTER task directories only hold staged symlinks).
