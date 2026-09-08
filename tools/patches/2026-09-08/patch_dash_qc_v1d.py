#!/usr/bin/env python3
"""tools/patches/<date>/patch_dash_qc_v1d.py -- MARKER DASH_QC_V1d

Known low-capture exons (assets/<panel>/known_low_exons.tsv, built by
tools/build_known_low_exons.py from the PoN normals) are panel-design facts.
This patch:
  coverage.py   reads the asset (module-level KNOWN_LOW_EXONS_PATH, set by
                build.py); each gene row gains known_low_exons and
                median_cov_excl_known; a gene is "low" on the median of its
                non-known exons (genes whose exons are all known-low are not
                low genes); driver_exon_low ignores known exons; parse() emits
                panel_limitations = [{gene, exon, sample_cov, normals_median,
                n_below, n_normals}] for every known exon present in the sample.
  build.py      --known-low-exons PATH (optional) -> p_coverage.KNOWN_LOW_EXONS_PATH.
  dashboard.nf  passes ${projectDir}/assets/${params.panel}/known_low_exons.tsv
                when it exists.
  template      "Known panel limitations" block on the overview (one line) and
                the QC tab (table with the cohort statistics).

Usage:  python3 <this file> [--apply]
Guard:  MARKER DASH_QC_V1d per file; each anchor exactly once; all-or-nothing.
"""

import argparse
import sys
import time
from pathlib import Path

MARKER = "DASH_QC_V1d"
TAG = "dash_qc_v1d"
REPO = Path(__file__).resolve().parents[3]
COV = "bin/dashboard_builder/parsers/coverage.py"
BUILD = "bin/dashboard_builder/build.py"
TPL = "bin/dashboard_builder/templates/sample_report.html.j2"
NF = "modules/local/dashboard.nf"

# ---- coverage.py ----------------------------------------------------------
C_DOC_OLD = "MARKER DASH_QC_V1b: low genes explained by a consensus LOSS are CNV findings, not limitations.\n"
C_DOC_NEW = C_DOC_OLD + (
    "MARKER DASH_QC_V1d: known low-capture exons (panel asset) are panel limitations; genes are judged\n"
    "on their non-known exons; parse() emits panel_limitations.\n"
)

C_CONST_OLD = 'CNV_LOW_EXPLAINS = ("LOSS",)   # DASH_QC_V1b: consensus calls that explain low coverage biologically\n'
C_CONST_NEW = C_CONST_OLD + '''
KNOWN_LOW_EXONS_PATH = None   # DASH_QC_V1d: set by build.py from --known-low-exons


def read_known_low(path):
    """(gene, exon) -> {median_cov, n_below, n_normals, frac_below} from known_low_exons.tsv; {} when absent."""
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    out = {}
    with open(p) as fh:
        hdr = None
        for line in fh:
            line = line.rstrip("\\n")
            if not line or line.startswith("#"):
                continue
            f = line.split("\\t")
            if hdr is None:
                hdr = f
                continue
            r = dict(zip(hdr, f))
            try:
                out[(r["gene"], r["exon"])] = {
                    "normals_median": float(r["median_cov"]), "n_below": int(r["n_below"]),
                    "n_normals": int(r["n_normals"]), "frac_below": float(r["frac_below"]),
                }
            except (KeyError, ValueError):
                continue
    return out
'''

C_LOAD_OLD = "    cinfo = _consensus_info(consensus_genes)   # DASH_QC_V1b\n"
C_LOAD_NEW = (
    "    cinfo = _consensus_info(consensus_genes)   # DASH_QC_V1b\n"
    "    known = read_known_low(KNOWN_LOW_EXONS_PATH)   # DASH_QC_V1d\n"
    "    panel_limitations = []\n"
)

C_GENES_OLD = '''    genes = []
    if "Gene" in valid.columns:
        for gene, sub in valid.groupby("Gene", sort=False):
            covs = sub["_cov"]
            i_min = covs.idxmin()
            n_low = int((covs < exon_low).sum())
            genes.append({
                "gene": gene,
                "n_exons": int(len(sub)),
                "median_cov": round(float(covs.median()), 1),
                "min_exon": str(sub.loc[i_min, "Exon"]) if "Exon" in sub.columns else "",
                "min_cov": round(float(covs.min()), 1),
                "n_low": n_low,
                "frac_low": round(n_low / float(len(sub)), 2),
                "driver_role": cinfo.get(gene, {}).get("role", ""),
                "cnv_call": cinfo.get(gene, {}).get("call", ""),   # DASH_QC_V1b
                "cnv_tier": cinfo.get(gene, {}).get("tier", ""),
            })
    genes.sort(key=lambda g: (g["median_cov"], g["gene"]))
    low_genes = [g for g in genes if g["median_cov"] < gene_low]
'''
C_GENES_NEW = '''    genes = []
    if "Gene" in valid.columns:
        for gene, sub in valid.groupby("Gene", sort=False):
            covs = sub["_cov"]
            i_min = covs.idxmin()
            n_low = int((covs < exon_low).sum())
            # DASH_QC_V1d: known low-capture exons of the panel are set aside
            exon_labels = sub["Exon"].astype(str) if "Exon" in sub.columns else pd.Series([""] * len(sub), index=sub.index)
            is_known = [(gene, e) in known for e in exon_labels]
            known_here = [e for e, k in zip(exon_labels, is_known) if k]
            for e, k, cv in zip(exon_labels, is_known, covs):
                if k:
                    kk = known[(gene, e)]
                    panel_limitations.append({"gene": gene, "exon": e, "sample_cov": round(float(cv), 1),
                                              "normals_median": kk["normals_median"], "n_below": kk["n_below"],
                                              "n_normals": kk["n_normals"]})
            rest = covs[[not k for k in is_known]]
            n_low_known = sum(1 for k, cv in zip(is_known, covs) if k and cv < exon_low)
            genes.append({
                "gene": gene,
                "n_exons": int(len(sub)),
                "median_cov": round(float(covs.median()), 1),
                "median_cov_excl_known": round(float(rest.median()), 1) if len(rest) else None,
                "known_low_exons": known_here,
                "min_exon": str(sub.loc[i_min, "Exon"]) if "Exon" in sub.columns else "",
                "min_cov": round(float(covs.min()), 1),
                "n_low": n_low,
                "n_low_known": n_low_known,
                "frac_low": round(n_low / float(len(sub)), 2),
                "driver_role": cinfo.get(gene, {}).get("role", ""),
                "cnv_call": cinfo.get(gene, {}).get("call", ""),   # DASH_QC_V1b
                "cnv_tier": cinfo.get(gene, {}).get("tier", ""),
            })
    genes.sort(key=lambda g: (g["median_cov"], g["gene"]))
    # DASH_QC_V1d: a gene is low on the median of its non-known exons; genes with only known exons are panel limitations
    low_genes = [g for g in genes if g["median_cov_excl_known"] is not None and g["median_cov_excl_known"] < gene_low]
'''

C_OUT_OLD = '    out["genes"] = genes\n    out["low_genes"] = low_genes\n    return out\n'
C_OUT_NEW = (
    '    out["genes"] = genes\n    out["low_genes"] = low_genes\n'
    '    out["panel_limitations"] = sorted(panel_limitations, key=lambda r: (r["gene"], r["exon"]))   # DASH_QC_V1d\n'
    '    return out\n'
)

C_DRV_OLD = '''    driver_exon_low = [g for g in (coverage or {}).get("genes", []) if coverage
                       and g.get("driver_role") and g["n_low"] > 0 and g["gene"] not in low_set
                       and g.get("cnv_call") not in CNV_LOW_EXPLAINS]
'''
C_DRV_NEW = '''    driver_exon_low = [g for g in (coverage or {}).get("genes", []) if coverage
                       and g.get("driver_role") and (g["n_low"] - g.get("n_low_known", 0)) > 0
                       and g["gene"] not in low_set
                       and g.get("cnv_call") not in CNV_LOW_EXPLAINS]   # DASH_QC_V1d: known exons ignored
'''

# the driver_exon_low reason names min_exon, which may be a known exon: name the worst non-known low exon instead
C_NAMES_OLD = '''        names = ", ".join("%s (%s %.0fx)" % (g["gene"], g["min_exon"], g["min_cov"]) for g in driver_exon_low[:12])
'''
C_NAMES_NEW = '''        names = ", ".join("%s (%s)" % (g["gene"], g.get("worst_unknown_exon", g["min_exon"])) for g in driver_exon_low[:12])   # DASH_QC_V1d
'''

# worst non-known low exon label per gene, computed in parse()
C_WORST_OLD = '''            rest = covs[[not k for k in is_known]]
'''
C_WORST_NEW = '''            rest = covs[[not k for k in is_known]]
            worst_unknown = ""
            if len(rest) and float(rest.min()) < exon_low:
                j = rest.idxmin()
                worst_unknown = "%s %.0fx" % (str(sub.loc[j, "Exon"]) if "Exon" in sub.columns else "", float(rest.min()))
'''
C_WORSTKEY_OLD = '''                "known_low_exons": known_here,
'''
C_WORSTKEY_NEW = '''                "known_low_exons": known_here,
                "worst_unknown_exon": worst_unknown,
'''

# ---- build.py -------------------------------------------------------------
B_ARG_ANCHOR = "    args = parser.parse_args()"
B_ARG_NEW = (
    "    p_coverage.KNOWN_LOW_EXONS_PATH = args.known_low_exons   # DASH_QC_V1d\n"
)
B_ADD_OLD = '''    parser.add_argument(
        "--panel-bed", default=None,
'''
B_ADD_NEW = '''    parser.add_argument(
        "--known-low-exons", dest="known_low_exons", default=None,
        help="known_low_exons.tsv for the panel (tools/build_known_low_exons.py): exons "
             "systematically under-captured in the PoN normals, reported as panel "
             "limitations and excluded from the sample QC verdict. Optional."   # DASH_QC_V1d
    )
    parser.add_argument(
        "--panel-bed", default=None,
'''

# ---- dashboard.nf ---------------------------------------------------------
N_DEF_OLD = '        def py            = params.dashboard_python ?: "${params.legacy_python_env}/bin/python"\n'
N_DEF_NEW = N_DEF_OLD + (
    '        def known_low     = file("${projectDir}/assets/${params.panel}/known_low_exons.tsv")   // DASH_QC_V1d\n'
    '        def known_low_arg = known_low.exists() ? "--known-low-exons ${known_low}" : \'\'\n'
)
N_CMD_OLD = "            ${task.ext.args ?: ''}\n"
N_CMD_NEW = "            ${known_low_arg} \\\\\n            ${task.ext.args ?: ''}\n"

# ---- template -------------------------------------------------------------
T_OV_OLD = "            <div class=\"small text-muted mt-1\">Full detail on the QC tab.</div>\n          </div>\n        {% endif %}\n"
T_OV_NEW = T_OV_OLD + (
    "        {# DASH_QC_V1d: known panel limitations, one line #}\n"
    "        {% if ctx.coverage and ctx.coverage.panel_limitations %}\n"
    "          <div class=\"alert alert-light border small\" role=\"alert\">\n"
    "            <strong>Known panel limitations</strong> (under-captured in the normal cohort; not counted against this sample):\n"
    "            {% for r in ctx.coverage.panel_limitations %}<span class=\"badge bg-light text-dark border me-1\">{{ r.gene }} {{ r.exon }} &middot; {{ r.sample_cov | format_num(0) }}x</span>{% endfor %}\n"
    "          </div>\n"
    "        {% endif %}\n"
)

T_QC_OLD = "        <h4 class=\"mt-4\">Run metrics (Picard CollectHsMetrics)</h4>\n"
T_QC_NEW = (
    "        {# DASH_QC_V1d: known panel limitations with cohort statistics #}\n"
    "        {% if ctx.coverage and ctx.coverage.panel_limitations %}\n"
    "          <h4 class=\"mt-4\">Known panel limitations</h4>\n"
    "          <p class=\"text-muted small mb-2\">Exons below {{ ctx.coverage.thresholds.exon_low }}x in at least half of the panel-of-normals cohort (assets/known_low_exons.tsv). "
    "They are a property of the capture design, are excluded from this sample's verdict, and variants in them are not reportable as negative.</p>\n"
    "          <table class=\"table table-sm tspipe-kv-table\" style=\"max-width: 760px;\">\n"
    "            <thead><tr><th>gene</th><th>exon</th><th>this sample</th><th>normals median</th><th>normals below threshold</th></tr></thead>\n"
    "            <tbody>\n"
    "              {% for r in ctx.coverage.panel_limitations %}\n"
    "                <tr><td>{{ r.gene }}</td><td>{{ r.exon }}</td><td class=\"value\">{{ r.sample_cov | format_num(0) }}x</td><td class=\"value\">{{ r.normals_median | format_num(0) }}x</td><td class=\"value\">{{ r.n_below }} / {{ r.n_normals }}</td></tr>\n"
    "              {% endfor %}\n"
    "            </tbody>\n"
    "          </table>\n"
    "        {% endif %}\n"
    "\n"
    "        <h4 class=\"mt-4\">Run metrics (Picard CollectHsMetrics)</h4>\n"
)

EDITS = [
    (COV, C_DOC_OLD, C_DOC_NEW, "replace"),
    (COV, C_CONST_OLD, C_CONST_NEW, "replace"),
    (COV, C_LOAD_OLD, C_LOAD_NEW, "replace"),
    (COV, C_GENES_OLD, C_GENES_NEW, "replace"),
    (COV, C_WORST_OLD, C_WORST_NEW, "replace"),
    (COV, C_WORSTKEY_OLD, C_WORSTKEY_NEW, "replace"),
    (COV, C_OUT_OLD, C_OUT_NEW, "replace"),
    (COV, C_DRV_OLD, C_DRV_NEW, "replace"),
    (COV, C_NAMES_OLD, C_NAMES_NEW, "replace"),
    (BUILD, B_ADD_OLD, B_ADD_NEW, "replace"),
    (BUILD, B_ARG_ANCHOR, B_ARG_NEW, "insert_after_line"),
    (NF, N_DEF_OLD, N_DEF_NEW, "replace"),
    (NF, N_CMD_OLD, N_CMD_NEW, "replace"),
    (TPL, T_OV_OLD, T_OV_NEW, "replace"),
    (TPL, T_QC_OLD, T_QC_NEW, "replace"),
]


def apply_edit(text, old, new, mode):
    if mode == "insert_after_line":
        lines = text.split("\n")
        hits = [i for i, l in enumerate(lines) if old in l]
        if len(hits) != 1:
            return None, len(hits)
        lines.insert(hits[0] + 1, new.rstrip("\n"))
        return "\n".join(lines), 1
    n = text.count(old)
    if n != 1:
        return None, n
    return text.replace(old, new, 1), 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    staged, skipped, errors = {}, [], []
    for rel, old, new, mode in EDITS:
        if rel in skipped:
            continue
        p = REPO / rel
        if rel not in staged:
            if not p.exists():
                errors.append("%s: file not found" % rel); continue
            text = p.read_text()
            if MARKER in text:
                print("SKIP  %s: %s already present" % (rel, MARKER)); skipped.append(rel); continue
            staged[rel] = text
        out, n = apply_edit(staged[rel], old, new, mode)
        if out is None:
            errors.append("%s: anchor matched %d times (need 1): %r" % (rel, n, old[:70])); continue
        staged[rel] = out
    if errors:
        print("ABORT -- nothing written:")
        for e in errors:
            print("  " + e)
        sys.exit(1)
    for rel, text in staged.items():
        print("PLAN  %s: %+d lines, marker %s" % (rel, text.count("\n") - (REPO / rel).read_text().count("\n"), MARKER))
    if not args.apply:
        print("dry run; re-run with --apply"); return
    stamp = time.strftime("%Y%m%d_%H%M%S")
    for rel, text in staged.items():
        p = REPO / rel
        bak = p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp))
        bak.write_text(p.read_text()); p.write_text(text)
        print("WROTE %s (backup %s)" % (rel, bak.name))
    print("done")


if __name__ == "__main__":
    main()
