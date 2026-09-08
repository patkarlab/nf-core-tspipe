#!/usr/bin/env python3
"""tools/patches/<date>/patch_dash_qc_v1e.py -- MARKER DASH_QC_V1e

On top of DASH_QC_V1d:
  * 200x reportability tier above the 100x floor: summary gains
    n_exons_ge_200 / pct_exons_ge_200; run-level limit "regions at >= 200x
    >= 95%" (REVIEW below); the overview card "% Target >= 100x (Picard)"
    becomes "% regions >= 200x (mosdepth)".
  * QC tab: "Regions below 200x" table (gene, exon, coverage, driver role,
    known-limitation flag, band = '< 100x' or '100-200x'); the legacy
    dashboard link is removed.
  * Per-gene chart: gene names below the 100x line drawn in red.

Usage:  python3 <this file> [--apply]
Guard:  MARKER DASH_QC_V1e per file; each anchor exactly once; all-or-nothing.
"""

import argparse
import sys
import time
from pathlib import Path

MARKER = "DASH_QC_V1e"
TAG = "dash_qc_v1e"
REPO = Path(__file__).resolve().parents[3]
COV = "bin/dashboard_builder/parsers/coverage.py"
TPL = "bin/dashboard_builder/templates/sample_report.html.j2"

# ---- coverage.py ----------------------------------------------------------
C_THR_OLD = '    "review_pct_dupe": 0.50,       # Picard PCT_EXC_DUPE above this -> REVIEW\n}\n'
C_THR_NEW = (
    '    "review_pct_dupe": 0.50,       # Picard PCT_EXC_DUPE above this -> REVIEW\n'
    '    "exon_reportable": 200,        # DASH_QC_V1e: reportability tier per region (exon)\n'
    '    "review_pct_exons_200x": 0.95, # DASH_QC_V1e: fraction of regions at >= exon_reportable below this -> REVIEW\n'
    '}\n'
)

C_SUM_OLD = '''    out["summary"] = {
        "median_of_per_exon": float(valid["_cov"].median()),
'''
C_SUM_NEW = '''    rep = QC_THRESHOLDS["exon_reportable"]   # DASH_QC_V1e
    n_ge_rep = int((valid["_cov"] >= rep).sum())
    below_rep = valid.loc[valid["_cov"] < rep].sort_values("_cov")
    regions_below_reportable = []
    for r in below_rep.to_dict(orient="records"):
        g, e = r.get("Gene", ""), str(r.get("Exon", ""))
        regions_below_reportable.append({
            "gene": g, "exon": e, "cov": round(float(r["_cov"]), 1),
            "band": "< %dx" % exon_low if float(r["_cov"]) < exon_low else "%d-%dx" % (exon_low, rep),
            "driver_role": cinfo.get(g, {}).get("role", ""),
            "known": (g, e) in known,
            "cnv_call": cinfo.get(g, {}).get("call", ""),
        })
    out["regions_below_reportable"] = regions_below_reportable
    out["summary"] = {
        "n_exons_ge_200": n_ge_rep,
        "pct_exons_ge_200": n_ge_rep / float(n_exons),
        "median_of_per_exon": float(valid["_cov"].median()),
'''

C_FLOOR_OLD = '''        run_rows.insert(0, {"key": "MOSDEPTH_MEDIAN_EXON", "label": "Median per-exon coverage (mosdepth, dup-inclusive)",
                            "value": med, "display": _fmt(med, "x"), "range": ">= " + _fmt(floor, "x"), "ok": ok})
'''
C_FLOOR_NEW = C_FLOOR_OLD + '''        # DASH_QC_V1e: reportability tier
        pct = float(coverage["summary"]["pct_exons_ge_200"])
        lim = QC_THRESHOLDS["review_pct_exons_200x"]
        ok2 = pct >= lim
        if not ok2:
            review.append("Regions at >= %dx (mosdepth, dup-inclusive) %s (limit >= %s)"
                          % (QC_THRESHOLDS["exon_reportable"], _fmt(pct, "pct"), _fmt(lim, "pct")))
        run_rows.insert(1, {"key": "MOSDEPTH_PCT_EXONS_200X", "label": "Regions (exons) at >= %dx (mosdepth, dup-inclusive)" % QC_THRESHOLDS["exon_reportable"],
                            "value": pct, "display": _fmt(pct, "pct"), "range": ">= " + _fmt(lim, "pct"), "ok": ok2})
'''

# ---- template -------------------------------------------------------------
T_CARD_OLD = (
    "              <div class=\"label\">% Target &ge; 100x (Picard)</div>\n"
    "              <div class=\"value\">{{ (m.PCT_TARGET_BASES_100X * 100) | format_num(1) if m.PCT_TARGET_BASES_100X is defined and m.PCT_TARGET_BASES_100X is not none else '\u2014' }}%</div>\n"
    "              <div class=\"subvalue\">Picard, dup-filtered</div>\n"
)
T_CARD_NEW = (
    "              {# DASH_QC_V1e: reportability tier #}\n"
    "              <div class=\"label\">% Regions &ge; {{ ctx.coverage.thresholds.exon_reportable if ctx.coverage else 200 }}x</div>\n"
    "              {% if ctx.coverage and ctx.coverage.summary %}\n"
    "                <div class=\"value\">{{ (ctx.coverage.summary.pct_exons_ge_200 * 100) | format_num(1) }}%</div>\n"
    "                <div class=\"subvalue\">{{ ctx.coverage.summary.n_exons_ge_200 }} of {{ ctx.coverage.summary.n_exons }} exons &middot; {{ ctx.coverage.regions_below_reportable | length }} below &middot; mosdepth, duplicates included</div>\n"
    "              {% else %}\n"
    "                <div class=\"value\">&mdash;</div>\n"
    "              {% endif %}\n"
)

T_TABLE_OLD = "        {# DASH_QC_V1d: known panel limitations with cohort statistics #}\n"
T_TABLE_NEW = (
    "        {# DASH_QC_V1e: every region under the reportability tier #}\n"
    "        <h4 class=\"mt-4\">Regions below {{ ctx.coverage.thresholds.exon_reportable if ctx.coverage else 200 }}x</h4>\n"
    "        {% if ctx.coverage and ctx.coverage.regions_below_reportable %}\n"
    "          <p class=\"text-muted small mb-2\">{{ ctx.coverage.summary.n_exons_ge_200 }} of {{ ctx.coverage.summary.n_exons }} regions ({{ (ctx.coverage.summary.pct_exons_ge_200 * 100) | format_num(1) }}%) are at or above {{ ctx.coverage.thresholds.exon_reportable }}x. "
    "The rest are listed here, lowest first: below {{ ctx.coverage.thresholds.exon_low }}x the region is low; between {{ ctx.coverage.thresholds.exon_low }}x and {{ ctx.coverage.thresholds.exon_reportable }}x it is covered but under the reportability tier. Known panel limitations are marked.</p>\n"
    "          <div class=\"table-responsive\">\n"
    "            <table id=\"qc-regions-table\" class=\"table table-sm table-striped table-hover w-100\">\n"
    "              <thead><tr><th>gene</th><th>exon</th><th>coverage</th><th>band</th><th>driver role</th><th>known limitation</th><th>CNV consensus</th></tr></thead>\n"
    "              <tbody>\n"
    "                {% for r in ctx.coverage.regions_below_reportable %}\n"
    "                  <tr class=\"{% if r.band.startswith('<') %}table-danger{% endif %}\"><td>{{ r.gene }}</td><td>{{ r.exon }}</td><td>{{ r.cov | format_num(0) }}</td><td>{{ r.band }}</td><td>{{ r.driver_role }}</td><td>{% if r.known %}yes{% endif %}</td><td>{{ r.cnv_call }}</td></tr>\n"
    "                {% endfor %}\n"
    "              </tbody>\n"
    "            </table>\n"
    "          </div>\n"
    "        {% elif ctx.coverage and ctx.coverage.summary %}\n"
    "          <p class=\"text-muted small\">All {{ ctx.coverage.summary.n_exons }} regions at or above {{ ctx.coverage.thresholds.exon_reportable }}x.</p>\n"
    "        {% endif %}\n"
    "\n"
    "        {# DASH_QC_V1d: known panel limitations with cohort statistics #}\n"
)

T_LEGACY_OLD = (
    "        {% if ctx.files.existing_dashboard %}\n"
    "          <p class=\"small text-muted mt-3\">Legacy pipeline QC dashboard: <a href=\"./{{ ctx.files.existing_dashboard }}\" target=\"_blank\">{{ ctx.files.existing_dashboard }}</a></p>\n"
    "        {% endif %}\n"
)
T_LEGACY_NEW = "        {# DASH_QC_V1e: legacy per-sample dashboard no longer referenced #}\n"

T_JS_OLD = "    if ($('#qc-gene-table').length)      { $('#qc-gene-table').DataTable({ pageLength: 25, order: [[2, 'asc']] }); }\n"
T_JS_NEW = T_JS_OLD + "    if ($('#qc-regions-table').length)   { $('#qc-regions-table').DataTable({ pageLength: 25, order: [[2, 'asc']] }); }   // DASH_QC_V1e\n"

T_TICK_OLD = "                   scales: { x: { ticks: { autoSkip: false, maxRotation: 90, minRotation: 90, font: { size: 8 } } },\n"
T_TICK_NEW = (
    "                   scales: { x: { ticks: { autoSkip: false, maxRotation: 90, minRotation: 90, font: { size: 8 },\n"
    "                                           color: function (c) { return (qg[c.index] && qg[c.index].median_cov < qlow) ? '#dc3545' : '#666666'; } } },   // DASH_QC_V1e\n"
)

EDITS = [
    (COV, C_THR_OLD, C_THR_NEW), (COV, C_SUM_OLD, C_SUM_NEW), (COV, C_FLOOR_OLD, C_FLOOR_NEW),
    (TPL, T_CARD_OLD, T_CARD_NEW), (TPL, T_TABLE_OLD, T_TABLE_NEW), (TPL, T_LEGACY_OLD, T_LEGACY_NEW),
    (TPL, T_JS_OLD, T_JS_NEW), (TPL, T_TICK_OLD, T_TICK_NEW),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    staged, skipped, errors = {}, [], []
    for rel, old, new in EDITS:
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
        n = staged[rel].count(old)
        if n != 1:
            errors.append("%s: anchor matched %d times (need 1): %r" % (rel, n, old[:70])); continue
        staged[rel] = staged[rel].replace(old, new, 1)
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
