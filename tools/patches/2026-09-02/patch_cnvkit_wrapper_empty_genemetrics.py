#!/usr/bin/env python3
"""Patch cnvkit_wrapper.py: write header-only annotated genemetrics when
the raw table has zero rows, instead of skipping the file.

Root cause: Female16 pilot 2026-09-01. Copy-flat normal -> empty
genemetrics -> Step 8 early return -> CNVKIT task failed on missing
required output. Zero calls is a legitimate result and must produce a
file. The file-not-found branch is left untouched (should stay fatal).

Dry-run by default; --apply to write. Idempotent via MARKER.
"""

import argparse
import shutil
import sys
import time

TARGET = "bin/cnvkit_wrapper.py"
MARKER = "MARKER: genemetrics_empty_headeronly"
TAG = "empty_genemetrics"

ANCHOR = """    if df.empty:
        log.warning("Genemetrics file is empty")
        return
"""

REPLACEMENT = r'''    if df.empty:
        # MARKER: genemetrics_empty_headeronly
        # Zero gene-level calls (e.g. copy-flat normals) is a valid
        # result. Write a header-only annotated table so the CNVKIT
        # module's required-output contract holds and downstream joins
        # retain the sample.
        log.warning("Genemetrics file is empty; writing header-only annotated table")
        for _col in ("LOO_FP_rate", "confidence", "blacklist_frac"):
            df[_col] = []
        df.to_csv(output_path, sep="\t", index=False)
        log.info("  Annotated genemetrics (header-only): %s", output_path)
        return
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="write changes (default: dry-run)")
    ap.add_argument("--target", default=TARGET)
    args = ap.parse_args()

    with open(args.target) as fh:
        src = fh.read()

    if MARKER in src:
        print("[skip] marker present; already patched: %s" % args.target)
        return 0
    n = src.count(ANCHOR)
    if n == 0:
        print("[error] anchor not found in %s -- source drifted" % args.target)
        return 1
    if n > 1:
        print("[error] anchor not unique (%d occurrences)" % n)
        return 1

    if not args.apply:
        print("[dry-run] anchor found, unique. Re-run with --apply.")
        return 0

    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = "%s.bak_%s_%s" % (args.target, TAG, ts)
    shutil.copy2(args.target, bak)
    print("[backup] %s" % bak)
    with open(args.target, "w") as fh:
        fh.write(src.replace(ANCHOR, REPLACEMENT))
    print("[patch] applied to %s" % args.target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
