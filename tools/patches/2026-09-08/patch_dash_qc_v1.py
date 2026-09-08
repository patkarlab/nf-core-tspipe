#!/usr/bin/env python3
"""tools/patches/<date>/patch_dash_qc_v1.py -- MARKER DASH_QC_V1

D7 (QC page overhaul) and D8 (median, not mean).

bin/dashboard_builder/parsers/coverage.py is REPLACED (old file backed up):
  * headline = median of per-exon coverages (mean kept in summary, not shown);
  * gene table: n_exons, median exon coverage, worst exon and depth, n and
    fraction of exons < 100x, driver_role joined from the sample's
    cnv_consensus4.genes.tsv when present;
  * complete low-coverage gene list (median < gene_low_median), sorted
    ascending, no cap; per-exon rows unchanged;
  * verdict(coverage, hsmetrics): PASS | PASS_WITH_LIMITATIONS | REVIEW with
    reasons, and a run-metrics table with acceptance ranges.
  Thresholds in QC_THRESHOLDS at the top of the file.

bin/dashboard_builder/build.py: pass the consensus genes path; ctx["qc_verdict"].

templates/sample_report.html.j2:
  * header pill shows the verdict instead of "QC Review Pending";
  * overview cards: Median Coverage; Low-Coverage Genes; complete low-gene
    badge list replaces the capped exon examples; "phase 2" note removed;
  * QC tab rewritten: verdict + reasons | low-coverage genes table | run
    metrics with ranges | per-gene median bar chart (Chart.js, log y, 100x
    line) | all genes table | fastp | per-exon table (collapsed).
    The embedded pipeline QC dashboard iframe is replaced by a link.
  * DataTable init for the two new tables; chart script.

bin/ is not hashed: re-render with `-c /tmp/dash_nocache.config`.

Usage:  python3 <this file> [--apply]
Guard:  MARKER DASH_QC_V1 per file; each anchor exactly once; all-or-nothing;
        backups <file>.bak_dash_qc_v1_<stamp>.
"""

import argparse
import sys
import time
from pathlib import Path

MARKER = "DASH_QC_V1"
TAG = "dash_qc_v1"
REPO = Path(__file__).resolve().parents[3]

COV = "bin/dashboard_builder/parsers/coverage.py"
BUILD = "bin/dashboard_builder/build.py"
TPL = "bin/dashboard_builder/templates/sample_report.html.j2"

# ---------------------------------------------------------------------------
# coverage.py -- full replacement
# ---------------------------------------------------------------------------
COVERAGE_PY = r'''"""Parse per-exon coverage TSV and derive gene-level and sample-level QC.

MARKER DASH_QC_V1 (D7 QC page overhaul, D8 median instead of mean).

Input schema (bin/parse_exon_coverage.py):
  Gene, Exon, Chr, Start, End, Length_bp, Mean_Coverage, Pct_100x, Pct_250x, Pct_500x, Flag
Mean_Coverage is mosdepth's per-region mean (duplicates included, the clinical
convention). Aggregates here use the MEDIAN across exons, which is robust to a
single skewed exon.

parse(path, consensus_genes=None) returns
  {
    'columns', 'rows', 'n'            per-exon table, unchanged
    'thresholds'                      QC_THRESHOLDS
    'summary': {
        'median_of_per_exon':  float  headline
        'mean_of_per_exon_means': float  kept for comparison; not displayed
        'n_exons', 'n_low_lt_100', 'n_low_lt_250'
        'n_genes', 'n_low_genes'
        'low_lt_100_examples'  kept for older templates (first 8 low exons)
    }
    'genes':     [ {gene, n_exons, median_cov, min_exon, min_cov, n_low, frac_low, driver_role} ... ]
    'low_genes': subset with median_cov < thresholds['gene_low_median'], ascending
  }

verdict(coverage, hsmetrics) returns
  {'status', 'label', 'pill', 'reasons': [...], 'run_metrics': [ {key,label,value,display,range,ok} ... ]}
"""

from pathlib import Path

import pandas as pd

QC_THRESHOLDS = {
    "gene_low_median": 100,        # gene is low when the median of its exon coverages is below this
    "exon_low": 100,               # exon is low below this (matches parse_exon_coverage.py)
    "review_median_target": 250,   # Picard MEDIAN_TARGET_COVERAGE below this -> REVIEW
    "review_pct_100x": 0.95,       # Picard PCT_TARGET_BASES_100X below this -> REVIEW
    "review_pct_dupe": 0.50,       # Picard PCT_EXC_DUPE above this -> REVIEW
}

# key, label, threshold key (or None), direction ('min' value must be >= thr; 'max' value must be <= thr), format
RUN_METRICS = [
    ("TOTAL_READS", "Total reads", None, None, "int"),
    ("PCT_PF_UQ_READS_ALIGNED", "PF unique reads aligned", None, None, "pct"),
    ("PCT_EXC_DUPE", "Bases excluded as duplicate", "review_pct_dupe", "max", "pct"),
    ("PCT_SELECTED_BASES", "On- or near-bait bases", None, None, "pct"),
    ("MEAN_TARGET_COVERAGE", "Mean target coverage (Picard, dup-filtered)", None, None, "x"),
    ("MEDIAN_TARGET_COVERAGE", "Median target coverage (Picard, dup-filtered)", "review_median_target", "min", "x"),
    ("FOLD_80_BASE_PENALTY", "Fold-80 base penalty (uniformity)", None, None, "f2"),
    ("PCT_TARGET_BASES_100X", "Target bases at >= 100x", "review_pct_100x", "min", "pct"),
    ("PCT_TARGET_BASES_250X", "Target bases at >= 250x", None, None, "pct"),
    ("PCT_TARGET_BASES_500X", "Target bases at >= 500x", None, None, "pct"),
    ("ZERO_CVG_TARGETS_PCT", "Targets with zero coverage", None, None, "pct"),
    ("AT_DROPOUT", "AT dropout", None, None, "f2"),
    ("GC_DROPOUT", "GC dropout", None, None, "f2"),
    ("HET_SNP_SENSITIVITY", "Het SNP sensitivity", None, None, "f3"),
]


def _fmt(value, kind):
    if value is None:
        return "\u2014"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)
    if kind == "int":
        return "{:,}".format(int(round(v)))
    if kind == "pct":
        return "{:.1f}%".format(v * 100.0)
    if kind == "x":
        return "{:.0f}x".format(v)
    if kind == "f2":
        return "{:.2f}".format(v)
    if kind == "f3":
        return "{:.3f}".format(v)
    return str(value)


def _range_text(thr_key, direction, kind):
    if thr_key is None:
        return ""
    thr = QC_THRESHOLDS[thr_key]
    shown = _fmt(thr, kind)
    return (">= " + shown) if direction == "min" else ("<= " + shown)


def _driver_roles(consensus_genes):
    """gene -> driver_role from <sample>.cnv_consensus4.genes.tsv (CMX_ANNOT_V1); {} when absent."""
    if not consensus_genes:
        return {}
    p = Path(consensus_genes)
    if not p.exists():
        return {}
    try:
        df = pd.read_csv(p, sep="\t", dtype=str, keep_default_na=False)
    except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError):
        return {}
    if "gene" not in df.columns or "driver_role" not in df.columns:
        return {}
    out = {}
    for g, r in zip(df["gene"], df["driver_role"]):
        r = (r or "").strip()
        if r and r != "NA":
            out[g] = r
    return out


def parse(path, consensus_genes=None):
    path = Path(path)
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False, na_values=[""])
    except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError):
        return None

    df = df.fillna("")
    cols = list(df.columns)
    rows = df.to_dict(orient="records")
    out = {"columns": cols, "rows": rows, "n": len(df), "thresholds": dict(QC_THRESHOLDS),
           "summary": None, "genes": [], "low_genes": []}

    if "Mean_Coverage" not in df.columns or not len(df):
        return out

    numeric = pd.to_numeric(df["Mean_Coverage"], errors="coerce")
    valid = df.assign(_cov=numeric).loc[numeric.notna()].copy()
    n_exons = int(len(valid))
    if n_exons == 0:
        return out

    exon_low = QC_THRESHOLDS["exon_low"]
    gene_low = QC_THRESHOLDS["gene_low_median"]
    roles = _driver_roles(consensus_genes)

    genes = []
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
                "driver_role": roles.get(gene, ""),
            })
    genes.sort(key=lambda g: (g["median_cov"], g["gene"]))
    low_genes = [g for g in genes if g["median_cov"] < gene_low]

    low_df = valid.loc[valid["_cov"] < exon_low].sort_values("_cov").head(8)
    low_examples = [{"Gene": r.get("Gene", ""), "Exon": r.get("Exon", ""), "Mean_Coverage": r.get("Mean_Coverage", "")}
                    for r in low_df.to_dict(orient="records")]

    out["summary"] = {
        "median_of_per_exon": float(valid["_cov"].median()),
        "mean_of_per_exon_means": float(valid["_cov"].mean()),
        "n_exons": n_exons,
        "n_low_lt_100": int((valid["_cov"] < 100).sum()),
        "n_low_lt_250": int((valid["_cov"] < 250).sum()),
        "n_genes": len(genes),
        "n_low_genes": len(low_genes),
        "low_lt_100_examples": low_examples,
    }
    out["genes"] = genes
    out["low_genes"] = low_genes
    return out


def verdict(coverage, hsmetrics):
    """Sample-level QC verdict from Picard run metrics and the gene-level coverage table."""
    m = (hsmetrics or {}).get("metrics", {}) if isinstance(hsmetrics, dict) else {}
    run_rows, review = [], []
    for key, label, thr_key, direction, kind in RUN_METRICS:
        val = m.get(key)
        ok = None
        if thr_key is not None and val is not None:
            try:
                v = float(val)
                thr = QC_THRESHOLDS[thr_key]
                ok = (v >= thr) if direction == "min" else (v <= thr)
                if not ok:
                    review.append("%s %s (limit %s)" % (label, _fmt(v, kind), _range_text(thr_key, direction, kind)))
            except (TypeError, ValueError):
                ok = None
        run_rows.append({"key": key, "label": label, "value": val, "display": _fmt(val, kind),
                         "range": _range_text(thr_key, direction, kind), "ok": ok})

    low_genes = (coverage or {}).get("low_genes", []) if coverage else []
    have_cov = bool(coverage and coverage.get("summary"))
    have_hs = bool(m)
    # driver genes with a healthy median but at least one exon below the exon threshold:
    # the gene is not "low", yet that exon is not reportable
    low_set = set(g["gene"] for g in low_genes)
    driver_exon_low = [g for g in (coverage or {}).get("genes", []) if coverage
                       and g.get("driver_role") and g["n_low"] > 0 and g["gene"] not in low_set]

    limitations = []
    if low_genes:
        names = ", ".join("%s (%.0fx)" % (g["gene"], g["median_cov"]) for g in low_genes[:12])
        more = " and %d more" % (len(low_genes) - 12) if len(low_genes) > 12 else ""
        limitations.append("%d gene(s) with median exon coverage below %dx: %s%s"
                           % (len(low_genes), QC_THRESHOLDS["gene_low_median"], names, more))
    if driver_exon_low:
        names = ", ".join("%s (%s %.0fx)" % (g["gene"], g["min_exon"], g["min_cov"]) for g in driver_exon_low[:12])
        more = " and %d more" % (len(driver_exon_low) - 12) if len(driver_exon_low) > 12 else ""
        limitations.append("%d driver gene(s) with individual exons below %dx (gene median acceptable): %s%s"
                           % (len(driver_exon_low), QC_THRESHOLDS["exon_low"], names, more))

    if not have_cov and not have_hs:
        status, label, pill, reasons = "PENDING", "QC not available", "qc-pill-pending", ["no coverage or HsMetrics file"]
    elif review:
        status, label, pill, reasons = "REVIEW", "QC: REVIEW", "qc-pill-fail", review + limitations
    elif limitations:
        status, label, pill, reasons = "PASS_WITH_LIMITATIONS", "QC: PASS WITH LIMITATIONS", "qc-pill-review", limitations
    else:
        status, label, pill, reasons = "PASS", "QC: PASS", "qc-pill-pass", []
        if not have_hs:
            reasons.append("HsMetrics not available; run-level checks not applied")
        if not have_cov:
            reasons.append("per-exon coverage not available; gene-level checks not applied")
    return {"status": status, "label": label, "pill": pill, "reasons": reasons, "run_metrics": run_rows}
'''

# ---------------------------------------------------------------------------
# build.py
# ---------------------------------------------------------------------------
BUILD_INIT_OLD = '        "coverage": None,\n'
BUILD_INIT_NEW = '        "coverage": None,\n        "qc_verdict": None,   # DASH_QC_V1\n'

BUILD_PARSE_OLD = '        ctx["coverage"] = p_coverage.parse(cov_path)\n'
BUILD_PARSE_NEW = (
    '        ctx["coverage"] = p_coverage.parse(\n'
    '            cov_path,\n'
    '            consensus_genes=effective_dir / "cnv" / "consensus" / f"{sample}.cnv_consensus4.genes.tsv")   # DASH_QC_V1\n'
)

BUILD_WARN_ANCHOR = 'logging.warning("[%s] coverage parse failed: %s", sample, exc)'
BUILD_WARN_NEW = (
    '    try:   # DASH_QC_V1: sample-level verdict from run metrics + gene-level coverage\n'
    '        ctx["qc_verdict"] = p_coverage.verdict(ctx.get("coverage"), ctx.get("hsmetrics"))\n'
    '    except Exception as exc:\n'
    '        logging.warning("[%s] qc verdict failed: %s", sample, exc)\n'
)

# ---------------------------------------------------------------------------
# template
# ---------------------------------------------------------------------------
TPL_PILL_OLD = '          <span class="badge fs-6 qc-pill-pending">QC Review Pending</span>\n'
TPL_PILL_NEW = (
    '          {# DASH_QC_V1: verdict pill #}\n'
    '          {% if ctx.qc_verdict %}\n'
    '            <span class="badge fs-6 {{ ctx.qc_verdict.pill }}">{{ ctx.qc_verdict.label }}</span>\n'
    '          {% else %}\n'
    '            <span class="badge fs-6 qc-pill-pending">QC not available</span>\n'
    '          {% endif %}\n'
)

TPL_CARD_MEAN_OLD = (
    '              <div class="label">Mean Coverage</div>\n'
    '              {% if ctx.coverage and ctx.coverage.summary %}\n'
    '                <div class="value">{{ ctx.coverage.summary.mean_of_per_exon_means | format_num(0) }}x</div>\n'
    '                <div class="subvalue">mean of {{ ctx.coverage.summary.n_exons }} per-exon means &middot; duplicates included</div>\n'
)
TPL_CARD_MEAN_NEW = (
    '              <div class="label">Median Coverage</div>\n'
    '              {% if ctx.coverage and ctx.coverage.summary %}\n'
    '                <div class="value">{{ ctx.coverage.summary.median_of_per_exon | format_num(0) }}x</div>\n'
    '                <div class="subvalue">median of {{ ctx.coverage.summary.n_exons }} per-exon coverages &middot; duplicates included</div>\n'
)

TPL_CARD_LOW_OLD = (
    '              <div class="label">Low-Coverage Exons</div>\n'
    '              {% if ctx.coverage and ctx.coverage.summary %}\n'
    '                <div class="value">{{ ctx.coverage.summary.n_low_lt_100 }}</div>\n'
    '                <div class="subvalue">below 100x &middot; {{ ctx.coverage.summary.n_low_lt_250 }} below 250x</div>\n'
)
TPL_CARD_LOW_NEW = (
    '              <div class="label">Low-Coverage Genes</div>\n'
    '              {% if ctx.coverage and ctx.coverage.summary %}\n'
    '                <div class="value">{{ ctx.coverage.summary.n_low_genes }}</div>\n'
    '                <div class="subvalue">median exon coverage below {{ ctx.coverage.thresholds.gene_low_median }}x &middot; {{ ctx.coverage.summary.n_low_lt_100 }} exons below 100x</div>\n'
)

TPL_ALERT_OLD = (
    '        {% if ctx.coverage and ctx.coverage.summary and ctx.coverage.summary.low_lt_100_examples %}\n'
    '          <div class="alert alert-light border" role="alert">\n'
    '            <strong>Low-coverage exons (&lt;100x):</strong>\n'
    '            {% for r in ctx.coverage.summary.low_lt_100_examples %}\n'
    '              <span class="badge bg-light text-dark border me-1">{{ r.Gene }} {{ r.Exon }} &middot; {{ r.Mean_Coverage }}x</span>\n'
    '            {% endfor %}\n'
    '            {% if ctx.coverage.summary.n_low_lt_100 > ctx.coverage.summary.low_lt_100_examples | length %}\n'
    '              <span class="text-muted">+{{ ctx.coverage.summary.n_low_lt_100 - (ctx.coverage.summary.low_lt_100_examples | length) }} more</span>\n'
    '            {% endif %}\n'
    '          </div>\n'
    '        {% endif %}\n'
    '\n'
    '        <div class="alert alert-light border" role="alert">\n'
    '          <strong>Note:</strong> Plain-language QC alerts and verdict logic will be added in phase 2.\n'
    '          Phase 1 shows raw metrics only; all reporting is for technical review prior to clinical sign-off.\n'
    '        </div>\n'
)
TPL_ALERT_NEW = (
    '        {# DASH_QC_V1: verdict reasons and the complete low-coverage gene list #}\n'
    '        {% if ctx.qc_verdict and ctx.qc_verdict.reasons %}\n'
    '          <div class="alert alert-light border" role="alert">\n'
    '            <strong>{{ ctx.qc_verdict.label }}.</strong>\n'
    '            {% for r in ctx.qc_verdict.reasons %}<div>{{ r }}</div>{% endfor %}\n'
    '          </div>\n'
    '        {% endif %}\n'
    '        {% if ctx.coverage and ctx.coverage.low_genes %}\n'
    '          <div class="alert alert-light border" role="alert">\n'
    '            <strong>Low-coverage genes (median exon coverage &lt; {{ ctx.coverage.thresholds.gene_low_median }}x), lowest first:</strong>\n'
    '            {% for g in ctx.coverage.low_genes %}\n'
    '              <span class="badge bg-light text-dark border me-1">{{ g.gene }} &middot; {{ g.median_cov | format_num(0) }}x{% if g.driver_role %} &middot; {{ g.driver_role }}{% endif %}</span>\n'
    '            {% endfor %}\n'
    '            <div class="small text-muted mt-1">Full detail on the QC tab.</div>\n'
    '          </div>\n'
    '        {% endif %}\n'
)

TPL_QC_OLD = (
    '        {# Pipeline-side QC dashboard, embedded for context. #}\n'
    '        {% if ctx.files.existing_dashboard %}\n'
    '          <h4>Pipeline QC dashboard</h4>\n'
    '          <p class="text-muted small mb-2">\n'
    '            The pre-existing dashboard generated by the pipeline (panel-level hero metrics,\n'
    '            per-gene coverage chart, low-coverage exon list). Mean coverage shown here uses\n'
    '            mosdepth-style numbers with duplicates included.\n'
    '          </p>\n'
    '          <iframe class="tspipe-iframe-full" data-src="./{{ ctx.files.existing_dashboard }}" loading="lazy"></iframe>\n'
    '        {% endif %}\n'
    '\n'
    '        <h4 class="mt-4">HsMetrics (Picard)</h4>\n'
    '        <p class="text-muted small mb-2">\n'
    '          Picard CollectHsMetrics uses MAPQ&ge;20, baseQ&ge;20, overlap-clipping and\n'
    '          duplicate exclusion. These numbers are typically lower than the mosdepth-style\n'
    '          mean coverage shown in the pipeline dashboard above.\n'
    '        </p>\n'
    '        {% if ctx.hsmetrics %}\n'
    '          <div class="row g-3 mb-4">\n'
    '            <div class="col-md-6">\n'
    '              <table class="table table-sm tspipe-kv-table">\n'
    '                <tbody>\n'
    "                  {% for k in ['MEAN_TARGET_COVERAGE','MEDIAN_TARGET_COVERAGE','MAX_TARGET_COVERAGE','MIN_TARGET_COVERAGE','ZERO_CVG_TARGETS_PCT','FOLD_80_BASE_PENALTY','HET_SNP_SENSITIVITY','HET_SNP_Q'] %}\n"
    '                    {% if m[k] is defined and m[k] is not none %}\n'
    '                      <tr><td class="label">{{ k }}</td><td class="value">{{ m[k] | format_num(3) }}</td></tr>\n'
    '                    {% endif %}\n'
    '                  {% endfor %}\n'
    '                </tbody>\n'
    '              </table>\n'
    '            </div>\n'
    '            <div class="col-md-6">\n'
    '              <table class="table table-sm tspipe-kv-table">\n'
    '                <tbody>\n'
    "                  {% for k in ['PCT_TARGET_BASES_1X','PCT_TARGET_BASES_10X','PCT_TARGET_BASES_30X','PCT_TARGET_BASES_100X','PCT_TARGET_BASES_250X','PCT_TARGET_BASES_500X','PCT_TARGET_BASES_1000X','PCT_EXC_DUPE','PCT_EXC_OFF_TARGET','AT_DROPOUT','GC_DROPOUT','FOLD_ENRICHMENT'] %}\n"
    '                    {% if m[k] is defined and m[k] is not none %}\n'
    '                      <tr><td class="label">{{ k }}</td><td class="value">{{ m[k] | format_num(3) }}</td></tr>\n'
    '                    {% endif %}\n'
    '                  {% endfor %}\n'
    '                </tbody>\n'
    '              </table>\n'
    '            </div>\n'
    '          </div>\n'
    '        {% else %}\n'
    '          <div class="tspipe-empty">HsMetrics file not available for this sample.</div>\n'
    '        {% endif %}\n'
    '\n'
    '        <h4 class="mt-4">fastp QC report</h4>\n'
    '        {% if ctx.files.fastp %}\n'
    '          <iframe class="tspipe-iframe-full" data-src="./{{ ctx.files.fastp }}" loading="lazy"></iframe>\n'
    '        {% else %}\n'
    '          <div class="tspipe-empty">fastp report not available.</div>\n'
    '        {% endif %}\n'
    '\n'
    '        <h4 class="mt-4">Per-exon coverage</h4>\n'
    '        {% if ctx.coverage and ctx.coverage.rows %}\n'
    "          {{ macros.render_datatable('coverage-table', ctx.coverage.columns, ctx.coverage.rows) }}\n"
    '        {% else %}\n'
    '          <div class="tspipe-empty">Per-exon coverage file not available.</div>\n'
    '        {% endif %}\n'
)

TPL_QC_NEW = (
    '        {# DASH_QC_V1: QC tab -- verdict | low-coverage genes | run metrics | per-gene chart | all genes | fastp | per-exon #}\n'
    '        <h4>Verdict</h4>\n'
    '        {% if ctx.qc_verdict %}\n'
    '          <p class="mb-1"><span class="badge fs-6 {{ ctx.qc_verdict.pill }}">{{ ctx.qc_verdict.label }}</span></p>\n'
    '          {% if ctx.qc_verdict.reasons %}\n'
    '            <ul class="small mb-2">{% for r in ctx.qc_verdict.reasons %}<li>{{ r }}</li>{% endfor %}</ul>\n'
    '          {% else %}\n'
    '            <p class="small text-muted mb-2">All run-level metrics within limits; every gene at or above {{ ctx.coverage.thresholds.gene_low_median if ctx.coverage else 100 }}x median exon coverage.</p>\n'
    '          {% endif %}\n'
    '          <p class="small text-muted mb-3">REVIEW: a run-level metric is outside its limit. PASS WITH LIMITATIONS: run-level metrics acceptable but one or more genes fall below the gene threshold; negative results in those genes are not reportable without review. PASS: no limitation.</p>\n'
    '        {% else %}\n'
    '          <div class="tspipe-empty">Verdict not available (coverage or HsMetrics missing).</div>\n'
    '        {% endif %}\n'
    '\n'
    '        <h4 class="mt-4">Low-coverage genes</h4>\n'
    '        {% if ctx.coverage and ctx.coverage.low_genes %}\n'
    '          <p class="text-muted small mb-2">Every gene whose median exon coverage is below {{ ctx.coverage.thresholds.gene_low_median }}x, lowest first. Coverage is mosdepth per-exon mean with duplicates included; the gene value is the median across its exons.</p>\n'
    '          <div class="table-responsive">\n'
    '            <table id="qc-low-genes-table" class="table table-sm table-striped table-hover w-100">\n'
    '              <thead><tr><th>gene</th><th>driver role</th><th>median exon cov</th><th>worst exon</th><th>worst exon cov</th><th>exons &lt; {{ ctx.coverage.thresholds.exon_low }}x</th><th>n exons</th></tr></thead>\n'
    '              <tbody>\n'
    '                {% for g in ctx.coverage.low_genes %}\n'
    '                  <tr><td>{{ g.gene }}</td><td>{{ g.driver_role }}</td><td>{{ g.median_cov | format_num(0) }}</td><td>{{ g.min_exon }}</td><td>{{ g.min_cov | format_num(0) }}</td><td>{{ g.n_low }} ({{ (g.frac_low * 100) | format_num(0) }}%)</td><td>{{ g.n_exons }}</td></tr>\n'
    '                {% endfor %}\n'
    '              </tbody>\n'
    '            </table>\n'
    '          </div>\n'
    '        {% elif ctx.coverage and ctx.coverage.summary %}\n'
    '          <p class="text-muted small">No gene below {{ ctx.coverage.thresholds.gene_low_median }}x median exon coverage.</p>\n'
    '        {% else %}\n'
    '          <div class="tspipe-empty">Per-exon coverage file not available.</div>\n'
    '        {% endif %}\n'
    '\n'
    '        <h4 class="mt-4">Run metrics (Picard CollectHsMetrics)</h4>\n'
    '        <p class="text-muted small mb-2">MAPQ &ge; 20, baseQ &ge; 20, overlap-clipped, duplicates excluded; these are lower than the duplicate-inclusive mosdepth coverages above. A limit is shown only for metrics that feed the verdict.</p>\n'
    '        {% if ctx.qc_verdict and ctx.qc_verdict.run_metrics %}\n'
    '          <table class="table table-sm tspipe-kv-table" style="max-width: 760px;">\n'
    '            <thead><tr><th>metric</th><th>value</th><th>limit</th><th></th></tr></thead>\n'
    '            <tbody>\n'
    '              {% for r in ctx.qc_verdict.run_metrics %}\n'
    '                <tr><td class="label">{{ r.label }}</td><td class="value">{{ r.display }}</td><td class="value">{{ r.range }}</td>\n'
    '                    <td>{% if r.ok is true %}<span class="badge qc-pill-pass">ok</span>{% elif r.ok is false %}<span class="badge qc-pill-fail">out of limit</span>{% endif %}</td></tr>\n'
    '              {% endfor %}\n'
    '            </tbody>\n'
    '          </table>\n'
    '        {% else %}\n'
    '          <div class="tspipe-empty">HsMetrics file not available for this sample.</div>\n'
    '        {% endif %}\n'
    '\n'
    '        <h4 class="mt-4">Per-gene median coverage</h4>\n'
    '        {% if ctx.coverage and ctx.coverage.genes %}\n'
    '          <p class="text-muted small mb-2">Median exon coverage per gene, lowest first; dashed line at {{ ctx.coverage.thresholds.gene_low_median }}x; red bars are below it. Log scale.</p>\n'
    '          <div style="position: relative; height: 320px;"><canvas id="qc-gene-chart"></canvas></div>\n'
    '          <script>window.QC_GENES = {{ ctx.coverage.genes | tojson }}; window.QC_GENE_LOW = {{ ctx.coverage.thresholds.gene_low_median }};</script>\n'
    '\n'
    '          <h4 class="mt-4">All genes</h4>\n'
    '          <div class="table-responsive">\n'
    '            <table id="qc-gene-table" class="table table-sm table-striped table-hover w-100">\n'
    '              <thead><tr><th>gene</th><th>driver role</th><th>median exon cov</th><th>worst exon</th><th>worst exon cov</th><th>exons &lt; {{ ctx.coverage.thresholds.exon_low }}x</th><th>n exons</th></tr></thead>\n'
    '              <tbody>\n'
    '                {% for g in ctx.coverage.genes %}\n'
    '                  <tr><td>{{ g.gene }}</td><td>{{ g.driver_role }}</td><td>{{ g.median_cov | format_num(0) }}</td><td>{{ g.min_exon }}</td><td>{{ g.min_cov | format_num(0) }}</td><td>{{ g.n_low }}</td><td>{{ g.n_exons }}</td></tr>\n'
    '                {% endfor %}\n'
    '              </tbody>\n'
    '            </table>\n'
    '          </div>\n'
    '        {% endif %}\n'
    '\n'
    '        <h4 class="mt-4">fastp QC report</h4>\n'
    '        {% if ctx.files.fastp %}\n'
    '          <iframe class="tspipe-iframe-full" data-src="./{{ ctx.files.fastp }}" loading="lazy"></iframe>\n'
    '        {% else %}\n'
    '          <div class="tspipe-empty">fastp report not available.</div>\n'
    '        {% endif %}\n'
    '\n'
    '        <details class="mt-4">\n'
    '          <summary><h4 class="d-inline">Per-exon coverage</h4> <span class="text-muted small">(all exons; expand)</span></summary>\n'
    '          {% if ctx.coverage and ctx.coverage.rows %}\n'
    "            {{ macros.render_datatable('coverage-table', ctx.coverage.columns, ctx.coverage.rows) }}\n"
    '          {% else %}\n'
    '            <div class="tspipe-empty">Per-exon coverage file not available.</div>\n'
    '          {% endif %}\n'
    '        </details>\n'
    '        {% if ctx.files.existing_dashboard %}\n'
    '          <p class="small text-muted mt-3">Legacy pipeline QC dashboard: <a href="./{{ ctx.files.existing_dashboard }}" target="_blank">{{ ctx.files.existing_dashboard }}</a></p>\n'
    '        {% endif %}\n'
)

TPL_JS_OLD = "    if ($('#coverage-table').length)     { $('#coverage-table').DataTable({ pageLength: 25, order: [] }); }\n"
TPL_JS_NEW = TPL_JS_OLD + (
    "    // DASH_QC_V1: gene tables + per-gene median chart\n"
    "    if ($('#qc-low-genes-table').length) { $('#qc-low-genes-table').DataTable({ pageLength: 25, order: [[2, 'asc']] }); }\n"
    "    if ($('#qc-gene-table').length)      { $('#qc-gene-table').DataTable({ pageLength: 25, order: [[2, 'asc']] }); }\n"
    "    const qcCanvas = document.getElementById('qc-gene-chart');\n"
    "    if (qcCanvas && window.Chart && window.QC_GENES) {\n"
    "      const qg = window.QC_GENES, qlow = window.QC_GENE_LOW;\n"
    "      new Chart(qcCanvas, {\n"
    "        type: 'bar',\n"
    "        data: { labels: qg.map(function (r) { return r.gene; }),\n"
    "                datasets: [{ label: 'median exon coverage', data: qg.map(function (r) { return Math.max(r.median_cov, 1); }),\n"
    "                             backgroundColor: qg.map(function (r) { return r.median_cov < qlow ? '#dc3545' : '#6c757d'; }) }] },\n"
    "        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } },\n"
    "                   scales: { x: { ticks: { autoSkip: false, maxRotation: 90, minRotation: 90, font: { size: 8 } } },\n"
    "                             y: { type: 'logarithmic', title: { display: true, text: 'median exon coverage (x)' } } } },\n"
    "        plugins: [{ id: 'qcThresholdLine', afterDraw: function (chart) {\n"
    "          const y = chart.scales.y.getPixelForValue(qlow); const c = chart.ctx;\n"
    "          c.save(); c.strokeStyle = '#dc3545'; c.setLineDash([4, 3]); c.beginPath();\n"
    "          c.moveTo(chart.chartArea.left, y); c.lineTo(chart.chartArea.right, y); c.stroke(); c.restore(); } }]\n"
    "      });\n"
    "    }\n"
)

EDITS = [
    (BUILD, BUILD_INIT_OLD, BUILD_INIT_NEW, "replace"),
    (BUILD, BUILD_PARSE_OLD, BUILD_PARSE_NEW, "replace"),
    (BUILD, BUILD_WARN_ANCHOR, BUILD_WARN_NEW, "insert_after_line"),
    (TPL, TPL_PILL_OLD, TPL_PILL_NEW, "replace"),
    (TPL, TPL_CARD_MEAN_OLD, TPL_CARD_MEAN_NEW, "replace"),
    (TPL, TPL_CARD_LOW_OLD, TPL_CARD_LOW_NEW, "replace"),
    (TPL, TPL_ALERT_OLD, TPL_ALERT_NEW, "replace"),
    (TPL, TPL_QC_OLD, TPL_QC_NEW, "replace"),
    (TPL, TPL_JS_OLD, TPL_JS_NEW, "replace"),
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
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    args = ap.parse_args()

    stamp = time.strftime("%Y%m%d_%H%M%S")
    staged, skipped, errors = {}, [], []

    # coverage.py: whole-file replacement, guarded by the marker
    cov = REPO / COV
    if not cov.exists():
        errors.append("%s: file not found" % COV)
    elif MARKER in cov.read_text():
        print("SKIP  %s: %s already present" % (COV, MARKER)); skipped.append(COV)
    else:
        staged[COV] = COVERAGE_PY

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
        orig = (REPO / rel).read_text()
        print("PLAN  %s: %+d lines, marker %s" % (rel, text.count("\n") - orig.count("\n"), MARKER))
    if not args.apply:
        print("dry run; re-run with --apply"); return
    for rel, text in staged.items():
        p = REPO / rel
        bak = p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp))
        bak.write_text(p.read_text()); p.write_text(text)
        print("WROTE %s (backup %s)" % (rel, bak.name))
    print("done")


if __name__ == "__main__":
    main()
