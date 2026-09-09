# Memo 17 — 2026-09-09 session: dashboard, sex-check policy, transcripts, IGV, blacklist V2, BAF_V2

Date: 2026-09-09. Repo `/goast/hemat_data/nf-core-tspipe`, HEAD 7e1de41. Memo 16 covers the
hardening set (710f80f); this memo covers the rest of the day. Patchers under
`tools/patches/2026-09-09/`; every change verified on run8 (session abea2914) and by visual check.

## 1. Change sets

| Commit | Tag | What |
|---|---|---|
| 2967ba9 | DASH_LAYOUT_V1 | CAVA line on every card; MNV badge + detail row; Reporting snapshot VV→CAVA→VEP (D3b gap); sticky sidebar (`align-self: flex-start`); wrapping cells; fixed Reporting column widths; growing tier textarea (Enter commits); builder 0.5.1-layout+cava |
| 4f011e3 | SEXCHECK_POLICY_V1 | Decision: the run never stops on the sex check. `sex_check.py` exception → status ERROR + traceback, exit 0; verdict ERROR / MISMATCH (by status) / INDETERMINATE → REVIEW; samplesheet sex kept |
| 30638c2 | ANNOT_TRANSCRIPTS_V1 | `VEP_Transcripts` last column (`Feature\|BIOTYPE\|Consequence\|HGVSc\|HGVSp\|flags`, flags REPORTED/MANE:NM/CANONICAL/PICK, regulatory features skipped); collapsible "All transcripts (VEP, Ensembl)" in the detail view; Q7 `PERL_HASH_SEED=0 PERL_PERTURB_KEYS=0` in `run_vep`; gene "-1" as em dash |
| 487f751 | IGV_V2A | FLT3 tab IGV chip (nearest chr13 row ≤ 300 bp), integer ITD position, domain from HGVSp (Rücker 2022 regions), Callers wrap in the igv-reports table, COSMIC list `COSV…, COSV…` |
| 4ded4db | IGV_V2B | `igv_reports.py --flt3-consensus`: one report row per positive ITD event from the separate ITD pathway; `--track-config` JSON: alignment `colorBy: strand`, "Exons (panel)" track from `targets.exonwise.bed` (`params.igv_gene_track` hook); module tuple gains the consensus TSV |
| — | DASH_REPORTING_CAVA_V1 | CAVA column + three TSV columns on the Reporting tab; CAVA and COSMIC read from the live clinical row keyed on chr:pos:ref:alt (stored selections pick up new fields) |
| d68982b | N10 housekeeping | probe BEDs → `assets/twist_myeloid/probes/`; normals and 24-male samplesheets, `verify_s3_archived.py` tracked; `subworkflows/local/reporting.nf` removed; scratch → `/goast/hemat_data/twist_val/repo_scratch_2026-09-09/`; 383 `.bak_*` purged; preview sessions cleaned |
| — | VARIANT_PON_V2 / V2b | Builder counts every consequence; non-coding alleles blacklisted only via the low-VAF artefact tiers; new tier UBIQUITOUS_SINGLE_CALLER (≥ 75 % of normals at median < 25 %, single-caller); cohort table lists BELOW_MIN_FRAC and NONCODING_POLYMORPHISM; 1,602 auto rows (was 259) |
| — | BAF_V2 (+hotfix1, +V2B) | Genome-wide per-arm detector (42 arms; backbone + 17p sites); self-calibrated noise floor; het-like-only bias correction; verdicts NEUTRAL/DEL/CNLOH/GAIN/IMBALANCE/INDETERMINATE with confidence and scope; consensus B arm per gene from the overlapping arm, GAIN possible, LOW confidence casts no vote; outputs `baf17p` → `baf`, routed via ORGANIZE into `clinical/cnv/baf/`; CNV tab arm table |
| 9a7970a | DASH_CNV_TABS_V1 | CNV tab as sub-tabs (Consensus \| BAF \| Genome-wide \| reconCNV \| Chromosome pages); DECoN folded under Consensus; exon figures under Chromosome pages; BAF table shows called arms only; detector figure with bottom-axis labels and legend |
| 7e1de41 | GENOME_V2 | One genome-wide figure (`plot_genome_overview.py`, same CLI/output): depth bins + arm medians, BAF by arm verdict, PURPLE total/minor CN; BAF sub-tab keeps the table only |

## 2. Findings worth keeping

- **Blacklist root cause (N13):** the V1 builder ignored non-coding calls entirely and treated
  single-caller alleles as noise even at 47/48 normals. TERC 169765047 A>C (44/48), 169765728 A>AT
  (48/48) / AT>A (44/48) and EGLN1 231421623 C>G (47/48) / C>T (46/48), 231421624 C>G (40/48) are
  now BLACKLIST with evidence. Counting every consequence without restriction would have added
  4,874 backbone/other germline-VAF alleles (V2 dry run: 6,364 rows) — hence V2b.
- **Seven PASS rows removed from the run8 clinical set**, all present in 38–48/48 normals at the
  tumour's VAF, FreeBayes + one other caller in the tumour: 26CGH1480 ARID1A p.Ala41Gly 7.8 %;
  26CGH1250 MN1 p.Leu570Val 11.6 %, NAF1 p.Pro470= 25.9 %, ZFHX4 p.Ala2015= 11.0 %; 26CGH799 ZFHX4
  p.Ala2015= 7.8 %; 26CGH60 CBL p.His41Pro 9.4 %; 26CGH885 MARCHF4 p.Pro178Gln 7.8 %. Reports already
  issued on the Twist assay carrying any of these should be re-checked (adds to memo 12 §4).
- **baf_background.tsv** median/MAD are computed over all normals: trimodal at common SNPs, cohort
  MAD 0.11–0.24 off 17p vs 0.024 on 17p; 5 % of 17p sites have a cohort median of 0/1. BAF_V2 uses
  the sample's other arms as the noise floor and corrects bias only at het-like sites. A het-only
  background rebuild is the proper fix.
- **BAF_V2 on run8** (all cross-checkable calls agree with PURPLE/PureCN/CNVkit): 26CGH60 9p DEL
  f 0.20; 26CGH1043 9p DEL f 0.74 + 13q CNLOH f 0.60 (FLT3/LIG4 CNLOH TIER_1 BH); 26CGH1250
  1q/4p/4q/6p/14q/17p/17q GAIN f 0.20–0.26 (= p/(2(2+p)) at purity 0.65) + 15q CNLOH f 0.65
  (IDH2/RAD51/MAP2K1/FANCI CNLOH TIER_1 BH); 26CGH132 20p CNLOH? LOW (11 sites); four samples clean.
  V1 would have labelled the gained 17p of 26CGH1250 CNLOH_17P.
- **Catalog spacing:** backbone tiles median 715 kb apart (30 % of consecutive sites are within one
  tile), 17p median 27 kb. Population phasing works on 17p only → MoChA-17p; LD clusters per tile
  in the next panel design.
- **VEP** orders equal-rank consequence terms by Perl hash iteration; fixed seed (Q7). Two rows
  moved on the first seeded run, as expected.
- The 1.8 % FLT3-ITD of 26CGH1480 is REJECT/LOW_CALLERS at 0.72 % in the SomaticSeq path; only
  the ITD pathway reports it — the IGV report now takes ITD rows from the consensus TSV.
- ORGANIZE stages the U2AF1 pileup report under a `NO_FILE_` name and then skips it (unfixed).

## 3. Verification record

- Resumes: 98/352 (HARDEN), 58/392 (ANNOT_TRANSCRIPTS; only Consequence tie order moved),
  26/… renders (DASH_LAYOUT, SEXCHECK: SEX_CHECK rows byte-identical), 26 (IGV_V2B), 50/400
  (PON_V2: clinical sets lost exactly the seven rows above, nothing gained), 34/416 (BAF_V2 after
  hotfix1), 42/408 (CNV_TABS), GENOME_V2 pending at time of writing.
- Offline: `check_annovar_fatal.py` A/B/C/D pass on `work/cd/a39e70a6…`; `compare_annotated.py`
  attributes the VEP nondeterminism; BAF_V2 synthetic planted 17p cnLOH / chr8 trisomy / 7q loss
  all called, diploid sample zero calls; blacklist builder synthetic cohort covers every tier.
- Visual: sticky menu, CAVA line, MNV badge, growing tier box, Reporting CAVA column and clean
  COSMIC lists, FLT3 chip landing on the ITD row, strand colouring, exon track, CNV sub-tabs and
  called-arm table — all confirmed by Nikhil.
