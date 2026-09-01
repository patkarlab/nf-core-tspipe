#!/usr/bin/env python3
"""Generate cnv_scatter_regions.txt for a panel from its exonwise BED.

Output replicates the conventions of the existing myeloid asset consumed
by bin/cnv_plots.py:
  - POSITIONAL lines: line 1 = chr1 ... line 22 = chr22, line 23 = chrX,
    line 24 = chrY. There is no chromosome column; the line index IS the
    chromosome.
  - Each populated line has two tab-separated fields: a comma-joined list
    of regions rendered as chrom:start-end (BED coordinates verbatim),
    and a comma-joined list of the matching labels (BED column 4),
    order-aligned, sorted by start coordinate within the chromosome.
  - Chromosomes with no exonwise rows produce an empty line so the
    positional contract holds (the myeloid file's chrY line is empty).

Labels are passed through verbatim (twist exonwise uses GENE_exon_N; the
myeloid asset uses GENE_Ex_N -- both are display strings). If the
cnv_plots.py parser turns out to pattern-match label text, re-run with
--label-ex to rewrite '_exon_' -> '_Ex_'.

Usage (from the repo root on gandalf):
    python tools/make_scatter_regions.py \
        --exonwise assets/twist_myeloid/targets.exonwise.bed \
        --out assets/twist_myeloid/cnv_scatter_regions.txt
"""

import argparse
import os
import sys

CHROMS = ["chr{0}".format(i) for i in range(1, 23)] + ["chrX", "chrY"]


def fail(msg):
    sys.stderr.write("[error] {0}\n".format(msg))
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description="Generate cnv_scatter_regions.txt from exonwise BED")
    ap.add_argument("--exonwise", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--label-ex", action="store_true",
                    help="rewrite '_exon_' to '_Ex_' in labels")
    args = ap.parse_args()

    if not os.path.isfile(args.exonwise):
        fail("exonwise BED not found: {0}".format(args.exonwise))

    per_chrom = {c: [] for c in CHROMS}
    n_rows = 0
    with open(args.exonwise) as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.rstrip("\n")
            if not line or line.startswith(("#", "track", "browser")):
                continue
            parts = line.split("\t")
            if len(parts) < 4:
                fail("line {0}: expected 4+ columns, got {1}".format(lineno, len(parts)))
            chrom, start, end, label = parts[0], parts[1], parts[2], parts[3]
            if chrom not in per_chrom:
                fail("line {0}: non-canonical chromosome '{1}' "
                     "(exonwise should be pre-filtered)".format(lineno, chrom))
            if args.label_ex:
                label = label.replace("_exon_", "_Ex_")
            per_chrom[chrom].append((int(start), int(end), label))
            n_rows += 1

    if n_rows == 0:
        fail("no usable rows in {0}".format(args.exonwise))

    out_lines = []
    n_populated = 0
    for chrom in CHROMS:
        rows = sorted(per_chrom[chrom])
        if not rows:
            out_lines.append("")
            continue
        regions = ",".join("{0}:{1}-{2}".format(chrom, s, e) for s, e, _ in rows)
        labels = ",".join(lbl for _, _, lbl in rows)
        out_lines.append(regions + "\t" + labels)
        n_populated += 1

    with open(args.out, "w") as out:
        out.write("\n".join(out_lines) + "\n")

    print("[ok] wrote {0}: 24 positional lines, {1} populated, {2} regions total".format(
        args.out, n_populated, n_rows))
    for i, chrom in enumerate(CHROMS):
        n = len(per_chrom[chrom])
        if n:
            print("[ok]   line {0:>2} {1:>5}: {2} regions".format(i + 1, chrom, n))


if __name__ == "__main__":
    main()
