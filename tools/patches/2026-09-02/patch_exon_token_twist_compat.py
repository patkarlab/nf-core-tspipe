#!/usr/bin/env python3
"""Widen the legacy gene-token regex _Ex_ to _(?:Ex|exon)_ in the legacy
CNV scripts so they parse twist_myeloid target names (GENE_exon_N) as
well as legacy MYOPOOL names (GENE_Ex_N).

Root cause (Female16 pilot, 2026-09-02): CNV_PLOTS died with "No genes
parsed from BED file". The same _Ex_ assumption sits in clean_gene() of
cnv_concordance.py, cnv_clinical_report.py, zscore_cnv.py and in the
cnvkit_wrapper.py gene-field parser: on twist names they fall through to
raw strings, silently turning gene-level grouping into exon-level
grouping on any sample with calls. Backward compatible.

Dry-run by default; --apply to write. Idempotent: skips a file when the
old token is absent and the new one present.
"""
import argparse
import shutil
import sys
import time

TAG = "exon_token"

# (file, [(old, new, expected_count), ...])
EDITS = [
    ("bin/cnv_plots.py", [
        (r'r"([A-Za-z][A-Za-z0-9]+)_Ex_(\w+)"',
         r'r"([A-Za-z][A-Za-z0-9]+)_(?:Ex|exon)_(\w+)"', 1),
    ]),
    ("bin/cnv_concordance.py", [
        (r"r'_([A-Za-z][A-Za-z0-9]+)_Ex_'",
         r"r'_([A-Za-z][A-Za-z0-9]+)_(?:Ex|exon)_'", 1),
        (r"r'(?:^|,)([A-Za-z][A-Za-z0-9]+)_Ex_'",
         r"r'(?:^|,)([A-Za-z][A-Za-z0-9]+)_(?:Ex|exon)_'", 1),
    ]),
    ("bin/cnv_clinical_report.py", [
        (r"r'_([A-Za-z][A-Za-z0-9]+)_Ex_'",
         r"r'_([A-Za-z][A-Za-z0-9]+)_(?:Ex|exon)_'", 1),
        (r"r'(?:^|,)([A-Za-z][A-Za-z0-9]+)_Ex_'",
         r"r'(?:^|,)([A-Za-z][A-Za-z0-9]+)_(?:Ex|exon)_'", 1),
    ]),
    ("bin/zscore_cnv.py", [
        (r"r'_([A-Za-z][A-Za-z0-9]+)_Ex_'",
         r"r'_([A-Za-z][A-Za-z0-9]+)_(?:Ex|exon)_'", 1),
        (r"r'(?:^|,)([A-Za-z][A-Za-z0-9]+)_Ex_'",
         r"r'(?:^|,)([A-Za-z][A-Za-z0-9]+)_(?:Ex|exon)_'", 1),
        (r"r'_Ex_(\d+)'",
         r"r'_(?:Ex|exon)_(\d+)'", 2),
    ]),
    ("bin/cnvkit_wrapper.py", [
        (r'r"([A-Za-z][A-Za-z0-9]+)_Ex_"',
         r'r"([A-Za-z][A-Za-z0-9]+)_(?:Ex|exon)_"', 1),
    ]),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="write changes (default: dry-run)")
    args = ap.parse_args()
    ts = time.strftime("%Y%m%d_%H%M%S")
    rc = 0

    for path, edits in EDITS:
        with open(path) as fh:
            src = fh.read()
        if all(src.count(o) == 0 and src.count(n) >= 1 for o, n, _ in edits):
            print("[skip] already patched: %s" % path)
            continue
        bad = [(o, src.count(o), k) for o, _, k in edits if src.count(o) != k]
        if bad:
            for o, got, k in bad:
                print("[error] %s: anchor %r found %d times, expected %d"
                      % (path, o, got, k))
            rc = 1
            continue
        new = src
        for o, n, _ in edits:
            new = new.replace(o, n)
        if not args.apply:
            print("[dry-run] %s: %d edit(s) ready" % (path, len(edits)))
            continue
        bak = "%s.bak_%s_%s" % (path, TAG, ts)
        shutil.copy2(path, bak)
        print("[backup] %s" % bak)
        with open(path, "w") as fh:
            fh.write(new)
        print("[patch] %s" % path)
    return rc


if __name__ == "__main__":
    sys.exit(main())
