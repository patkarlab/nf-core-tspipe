"""Parse fastp JSON (MARKER DASH_QC_V2).

Returns a flat dict of read-level metrics or None when the file is absent or
unreadable. Limits live in FASTP_THRESHOLDS and are applied by
coverage.verdict(); this module only extracts.
"""

import json
from pathlib import Path

FASTP_THRESHOLDS = {
    "q30_min": 0.85,        # Q30 fraction after filtering below this -> REVIEW
    "insert_peak_min": 150, # insert-size peak (bp) below this -> REVIEW
}


def parse(path):
    p = Path(path)
    if not p.exists():
        return None
    try:
        with open(p) as fh:
            d = json.load(fh)
    except (OSError, ValueError):
        return None
    s = d.get("summary", {}) or {}
    b = s.get("before_filtering", {}) or {}
    a = s.get("after_filtering", {}) or {}
    fr = d.get("filtering_result", {}) or {}
    ad = d.get("adapter_cutting", {}) or {}
    tot_b, tot_a = b.get("total_reads"), a.get("total_reads")
    trimmed = ad.get("adapter_trimmed_reads")
    return {
        "reads_before": tot_b,
        "reads_after": tot_a,
        "pct_passed": (tot_a / float(tot_b)) if (tot_a is not None and tot_b) else None,
        "q30_before": b.get("q30_rate"),
        "q30_after": a.get("q30_rate"),
        "mean_len_r1_after": a.get("read1_mean_length"),
        "mean_len_r2_after": a.get("read2_mean_length"),
        "adapter_trimmed_frac": (trimmed / float(tot_b)) if (trimmed is not None and tot_b) else None,
        "dup_rate": (d.get("duplication") or {}).get("rate"),
        "insert_peak": (d.get("insert_size") or {}).get("peak"),
        "low_quality_reads": fr.get("low_quality_reads"),
        "too_short_reads": fr.get("too_short_reads"),
        "thresholds": dict(FASTP_THRESHOLDS),
    }
