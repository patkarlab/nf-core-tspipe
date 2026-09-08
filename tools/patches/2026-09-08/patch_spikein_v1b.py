#!/usr/bin/env python3
"""tools/patches/2026-09-08/patch_spikein_v1b.py -- MARKER SPIKEIN_V1b (D13)

bin/spikein_sites.py: report the alt allele only when it reaches ALT_SHOW_MIN_AF
(2%) of depth. CollectAllelicCounts reports the commonest non-reference base,
so a hom_ref site at 1100x showed "C>T" from a handful of error reads
(26CGH799/885 at rs3824662). Genotype and risk_copies are unchanged.

Costs an 18-task resume (SPIKEIN_SITES 8, ORGANIZE 8, DASHBOARD, BUNDLE).
Dry-run by default; --apply writes with a .bak_spikein_v1b_<ts> backup.
"""

import argparse
import shutil
import sys
import time
from pathlib import Path

MARKER = "SPIKEIN_V1b"
TAG = "spikein_v1b"
REPO = Path(__file__).resolve().parents[3]
TARGET = "bin/spikein_sites.py"

EDITS = [
    ("after", "HOM_ALT_MIN = 0.85",
     "ALT_SHOW_MIN_AF = 0.02   # SPIKEIN_V1b: alt allele shown only at >= 2% of depth\n"),
    ("replace", 'alt = rec["alt"] if rec["alt_count"] > 0 else "-"',
     '                alt = rec["alt"] if (depth > 0 and rec["alt_count"] / float(depth) >= ALT_SHOW_MIN_AF) else "-"   # SPIKEIN_V1b\n'),
]


def find_line(lines, anchor):
    hits = [i for i, l in enumerate(lines) if anchor in l]
    if len(hits) != 1:
        raise RuntimeError("anchor matched %d lines (need 1): %r" % (len(hits), anchor))
    return hits[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--repo", default=str(REPO))
    args = ap.parse_args()
    p = Path(args.repo) / TARGET
    src = p.read_text()
    if MARKER in src:
        print("[skip]   %s already carries %s" % (TARGET, MARKER))
        return 0
    lines = src.splitlines(keepends=True)
    try:
        for op, anchor, text in EDITS:
            find_line(lines, anchor)
        for op, anchor, text in EDITS:
            i = find_line(lines, anchor)
            new = text.splitlines(keepends=True)
            lines[i + 1:i + 1] = new if op == "after" else []
            if op == "replace":
                lines[i:i + 1] = new
    except RuntimeError as exc:
        print("[error]  %s: %s" % (TARGET, exc))
        return 1
    print("[patch]  %s: %d edit(s)" % (TARGET, len(EDITS)))
    if not args.apply:
        print("[dry]    re-run with --apply")
        return 0
    bak = p.with_name(p.name + ".bak_%s_%s" % (TAG, time.strftime("%Y%m%d_%H%M%S")))
    shutil.copy2(p, bak)
    p.write_text("".join(lines))
    print("[backup] %s\n[write]  %s\n[done]" % (bak.name, TARGET))
    return 0


if __name__ == "__main__":
    sys.exit(main())
