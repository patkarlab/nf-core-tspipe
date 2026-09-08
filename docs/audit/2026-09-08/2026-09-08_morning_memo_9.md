# 2026-09-08 morning memo 9 — C1 annotation, C11 dashboard filters/glossary, C10 ideogram, DECoN brackets

Session 2026-09-07 22:00 to 2026-09-08 09:10. Repo /goast/hemat_data/nf-core-tspipe,
HEAD 6deccfa (main, 8 commits ahead of origin/main; push pending). Run8 session
abea2914-e2f9-44c0-961a-2f9c50eab4d9 resumed six times, all clean; last full
resume 18 succeeded / 400 cached; final idempotency resume 2 / 416.

## 1. What changed (commits, in order)

| commit  | marker           | change |
|---------|------------------|--------|
| 0821ebc | CMX_ANNOT_V1     | C1. Seven columns appended to `<sample>.cnv_consensus4.genes.tsv` and to the JSON `genes[]` rows: `cytoband`, `clingen_hi`, `clingen_ts`, `driver_role`, `driver_report_del`, `driver_report_amp`, `driver_amp_ratio`. Loaders and `annotate_gene()` in `bin/cnv_consensus_multi.py`; `--cytoband/--clingen/--driver-panel` optional. Module gains three `path` inputs; `workflows/tspipe.nf` resolves them (`params.cytoband`, `params.clingen`, `params.hmf_driver_panel`; `assets/` fallback; empty list when absent). Legacy 27 columns untouched. |
| 00fb8df | DASH_ANNOT_V1    | Dashboard `CONSENSUS_COLUMNS`: `cytoband` after `gene`; `driver_role`, `clingen_hi`, `clingen_ts` at the tail. |
| 2b46c92 | DASH_TIER_V1     | C11. Tier button group above the consensus table (Reportable = TIER_1+TIER_2 default; TIER_1; TIER_2; TIER_3; REVIEW; All). Consensus and DECoN tables initialised as DataTables (they were plain tables); dead `#cnv-annotated-table` init from the 7b-retired CNV_ANNOTATE removed. Tier column located by header text. |
| 33f69e2 | DASH_GLOSS_V1    | Collapsed "Column key" under the consensus description (all 30 columns, arms, tier rule, `loo_fp_any`, ClinGen score meanings). |
| 08ecb31 | DASH_DECON_V1    | DECoN table: BF explained (log10; BF 5 ≈ 100,000:1; arm-E thresholds 8 multi-exon / 12 single-exon), Reads.ratio interpretation, column key. |
| 6718b83 | DASH_DECON_V1b   | Column key corrected to the parser's vocabulary: `decision` PASS / PASS_MULTIDEL / BELOW_BF, `reportable` yes/no, `exon_flags` `-` until C4. |
| d4aefc0 | IDEO_V1          | C10. `bin/plot_targets_trio.py` `--every-chrom` pages: cytoband strip in target space directly under the targets track (Giemsa shading, band names, dotted divider where untargeted bands are skipped); band in the gene footer (`9p21.3  21.97-21.99 Mb`); backbone runs labelled by band range (`9q21.33-q34.3 backbone (n=59)`). `--cytoband` optional; CHROM_PAGES gains `path cytoband`; wired from `ch_cnv_cytoband`. |
| 6deccfa | DECON_BRACKET_V1 | Gene panels: DECoN writes a multi-gene call once per gene (same CNV.ID/Start/End, `Gene` column names the gene); brackets were matched by coordinate overlap so every gene in a multi-gene deletion drew all rows. Now matched on `Gene`, dedup on `CNV.ID`. Gene-panel titles carry the band (`CDKN2A (3 ex)  9p21.3`). |

Patchers: `tools/patches/2026-09-07/patch_cmx_annot_v1.py`,
`patch_dash_annot_cols_v1.py`; `tools/patches/2026-09-08/patch_dash_tier_filter_v1.py`,
`patch_dash_cnv_glossary_v1.py`, `patch_dash_decon_desc_v1.py`, `patch_dash_decon_desc_v1b.py`,
`patch_chrom_pages_ideogram_v1.py`, `patch_decon_bracket_v1.py`. All dry-run by default,
MARKER-guarded, all-or-nothing, `.bak_*` backups (gitignored).

## 2. Decisions

- Gene role from the hmftools DriverGenePanel already in `assets/twist_myeloid/hmftools/`
  (not `myeloid_driver_genes.tsv`): one CNV-module asset, explicit `reportDeletion` /
  `reportAmplification` flags. Full band granularity for cytoband.
- Rendered consensus table shows `driver_role`, `clingen_hi`, `clingen_ts`; the three
  `driver_report_*` / `driver_amp_ratio` columns stay TSV/JSON-only.
- Ideogram sits under the targets track, not above panel 1: gene names float above
  panel 1 (`clip_on=False`) and would collide. Target-space, not physical scale, so the
  strip aligns with the panels; the Mb range stays in the footer.
- Tier filter defaults to the reportable set (TIER_1 + TIER_2).

## 3. Verification (pasted evidence)

- Offline: `cnv_consensus_multi.py` re-run in the cached run8 task for 26CGH1250 with the
  three assets: first 27 columns byte-identical to the published table; 135 genes,
  0 cytoband NA; TP53 17p13.1 HI 3 TSG, RUNX1 21q22.12 HI 3, IKZF1 7p12.2 HI 3,
  ERG/MYC ONCO with amplificationRatio 3.
- Run8 resume after CMX_ANNOT_V1: 34 succeeded / 384 cached; all eight samples
  135 genes, 0 cytoband NA.
- Dashboard: `cnv-tier-filter`, "Column key", four annotation column names and the
  DECoN BF text present in all eight `<sample>_report.html`; `cnv-annotated-table` absent.
- Chromosome pages: 26CGH60 chr9 rendered offline in the CHROM_PAGES container — 9p24
  at JAK2, dark 9p21.3 at CDKN2A/B, backbone runs `9p13.2-q21.32` and `9q21.33-q34.3`,
  dividers at skipped bands, one bracket each on CDKN2A/CDKN2B/PAX5 (CNV.ID 6,
  15-exon deletion), titles with bands. Then resume 18/400 for IDEO_V1 and again for
  DECON_BRACKET_V1 (CHROM_PAGES 8 + ORGANIZE 8 + DASHBOARD + BUNDLE, as predicted).
- Report zip for laptop review: `~/inbox/to_claude/run8_clinical_20260908_0906.zip`
  (118 MB): `assets/` + eight `clinical/` trees minus BAM/BAI. Reports need
  `../../assets/` two levels up, hence `assets/` at the zip root.

## 4. Observations for the register

- Nine consensus genes have `driver_role` NA: five non-gene targets
  (GATA3_intronic, ANKRD26_5UTR, MLH1_5UTR, KLHDC8B_5UTR, DKC1_5UTR) and four real genes
  absent from the 127-row DriverGenePanel: IDH1, IDH2, BRAF, FANCI. Not a CNV
  concern; record under N8 so the panel provenance explains the omission.
- Report HTML is not standalone (CSS/JS at `../../assets/`); opened outside the outdir
  tree it renders unstyled. Already N9; pulled forward (see §6).
- `nextflow log` prints "Missing cache index file … index.silly_bardeen" — a cleaned
  stub session whose log entry survives. N10.
- `pgrep -u hemat -af nextflow` matches unrelated git traffic (`ssh … git-upload-pack
  'patkarlab/mm-awgs-nextflow.git'`), which let a redundant resume launch. Harmless
  (all cached), but the check must be tighter (§5).

## 5. Operating rules — additions

- Live-run check: `pgrep -u hemat -af "nextflow.*\.jar run"` (not bare `nextflow`).
- Offline re-render of a `bin/` script against a cached task: find the task dir with
  `nextflow log <uuid> -f process,tag,status,workdir | grep <PROCESS> | grep <sample>`
  (tag = meta.id, carries the `-TwistMyVal` suffix); take the container from
  `grep -o "/[^ ]*\.\(img\|sif\)" .command.run`; run
  `singularity exec -B /goast,/tmp $IMG bash <script>` with the script called by
  absolute path (Singularity resets PATH) and `MPLCONFIGDIR` set under /tmp.
- `-f` filters on `nextflow log` are quoted-exact; `tag == "26CGH1250"` matches
  nothing because the tag is `26CGH1250-TwistMyVal`.
- After a `-c /tmp/dash_nocache.config` run, the next plain resume re-executes
  DASHBOARD and REPORT_BUNDLE once (no cached task exists); ORGANIZE_OUTPUT re-runs
  whenever CHROM_PAGES/EXON_PLOTS republish, so a CHROM_PAGES change costs 18 tasks.
- Zips for review must include `assets/` at the root beside the sample folders.

## 6. Register changes

Closed: C1 (CMX_ANNOT_V1 + DASH_ANNOT_V1), C10 (IDEO_V1; new item, closed same
session), C11 (DASH_TIER_V1; new item, closed same session).
Modified:
- N8: add "IDH1, IDH2, BRAF, FANCI absent from DriverGenePanel.twist_myeloid.38.tsv;
  decide whether to add them (role known: ONCO/ONCO/ONCO/TSG) or document the omission".
- N9: "standalone report by default" pulled forward to next after the CNV extensions —
  inline `assets/` at build time or ship them inside the bundle beside the report.
- N10: add today's `.bak_*` files (all patchers), the `silly_bardeen` log entry,
  and `git push` of the 8 commits.
- C4 (DECoN follow-ups) now also owns the `exon_flags` column population; the
  dashboard key already describes the intended flags.
- SOP addenda pending for `cnv_consensus` (seven columns, assets, NA semantics) and
  `chrom_pages` (ideogram, band labels, bracket rule) — to be appended this session.

## 7. Suggested next

C2 BAF_V2 (genome-wide arms/segments on the v2 catalog; raises cnLOH outside 17p
from TIER_3 to TIER_1/2) is the largest remaining CNV gain, and the ideogram now makes
arm-level events legible on the pages. N1 (conformity gate) remains the alternative if
the CNV side should pause. N9 standalone report is a half-session and would end the
zip/assets friction for laptop review.
