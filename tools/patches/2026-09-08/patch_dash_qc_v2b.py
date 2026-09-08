#!/usr/bin/env python3
"""tools/patches/<date>/patch_dash_qc_v2b.py -- MARKER DASH_QC_V2b

Threshold correction: fastp insert-size peaks on run8 are 144-164 bp on eight
good libraries, so the 150 bp limit from DASH_QC_V2 split the run. REVIEW now
at < 120 bp, which is where a degraded / over-fragmented library sits.

Usage:  python3 <this file> [--apply]
"""

import argparse
import sys
import time
from pathlib import Path

MARKER = "DASH_QC_V2b"
REPO = Path(__file__).resolve().parents[3]
FP = "bin/dashboard_builder/parsers/fastp.py"
OLD = '    "insert_peak_min": 150, # insert-size peak (bp) below this -> REVIEW\n'
NEW = '    "insert_peak_min": 120, # insert-size peak (bp) below this -> REVIEW (DASH_QC_V2b: run8 peaks 144-164 bp)\n'


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--apply", action="store_true"); args = ap.parse_args()
    p = REPO / FP; text = p.read_text()
    if MARKER in text:
        print("SKIP  %s: already applied" % FP); return
    if text.count(OLD) != 1:
        print("ABORT: anchor matched %d times" % text.count(OLD)); sys.exit(1)
    print("PLAN  %s: insert_peak_min 150 -> 120" % FP)
    if not args.apply:
        print("dry run; re-run with --apply"); return
    p.with_name(p.name + ".bak_dash_qc_v2b_%s" % time.strftime("%Y%m%d_%H%M%S")).write_text(text)
    p.write_text(text.replace(OLD, NEW, 1)); print("WROTE %s\ndone" % FP)


if __name__ == "__main__":
    main()
