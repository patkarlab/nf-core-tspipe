#!/usr/bin/env python3
"""
tools/compare_tsv_to_production.py - 2026-05-17

Compare an nf-core port output TSV against the production reference TSV
for the same sample and report variant-key set differences. Designed for
the three-tier comparison from the 2026-05-16 session audit:

    annotated TSV   (post VEP_ANNOTATE)
    filtered TSV    (post VARIANT_FILTER)
    clinical TSV    (post clinical tiering)

A "variant key" is a tuple of identifying columns (default: chromosome,
position, reference allele, alternate allele). Two rows are considered
to refer to the same variant if their keys are equal; their other column
values are not compared here. For content-level diffs on the common
intersection, a separate pass would be needed.

Usage
-----
Run once per tier. Example for the annotated tier:

    python3 tools/compare_tsv_to_production.py \\
        --port /goast/hemat_data/nfcore_runs/<run>/25NGS1307/<path>/annotated.tsv \\
        --prod /home/hemat/targeted-seq-pipeline/results/25NGS1307/<path>/annotated.tsv \\
        --label annotated

Outputs go to /tmp by default; override with --out-dir. The summary
prints to stdout in the same shape as the 2026-05-16 audit table:

    === Comparison: annotated ===
      Port:        <path>   keys=N1
      Production:  <path>   keys=N2
      Key columns: Chr,Start,Ref,Alt
      Common:      M
      Port-only:   K1       (written to /tmp/annotated_port_only.tsv)
      Prod-only:   K2       (written to /tmp/annotated_prod_only.tsv)

If your TSVs use non-standard column names, override the key resolution
with --key-cols. For example:

    --key-cols "CHROM,POS,REF,ALT"

Dependencies: Python 3 standard library only (no pandas).
"""

import argparse
import csv
import pathlib
import sys

# Default key-column tuples to try in order. Each tuple is one possible
# layout; we use the first layout where every column is present in both
# files' headers. These cover production's typical TSV column names
# (ANNOVAR-style "Chr/Start/Ref/Alt") plus common VCF-style fallbacks.
KEY_COL_CANDIDATES = [
    ("Chr",    "Start", "Ref", "Alt"),
    ("CHROM",  "POS",   "REF", "ALT"),
    ("#CHROM", "POS",   "REF", "ALT"),
    ("chrom",  "pos",   "ref", "alt"),
]


def parse_args():
    ap = argparse.ArgumentParser(
        description=(
            "Compare port vs production TSV by variant key set. "
            "Reports counts and writes port-only / prod-only diff TSVs."
        )
    )
    ap.add_argument("--port", required=True, type=pathlib.Path,
                    help="Path to the port-side TSV.")
    ap.add_argument("--prod", required=True, type=pathlib.Path,
                    help="Path to the production-side TSV.")
    ap.add_argument("--label", default=None,
                    help=("Label for the comparison (e.g. 'annotated', "
                          "'filtered', 'clinical'). Default: derived from "
                          "the port filename stem."))
    ap.add_argument("--key-cols", default=None,
                    help=("Comma-separated column names forming the variant "
                          "key. Default: auto-detect from a list of common "
                          "layouts. Override if your TSV uses non-standard "
                          "names."))
    ap.add_argument("--out-dir", default=pathlib.Path("/tmp"),
                    type=pathlib.Path,
                    help=("Directory to write port-only / prod-only diff "
                          "TSVs. Default: /tmp"))
    ap.add_argument("--no-write", action="store_true",
                    help="Print summary only; skip writing diff TSVs.")
    return ap.parse_args()


def sniff_delim(path):
    """Return '\\t' if the first line looks tab-separated, else ','.

    Lightweight alternative to csv.Sniffer, which can over-think things
    on small files. Most pipeline outputs are TSV; the comma fallback is
    just to be polite.
    """
    with path.open() as f:
        first = f.readline()
    return "\t" if "\t" in first else ","


def read_header(path):
    """Return the header (list of column names) of a CSV/TSV file."""
    delim = sniff_delim(path)
    with path.open() as f:
        reader = csv.reader(f, delimiter=delim)
        try:
            return next(reader)
        except StopIteration:
            sys.exit(f"ERROR: {path} appears to be empty.")


def resolve_key_cols(port_path, prod_path, override):
    """Pick the key columns. If --key-cols is given, parse it and
    require that every column is present in BOTH file headers.
    Otherwise, walk KEY_COL_CANDIDATES and pick the first layout that
    matches both files.
    """
    port_header = read_header(port_path)
    prod_header = read_header(prod_path)

    if override:
        cols = tuple(c.strip() for c in override.split(","))
        missing_port = [c for c in cols if c not in port_header]
        missing_prod = [c for c in cols if c not in prod_header]
        if missing_port or missing_prod:
            sys.exit(
                f"ERROR: requested key columns not found.\n"
                f"  Missing in port ({port_path.name}): {missing_port}\n"
                f"  Missing in prod ({prod_path.name}): {missing_prod}\n"
                f"  Port header:  {port_header}\n"
                f"  Prod header:  {prod_header}"
            )
        return cols

    for cand in KEY_COL_CANDIDATES:
        if all(c in port_header for c in cand) and \
           all(c in prod_header for c in cand):
            return cand

    sys.exit(
        f"ERROR: could not auto-detect key columns. Tried these layouts:\n"
        f"  {KEY_COL_CANDIDATES}\n"
        f"Specify the right columns explicitly with --key-cols.\n"
        f"  Port header ({port_path.name}):  {port_header}\n"
        f"  Prod header ({prod_path.name}):  {prod_header}"
    )


def load_tsv(path, key_cols):
    """Load a TSV. Returns (header, rows_by_key) where rows_by_key
    maps a tuple of key-column values to the full row dict.

    Duplicate keys within one file (same chrom/pos/ref/alt appearing
    twice) keep the first occurrence and log a warning. This is a
    defensive choice; multi-allelic sites that have been split should
    have distinct ALT alleles and thus distinct keys, so a duplicate
    here usually signals an upstream bug.
    """
    delim = sniff_delim(path)
    rows_by_key = {}
    duplicates = 0
    with path.open() as f:
        reader = csv.DictReader(f, delimiter=delim)
        header = reader.fieldnames
        for row in reader:
            key = tuple(row[c] for c in key_cols)
            if key in rows_by_key:
                duplicates += 1
                continue
            rows_by_key[key] = row
    if duplicates:
        print(
            f"  (warning: {duplicates} duplicate key(s) in {path.name}; "
            "first occurrence kept)", file=sys.stderr,
        )
    return header, rows_by_key


def write_diff(path, header, rows_by_key, keys, delim="\t"):
    """Write a subset of rows (those whose key is in `keys`) to a TSV
    at `path`, preserving the original column order.
    """
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=header, delimiter=delim, lineterminator="\n",
        )
        writer.writeheader()
        # Sort keys for stable diff output (chrom string, then pos as
        # int when possible, then ref, then alt).
        for k in sorted(keys, key=_sort_key):
            writer.writerow(rows_by_key[k])


def _sort_key(k):
    """Best-effort numeric sort on the second key element (position),
    falling back to string compare if it isn't an int.
    """
    chrom, pos = k[0], k[1]
    try:
        pos_i = int(pos)
    except (TypeError, ValueError):
        pos_i = 0
    return (chrom, pos_i, k[2], k[3])


def main():
    args = parse_args()

    if not args.port.is_file():
        sys.exit(f"ERROR: port TSV not found: {args.port}")
    if not args.prod.is_file():
        sys.exit(f"ERROR: prod TSV not found: {args.prod}")

    key_cols = resolve_key_cols(args.port, args.prod, args.key_cols)

    port_header, port_rows = load_tsv(args.port, key_cols)
    prod_header, prod_rows = load_tsv(args.prod, key_cols)

    port_keys = set(port_rows.keys())
    prod_keys = set(prod_rows.keys())
    common = port_keys & prod_keys
    port_only = port_keys - prod_keys
    prod_only = prod_keys - port_keys

    label = args.label or args.port.stem

    print(f"=== Comparison: {label} ===")
    print(f"  Port:        {args.port}   keys={len(port_keys)}")
    print(f"  Production:  {args.prod}   keys={len(prod_keys)}")
    print(f"  Key columns: {','.join(key_cols)}")
    print(f"  Common:      {len(common)}")
    print(f"  Port-only:   {len(port_only)}")
    print(f"  Prod-only:   {len(prod_only)}")

    if args.no_write:
        return 0

    args.out_dir.mkdir(parents=True, exist_ok=True)
    port_only_path = args.out_dir / f"{label}_port_only.tsv"
    prod_only_path = args.out_dir / f"{label}_prod_only.tsv"

    write_diff(port_only_path, port_header, port_rows, port_only)
    write_diff(prod_only_path, prod_header, prod_rows, prod_only)
    print(f"  Port-only diff: {port_only_path}")
    print(f"  Prod-only diff: {prod_only_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
