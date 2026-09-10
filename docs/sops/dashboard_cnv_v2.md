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

## Addendum 2026-09-10 — TP53 / 17p observation block (TP53_OBS_V1)

What. One card at the top of the CNV tab (`#tp53-observation-card`, above the sub-tabs)
and a one-line mirror at the top of the Reporting tab (`#reporting-tp53-line`). The card
puts, side by side, every TP53 row of the clinical table (HGVS by VariantValidator →
CAVA → VEP, transcript from the same source, VAF with alt/ref counts, callers,
SomaticSeq verdict, ClinVar, OncoVI) and the 17p allelic evidence at TP53 (consensus
call/tier/arm letters/cytoband, allelic_state, CNVkit, GATK, the BAF_V2 17p arm row,
PURPLE total/minor CN and LOH, PureCN C and LOH, PURPLE and PureCN purity with the
PURPLE status shown as is — WARN_LOW_PURITY / FAIL_NO_TUMOR carry an "advisory" tag).
More than one TP53 row is itself flagged as an observation. The block classifies
nothing: it never derives "multi-hit" or any WHO-HAEM5 / ICC category.

Interpretation line. Looked up in `assets/<panel>/tp53_interpretation_rules.tsv`
(columns `condition`, `wording`, `note`; `#` comments). Rules are tried top to bottom and
the first match is shown with its line number and condition; with no match (or no
rules) the line reads "per reporting pathologist". A condition is `;`-separated clauses
`field op value` (`== != >= <= > < in notin`; `default` / `*` matches everything); the
field vocabulary is listed in the asset header and every sample's values are shown under
"Fields available to the rule table" on the card, so a rule can be checked against a real
sample before it is saved. A malformed clause or an unknown field is reported in red on
the card instead of silently never matching. Changing the wording or the rules needs no
code change and no resume beyond DASHBOARD / REPORT_BUNDLE.

Files. `bin/dashboard_builder/parsers/tp53.py` (stdlib; reads the clinical rows already
parsed by `parsers/variants.py`, `cnv/consensus/<S>.cnv_consensus4.{genes.tsv,json}`,
`cnv/baf/<S>.baf.summary.tsv` with the consensus-JSON `baf_arms` as fallback,
`cnv/purple/<S>.purple.h_summary.tsv`); `build.py` (`--tp53-rules`, `ctx["tp53"]`,
builder 0.5.2-tp53); `sample_report.html.j2` (card + mirror); `modules/local/dashboard.nf`
passes the asset when it exists. Patcher `tools/patches/2026-09-10/patch_tp53_obs_v1.py`;
offline check `tools/patches/2026-09-10/check_tp53_block.sh` (renders 26CGH1250 as
published and a copy of 26CGH60 with two synthetic TP53 rows in a scratch view, zips the
reports to `~/inbox/from_claude/`). Run8 carries no real TP53 variant; the variant half
was exercised on the synthetic rows only.

Re-rendering. `dashboard.nf` changed, so a plain resume re-executes DASHBOARD and the
eight REPORT_BUNDLE tasks; later edits to the parser, the template or the rule asset are
unhashed and need `-c /tmp/dash_nocache.config` as before.

## Addendum 2026-09-10 — dedicated 17p figure (ARM17P_V1)

`bin/plot_arm_17p.py` runs in CHROM_PAGES after the genome overview and writes
`chrom_pages/<S>.17p.png` (GATK container, Python 3.6 / matplotlib 3.2). Four tracks along 17p
in genomic coordinates: denoised log2 copy ratio bins with CNVkit segments and the arm median
(depth bins exist only at PRPF8, TP53 and KDM6B; the 17p SNP windows carry no depth bin, which
the track states); raw ALT fraction of every catalog site, heterozygous sites coloured by the
BAF_V2 arm verdict (circles = SNP windows, triangles = backbone sites) with the 0.5 ± f/2 band;
PURPLE total and minor-allele copy number; gene strip in consensus colours with the centromere
shaded. Title: TP53 consensus row, PURPLE at TP53, purity. Panel genes come from the consensus
JSON, PURPLE segments from `--purple-dir`, site class from the BED interval width
(`snp_sites.baf.base.bed` is 120-bp windows only, so anything outside a window is a backbone
site). The dashboard (`parsers/cnv_v2.py`, `ctx.cnv.arm17p_figure`) shows it inside the TP53 /
17p observation card as a report-selectable plot (`arm17p::1`), so it can be ticked into the
Reporting tab and travels in the bundle with the rest of `cnv/`. An optional `--clinical`
argument overlays the TP53 variant VAF(s); not used in the pipeline because the clinical table
does not exist at CHROM_PAGES time (the dashboard python, targeted-seq env, has matplotlib 3.10,
so a dashboard-time overlay is possible). Changing the figure re-executes CHROM_PAGES for every
sample (plus ORGANIZE, DASHBOARD, bundles). Patcher `tools/patches/2026-09-10/patch_arm17p_v1.py`.

### Revision 2026-09-10 (ARM17P_V2 + TP53_ON_17P_V1): the 17p page

Placement: `plot_arm_17p.py` appends a row `chr17p` to `chrom_pages/<S>.chrom_pages.tsv`, so the
17p figure is a chromosome page — pill "17p" right after "17" (`parsers/cnv_v2.py` `_chrom_key`
sorts an arm suffix after its chromosome), its own Include checkbox (`chrom_page::chr17p`), in
the bundle like the other pages. The TP53 / 17p observation card (TP53_OBS_V1) no longer heads
the CNV tab: it is a template macro `tp53_card` rendered inside the 17p pane above the figure;
on a run without a 17p page it renders at the end of the CNV tab instead. The Reporting-tab
one-line mirror is unchanged.

Depth track: the gene exon bins are not drawn (they are on the chr17 page; `--exon-bins`
restores them). The track shows the SNP-window depth ratios — median over each window's catalog
positions of log2(sample depth / cohort median depth), computed as on the chromosome pages from
`--allelic` and `--background` — sample-normalised by subtracting the median of the same ratio
over every catalog position outside chr17 (the backbone, from the background table), plus the
CNVkit segment and the exon-bin arm median as lines. The legend prints the 17p window median and
its offset from the exon-bin median; heterozygous sites are coloured by the BAF_V2 arm verdict
and the legend says so.

Why normalised, and how to read it (eight run8 samples, 2026-09-10; table in
`docs/audit/2026-09-10/17p_window_depth_medians.md`): raw ratios are not a copy-number measure —
the seven 17p-neutral samples spread from −0.05 to −0.33 with each library's depth relative to
the cohort, and the 26CGH1250 chromosome-17 gain is invisible. After backbone normalisation the
seven neutral samples collapse to −0.18 ± 0.03 and 26CGH1250 sits at +0.13, i.e. +0.31 above the
neutral level, equal to its exon-bin arm median. The remaining −0.18 is a probe-batch offset (the
17p supplementary windows yield ~12 % less relative to the backbone in run8 than in the 48-normal
cohort); it is constant within a run and is not removed. Read the track by its shape along the
arm and by the window-minus-exon-bin offset: the same offset as the run's other samples means the
windows moved with the genes; a different one means windows and genes disagree. A per-run
calibration would remove the batch term once runs are large enough; supplementary windows with
matched control windows elsewhere would remove it by design (Twist letter).
