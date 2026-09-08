# 2026-09-08 afternoon memo 12 — reportable rule (D14, D15), COSMIC IDs (A19), variant panel-of-normals blacklist (N13), Blacklisted tab (D16)

Session 2026-09-08 13:30–15:00. HEAD 32a2f6b on origin. Run8 (session abea2914) resumed twice:
58/360 for the filter+annotation change (VEP_ANNOTATE re-run for A19), 50/368 for the blacklist;
dashboard re-rendered for D16. Nothing running.

## 1. Commits

| commit  | marker / tool            | change |
|---------|--------------------------|--------|
| faaff85 | FILTER_D14_D15_A19_V1    | D14: `synonymous_variant` in REPORTABLE_CONSEQUENCES; `Variant_Class` column (nonsynonymous / splice / synonymous / other) on every row. D15: `CLINVAR_BENIGN` filter — ClinVar exactly Benign, Likely_benign or Benign/Likely_benign (no conflicting / uncertain / pathogenic), applied after frequency and impact, before the consequence rule, hotspot residues exempt; in both filter tallies. A19: `COSMIC_ID` from VEP `Existing_variation` COSV/COSM tokens; the ANNOVAR cosmic103 table in use carries occurrence counts, not identifiers (N12). Module bumps on VARIANT_FILTER and VEP_ANNOTATE. |
| 10e0031 | VARIANT_PON_V1 (N13)     | `tools/build_variant_pon_blacklist.py`: 259 auto rows in `references/blacklist_file.tsv` (11-column schema, `exact` match mode, reason strings tagged `[auto:VARIANT_PON_V1]`, replaced wholesale on rebuild; curated rows untouched). `references/variant_pon_cohort_table.tsv` keeps every cohort locus with its disposition. |
| 32a2f6b | DASH_BLACKLIST_V1 (D16)  | "Blacklisted" tab: the sample's `Filter == BLACKLIST` rows with gene, position, HGVS, class, VAF, callers, reason, cohort evidence, date; DataTable; nav badge counts rows with ≥ 2 callers. |

## 2. The variant panel-of-normals (N13)

Rule (Nikhil): exonic variants seen in normals at > 10% cohort frequency and VAF < 20% are
artefacts. Implemented with refinements, all on the same allele (chr:pos:ref:alt), coding or
splice consequences only, from the 48 normals' `somaticseq.filtered.tsv` (every row, any Filter):

| disposition | rule | n |
|---|---|---|
| UBIQUITOUS_IN_NORMALS | ≥ 50% of normals at any VAF; if median VAF < 25%, the calls must have ≥ 2 callers in ≥ 5 normals | 149 |
| RECURRENT_IN_NORMALS_LOWVAF | ≥ 10% of normals (5/48), median VAF < 25%, ≥ 2 callers in ≥ 5 normals | 5 |
| POPULATION_POLYMORPHISM_LOCAL | ≥ 10% of normals, median VAF ≥ 35% (germline polymorphism of the local population, under-represented in gnomAD) | 105 |
| LOWVAF_SINGLE_CALLER (not blacklisted) | ≥ 10% of normals but only single-caller calls | 1,057 |
| MID_BAND (not blacklisted) | median VAF 25–35%: KDM6B Pro263_Pro264del/Thr761_Thr762del, MN1 Gln549_Gln550del/Gln550dup, CEBPA His195_Pro196dup — polymorphic repeat indels | 5 |
| HOTSPOT_EXEMPT | residue in myeloid_hotspots.tsv (CHIP in normals is real) | 0 |

The first build on 48 normals with the plain rule produced 1,079 "low-VAF artefacts", most of them
single-caller 1–3% blips shared by a few normals; the caller-support requirement and the
ubiquity rule reduced the blacklist to 259 loci while keeping every genuine artefact.

## 3. Effect on run8 (the clinically important part)

Clinical PASS per sample, before D14/D15 → after D14/D15 → after N13:
1043 6→10→6; 1250 10→13→8; 1292 11→11→8; 132 11→13→10; 1480 17→22→18; 60 10→10→6;
799 6→12→8; 885 13→17→10. Caller-supported blacklisted rows per sample: 132–155.

Every row N13 removed from the clinical table is a cohort artefact that had been passing as a
somatic call, several in driver genes:

| variant | normals | tumours (of 8) | note |
|---|---|---|---|
| CBL p.Asp460del (chr11:119278645 TATG>T) | 24/48, median 3.4% | 5 | repeat slippage; carried a ClinVar VUS record since A18 |
| ASXL1 p.Ala637Pro | 48/48, 16.9% | 3 | systematic |
| GATA2 p.His111Pro | 48/48, 9.0% | 4 | systematic |
| SETD2 p.Arg404Lys | 48/48, 11.4% | 1 | systematic |
| STAT5B p.Gln368ArgfsTer2 | 24/48, 3.5% | 4 | homopolymer |
| PTEN p.Cys65_Ala66delinsSer, p.Ala69= | 28/48, 32/48 | 2, 6 | PTENP1 pseudogene mis-mapping |
| SF3A1 p.Gln122del | 22/48, 3.4% | 1 | repeat |
| GATA2 p.Gly263=, ARID1A p.Gly191=, ZFHX4 p.Ala2015= | 48/48 | 4, 3, 2 | synonymous, admitted by D14 then removed by N13 |

D15 demotions with ≥ 2 callers: PTEN p.Arg52GlyfsTer10 (polyT), ARID1A p.Gln1334del (recurrent
4–6%, Benign, three samples), KMT2A p.Ala3492Thr (Likely_benign at 24%), and germline-range benign
missense/synonymous in CSF1R, SETD2, ASXL2, PRPF8, CBL, WT1, PTPN11.

D14 admitted 1–6 coding synonymous calls per sample; after N13 the remaining ones are ~50% VAF rare
germline polymorphisms with COSMIC IDs (U2AF1 p.Ala68=, CSF1R p.Ile646=, RAD21 p.Gln156=, GATA2
p.Ala198=). A19 gives them real COSV identifiers in the report.

The blacklisted rows remain visible in the new Blacklisted tab with their cohort evidence.

## 4. Clinical action (Nikhil)

Reports signed out on the Twist myeloid assay before 2026-09-08 were produced without the cohort
blacklist. ASXL1 p.Ala637Pro, GATA2 p.His111Pro and SETD2 p.Arg404Lys are systematic at 9–17% VAF
in every normal and would have appeared as PASS missense calls in driver genes. Whether and how to
re-check issued reports against `references/blacklist_file.tsv` (259 loci, or the eight rows in the
table above as a minimum) is a laboratory decision, recorded here.

## 5. Register

- Closed: D14, D15, A19, N13 (new, closed), D16 (new, closed).
- N12 (new): the ANNOVAR cosmic103 table carries counts, not IDs; rebuild it with identifiers (COSMIC v103 → current) so ANNOVAR and VEP agree.
- A9 redesign letter: ASXL1 exon 12 around p.637, GATA2 exon around p.111, SETD2 around p.404 are systematic artefact sites at 9–17% in all normals — probe design or chemistry, worth naming alongside CCNC/ANKRD26.
- SOP: rebuild the variant PoN whenever the normals or the panel change; the command and rules are in `docs/sops/variant_filter.md`.
- Operating rule: any change to `variant_filter.py` is checked offline first on the newest `*.annotated.tsv` in `work/` (found with `ls -t`, not `nextflow log`, whose task listing lags) run in the `targeted-seq` conda env with `--outdir` holding a copy of the annotated table.
