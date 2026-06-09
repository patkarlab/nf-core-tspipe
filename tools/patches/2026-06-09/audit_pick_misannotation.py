#!/usr/bin/env python3
"""
audit_pick_misannotation.py   (READ-ONLY - makes no changes)

Quantify the blast radius of the VEP --pick misannotation bug across archived
runs, WITHOUT re-annotating anything. It scans existing *.annotated.tsv files
and flags rows whose recorded annotation carries the signature of the bug:

    a variant that HAS caller support (VariantCaller_Count >= 1, i.e. it was a
    real SomaticSeq call) but whose Consequence is a non-coding "*_gene_variant"
    / intergenic MODIFIER, OR whose Gene is the sentinel "-1".

Under --pick, a coding variant overlapping a neighbouring gene could be recorded
as that neighbour's upstream/downstream_gene_variant (or with Gene=-1). Those are
the rows that, after the --flag_pick fix, flip to a coding consequence on the
correct gene. Counting them per file estimates how many variants - and which
archived clinical reports - were affected.

NOTE: this is a heuristic upper-bound screen on the OLD files. A row flagged here
is "suspicious under --pick"; the definitive per-locus proof is the old-vs-new
diff we already ran on 26CGH400 (118 changed loci). Use this to rank which
archived reports need re-review, not as a final per-variant verdict.

Usage:
    python3 audit_pick_misannotation.py [--root test_run] [--csv report.csv]

Output: per-file counts (total supported variants, suspicious rows, and the
distinct genes that appear on suspicious rows), plus a summary. Read-only.
"""

import argparse
import csv
import glob
import os
import sys

# Consequence terms that are non-coding / regulatory MODIFIERs. A SUPPORTED
# variant landing on one of these is the --pick misannotation signature.
NONCODING_TERMS = set([
    "upstream_gene_variant",
    "downstream_gene_variant",
    "intergenic_variant",
    "regulatory_region_variant",
    "TF_binding_site_variant",
    "feature_truncation",
    "feature_elongation",
])

SENTINEL = "-1"


def supported(row):
    """True if the row had real SomaticSeq caller support (was a genuine call)."""
    v = row.get("VariantCaller_Count", SENTINEL)
    try:
        return int(float(v)) >= 1
    except (ValueError, TypeError):
        return False


def is_suspicious(row):
    """Signature of --pick misannotation on a supported variant."""
    if not supported(row):
        return False
    gene = (row.get("Gene") or "").strip()
    cons = (row.get("Consequence") or "").strip()
    if gene == SENTINEL or gene == "":
        return True
    # Consequence may be '&'-joined; treat as non-coding only if EVERY term is
    # non-coding (a mixed term like splice_region&intron is not the signature).
    terms = [t for t in cons.split("&") if t]
    if terms and all(t in NONCODING_TERMS for t in terms):
        return True
    return False


def audit_file(path):
    total = 0
    suspicious = 0
    genes = {}
    try:
        with open(path) as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                if not supported(row):
                    continue
                total += 1
                if is_suspicious(row):
                    suspicious += 1
                    g = (row.get("Gene") or "").strip() or SENTINEL
                    genes[g] = genes.get(g, 0) + 1
    except Exception as e:
        return None, None, {"_error": str(e)}
    return total, suspicious, genes


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default="test_run",
                    help="Directory to scan recursively (default: test_run)")
    ap.add_argument("--csv", default=None,
                    help="Optional path to write a per-file CSV summary")
    args = ap.parse_args()

    pattern = os.path.join(args.root, "**", "*.annotated.tsv")
    files = sorted(glob.glob(pattern, recursive=True))
    if not files:
        # also try the work dirs, where annotated.tsv often lives
        files = sorted(glob.glob(os.path.join(args.root, "**", "*.annotated.tsv"),
                                 recursive=True))
    if not files:
        sys.stderr.write("No *.annotated.tsv found under %s\n" % args.root)
        return 1

    rows_out = []
    files_affected = 0
    total_suspicious = 0
    print("%-70s %8s %8s  %s" % ("file", "support", "suspect", "genes_on_suspect_rows"))
    print("-" * 120)
    for path in files:
        total, suspicious, genes = audit_file(path)
        if total is None:
            print("%-70s  ERROR: %s" % (path[-70:], genes.get("_error")))
            continue
        short = path if len(path) <= 70 else "..." + path[-67:]
        genestr = ", ".join("%s(%d)" % (g, n)
                            for g, n in sorted(genes.items(), key=lambda x: -x[1])[:8])
        print("%-70s %8d %8d  %s" % (short, total, suspicious, genestr))
        rows_out.append((path, total, suspicious, genestr))
        if suspicious > 0:
            files_affected += 1
            total_suspicious += suspicious

    print("-" * 120)
    print("SUMMARY: %d files scanned | %d files with >=1 suspicious row | %d suspicious variant-rows total"
          % (len(files), files_affected, total_suspicious))
    print("(Suspicious = supported call recorded as non-coding *_gene_variant or Gene=-1; "
          "these are the rows that flip to a coding call under --flag_pick.)")

    if args.csv:
        with open(args.csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["file", "supported_variants", "suspicious_rows", "genes_on_suspicious_rows"])
            w.writerows(rows_out)
        print("CSV written: %s" % args.csv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
