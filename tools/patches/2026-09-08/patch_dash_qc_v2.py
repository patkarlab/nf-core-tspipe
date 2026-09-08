#!/usr/bin/env python3
"""tools/patches/<date>/patch_dash_qc_v2.py -- MARKER DASH_QC_V2

Read-level QC and sample identity in the QC tab.

Pipeline
  subworkflows/local/preprocessing.nf  emit fastp_json (sex-resolved like fastp_html)
  workflows/tspipe.nf                  ORGANIZE join chain gains PREPROCESSING.out.fastp_json
  modules/local/organize_output.nf     input path(fastp_json) after fastp_html; --fastp-json; stub touch
  bin/organize_output.py               --fastp-json (optional) -> clinical/<S>_fastp.json
Dashboard
  parsers/fastp.py (new)               reads/Q30/length/adapter/dup/insert-peak from <S>_fastp.json
  build.py                             ctx["fastp"]; verdict computed AFTER cnv_v2 parse and given
                                       fastp + sex_check
  parsers/coverage.py verdict()        fastp limits (Q30 >= 0.85, insert peak >= 150 bp) -> REVIEW;
                                       sex: sheet vs chrX-heterozygosity mismatch -> REVIEW;
                                       SHEET_UNKNOWN and X_DEPTH_CONFLICT -> findings;
                                       returns read_metrics and identity for the template
  template                             "Sample identity (sex check)" block after the verdict;
                                       "Read-level QC (fastp)" table replaces the iframe, with the
                                       fastp HTML as one link under it

ORGANIZE_OUTPUT is a hashed module change: plain resume (ORGANIZE 8 + DASHBOARD + BUNDLE).
The report bundle's required-tree check is untouched (the JSON is optional there).

Usage:  python3 <this file> [--apply]
Guard:  MARKER DASH_QC_V2 per file; each anchor exactly once; all-or-nothing.
"""

import argparse
import sys
import time
from pathlib import Path

MARKER = "DASH_QC_V2"
TAG = "dash_qc_v2"
REPO = Path(__file__).resolve().parents[3]

PRE = "subworkflows/local/preprocessing.nf"
WF = "workflows/tspipe.nf"
ORG_NF = "modules/local/organize_output.nf"
ORG_PY = "bin/organize_output.py"
BUILD = "bin/dashboard_builder/build.py"
COV = "bin/dashboard_builder/parsers/coverage.py"
TPL = "bin/dashboard_builder/templates/sample_report.html.j2"
FASTP_PY = "bin/dashboard_builder/parsers/fastp.py"

# ---- pipeline -------------------------------------------------------------
PRE_EMIT_ANCHOR = "ch_sexed_fastp_html = withResolvedSex(FASTP.out.html, ch_sex_by_id)"
PRE_EMIT_NEW = "        ch_sexed_fastp_json = withResolvedSex(FASTP.out.json, ch_sex_by_id)   // DASH_QC_V2\n"
PRE_OUT_ANCHOR = "fastp_html    = ch_sexed_fastp_html"
PRE_OUT_NEW = "        fastp_json    = ch_sexed_fastp_json   // DASH_QC_V2\n"

WF_JOIN_ANCHOR = ".join(PREPROCESSING.out.fastp_html)"
WF_JOIN_NEW = "        .join(PREPROCESSING.out.fastp_json)                                  // + fastp_json (DASH_QC_V2)\n"

ORG_IN_OLD = "              path(fastp_html),\n"
ORG_IN_NEW = "              path(fastp_html),\n              path(fastp_json),   // MARKER DASH_QC_V2\n"
ORG_CMD_OLD = "            --fastp-html          ${fastp_html} \\\\\n"
ORG_CMD_NEW = ORG_CMD_OLD + "            --fastp-json          ${fastp_json} \\\\\n"
ORG_STUB_OLD = "        touch clinical/${meta.id}_fastp.html\n"
ORG_STUB_NEW = ORG_STUB_OLD + "        touch clinical/${meta.id}_fastp.json\n"

PY_ARG_OLD = '    parser.add_argument("--fastp-html", required=True)\n'
PY_ARG_NEW = PY_ARG_OLD + '    parser.add_argument("--fastp-json", default=None, help="fastp JSON metrics (optional; DASH_QC_V2)")\n'
PY_LINK_OLD = (
    '    hardlink(args.fastp_html,    out / (s + "_fastp.html"),\n'
    '             "Fastp trimming QC report")\n'
)
PY_LINK_NEW = PY_LINK_OLD + (
    '    if args.fastp_json:   # DASH_QC_V2\n'
    '        hardlink(args.fastp_json, out / (s + "_fastp.json"),\n'
    '                 "Fastp trimming QC metrics (JSON)")\n'
)

# ---- new parser -----------------------------------------------------------
FASTP_SRC = '''"""Parse fastp JSON (MARKER DASH_QC_V2).

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
'''

# ---- build.py -------------------------------------------------------------
B_IMPORT_OLD = "from parsers import cnv_v2 as p_cnv_v2   # MARKER DASH_CNV_V1\n"
B_IMPORT_NEW = B_IMPORT_OLD + "from parsers import fastp as p_fastp   # DASH_QC_V2\n"
B_INIT_OLD = '        "qc_verdict": None,   # DASH_QC_V1\n'
B_INIT_NEW = '        "qc_verdict": None,   # DASH_QC_V1\n        "fastp": None,   # DASH_QC_V2\n'
B_VERD_OLD = (
    '    try:   # DASH_QC_V1: sample-level verdict from run metrics + gene-level coverage\n'
    '        ctx["qc_verdict"] = p_coverage.verdict(ctx.get("coverage"), ctx.get("hsmetrics"))\n'
    '    except Exception as exc:\n'
    '        logging.warning("[%s] qc verdict failed: %s", sample, exc)\n'
)
B_VERD_NEW = (
    '    fastp_path = effective_dir / f"{sample}_fastp.json"   # DASH_QC_V2\n'
    '    try:\n'
    '        ctx["fastp"] = p_fastp.parse(fastp_path)\n'
    '    except Exception as exc:\n'
    '        logging.warning("[%s] fastp parse failed: %s", sample, exc)\n'
)
B_CNV_ANCHOR = '        ctx["cnv"] = {}'
B_CNV_NEW = (
    '    try:   # DASH_QC_V2: verdict after coverage, hsmetrics, fastp and the sex check are all parsed\n'
    '        ctx["qc_verdict"] = p_coverage.verdict(ctx.get("coverage"), ctx.get("hsmetrics"),\n'
    '                                               fastp=ctx.get("fastp"),\n'
    '                                               sex_check=(ctx.get("cnv") or {}).get("sex_check"))\n'
    '    except Exception as exc:\n'
    '        logging.warning("[%s] qc verdict failed: %s", sample, exc)\n'
)

# ---- coverage.py verdict ---------------------------------------------------
C_SIG_OLD = "def verdict(coverage, hsmetrics):\n"
C_SIG_NEW = "def verdict(coverage, hsmetrics, fastp=None, sex_check=None):   # DASH_QC_V2: fastp + sex check\n"

C_BLOCK_ANCHOR_OLD = "    if not have_cov and not have_hs:\n"
C_BLOCK_NEW = '''    # DASH_QC_V2: read-level QC from fastp
    read_rows = []
    fp = fastp or {}
    if fp:
        thr = fp.get("thresholds", {})

        def _add(label, val, disp, rng="", ok=None):
            read_rows.append({"label": label, "value": val, "display": disp, "range": rng, "ok": ok})

        _add("Total reads before filtering (both mates)", fp.get("reads_before"), _fmt(fp.get("reads_before"), "int"))
        _add("Reads passing fastp filters", fp.get("pct_passed"), _fmt(fp.get("pct_passed"), "pct"))
        q30, q30_min = fp.get("q30_after"), thr.get("q30_min", 0.85)
        ok_q = None if q30 is None else (q30 >= q30_min)
        _add("Q30 bases after filtering", q30, _fmt(q30, "pct"), ">= " + _fmt(q30_min, "pct"), ok_q)
        if ok_q is False:
            review.append("Q30 bases after filtering %s (limit >= %s)" % (_fmt(q30, "pct"), _fmt(q30_min, "pct")))
        l1, l2 = fp.get("mean_len_r1_after"), fp.get("mean_len_r2_after")
        _add("Mean read length after trimming (R1 / R2)", l1, "%s / %s bp" % (l1 if l1 is not None else "\\u2014", l2 if l2 is not None else "\\u2014"))
        _add("Reads with adapter trimmed", fp.get("adapter_trimmed_frac"), _fmt(fp.get("adapter_trimmed_frac"), "pct"))
        _add("Duplication estimate (fastp, sequence-based)", fp.get("dup_rate"), _fmt(fp.get("dup_rate"), "pct"))
        ip, ip_min = fp.get("insert_peak"), thr.get("insert_peak_min", 150)
        ok_i = None if ip is None else (ip >= ip_min)
        _add("Insert size peak", ip, ("%d bp" % ip) if ip is not None else "\\u2014", ">= %d bp" % ip_min, ok_i)
        if ok_i is False:
            review.append("Insert size peak %d bp (limit >= %d bp)" % (ip, ip_min))

    # DASH_QC_V2: sample identity from SEX_CHECK
    identity = []
    sx = sex_check or {}
    if sx:
        sheet = (sx.get("sheet_sex") or "").strip().lower()
        het = (sx.get("het_inferred_sex") or "").strip().lower()
        dep = (sx.get("depth_inferred_sex") or "").strip().lower()
        res = (sx.get("resolved_sex") or "").strip().lower()
        flags = str(sx.get("flags") or "")
        status_sx = str(sx.get("status") or "")
        identity = [
            ("Samplesheet sex", sheet or "unknown"),
            ("Sex by chrX heterozygosity", "%s (chrX het fraction %s vs autosomal %s; %s chrX catalog sites)"
             % (het or "NA", sx.get("x_het_frac", "NA"), sx.get("auto_het_frac", "NA"), sx.get("n_x_het_sites", "NA"))),
            ("Sex by X/autosome depth", "%s (X/A %s)" % (dep or "NA", sx.get("x_auto_ratio", "NA"))),
            ("Sex used by the pipeline", res or "NA"),
            ("Sex-check status", ("%s %s" % (status_sx, flags)).strip()),
        ]
        if sheet in ("male", "female") and het in ("male", "female") and sheet != het:
            review.append("Sex mismatch: samplesheet %s, chrX heterozygosity %s (possible sample swap)" % (sheet, het))
        elif sheet not in ("male", "female"):
            findings.append("Sex not given on the samplesheet; %s inferred from chrX heterozygosity" % (het or res or "unknown"))
        if "X_DEPTH_CONFLICT" in flags:
            findings.append("chrX depth (%s, X/A %s) disagrees with chrX heterozygosity (%s): consistent with a chrX copy-number change in the tumour; see the CNV tab"
                            % (dep or "NA", sx.get("x_auto_ratio", "NA"), het or "NA"))

    if not have_cov and not have_hs:
'''

C_RET_OLD = '    return {"status": status, "label": label, "pill": pill, "reasons": reasons, "run_metrics": run_rows}\n'
C_RET_NEW = (
    '    return {"status": status, "label": label, "pill": pill, "reasons": reasons, "run_metrics": run_rows,\n'
    '            "read_metrics": read_rows, "identity": identity}   # DASH_QC_V2\n'
)

# ---- template -------------------------------------------------------------
T_ID_OLD = "        <h4 class=\"mt-4\">Low-coverage genes</h4>\n"
T_ID_NEW = (
    "        {# DASH_QC_V2: sample identity #}\n"
    "        <h4 class=\"mt-4\">Sample identity (sex check)</h4>\n"
    "        {% if ctx.qc_verdict and ctx.qc_verdict.identity %}\n"
    "          <p class=\"text-muted small mb-2\">Sex is decided by chrX heterozygosity at the het catalog (males near 0, females near the autosomal fraction); X/autosome depth confirms it or flags a chrX copy-number change. A samplesheet sex that contradicts heterozygosity is a possible sample swap and sets REVIEW.</p>\n"
    "          <table class=\"table table-sm tspipe-kv-table\" style=\"max-width: 760px;\"><tbody>\n"
    "            {% for k, v in ctx.qc_verdict.identity %}<tr><td class=\"label\">{{ k }}</td><td class=\"value\">{{ v }}</td></tr>{% endfor %}\n"
    "          </tbody></table>\n"
    "        {% else %}\n"
    "          <div class=\"tspipe-empty\">Sex check not available.</div>\n"
    "        {% endif %}\n"
    "\n"
    "        <h4 class=\"mt-4\">Low-coverage genes</h4>\n"
)

T_FASTP_OLD = (
    "        <h4 class=\"mt-4\">fastp QC report</h4>\n"
    "        {% if ctx.files.fastp %}\n"
    "          <iframe class=\"tspipe-iframe-full\" data-src=\"./{{ ctx.files.fastp }}\" loading=\"lazy\"></iframe>\n"
    "        {% else %}\n"
    "          <div class=\"tspipe-empty\">fastp report not available.</div>\n"
    "        {% endif %}\n"
)
T_FASTP_NEW = (
    "        {# DASH_QC_V2: read-level QC table replaces the fastp iframe #}\n"
    "        <h4 class=\"mt-4\">Read-level QC (fastp)</h4>\n"
    "        {% if ctx.qc_verdict and ctx.qc_verdict.read_metrics %}\n"
    "          <p class=\"text-muted small mb-2\">From fastp on the raw FASTQs, before alignment. Adapter trimming on a third of reads is expected with ~160 bp inserts on 150 bp reads. Limits are shown only for metrics that feed the verdict.</p>\n"
    "          <table class=\"table table-sm tspipe-kv-table\" style=\"max-width: 760px;\">\n"
    "            <thead><tr><th>metric</th><th>value</th><th>limit</th><th></th></tr></thead>\n"
    "            <tbody>\n"
    "              {% for r in ctx.qc_verdict.read_metrics %}\n"
    "                <tr><td class=\"label\">{{ r.label }}</td><td class=\"value\">{{ r.display }}</td><td class=\"value\">{{ r.range }}</td>\n"
    "                    <td>{% if r.ok is true %}<span class=\"badge qc-pill-pass\">ok</span>{% elif r.ok is false %}<span class=\"badge qc-pill-fail\">out of limit</span>{% endif %}</td></tr>\n"
    "              {% endfor %}\n"
    "            </tbody>\n"
    "          </table>\n"
    "          {% if ctx.files.fastp %}<p class=\"small text-muted\">Full fastp report (per-base quality, GC content, k-mer plots): <a href=\"./{{ ctx.files.fastp }}\" target=\"_blank\">{{ ctx.files.fastp }}</a></p>{% endif %}\n"
    "        {% elif ctx.files.fastp %}\n"
    "          <div class=\"tspipe-empty\">fastp metrics not available (no <code>_fastp.json</code> in clinical/); full report: <a href=\"./{{ ctx.files.fastp }}\" target=\"_blank\">{{ ctx.files.fastp }}</a></div>\n"
    "        {% else %}\n"
    "          <div class=\"tspipe-empty\">fastp output not available.</div>\n"
    "        {% endif %}\n"
)

EDITS = [
    (PRE, PRE_EMIT_ANCHOR, PRE_EMIT_NEW, "insert_after_line"),
    (PRE, PRE_OUT_ANCHOR, PRE_OUT_NEW, "insert_after_line"),
    (WF, WF_JOIN_ANCHOR, WF_JOIN_NEW, "insert_after_line"),
    (ORG_NF, ORG_IN_OLD, ORG_IN_NEW, "replace"),
    (ORG_NF, ORG_CMD_OLD, ORG_CMD_NEW, "replace"),
    (ORG_NF, ORG_STUB_OLD, ORG_STUB_NEW, "replace"),
    (ORG_PY, PY_ARG_OLD, PY_ARG_NEW, "replace"),
    (ORG_PY, PY_LINK_OLD, PY_LINK_NEW, "replace"),
    (BUILD, B_IMPORT_OLD, B_IMPORT_NEW, "replace"),
    (BUILD, B_INIT_OLD, B_INIT_NEW, "replace"),
    (BUILD, B_VERD_OLD, B_VERD_NEW, "replace"),
    (BUILD, B_CNV_ANCHOR, B_CNV_NEW, "insert_after_line"),
    (COV, C_SIG_OLD, C_SIG_NEW, "replace"),
    (COV, C_BLOCK_ANCHOR_OLD, C_BLOCK_NEW, "replace"),
    (COV, C_RET_OLD, C_RET_NEW, "replace"),
    (TPL, T_ID_OLD, T_ID_NEW, "replace"),
    (TPL, T_FASTP_OLD, T_FASTP_NEW, "replace"),
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
    fp_new = REPO / FASTP_PY
    if fp_new.exists() and MARKER in fp_new.read_text():
        print("SKIP  %s: already present" % FASTP_PY)
    elif fp_new.exists():
        errors.append("%s exists without the marker; refusing to overwrite" % FASTP_PY)
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
    if not fp_new.exists():
        print("PLAN  %s: new file" % FASTP_PY)
    if not args.apply:
        print("dry run; re-run with --apply"); return
    stamp = time.strftime("%Y%m%d_%H%M%S")
    for rel, text in staged.items():
        p = REPO / rel
        bak = p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp))
        bak.write_text(p.read_text()); p.write_text(text)
        print("WROTE %s (backup %s)" % (rel, bak.name))
    if not fp_new.exists():
        fp_new.write_text(FASTP_SRC); print("WROTE %s (new)" % FASTP_PY)
    print("done")


if __name__ == "__main__":
    main()
