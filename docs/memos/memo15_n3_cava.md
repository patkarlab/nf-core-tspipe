# Memo 15 (2026-09-08, 22:50) — N3 CAVA integration; D3 MANE-first consequence selection

## Summary

CAVA 2.0.15 (sicotteh/CAVA, the maintained Python 3 successor of RahmanTeam/CAVA) now
annotates every post-MNV consensus VCF on the MANE 1.5 GRCh38 RefSeq catalog, in its own
container, in parallel with VEP. `annotate.py` merges its tags into nine `CAVA_*` columns
appended after `MNV_Note`. Comparing CAVA with VEP on the eight run8 cases exposed that
VEP's consequence selection (severity-first since the CSF3R fix) reported a share of
variants on non-MANE isoforms; per Nikhil's decision the selection is now MANE-first.
Run8 re-annotated; clinical rows 73/73 carry CAVA, 72 agree with VEP on the protein
change, the one difference is repeat notation.

## Commits (all on main)

| Commit  | Tag          | Content |
|---|---|---|
| d9cc4b9 | CAVA_V1a     | `containers/cava/Dockerfile` (pinned commit 398eb1d), `tools/fetch_cava_catalog.py` (LFS media download with sha256 check; gandalf has no git-lfs), `assets/cava/mane-1.5-grch38-refseq/` (4 files + PROVENANCE.txt, ~3 MB, in git), `assets/cava/cava_config.template.txt`, `tests/run_cava_smoke.sh` + expected TSV |
| 813eda1 | CAVA_V1b/V1c | `modules/local/cava.nf` (`container 'local/cava:v2.0.15'`; singularity cache resolves `local-cava-v2.0.15.img` by Nextflow's naming convention, docker uses the tag — portable to clinical-23), `annotate.py --cava-vcf` + `parse_cava_vcf()` + transcript selection + `CAVA_HGVSp_Match`, `vep_annotate.nf` input `[meta, vcf, cava_vcf]`, `annotation.nf` wiring, `nextflow.config` params `cava_catalog` / `cava_config`, `modules.config` publishDir, `variant-browser.js` CAVA detail group + compact-line CSN fallback + badges "CAVA differs" / "alt alignment", `tools/check_cava_merge.py` |
| f18a88b | CSQ_MANE_V1  | `_pick_csq()`: if any CSQ block carries MANE_SELECT, choose among those only (by severity); severity over all blocks only when no MANE block exists (D3) |
| 7d85f53 | CAVA_V1b2    | multi-transcript HGVS split tolerates `.` placeholders (GNAS, KRAS, CDKN2A, PRPF40B); cache-bust for CSQ_MANE_V1 |

Pending, this memo's bundle: DASH_HGVS_PREF_V1 (D3b) — card nomenclature VV → CAVA → VEP.

## New columns (annotated / filtered / clinical TSVs, positions 32–40)

`CAVA_CSN`, `CAVA_HGVSc`, `CAVA_HGVSp`, `CAVA_Transcript`, `CAVA_Class`, `CAVA_SO`,
`CAVA_Impact`, `CAVA_AltAnn`, `CAVA_HGVSp_Match` (MATCH / DIFFER / NA after normalising
accession, parentheses, `%3D`). `-1` where CAVA produced no annotation (rows outside any
MANE transcript: backbone tiles, intergenic; ~36 % of filtered rows).

Where MANE 1.5 lists more than one transcript (GATA2, CUX1, NF1 in the panel; GNAS, KRAS
plus-clinical) the transcript matching VEP's MANE_SELECT is taken, else CAVA's first.

## Run8 outcome (resume 2, 58 tasks, completed 22:44)

Filtered tables: 42,352 rows, 25,483 with CAVA, HGVSp MATCH 5,801 / DIFFER 47 / NA
36,504, ALTANN 4,214. All 47 DIFFER rows are nomenclature, not substance:

- FLT3-ITD / UBTF-TD insertions: VEP `p.X_YinsA…Ter` / `delins…Ter` vs CAVA `p.(YAfsTer n)`;
  CAVA `p.(?)` with `c.1807_1837+27dup` where the duplication crosses the exon boundary.
- Repeat-region indels (KDM6B, ZFHX4, MN1): CAVA repeat-allele notation `p.(Pro252_Pro264[11];[2])`.

Clinical tables: 73 rows, 73 with CAVA, 72 MATCH; the one DIFFER is MN1 (26CGH1292,
PASS) in repeat notation. ALTANN on 12 clinical rows.

## D3 finding and fix

Before CSQ_MANE_V1, resume 1 showed SF1 (×17), PAX5, IRF1, U2AF2, PRPF40B and one PASS
call (UBTF chr17:44207341 G>A in 26CGH60, `p.Thr694Met` on ENSP00000431539) reported on
non-MANE isoforms: a missense on an alternative transcript outranked a synonymous call on
MANE under severity-first selection. After the fix UBTF is `synonymous_variant`
NM_014233.4 `p.Asp732=`, CAVA agrees (SY), and it remains PASS through the D14
synonymous-reportable rule with its class visible. CSF3R T618I is unaffected (its MANE
block is missense; the MRPS15 MANE block is upstream).

Clarification for the fellow's D3 wording: VEP writes ENST/ENSP accessions on every
HGVS string, MANE or not (Ensembl cache). The RefSeq form comes from VariantValidator
(clinical set) and now from CAVA (all rows); D3b makes the cards prefer those.

## Verification

- `tests/run_cava_smoke.sh` — PASS on gandalf (7 TP53/SRSF2 variants incl. an SRSF2
  insertion with ALTANN).
- `tools/check_cava_merge.py` — per-sample counts and the DIFFER table
  (`~/inbox/to_claude/run8_cava_differ_v2.tsv`).
- Dashboards rebuilt in resume 2 (DASHBOARD re-ran downstream of VEP_ANNOTATE).

## Gandalf notes

- `docker build` needs `--network=host` on gandalf: BuildKit RUN steps get no DNS
  (`docker run` does). The Dockerfile also forces apt to IPv4.
- The catalog fetcher retries; GitHub's LFS media endpoint reset once.
- CAVA passes reference-mismatched records through unannotated with an error line
  (does not abort); the merge records them as `-1` and the checker counts them.

## Register

N3 closed. D3 closed (CSQ_MANE_V1) pending D3b render. D6 closed (CSN on cards).
N6 note: `local/<name>:<tag>` + `local-<name>-<tag>.img` is the portable convention;
GHCR push optional later.
Nikhil's items unchanged: A9, A10, A11, A15, sex-check audit decisions, memo 12 §4,
clinical comparison of the eight cases.
Suggested next: D3b apply + nocache render, then the remaining D block (D1, D4, D5, D9,
D10, D11, D12) or C2 BAF_V2.
