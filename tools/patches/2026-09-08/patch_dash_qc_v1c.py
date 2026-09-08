#!/usr/bin/env python3
"""tools/patches/<date>/patch_dash_qc_v1c.py -- MARKER DASH_QC_V1c

Threshold correction after the first render (all eight run8 samples REVIEW):
Picard CollectHsMetrics caps per-base coverage at COVERAGE_CAP=200 by default, so
MEDIAN_TARGET_COVERAGE reads 200 on every deep sample and cannot be a limit.
Until the HSMETRICS module passes a higher cap (register N11), the verdict uses:
  PCT_TARGET_BASES_100X >= 0.95, PCT_TARGET_BASES_250X >= 0.90, PCT_EXC_DUPE <= 0.50,
  and a floor on the reported number: mosdepth median of per-exon coverage >= 500x.
The Picard median row stays in the run-metrics table, labelled as capped.

Usage:  python3 <this file> [--apply]
Guard:  MARKER DASH_QC_V1c; each anchor exactly once; all-or-nothing.
"""

import argparse
import sys
import time
from pathlib import Path

MARKER = "DASH_QC_V1c"
TAG = "dash_qc_v1c"
REPO = Path(__file__).resolve().parents[3]
COV = "bin/dashboard_builder/parsers/coverage.py"

THR_OLD = '''QC_THRESHOLDS = {
    "gene_low_median": 100,        # gene is low when the median of its exon coverages is below this
    "exon_low": 100,               # exon is low below this (matches parse_exon_coverage.py)
    "review_median_target": 250,   # Picard MEDIAN_TARGET_COVERAGE below this -> REVIEW
    "review_pct_100x": 0.95,       # Picard PCT_TARGET_BASES_100X below this -> REVIEW
    "review_pct_dupe": 0.50,       # Picard PCT_EXC_DUPE above this -> REVIEW
}
'''
THR_NEW = '''QC_THRESHOLDS = {   # DASH_QC_V1c: Picard median dropped (capped at COVERAGE_CAP=200 until N11)
    "gene_low_median": 100,        # gene is low when the median of its exon coverages is below this
    "exon_low": 100,               # exon is low below this (matches parse_exon_coverage.py)
    "review_median_mosdepth": 500, # mosdepth median of per-exon coverage (dup-inclusive, the reported number) below this -> REVIEW
    "review_pct_100x": 0.95,       # Picard PCT_TARGET_BASES_100X below this -> REVIEW
    "review_pct_250x": 0.90,       # Picard PCT_TARGET_BASES_250X below this -> REVIEW
    "review_pct_dupe": 0.50,       # Picard PCT_EXC_DUPE above this -> REVIEW
}
'''

RM_OLD = '''    ("MEDIAN_TARGET_COVERAGE", "Median target coverage (Picard, dup-filtered)", "review_median_target", "min", "x"),
    ("FOLD_80_BASE_PENALTY", "Fold-80 base penalty (uniformity)", None, None, "f2"),
    ("PCT_TARGET_BASES_100X", "Target bases at >= 100x", "review_pct_100x", "min", "pct"),
    ("PCT_TARGET_BASES_250X", "Target bases at >= 250x", None, None, "pct"),
'''
RM_NEW = '''    ("MEDIAN_TARGET_COVERAGE", "Median target coverage (Picard; capped at 200 by COVERAGE_CAP)", None, None, "x"),
    ("FOLD_80_BASE_PENALTY", "Fold-80 base penalty (uniformity)", None, None, "f2"),
    ("PCT_TARGET_BASES_100X", "Target bases at >= 100x", "review_pct_100x", "min", "pct"),
    ("PCT_TARGET_BASES_250X", "Target bases at >= 250x", "review_pct_250x", "min", "pct"),
'''

# coverage floor on the mosdepth median: inserted at the top of verdict's run-metrics loop output
FLOOR_OLD = '''    low_genes = (coverage or {}).get("low_genes", []) if coverage else []
    have_cov = bool(coverage and coverage.get("summary"))
    have_hs = bool(m)
'''
FLOOR_NEW = '''    low_genes = (coverage or {}).get("low_genes", []) if coverage else []
    have_cov = bool(coverage and coverage.get("summary"))
    have_hs = bool(m)
    # DASH_QC_V1c: floor on the reported coverage (mosdepth median of per-exon coverage, duplicates included)
    if have_cov:
        med = float(coverage["summary"]["median_of_per_exon"])
        floor = QC_THRESHOLDS["review_median_mosdepth"]
        ok = med >= floor
        if not ok:
            review.append("Median per-exon coverage (mosdepth, dup-inclusive) %s (limit >= %s)" % (_fmt(med, "x"), _fmt(floor, "x")))
        run_rows.insert(0, {"key": "MOSDEPTH_MEDIAN_EXON", "label": "Median per-exon coverage (mosdepth, dup-inclusive)",
                            "value": med, "display": _fmt(med, "x"), "range": ">= " + _fmt(floor, "x"), "ok": ok})
'''

EDITS = [(COV, THR_OLD, THR_NEW), (COV, RM_OLD, RM_NEW), (COV, FLOOR_OLD, FLOOR_NEW)]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    p = REPO / COV
    text = p.read_text()
    if MARKER in text:
        print("SKIP  %s: %s already present" % (COV, MARKER)); return
    new = text
    for rel, old, rep in EDITS:
        n = new.count(old)
        if n != 1:
            print("ABORT -- nothing written: anchor matched %d times (need 1): %r" % (n, old[:70])); sys.exit(1)
        new = new.replace(old, rep, 1)
    print("PLAN  %s: %+d lines, marker %s" % (COV, new.count("\\n") - text.count("\\n"), MARKER))
    if not args.apply:
        print("dry run; re-run with --apply"); return
    bak = p.with_name(p.name + ".bak_%s_%s" % (TAG, time.strftime("%Y%m%d_%H%M%S")))
    bak.write_text(text); p.write_text(new)
    print("WROTE %s (backup %s)\\ndone" % (COV, bak.name))


if __name__ == "__main__":
    main()
