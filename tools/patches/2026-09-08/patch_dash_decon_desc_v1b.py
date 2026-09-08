#!/usr/bin/env python3
"""tools/patches/<date>/patch_dash_decon_desc_v1b.py -- MARKER DASH_DECON_V1b

Corrects three rows of the DASH_DECON_V1 column key to the vocabulary actually
written by the DECoN parser on run8:
  decision   PASS | PASS_MULTIDEL | BELOW_BF
  reportable yes | no
  exon_flags '-' in the current version (per-exon flags are C4, not yet implemented)

Usage:  python3 <this file> [--apply]
Guard:  MARKER DASH_DECON_V1b; each anchor exactly once; all-or-nothing.
"""

import argparse
import sys
import time
from pathlib import Path

MARKER = "DASH_DECON_V1b"
TAG = "dash_decon_v1b"
REPO = Path(__file__).resolve().parents[3]
TARGET = "bin/dashboard_builder/templates/sample_report.html.j2"

ROW = "                <tr><td class=\"text-nowrap\"><code>%s</code></td><td>%s</td></tr>\n"

EDITS = [
    (ROW % ("decision",
            "how the call was classified: PASS, BELOW_BF (BF under the reporting threshold), or a flag naming why it is "
            "not reportable"),
     ROW % ("decision",
            "PASS: single-exon call at BF &ge; 12; PASS_MULTIDEL: multi-exon deletion at BF &ge; 8; "
            "BELOW_BF: listed for context only, under the reporting threshold")),
    (ROW % ("reportable", "TRUE when the call meets the BF threshold and carries no disqualifying flag"),
     ROW % ("reportable", "yes when decision is PASS or PASS_MULTIDEL, otherwise no")),
    (ROW % ("exon_flags",
            "per-exon caveats such as PROBE_VARIANT (a variant under a probe can mimic a deletion), "
            "RECURRENT_IN_NORMALS or LOW_POWER"),
     ROW % ("exon_flags",
            "reserved for per-exon caveats (probe-site variant, recurrent in normals, low power); "
            "'-' in the current version")),
    ("          {# DASH_DECON_V1: BF explanation and column key #}\n",
     "          {# DASH_DECON_V1: BF explanation and column key; DASH_DECON_V1b: vocabulary corrected #}\n"),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    p = REPO / TARGET
    text = p.read_text()
    if MARKER in text:
        print("SKIP  %s: %s already present" % (TARGET, MARKER)); return
    new = text
    for old, rep in EDITS:
        n = new.count(old)
        if n != 1:
            print("ABORT -- nothing written: anchor matched %d times (need 1): %r" % (n, old[:80])); sys.exit(1)
        new = new.replace(old, rep, 1)
    print("PLAN  %s: %d rows corrected, marker %s" % (TARGET, len(EDITS) - 1, MARKER))
    if not args.apply:
        print("dry run; re-run with --apply"); return
    bak = p.with_name(p.name + ".bak_%s_%s" % (TAG, time.strftime("%Y%m%d_%H%M%S")))
    bak.write_text(text); p.write_text(new)
    print("WROTE %s (backup %s)\ndone" % (TARGET, bak.name))


if __name__ == "__main__":
    main()
