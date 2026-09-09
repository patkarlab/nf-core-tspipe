#!/usr/bin/env python3
"""Compare two annotate.py output TSVs keyed on (Chr, Start, End, Ref, Alt).

Reports rows present in only one file and, for shared rows, the number of
mismatches per column with the first few examples, so a run-to-run difference
can be attributed to VEP, ANNOVAR, CAVA, or the merge itself.

usage: compare_annotated.py OLD.tsv NEW.tsv [--examples N]
"""
import argparse
import csv
from collections import Counter, OrderedDict

KEY = ("Chr", "Start", "End", "Ref", "Alt")


def load(path):
    with open(path, newline="") as f:
        rdr = csv.DictReader(f, delimiter="\t")
        cols = rdr.fieldnames
        rows = OrderedDict()
        for r in rdr:
            k = tuple(r[c] for c in KEY)
            if k in rows:
                k = k + (len(rows),)   # keep duplicates distinct
            rows[k] = r
    return cols, rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--examples", type=int, default=3)
    a = ap.parse_args()

    ca, ra = load(a.old)
    cb, rb = load(a.new)
    print("rows: old %d, new %d; columns: old %d, new %d, header %s" % (
        len(ra), len(rb), len(ca), len(cb), "identical" if ca == cb else "DIFFERENT"))
    if ca != cb:
        print("  only in old:", sorted(set(ca) - set(cb)))
        print("  only in new:", sorted(set(cb) - set(ca)))
    only_a = [k for k in ra if k not in rb]
    only_b = [k for k in rb if k not in ra]
    print("rows only in old: %d; only in new: %d" % (len(only_a), len(only_b)))
    for k in only_a[: a.examples]:
        print("  old-only:", ":".join(k[:5]))
    for k in only_b[: a.examples]:
        print("  new-only:", ":".join(k[:5]))

    mism = Counter()
    ex = {}
    shared = 0
    for k, x in ra.items():
        y = rb.get(k)
        if y is None:
            continue
        shared += 1
        for c in ca:
            if c in cb and x[c] != y[c]:
                mism[c] += 1
                ex.setdefault(c, []).append((":".join(k[:5]), x[c], y[c]))
    print("shared rows: %d; rows with any difference: %d" % (
        shared, len({e[0] for v in ex.values() for e in v})))
    if not mism:
        print("no column differences on shared rows")
        return
    print("mismatches per column:")
    for c, n in mism.most_common():
        print("  %-22s %6d" % (c, n))
        for key, xv, yv in ex[c][: a.examples]:
            print("      %-28s old=%r new=%r" % (key, xv[:80], yv[:80]))


if __name__ == "__main__":
    main()
