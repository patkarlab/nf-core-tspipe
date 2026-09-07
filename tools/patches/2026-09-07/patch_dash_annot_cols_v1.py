#!/usr/bin/env python3
"""tools/patches/<date>/patch_dash_annot_cols_v1.py -- MARKER DASH_ANNOT_V1

Follow-up to CMX_ANNOT_V1: the dashboard consensus table selects a fixed
column list (CONSENSUS_COLUMNS in bin/dashboard_builder/parsers/cnv_v2.py),
so the annotation columns were in the TSV/JSON/bundle but not rendered.

Change: cytoband inserted after gene; driver_role, clingen_hi, clingen_ts
appended after loo_fp_any. driver_report_del/amp and driver_amp_ratio stay
TSV-only. Rows are built with r.get(c, ""), so pre-CMX_ANNOT_V1 TSVs render
blanks rather than fail.

bin/ is not hashed and modules/local/dashboard.nf has no bump comment: force
the re-render with `-c /tmp/dash_nocache.config` (see docs/sops).

Usage:  python3 <this file>            # dry run
        python3 <this file> --apply
Guard:  MARKER DASH_ANNOT_V1; single exact anchor; backup <file>.bak_dash_annot_v1_<stamp>.
"""

import argparse
import sys
import time
from pathlib import Path

MARKER = "DASH_ANNOT_V1"
TAG = "dash_annot_v1"
REPO = Path(__file__).resolve().parents[3]
TARGET = "bin/dashboard_builder/parsers/cnv_v2.py"

OLD = (
    'CONSENSUS_COLUMNS = ["gene", "chrom", "start", "end", "consensus_call", "tier", "flags",\n'
    '                     "k_call", "k_cn", "k_log2", "g_call", "g_seg_log2", "b_call", "p_call", "p_C",\n'
    '                     "e_call", "e_bf", "h_call", "h_cn_min", "h_cn_max", "h_loh", "loo_fp_any"]\n'
)
NEW = (
    '# MARKER DASH_ANNOT_V1: cytoband beside gene; driver_role, clingen_hi, clingen_ts at the tail\n'
    '# (CMX_ANNOT_V1 columns; blank on pre-annotation TSVs because rows use r.get(c, ""))\n'
    'CONSENSUS_COLUMNS = ["gene", "cytoband", "chrom", "start", "end", "consensus_call", "tier", "flags",\n'
    '                     "k_call", "k_cn", "k_log2", "g_call", "g_seg_log2", "b_call", "p_call", "p_C",\n'
    '                     "e_call", "e_bf", "h_call", "h_cn_min", "h_cn_max", "h_loh", "loo_fp_any",\n'
    '                     "driver_role", "clingen_hi", "clingen_ts"]\n'
)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    args = ap.parse_args()

    p = REPO / TARGET
    if not p.exists():
        print("ABORT: %s not found" % TARGET)
        sys.exit(1)
    text = p.read_text()
    if MARKER in text:
        print("SKIP  %s: %s already present" % (TARGET, MARKER))
        return
    n = text.count(OLD)
    if n != 1:
        print("ABORT -- nothing written: anchor matched %d times (need 1)" % n)
        sys.exit(1)
    new_text = text.replace(OLD, NEW, 1)
    print("PLAN  %s: +%d lines, marker %s" % (TARGET, new_text.count("\n") - text.count("\n"), MARKER))
    if not args.apply:
        print("dry run; re-run with --apply")
        return
    stamp = time.strftime("%Y%m%d_%H%M%S")
    bak = p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp))
    bak.write_text(text)
    p.write_text(new_text)
    print("WROTE %s (backup %s)" % (TARGET, bak.name))
    print("done")


if __name__ == "__main__":
    main()
