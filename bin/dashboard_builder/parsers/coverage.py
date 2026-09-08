"""Parse per-exon coverage TSV and derive gene-level and sample-level QC.

MARKER DASH_QC_V1 (D7 QC page overhaul, D8 median instead of mean).
MARKER DASH_QC_V1b: low genes explained by a consensus LOSS are CNV findings, not limitations.

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


CNV_LOW_EXPLAINS = ("LOSS",)   # DASH_QC_V1b: consensus calls that explain low coverage biologically


def _consensus_info(consensus_genes):
    """gene -> {role, call, tier} from <sample>.cnv_consensus4.genes.tsv (CMX_ANNOT_V1); {} when absent."""
    if not consensus_genes:
        return {}
    p = Path(consensus_genes)
    if not p.exists():
        return {}
    try:
        df = pd.read_csv(p, sep="\t", dtype=str, keep_default_na=False)
    except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError):
        return {}
    if "gene" not in df.columns:
        return {}
    out = {}
    for _, r in df.iterrows():
        role = (r.get("driver_role", "") or "").strip()
        call = (r.get("consensus_call", "") or "").strip()
        tier = (r.get("tier", "") or "").strip()
        out[r["gene"]] = {"role": "" if role == "NA" else role,
                          "call": "" if call in ("NA", "NEUTRAL") else call,
                          "tier": "" if tier == "NA" else tier}
    return out


def _driver_roles(consensus_genes):
    """Kept for compatibility: gene -> driver_role."""
    return dict((g, v["role"]) for g, v in _consensus_info(consensus_genes).items() if v["role"])


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
    cinfo = _consensus_info(consensus_genes)   # DASH_QC_V1b

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
                "driver_role": cinfo.get(gene, {}).get("role", ""),
                "cnv_call": cinfo.get(gene, {}).get("call", ""),   # DASH_QC_V1b
                "cnv_tier": cinfo.get(gene, {}).get("tier", ""),
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
    # DASH_QC_V1b: a low gene with a consensus LOSS is a CNV finding, not a limitation
    explained = [g for g in low_genes if g.get("cnv_call") in CNV_LOW_EXPLAINS]
    low_tech = [g for g in low_genes if g.get("cnv_call") not in CNV_LOW_EXPLAINS]
    driver_exon_low = [g for g in (coverage or {}).get("genes", []) if coverage
                       and g.get("driver_role") and g["n_low"] > 0 and g["gene"] not in low_set
                       and g.get("cnv_call") not in CNV_LOW_EXPLAINS]

    limitations, findings = [], []
    if low_tech:
        names = ", ".join("%s (%.0fx)" % (g["gene"], g["median_cov"]) for g in low_tech[:12])
        more = " and %d more" % (len(low_tech) - 12) if len(low_tech) > 12 else ""
        limitations.append("%d gene(s) with median exon coverage below %dx: %s%s"
                           % (len(low_tech), QC_THRESHOLDS["gene_low_median"], names, more))
    if explained:
        names = ", ".join("%s (%.0fx; consensus %s %s)" % (g["gene"], g["median_cov"], g["cnv_call"], g["cnv_tier"])
                          for g in explained[:12])
        findings.append("%d low-coverage gene(s) explained by a copy-number loss, not a library limitation: %s"
                        % (len(explained), names))
    if driver_exon_low:
        names = ", ".join("%s (%s %.0fx)" % (g["gene"], g["min_exon"], g["min_cov"]) for g in driver_exon_low[:12])
        more = " and %d more" % (len(driver_exon_low) - 12) if len(driver_exon_low) > 12 else ""
        limitations.append("%d driver gene(s) with individual exons below %dx (gene median acceptable): %s%s"
                           % (len(driver_exon_low), QC_THRESHOLDS["exon_low"], names, more))

    if not have_cov and not have_hs:
        status, label, pill, reasons = "PENDING", "QC not available", "qc-pill-pending", ["no coverage or HsMetrics file"]
    elif review:
        status, label, pill, reasons = "REVIEW", "QC: REVIEW", "qc-pill-fail", review + limitations + findings
    elif limitations:
        status, label, pill, reasons = "PASS_WITH_LIMITATIONS", "QC: PASS WITH LIMITATIONS", "qc-pill-review", limitations + findings
    else:
        status, label, pill, reasons = "PASS", "QC: PASS", "qc-pill-pass", list(findings)
        if not have_hs:
            reasons.append("HsMetrics not available; run-level checks not applied")
        if not have_cov:
            reasons.append("per-exon coverage not available; gene-level checks not applied")
    return {"status": status, "label": label, "pill": pill, "reasons": reasons, "run_metrics": run_rows}
