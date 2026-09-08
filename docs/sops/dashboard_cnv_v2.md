# DASH_CNV_V1 -- CNV tab on the v2 outputs -- 2026-09-07

Reads clinical/cnv/ (ORG_CNV_V1) through bin/dashboard_builder/parsers/cnv_v2.py,
merged into ctx["cnv"] by build.py (never fatal). The CNV tab opens with:
  - one line: PURPLE status/purity/ploidy/sex (advisory badge when not trusted),
    sex check, consensus tier counts, blacklisted genes
  - consensus table (non-neutral genes; tiers; per-arm calls K G B P E H; LOO fp)
  - DECoN table (reportable + multi-exon calls at BF >= 5)
  - chromosome pages gallery (24 pages, report-selectable cards)
  - exon-level figures gallery
Legacy sections remain below a "Legacy CNV views" divider until 7b.

Files
    bin/dashboard_builder/parsers/cnv_v2.py
    tools/patches/2026-09-07/patch_dashboard_cnv_v2.py   build.py + sample_report.html.j2

Placement (repo root)
    cp <bundle>/bin/dashboard_builder/parsers/cnv_v2.py bin/dashboard_builder/parsers/
    cp <bundle>/tools/patches/2026-09-07/patch_dashboard_cnv_v2.py tools/patches/2026-09-07/
    python3 tools/patches/2026-09-07/patch_dashboard_cnv_v2.py [--apply]

Rebuild: bin/ is not hashed by Nextflow, so a resume leaves DASHBOARD cached;
force it once with a throwaway config:
    printf "process { withName: 'DASHBOARD' { cache = false } }\n" > /tmp/dash_nocache.config
    nextflow run . ... -resume <session> -c conf/twist_apply.config -c /tmp/dash_nocache.config

## Addendum 2026-09-08 — annotation columns, tier filter, column keys (DASH_ANNOT_V1, DASH_TIER_V1, DASH_GLOSS_V1, DASH_DECON_V1/V1b)

Consensus table. `CONSENSUS_COLUMNS` in `bin/dashboard_builder/parsers/cnv_v2.py` now
renders `gene, cytoband, chrom, start, end, consensus_call, tier, flags, k_*, g_*, b_call,
p_*, e_*, h_*, loo_fp_any, driver_role, clingen_hi, clingen_ts`. Rows use
`r.get(c, "")`, so a pre-annotation TSV renders blanks rather than failing.
`driver_report_del/amp` and `driver_amp_ratio` are TSV/JSON-only.

Tier filter. A button group (`#cnv-tier-filter`) above the consensus table:
Reportable (TIER_1 + TIER_2, default) | TIER_1 | TIER_2 | TIER_3 | REVIEW | All. It
drives a DataTables column regex search on the `tier` column, which is located by header
text so column order changes cannot break it. The consensus and DECoN tables are
initialised as DataTables (sort, search, paging; they were plain tables). The
`#cnv-annotated-table` initialisation left over from the 7b-retired CNV_ANNOTATE is gone.

Column keys. Collapsed `<details>` "Column key" blocks under the consensus and DECoN
descriptions; closed by default so the tables do not move. The consensus key covers
every rendered column, the arm letters, the tier rule, `loo_fp_any` (leave-one-out
false-positive fraction from the PoN; < 0.10 required for TIER_1/2) and the ClinGen
score scale. The DECoN block explains BF (log10; BF 5 about 100,000:1), the arm-E
thresholds (8 multi-exon deletion, 12 single-exon), Reads.ratio, and the parser's
vocabulary: `decision` PASS / PASS_MULTIDEL / BELOW_BF, `reportable` yes/no,
`exon_flags` `-` until C4 populates it.

Re-rendering. All of this is template/`bin/` and unhashed: force with
`-c /tmp/dash_nocache.config`; the next plain resume re-executes DASHBOARD and
REPORT_BUNDLE once more. Reports reference `../../assets/` two levels up; any copy
for review outside the outdir must carry `assets/` at the root beside the sample
folders (register N9, standalone report). Patchers in `tools/patches/2026-09-07/`
(`patch_dash_annot_cols_v1.py`) and `tools/patches/2026-09-08/`
(`patch_dash_tier_filter_v1.py`, `patch_dash_cnv_glossary_v1.py`,
`patch_dash_decon_desc_v1.py`, `patch_dash_decon_desc_v1b.py`).
