#!/usr/bin/env python3
"""tools/patches/<date>/patch_dash_qc_v1b.py -- MARKER DASH_QC_V1b

Follow-up to DASH_QC_V1. A gene with low median exon coverage because it is
deleted in the tumour (26CGH1043 CDKN2A, consensus LOSS) is a finding, not a
library limitation. The parser now reads consensus_call and tier next to
driver_role from <sample>.cnv_consensus4.genes.tsv; each gene row carries
cnv_call and cnv_tier; low genes whose cnv_call is LOSS are listed with the
call but excluded from the limitation count, and the verdict names them in a
separate line. The same exclusion applies to driver genes with individual low
exons. Template: CNV column in the low-genes and all-genes tables; the
overview badge shows the call.

bin/ is not hashed: re-render with `-c /tmp/dash_nocache.config`.

Usage:  python3 <this file> [--apply]
Guard:  MARKER DASH_QC_V1b per file; each anchor exactly once; all-or-nothing.
"""

import argparse
import sys
import time
from pathlib import Path

MARKER = "DASH_QC_V1b"
TAG = "dash_qc_v1b"
REPO = Path(__file__).resolve().parents[3]
COV = "bin/dashboard_builder/parsers/coverage.py"
TPL = "bin/dashboard_builder/templates/sample_report.html.j2"

# ---- coverage.py ----------------------------------------------------------
C_DOC_OLD = "MARKER DASH_QC_V1 (D7 QC page overhaul, D8 median instead of mean).\n"
C_DOC_NEW = (
    "MARKER DASH_QC_V1 (D7 QC page overhaul, D8 median instead of mean).\n"
    "MARKER DASH_QC_V1b: low genes explained by a consensus LOSS are CNV findings, not limitations.\n"
)

C_ROLES_OLD = '''def _driver_roles(consensus_genes):
    """gene -> driver_role from <sample>.cnv_consensus4.genes.tsv (CMX_ANNOT_V1); {} when absent."""
    if not consensus_genes:
        return {}
    p = Path(consensus_genes)
    if not p.exists():
        return {}
    try:
        df = pd.read_csv(p, sep="\\t", dtype=str, keep_default_na=False)
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
'''
C_ROLES_NEW = '''CNV_LOW_EXPLAINS = ("LOSS",)   # DASH_QC_V1b: consensus calls that explain low coverage biologically


def _consensus_info(consensus_genes):
    """gene -> {role, call, tier} from <sample>.cnv_consensus4.genes.tsv (CMX_ANNOT_V1); {} when absent."""
    if not consensus_genes:
        return {}
    p = Path(consensus_genes)
    if not p.exists():
        return {}
    try:
        df = pd.read_csv(p, sep="\\t", dtype=str, keep_default_na=False)
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
'''

C_LOAD_OLD = "    roles = _driver_roles(consensus_genes)\n"
C_LOAD_NEW = "    cinfo = _consensus_info(consensus_genes)   # DASH_QC_V1b\n"

C_ROW_OLD = '                "driver_role": roles.get(gene, ""),\n            })\n'
C_ROW_NEW = (
    '                "driver_role": cinfo.get(gene, {}).get("role", ""),\n'
    '                "cnv_call": cinfo.get(gene, {}).get("call", ""),   # DASH_QC_V1b\n'
    '                "cnv_tier": cinfo.get(gene, {}).get("tier", ""),\n'
    '            })\n'
)

C_VERD_OLD = '''    low_set = set(g["gene"] for g in low_genes)
    driver_exon_low = [g for g in (coverage or {}).get("genes", []) if coverage
                       and g.get("driver_role") and g["n_low"] > 0 and g["gene"] not in low_set]

    limitations = []
    if low_genes:
        names = ", ".join("%s (%.0fx)" % (g["gene"], g["median_cov"]) for g in low_genes[:12])
        more = " and %d more" % (len(low_genes) - 12) if len(low_genes) > 12 else ""
        limitations.append("%d gene(s) with median exon coverage below %dx: %s%s"
                           % (len(low_genes), QC_THRESHOLDS["gene_low_median"], names, more))
'''
C_VERD_NEW = '''    low_set = set(g["gene"] for g in low_genes)
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
'''

C_STATUS_OLD = '''    elif review:
        status, label, pill, reasons = "REVIEW", "QC: REVIEW", "qc-pill-fail", review + limitations
    elif limitations:
        status, label, pill, reasons = "PASS_WITH_LIMITATIONS", "QC: PASS WITH LIMITATIONS", "qc-pill-review", limitations
    else:
        status, label, pill, reasons = "PASS", "QC: PASS", "qc-pill-pass", []
'''
C_STATUS_NEW = '''    elif review:
        status, label, pill, reasons = "REVIEW", "QC: REVIEW", "qc-pill-fail", review + limitations + findings
    elif limitations:
        status, label, pill, reasons = "PASS_WITH_LIMITATIONS", "QC: PASS WITH LIMITATIONS", "qc-pill-review", limitations + findings
    else:
        status, label, pill, reasons = "PASS", "QC: PASS", "qc-pill-pass", list(findings)
'''

# ---- template -------------------------------------------------------------
T_BADGE_OLD = (
    "              <span class=\"badge bg-light text-dark border me-1\">{{ g.gene }} &middot; {{ g.median_cov | format_num(0) }}x"
    "{% if g.driver_role %} &middot; {{ g.driver_role }}{% endif %}</span>\n"
)
T_BADGE_NEW = (
    "              <span class=\"badge bg-light text-dark border me-1\">{{ g.gene }} &middot; {{ g.median_cov | format_num(0) }}x"
    "{% if g.driver_role %} &middot; {{ g.driver_role }}{% endif %}"
    "{% if g.cnv_call %} &middot; CNV {{ g.cnv_call }} {{ g.cnv_tier }}{% endif %}</span>   {# DASH_QC_V1b #}\n"
)

T_LOWHEAD_OLD = (
    "              <thead><tr><th>gene</th><th>driver role</th><th>median exon cov</th><th>worst exon</th><th>worst exon cov</th>"
    "<th>exons &lt; {{ ctx.coverage.thresholds.exon_low }}x</th><th>n exons</th></tr></thead>\n"
    "              <tbody>\n"
    "                {% for g in ctx.coverage.low_genes %}\n"
    "                  <tr><td>{{ g.gene }}</td><td>{{ g.driver_role }}</td><td>{{ g.median_cov | format_num(0) }}</td><td>{{ g.min_exon }}</td>"
    "<td>{{ g.min_cov | format_num(0) }}</td><td>{{ g.n_low }} ({{ (g.frac_low * 100) | format_num(0) }}%)</td><td>{{ g.n_exons }}</td></tr>\n"
)
T_LOWHEAD_NEW = (
    "              <thead><tr><th>gene</th><th>driver role</th><th>median exon cov</th><th>worst exon</th><th>worst exon cov</th>"
    "<th>exons &lt; {{ ctx.coverage.thresholds.exon_low }}x</th><th>n exons</th><th>CNV consensus</th></tr></thead>\n"
    "              <tbody>\n"
    "                {% for g in ctx.coverage.low_genes %}\n"
    "                  <tr><td>{{ g.gene }}</td><td>{{ g.driver_role }}</td><td>{{ g.median_cov | format_num(0) }}</td><td>{{ g.min_exon }}</td>"
    "<td>{{ g.min_cov | format_num(0) }}</td><td>{{ g.n_low }} ({{ (g.frac_low * 100) | format_num(0) }}%)</td><td>{{ g.n_exons }}</td>"
    "<td>{% if g.cnv_call %}{{ g.cnv_call }} {{ g.cnv_tier }}{% endif %}</td></tr>   {# DASH_QC_V1b #}\n"
)

T_ALLHEAD_OLD = (
    "              <thead><tr><th>gene</th><th>driver role</th><th>median exon cov</th><th>worst exon</th><th>worst exon cov</th>"
    "<th>exons &lt; {{ ctx.coverage.thresholds.exon_low }}x</th><th>n exons</th></tr></thead>\n"
    "              <tbody>\n"
    "                {% for g in ctx.coverage.genes %}\n"
    "                  <tr><td>{{ g.gene }}</td><td>{{ g.driver_role }}</td><td>{{ g.median_cov | format_num(0) }}</td><td>{{ g.min_exon }}</td>"
    "<td>{{ g.min_cov | format_num(0) }}</td><td>{{ g.n_low }}</td><td>{{ g.n_exons }}</td></tr>\n"
)
T_ALLHEAD_NEW = (
    "              <thead><tr><th>gene</th><th>driver role</th><th>median exon cov</th><th>worst exon</th><th>worst exon cov</th>"
    "<th>exons &lt; {{ ctx.coverage.thresholds.exon_low }}x</th><th>n exons</th><th>CNV consensus</th></tr></thead>\n"
    "              <tbody>\n"
    "                {% for g in ctx.coverage.genes %}\n"
    "                  <tr><td>{{ g.gene }}</td><td>{{ g.driver_role }}</td><td>{{ g.median_cov | format_num(0) }}</td><td>{{ g.min_exon }}</td>"
    "<td>{{ g.min_cov | format_num(0) }}</td><td>{{ g.n_low }}</td><td>{{ g.n_exons }}</td>"
    "<td>{% if g.cnv_call %}{{ g.cnv_call }} {{ g.cnv_tier }}{% endif %}</td></tr>\n"
)

T_LOWDESC_OLD = (
    "          <p class=\"text-muted small mb-2\">Every gene whose median exon coverage is below {{ ctx.coverage.thresholds.gene_low_median }}x, lowest first. "
    "Coverage is mosdepth per-exon mean with duplicates included; the gene value is the median across its exons.</p>\n"
)
T_LOWDESC_NEW = (
    "          <p class=\"text-muted small mb-2\">Every gene whose median exon coverage is below {{ ctx.coverage.thresholds.gene_low_median }}x, lowest first. "
    "Coverage is mosdepth per-exon mean with duplicates included; the gene value is the median across its exons. "
    "A gene with a consensus LOSS in the CNV tab is low because it is deleted, and is not counted as a limitation.</p>\n"
)

EDITS = [
    (COV, C_DOC_OLD, C_DOC_NEW), (COV, C_ROLES_OLD, C_ROLES_NEW), (COV, C_LOAD_OLD, C_LOAD_NEW),
    (COV, C_ROW_OLD, C_ROW_NEW), (COV, C_VERD_OLD, C_VERD_NEW), (COV, C_STATUS_OLD, C_STATUS_NEW),
    (TPL, T_BADGE_OLD, T_BADGE_NEW), (TPL, T_LOWHEAD_OLD, T_LOWHEAD_NEW),
    (TPL, T_ALLHEAD_OLD, T_ALLHEAD_NEW), (TPL, T_LOWDESC_OLD, T_LOWDESC_NEW),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    staged, errors, skipped = {}, [], []
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
