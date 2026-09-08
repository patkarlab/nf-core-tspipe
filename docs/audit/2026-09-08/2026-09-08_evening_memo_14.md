# Memo 14 — 2026-09-08 late evening — N2 MNV merge (MNV_MERGE_V1)

Repo /goast/hemat_data/nf-core-tspipe, start HEAD 350d24f (memo 13, D13). Run8 session
abea2914-e2f9-44c0-961a-2f9c50eab4d9; one effective resume, 66 tasks (MNV_MERGE 8,
VEP_ANNOTATE 8, VARIANT_FILTER 8 and the downstream chain), 368 cached.

## 1. Facts established before designing

- The "design on record" for N2 was one line in the 09-03 memo. The design was built from
  run8 data instead.
- Adjacent-SNV scan (≤ 2 bp) of the eight filtered tables: hundreds of pairs, none involving
  a clinical-grade call. Two families: germline dinucleotide polymorphisms at 40–50 % with
  4–5 callers (DNAJC3, CDH13, FNIP1, CSF1R, ZNF831 …), and FreeBayes-only pairs at 4–7 %
  recurring at the same positions in every sample (EGLN1 231421623/624, RUNX1
  34792256/258/260, SF1, NOTCH3, U2AF2, GATA2 128486288/290, NOTCH1, IL7R, MN1, KDM6B …).
  The second family is a haplotype-caller cluster artefact already removed by LOW_CALLERS,
  and — like the TERC loci in memo 13 — absent from the N13 cohort table.
- SomaticSeq decomposes every caller MNV: 0 MNV records in the consensus against 30–43
  native MNVs per VarDict VCF and 16–29 per Mutect2 VCF. VarDict's MNVs are split with
  credit; Mutect2's MNV support is lost on the components (chr13:95791956 CT>TC is one
  Mutect2 record; the consensus SNVs carry MVDKFP=0,1,1,1,0,1). Mutect2 phase sets
  (FORMAT PGT/PID, ~210 records per sample) survive FilterMutectCalls, so the filtered
  Mutect2 VCF already reachable as VARIANT_CALLING.out.mutect2_vcf is the evidence source.
- `flag_overlapping_variants` requires an indel on one side, so an MNV and its SNV
  components never trigger it; the dashboard does not enumerate Filter values.

Decisions (Nikhil): MNV record added alongside tagged components (nothing removed); window
≤ 2 bp (same-codon scope); read-level co-occurrence deferred.

## 2. Built (commit after memo 13)

New: bin/mnv_merge.py, modules/local/mnv_merge.nf, docs/sops/mnv_merge.md,
tools/patches/2026-09-08/patch_mnv_merge_v1.py (3 files, 9 anchors).
Patched: workflows/tspipe.nf (MNV_MERGE on SOMATICSEQ_POSTPROCESS.out.vcf joined with
VARIANT_CALLING.out.mutect2_vcf / vardict_vcf and ch_reference; ch_somaticseq_vcf =
MNV_MERGE.out.vcf); bin/annotate.py (MNV_Note column from INFO MNV_OF / MNV_EVIDENCE /
MNV_PARENT; Filter is now column 36); bin/variant_filter.py (MNV_COMPONENT after BLACKLIST;
MNV inherits BLACKLIST from any component and COMMON_POLYMORPHISM when all components are
common; MNV_COMPONENT in both filter-count tables).

Offline check on 26CGH60 before the resume: 21 MNVs (MUTECT2_MNV|VARDICT_MNV 10,
VARDICT_MNV 5, VARDICT_MNV|MUTECT2_PID 5, MUTECT2_MNV 1); chr13 pair rebuilt as CT>TC with
NUM_TOOLS 5. The pipeline run reproduced the numbers exactly.

## 3. Run8 result

- Per sample 21–30 MNVs from 85–108 candidate runs (1043 25, 1250 30, 1292 21, 132 25,
  1480 27, 60 21, 799 28, 885 21); MNV_COMPONENT 43–63 rows per sample.
- 198 MNV rows: 168 COMMON_POLYMORPHISM (inherited; own Max_AF −1), 29 LOW_IMPACT,
  1 BLACKLIST (inherited), 0 PASS. No MNV in any clinical table; PASS counts unchanged at
  6/8/8/10/18/6/8/10.
- chr13:95791956 CT>TC (DNAJC3 3'UTR) now annotates as c.*926_*927delinsTC with
  Mutect2,VarScan,VarDict,Strelka,Platypus; components c.*926C>T and c.*927T>C are
  MNV_COMPONENT.

## 4. Register deltas

Closed: N2 (V1; read-level arm not needed on run8, revisit only if a phase-less pair ever
matters). N3 (CAVA) is next and is independent.
N13 follow-up widened: two artefact families present in 8/8 tumours are absent from the
48-normal cohort table — the TERC loci (memo 13) and the FreeBayes-only adjacent clusters.
Establish whether the normals' filtered tables never carried LOW_IMPACT / LOW_CALLERS rows
or the builder's disposition rules excluded them.
D-list note: the Variants tabs could show MNV_Note; not needed for review, optional.
Dashboard/SOP column note: `Filter` moved from column 35 to 36 in the filtered/clinical
tables; any ad-hoc `cut -f35` in scripts or SOPs must become `-f36` (D16 and the QC SOP
read by name and are unaffected).

## 5. Operating notes added

- Two `nextflow run -resume` on one session: the second fails on the cache LOCK and, if it
  shares the log file, its error is written into the running run's log. Never put the
  launch on the same line as a patch step; check `pgrep -u hemat -af "nextflow.*\.jar run"`
  first and wait with `while pgrep …; do sleep 15; done`.
- `nextflow log <run>` cannot open the cache while a run is alive (it prints the same lock
  error); use `grep -oE "Submitted process > [^ ]+" .nextflow.log | sort | uniq -c` for
  live progress and per-task stderr from `work/*/*/.command.log`.
- Console process names are abbreviated (`TSP…OTATE`); grep the tail of the name.
- The newest `*.annotated.tsv` / `*.somaticseq.vcf` under work/ by mtime is usually a
  staged symlink in a consumer's task directory; find the producer with `-type f`.
