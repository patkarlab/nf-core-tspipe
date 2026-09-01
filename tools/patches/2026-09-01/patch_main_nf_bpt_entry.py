#!/usr/bin/env python3
"""Add the BUILD_PON_TWIST include to main.nf (marker BPT_ENTRY_V1).

Nextflow's -entry selects any workflow visible at top level of main.nf,
including included ones (main.nf documents this for BUILD_PON), so the
entire patch is one include line inserted after the BUILD_PON include.

Idempotent, anchor-based, dry-run by default. Run from the repo root:
    python tools/patches/2026-09-01/patch_main_nf_bpt_entry.py           # dry-run
    python tools/patches/2026-09-01/patch_main_nf_bpt_entry.py --apply
"""

import argparse
import os
import shutil
import sys
from datetime import datetime

TARGET = "main.nf"
MARKER = "BPT_ENTRY_V1"
ANCHOR = "include { BUILD_PON } from './workflows/build_pon'"
INSERT = ("include { BUILD_PON_TWIST } from './workflows/build_pon_twist'"
          "   // BPT_ENTRY_V1 -- run with: -entry BUILD_PON_TWIST")


def main():
    ap = argparse.ArgumentParser(description="Patch main.nf: BUILD_PON_TWIST entry include")
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry-run)")
    ap.add_argument("--file", default=TARGET, help="target file (default: main.nf)")
    args = ap.parse_args()

    if not os.path.isfile(args.file):
        print("[error] target not found: {0} (run from the repo root)".format(args.file))
        sys.exit(1)

    with open(args.file) as fh:
        text = fh.read()

    if MARKER in text:
        print("[skip] marker {0} already present in {1}; nothing to do".format(MARKER, args.file))
        return

    n_anchor = text.count(ANCHOR)
    if n_anchor != 1:
        print("[error] anchor found {0} times (need exactly 1): {1}".format(n_anchor, ANCHOR))
        sys.exit(1)

    lines = text.splitlines(True)
    anchor_idx = None
    for i, line in enumerate(lines):
        if ANCHOR in line:
            anchor_idx = i
            break

    new_lines = lines[: anchor_idx + 1] + [INSERT + "\n"] + lines[anchor_idx + 1:]
    new_text = "".join(new_lines)

    print("[plan] insert after line {0} of {1}:".format(anchor_idx + 1, args.file))
    print("       {0}".format(lines[anchor_idx].rstrip()))
    print("     + {0}".format(INSERT))

    if not args.apply:
        print("[dry-run] no changes written; re-run with --apply")
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = "{0}.bak_bpt_entry_{1}".format(args.file, ts)
    shutil.copy2(args.file, backup)
    print("[backup] {0}".format(backup))

    with open(args.file, "w") as fh:
        fh.write(new_text)

    with open(args.file) as fh:
        verify = fh.read()
    if verify.count(MARKER) != 1:
        print("[error] post-write verification failed: marker count = {0}; "
              "restore from {1}".format(verify.count(MARKER), backup))
        sys.exit(1)
    print("[patch] {0}: BUILD_PON_TWIST include added ({1})".format(args.file, MARKER))


if __name__ == "__main__":
    main()
