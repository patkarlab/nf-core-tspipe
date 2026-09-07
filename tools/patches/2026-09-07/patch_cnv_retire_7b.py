#!/usr/bin/env python3
"""
patch_cnv_retire_7b.py -- CNV_RETIRE_7B: retire the legacy CNV chain.

Retired: ZSCORE_CNV, CNV_PLOTS, CNV_CONCORDANCE, CNV_CLINICAL_REPORT, CNV_ANNOTATE
(handoff item 7b; decision 2026-09-07 evening: CNV_ANNOTATE goes too, its
cytoband/ClinGen/gene-role columns move into the consensus table as a follow-up).

Edits (all-or-nothing, dry run by default, --apply writes, .bak_cnv_retire_7b_<ts>):
  subworkflows/local/cnv_calling.nf    rewritten: CNVKIT only
  workflows/tspipe.nf                  channels, CNV_CALLING call, consensus join, ORGANIZE assembly
  modules/local/cnv_consensus_multi.nf concordance input and argument removed
  bin/cnv_consensus_multi.py           --concordance optional and ignored; passthrough removed
  modules/local/organize_output.nf     five legacy inputs and arguments removed
  bin/organize_output.py               five legacy arguments and the hardlink block removed
  conf/modules.config                  five publishDir blocks removed
  bin/dashboard_builder/build.py       legacy parsers/cnv.py import and parse removed
  docs/sops/cnv_calling.md             SOP for the surviving subworkflow

Deletions are NOT done here; git rm the eleven files listed in the SOP after --apply.
"""

import argparse
import os
import re
import stat
import sys
import time

MARKER = "CNV_RETIRE_7B"
TAG = "cnv_retire_7b"

NEW_CNV_CALLING_NF = r'''/*
 * subworkflows/local/cnv_calling.nf  (CNV_CALLING_V2, MARKER CNV_RETIRE_7B)
 *
 * Per-sample CNVkit arm (K) of the multi-arm consensus. The legacy chain that
 * once hung off it (ZSCORE_CNV, CNV_PLOTS, CNV_CONCORDANCE, CNV_CLINICAL_REPORT,
 * CNV_ANNOTATE) was retired on 2026-09-07 (handoff item 7b): the consensus,
 * exon plots, chromosome pages, reconCNV and the dashboard CNV tab read the
 * CNVkit outputs emitted here and the other arms directly.
 *
 * Sex-stratified reference selection happens inside CNVKIT from meta.sex
 * (SEXSTRAT_V1; params.cnv_sex_fallback for anything else).
 */

include { CNVKIT } from '../../modules/local/cnvkit'

workflow CNV_CALLING {

    take:
        bam_ch                 // [meta, bam, bai]
        reference_ch           // value [fasta, fai, dict]
        bed_ch                 // value path (panel BED)
        pon_male_ch            // value path (cnvkit_pon_male.cnn)
        pon_female_ch          // value path (cnvkit_pon_female.cnn)
        loo_summary_ch         // value path (cnvkit_loo_summary.tsv)
        noisy_bins_ch          // value path (cnvkit_noisy_bins.bed)
        loo_summary_female_ch  // SEXSTRAT_V1 value path (cnvkit_loo_summary_female.tsv, or the male file)
        noisy_bins_female_ch   // SEXSTRAT_V1 value path (cnvkit_noisy_bins_female.bed, or the male file)

    main:
        CNVKIT(
            bam_ch,
            reference_ch,
            bed_ch,
            pon_male_ch,
            pon_female_ch,
            noisy_bins_ch,
            loo_summary_ch,
            noisy_bins_female_ch,   // SEXSTRAT_V1
            loo_summary_female_ch,  // SEXSTRAT_V1
        )

    emit:
        cnvkit_calls       = CNVKIT.out.call_cns
        cnvkit_cnr         = CNVKIT.out.cnr
        cnvkit_cns         = CNVKIT.out.cns
        cnvkit_genemetrics = CNVKIT.out.genemetrics
}
'''

NEW_SOP = r'''# SOP: CNV_CALLING (V2) and the retired legacy CNV chain (7b)

## What the subworkflow does now

`subworkflows/local/cnv_calling.nf` runs CNVKIT only: batch against the
sex-stratified PoN, call, genemetrics. It emits `cnvkit_calls` (.call.cns),
`cnvkit_cnr`, `cnvkit_cns` and `cnvkit_genemetrics`. Consumers:
CNV_CONSENSUS_MULTI (arm K), RECONCNV, CHROM_PAGES/EXON_PLOTS through the
consensus JSON.

Inputs: BAM, reference, panel BED, male and female PoN, LOO summary and
noisy-bins BED per stratum. No longer inputs of the pipeline:
`loo_bin_noise_profile.tsv` (ZSCORE_CNV), `cytoBand_hg38.txt` and the
ClinGen list (CNV_ANNOTATE), `cnv_scatter_regions.txt` (CNV_PLOTS). The
asset files stay in the repo; `params.cnv_noise_profile`, `params.cytoband`
and `params.clingen` are accepted and ignored.

## Retired on 2026-09-07 (CNV_RETIRE_7B)

Processes and scripts removed from the DAG and the tree:

    modules/local/zscore_cnv.nf            bin/zscore_cnv.py
    modules/local/cnv_plots.nf             bin/cnv_plots.py
    modules/local/cnv_concordance.nf       bin/cnv_concordance.py
    modules/local/cnv_clinical_report.nf   bin/cnv_clinical_report.py
    modules/local/cnv_annotate.nf          bin/cnv_annotate.py
    bin/dashboard_builder/parsers/cnv.py

Why: the two-caller (CNVkit + Z-score) concordance, its tiered clinical
report and its plot layout were superseded by the six-arm consensus
(CMX_V2), the target-space chromosome pages, exon plots and reconCNV, and
by the dashboard CNV tab built on the consensus table (DASH_CNV_V1). The
annotated table (cytoband, ClinGen HI/TS, gene role, heme significance) was
no longer rendered anywhere; its useful columns are to be added to the
consensus `genes.tsv` in `cnv_consensus_multi.py` (follow-up).

Downstream changes:
- CNV_CONSENSUS_MULTI no longer takes the concordance table; `--concordance`
  in `cnv_consensus_multi.py` is optional and ignored.
- ORGANIZE_OUTPUT no longer receives the clinical/annotated tables or the
  CNVkit plot outputs; `organize_output.py` lost those five arguments and
  `<sample>/cnv_consensus/` and `<sample>/cnvkit_plots/` are no longer
  created under clinical/. Everything CNV lives under `clinical/cnv/`.
- `conf/modules.config`: the five publishDir blocks are gone, so
  `<outdir>/<sample>/cnv/{zscore,plots,concordance,report,annotated}` are
  no longer produced. `cnv/cnvkit` remains.
- Dashboard: `build.py` reads `parsers/cnv_v2.py` only.

Task-hash effect: CNV_CONSENSUS_MULTI (input tuple changed) and ORGANIZE_OUTPUT
re-execute for every sample on a resume; EXON_PLOTS, CHROM_PAGES, DASHBOARD and
REPORT_BUNDLE follow. CNVKIT and the other arms stay cached.

## Rollback

Patcher `tools/patches/2026-09-07/patch_cnv_retire_7b.py` leaves
`.bak_cnv_retire_7b_<ts>` copies of every edited file; the deleted files
are in git history at a2bc0b1.
'''

TSPIPE_EDITS = [
    (
        "noise profile channel",
        """    ch_cnv_noise_profile = Channel.value(file(
        params.cnv_noise_profile ?: "${projectDir}/assets/${params.panel}/loo_bin_noise_profile.tsv",
        checkIfExists: true))
""",
        """    // MARKER CNV_RETIRE_7B: loo_bin_noise_profile.tsv (ZSCORE_CNV), cytoBand/ClinGen
    // (CNV_ANNOTATE) and cnv_scatter_regions.txt (CNV_PLOTS) are no longer pipeline
    // inputs; params.cnv_noise_profile, params.cytoband, params.clingen are ignored.
""",
    ),
    (
        "SEXSTRAT comment",
        """    // meta.sex happens inside CNVKIT, CNV_ANNOTATE, CNV_CONSENSUS_MULTI and
""",
        """    // meta.sex happens inside CNVKIT, CNV_CONSENSUS_MULTI and
""",
    ),
    (
        "cytoband/clingen/scatter channels",
        """    // Panel-agnostic annotation references.
    ch_cytoband = Channel.value(file(
        params.cytoband ?: "${projectDir}/assets/references/cytoBand_hg38.txt",
        checkIfExists: true))
    ch_clingen  = Channel.value(file(
        params.clingen  ?: "${projectDir}/assets/references/ClinGen_gene_curation_list_GRCh38.tsv",
        checkIfExists: true))
    // Panel-specific chr-gene scatter regions (no runtime override; lives in panel assets).
    ch_scatter_regions = Channel.value(file(
        "${projectDir}/assets/${params.panel}/cnv_scatter_regions.txt",
        checkIfExists: true))
""",
        "",
    ),
    (
        "CNV_CALLING call",
        """    // ----- 4. CNV calling (CNVKit + Z-score + concordance) --------------
    // nf-core CNV wiring v1 (apply_nfcore_cnv_wiring_part1)
    CNV_CALLING(
        ch_final_bam,
        ch_reference,
        ch_bed,
        ch_cnv_pon_male,
        ch_cnv_pon_female,
        ch_cnv_loo_summary,
        ch_cnv_noisy_bins,
        ch_cnv_noise_profile,
        ch_cytoband,
        ch_clingen,
        ch_scatter_regions,
        ch_cnv_loo_summary_female,   // SEXSTRAT_V1
        ch_cnv_noisy_bins_female,    // SEXSTRAT_V1
    )
""",
        """    // ----- 4. CNV calling: CNVkit arm K (MARKER CNV_RETIRE_7B; legacy chain retired) -----
    CNV_CALLING(
        ch_final_bam,
        ch_reference,
        ch_bed,
        ch_cnv_pon_male,
        ch_cnv_pon_female,
        ch_cnv_loo_summary,
        ch_cnv_noisy_bins,
        ch_cnv_loo_summary_female,   // SEXSTRAT_V1
        ch_cnv_noisy_bins_female,    // SEXSTRAT_V1
    )
""",
    ),
    (
        "consensus join",
        """        ch_consensus_in = CNV_CALLING.out.concordance
            .join( CNV_CALLING.out.cnvkit_cnr,           by: 0 )
            .join( CNV_CALLING.out.cnvkit_calls,         by: 0 )
""",
        """        ch_consensus_in = CNV_CALLING.out.cnvkit_cnr                       // CNV_RETIRE_7B: no concordance input
            .join( CNV_CALLING.out.cnvkit_calls,         by: 0 )
""",
    ),
    (
        "ORGANIZE assembly",
        """        .join(CNV_CALLING.out.clinical_report)                               // + cnv_clinical_tsv
        .join(CNV_CALLING.out.annotated)                                     // + cnv_annotated_tsv
        .join(CNV_CALLING.out.cnvkit_diagram_pdf)                            // + cnvkit_diagram
        .join(CNV_CALLING.out.cnvkit_scatter_png)                            // + cnvkit_scatter
        .join(CNV_CALLING.out.plots_dir)                                     // + cnvkit_plots_dir
""",
        "",
    ),
]

CMX_NF_EDITS = [
    (
        "input tuple",
        """        tuple val(meta), path(concordance), path(cnr), path(call_cns),
""",
        """        tuple val(meta), path(cnr), path(call_cns),   // MARKER CNV_RETIRE_7B: concordance input removed
""",
    ),
    (
        "script argument",
        """            --concordance ${concordance} \\\\
""",
        "",
    ),
    (
        "version comment",
        """        # consensus rule version: CMX_V2_4 (bash comment; busts the task cache)
""",
        """        # consensus rule version: CMX_V2_4; inputs CNV_RETIRE_7B (bash comment; busts the task cache)
""",
    ),
]

CMX_PY_EDITS = [
    (
        "required arguments",
        """    for name in ["sample", "concordance", "cnr", "call-cns", "gatk-genes",
                 "gatk-called", "denoised", "baf-summary", "baf-sites",
                 "loo-summary", "out-prefix"]:
        ap.add_argument("--" + name, required=True)
""",
        """    for name in ["sample", "cnr", "call-cns", "gatk-genes",
                 "gatk-called", "denoised", "baf-summary", "baf-sites",
                 "loo-summary", "out-prefix"]:
        ap.add_argument("--" + name, required=True)
    ap.add_argument("--concordance", default=None,
                    help="legacy two-caller concordance table; accepted and ignored (CNV_RETIRE_7B)")
""",
    ),
    (
        "existence check",
        """    for p in [args.concordance, args.cnr, args.call_cns, args.gatk_genes,
""",
        """    for p in [args.cnr, args.call_cns, args.gatk_genes,
""",
    ),
    (
        "legacy passthrough",
        """    # ---- legacy concordance passthrough (CMX_V2: Z-score is not an arm)
    lg_header, lg_rows = read_tsv(args.concordance, comment="#")
    gene_col = "gene" if "gene" in lg_header else (
        "Gene" if "Gene" in lg_header else None)
    legacy = {}
    if gene_col is None:
        warn("legacy concordance has no gene/Gene column; passthrough skipped")
    else:
        for r in lg_rows:
            legacy[r[gene_col]] = r
""",
        """    # ---- legacy concordance passthrough retired (CNV_RETIRE_7B); --concordance is ignored
    legacy = {}
""",
    ),
]

ORG_NF_EDITS = [
    (
        "input paths",
        """              path(cnv_clinical_tsv),
              path(cnv_annotated_tsv),
              path(cnvkit_diagram),
              path(cnvkit_scatter),
              path(cnvkit_plots_dir),
""",
        """              // MARKER CNV_RETIRE_7B: legacy CNV inputs (clinical/annotated tables, CNVkit plots) removed
""",
    ),
    (
        "script arguments",
        """            --cnv-clinical-tsv    ${cnv_clinical_tsv} \\\\
            --cnv-annotated-tsv   ${cnv_annotated_tsv} \\\\
            --cnvkit-diagram-pdf  ${cnvkit_diagram} \\\\
            --cnvkit-scatter-png  ${cnvkit_scatter} \\\\
            --cnvkit-plots-dir    ${cnvkit_plots_dir} \\\\
""",
        "",
    ),
]

ORG_PY_EDITS = [
    (
        "arguments",
        """    parser.add_argument("--cnv-clinical-tsv", required=True)
    parser.add_argument("--cnv-annotated-tsv", required=True)
    parser.add_argument("--cnvkit-diagram-pdf", required=True)
    parser.add_argument("--cnvkit-scatter-png", required=True)
    parser.add_argument("--cnvkit-plots-dir", required=True)
""",
        """    # MARKER CNV_RETIRE_7B: legacy CNV arguments (clinical/annotated tables, CNVkit plots) removed
""",
    ),
    (
        "hardlink block",
        """    # --- CNV ---
    logger.info("--- CNV ---")
    cnv_dst = out / "cnv_consensus"
    hardlink(args.cnv_clinical_tsv,
             cnv_dst / (s + "_cnv_clinical.tsv"),
             "CNV consensus clinical TSV")
    hardlink(args.cnv_annotated_tsv,
             cnv_dst / (s + "_cnv_annotated.tsv"),
             "CNV per-gene annotated table (cytoband, ClinGen HI/TS, gene role, heme significance, CDKN2A/2B + 9p/9q rescue)")

    plot_dst = out / "cnvkit_plots"
    hardlink(args.cnvkit_diagram_pdf,
             plot_dst / (s + ".final-diagram.pdf"),
             "CNVkit diagram")
    hardlink(args.cnvkit_scatter_png,
             plot_dst / (s + ".final-scatter.png"),
             "CNVkit scatter")
    # Subdir plots: combined/, overview/, per_chromosome/, per_gene/
    for sub in ("combined", "overview", "per_chromosome", "per_gene"):
        subsrc = Path(args.cnvkit_plots_dir) / sub
        if subsrc.exists():
            hardlink_dir(subsrc, plot_dst / sub, "CNVkit " + sub + " plots")
""",
        """    # --- CNV legacy deliverables (cnv_consensus/, cnvkit_plots/) retired: CNV_RETIRE_7B ---
""",
    ),
]

MODULES_CONFIG_EDITS = [
    (
        "five legacy publishDir blocks",
        """    withName: 'ZSCORE_CNV' {
        publishDir = [
            path: { "${params.outdir}/${meta.id}/cnv/zscore" },
            mode: params.publish_dir_mode,
            pattern: '*.tsv'
        ]
    }

    withName: 'CNV_PLOTS' {
        // Two locations: top-level PDFs go directly under cnv/plots/, the
        // detailed plots/ subtree (combined, overview, per_chromosome,
        // per_gene) lands under cnv/plots/details/.
        publishDir = [
            [
                path: { "${params.outdir}/${meta.id}/cnv/plots" },
                mode: params.publish_dir_mode,
                pattern: '*.pdf'
            ],
            [
                path: { "${params.outdir}/${meta.id}/cnv/plots/details" },
                mode: params.publish_dir_mode,
                pattern: 'plots/**',
                saveAs: { fn -> fn.startsWith('plots/') ? fn.substring(6) : fn }
            ]
        ]
    }

    withName: 'CNV_CONCORDANCE' {
        publishDir = [
            path: { "${params.outdir}/${meta.id}/cnv/concordance" },
            mode: params.publish_dir_mode,
            pattern: '*.tsv'
        ]
    }

    withName: 'CNV_CLINICAL_REPORT' {
        publishDir = [
            path: { "${params.outdir}/${meta.id}/cnv/report" },
            mode: params.publish_dir_mode,
            pattern: '*.{tsv,txt}'
        ]
    }

    withName: 'CNV_ANNOTATE' {
        publishDir = [
            path: { "${params.outdir}/${meta.id}/cnv/annotated" },
            mode: params.publish_dir_mode,
            pattern: '*.tsv'
        ]
    }
""",
        """    // MARKER CNV_RETIRE_7B: ZSCORE_CNV, CNV_PLOTS, CNV_CONCORDANCE, CNV_CLINICAL_REPORT
    // and CNV_ANNOTATE retired on 2026-09-07; their publishDir blocks removed.
""",
    ),
]

BUILD_PY_EDITS = [
    (
        "legacy import",
        """from parsers import cnv as p_cnv
""",
        "",
    ),
    (
        "CNV parse block",
        """    # --- CNV ---
    try:
        ctx["cnv"] = p_cnv.parse(effective_dir, sample)
        # DASH_CNV_V1: v2 outputs (clinical/cnv/) merged into the same context; never fatal
        try:
            ctx["cnv"].update(p_cnv_v2.parse(effective_dir, sample))
        except Exception as exc:  # noqa: BLE001
            logging.warning("[%s] cnv v2 parse failed: %s", sample, exc)
    except Exception as exc:
        logging.warning("[%s] cnv parse failed: %s", sample, exc)
        ctx["cnv"] = {"clinical_table": None, "annotated_table": None,
                      "scatter_png": None, "diagram_pdf": None,
                      "per_chrom_pngs": [], "per_gene_pngs": []}
""",
        """    # --- CNV (MARKER CNV_RETIRE_7B: v2 parser only; legacy parsers/cnv.py retired) ---
    try:
        ctx["cnv"] = p_cnv_v2.parse(effective_dir, sample)
    except Exception as exc:  # noqa: BLE001
        logging.warning("[%s] cnv v2 parse failed: %s", sample, exc)
        ctx["cnv"] = {}
""",
    ),
]

FULL_WRITES = [
    ("subworkflows/local/cnv_calling.nf", NEW_CNV_CALLING_NF, "ZSCORE_CNV", False),
    ("docs/sops/cnv_calling.md", NEW_SOP, None, False),
]

ANCHOR_FILES = [
    ("workflows/tspipe.nf", TSPIPE_EDITS),
    ("modules/local/cnv_consensus_multi.nf", CMX_NF_EDITS),
    ("bin/cnv_consensus_multi.py", CMX_PY_EDITS),
    ("modules/local/organize_output.nf", ORG_NF_EDITS),
    ("bin/organize_output.py", ORG_PY_EDITS),
    ("conf/modules.config", MODULES_CONFIG_EDITS),
    ("bin/dashboard_builder/build.py", BUILD_PY_EDITS),
]


def flex_pattern(anchor):
    lines = anchor.rstrip("\n").split("\n")
    out = []
    for ln in lines:
        stripped = ln.lstrip(" \t")
        body = re.escape(stripped)
        body = re.sub(r"(\\ )+", r"[ \\t]+", body)
        out.append(r"[ \t]*" + body)
    pat = r"\n".join(out)
    if anchor.endswith("\n"):
        pat += r"\n"
    return re.compile(pat)


def brace_balance(text):
    return text.count("{") - text.count("}")


def read(path):
    with open(path) as fh:
        return fh.read()


def backup(path, ts):
    bak = "%s.bak_%s_%s" % (path, TAG, ts)
    with open(path) as src, open(bak, "w") as dst:
        dst.write(src.read())
    os.chmod(bak, os.stat(path).st_mode)
    print("[backup] %s" % bak)


def plan(repo):
    actions = []
    errors = 0

    for rel, payload, guard, executable in FULL_WRITES:
        path = os.path.join(repo, rel)
        if os.path.exists(path):
            cur = read(path)
            if MARKER in cur:
                print("[skip] %s already carries %s" % (rel, MARKER))
                continue
            if guard and guard not in cur:
                print("[error] %s: guard '%s' not found" % (rel, guard))
                errors += 1
                continue
        elif guard:
            print("[error] %s: file missing" % rel)
            errors += 1
            continue
        else:
            print("[info] %s: new file" % rel)
        actions.append((rel, payload, executable))

    for rel, edits in ANCHOR_FILES:
        path = os.path.join(repo, rel)
        if not os.path.exists(path):
            print("[error] %s: file missing" % rel)
            errors += 1
            continue
        cur = read(path)
        if MARKER in cur:
            print("[skip] %s already carries %s" % (rel, MARKER))
            continue
        new = cur
        ok = True
        for label, old, rep in edits:
            pat = flex_pattern(old)
            hits = list(pat.finditer(new))
            if len(hits) != 1:
                print("[error] %s: anchor '%s' matched %d times (need exactly 1)" % (rel, label, len(hits)))
                ok = False
                continue
            new = new[:hits[0].start()] + rep + new[hits[0].end():]
        if not ok:
            errors += 1
            continue
        if brace_balance(new) != brace_balance(cur):
            print("[error] %s: brace balance changed (%d -> %d)" % (rel, brace_balance(cur), brace_balance(new)))
            errors += 1
            continue
        if MARKER not in new:
            print("[error] %s: no %s marker after edits (idempotency guard)" % (rel, MARKER))
            errors += 1
            continue
        actions.append((rel, new, False))

    if errors:
        print("[error] %d problem(s); nothing written" % errors)
        sys.exit(1)
    return actions


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=os.getcwd())
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    repo = os.path.abspath(args.repo)

    actions = plan(repo)
    if not actions:
        print("[ok] nothing to do")
        return
    for rel, _, _ in actions:
        print("[plan] %s" % rel)
    if not args.apply:
        print("[dry-run] %d file(s) would change; re-run with --apply" % len(actions))
        return

    ts = time.strftime("%Y%m%d_%H%M%S")
    for rel, new, executable in actions:
        path = os.path.join(repo, rel)
        d = os.path.dirname(path)
        if not os.path.isdir(d):
            os.makedirs(d)
        if os.path.exists(path):
            backup(path, ts)
        with open(path, "w") as fh:
            fh.write(new)
        if executable:
            os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print("[patch] %s" % rel)

    for rel, _, _ in actions:
        path = os.path.join(repo, rel)
        txt = read(path)
        print("[check] %s: %s x%d, braces %+d" % (rel, MARKER, txt.count(MARKER), brace_balance(txt)))


if __name__ == "__main__":
    main()
