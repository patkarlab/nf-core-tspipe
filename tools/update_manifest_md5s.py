#!/usr/bin/env python3
"""
update_manifest_md5s.py

Re-sync a MANIFEST.tsv after the asset files it tracks have been modified.

Recomputes md5, size_bytes, and (for .cnn / .bed files) the validation
string for every file listed in the manifest. Preserves '#' comment
preamble at the top of the file.

This is a maintenance utility, not a patch. It is fully idempotent: if
nothing has changed since the last write, the script reports "already in
sync" and exits 0.

Used to recover from a half-applied
`apply_drop_alt_contig_permanent_fix.py` run that updated BED + PoN
files but bombed on the MANIFEST step (the manifest's `#`-comment
preamble tripped the original pandas reader). The BED and PoN are
already correct on disk; this tool just brings the manifest back into
sync.

Usage
-----
    # Default manifest path
    python3 tools/update_manifest_md5s.py

    # Specify a path
    python3 tools/update_manifest_md5s.py path/to/MANIFEST.tsv

    # Preview without writing
    python3 tools/update_manifest_md5s.py --dry-run
"""

import argparse
import hashlib
import shutil
import sys
import time
from pathlib import Path


DEFAULT_MANIFEST = Path(
    "/goast/hemat_data/nf-core-tspipe/assets/myeloid_cnv/MANIFEST.tsv"
)


def md5_of(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def revalidate_cnn(path: Path) -> str:
    """Return an 'ok (N cols, M bins)' validation string for a .cnn file."""
    with open(path) as f:
        header = f.readline().rstrip("\n")
        n_bins = sum(1 for _ in f)
    n_cols = len(header.split("\t"))
    return f"ok ({n_cols} cols, {n_bins} bins)"


def revalidate_bed(path: Path) -> str:
    """Return an 'ok (N bins)' validation string for a BED file."""
    with open(path) as f:
        n_lines = sum(1 for ln in f if ln.strip() and not ln.startswith("#"))
    return f"ok ({n_lines} bins)"


def parse_manifest(path: Path):
    """
    Split a MANIFEST.tsv into:
      - comments: list of '# ...' lines at the top
      - header: list of column names (the first non-comment line)
      - rows: list of list-of-strings for each data row
    """
    comments = []
    table_lines = []
    with open(path) as f:
        in_table = False
        for ln in f:
            stripped = ln.rstrip("\n")
            if not in_table and stripped.startswith("#"):
                comments.append(stripped)
            elif stripped.strip() == "":
                # Blank line: if we're still in the comment section,
                # treat it as comment; if in table, ignore
                if not in_table:
                    comments.append(stripped)
            else:
                in_table = True
                table_lines.append(stripped)
    if len(table_lines) < 2:
        sys.exit(f"ERROR: MANIFEST has no data rows: {path}")
    header = table_lines[0].split("\t")
    rows = [ln.split("\t") for ln in table_lines[1:]]
    return comments, header, rows


def main():
    ap = argparse.ArgumentParser(
        description="Refresh MD5s / sizes / validation in a MANIFEST.tsv.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("manifest", nargs="?", type=Path, default=DEFAULT_MANIFEST,
                    help=f"Path to MANIFEST.tsv (default: {DEFAULT_MANIFEST})")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print what would change without writing.")
    args = ap.parse_args()

    if not args.manifest.is_file():
        sys.exit(f"ERROR: manifest not found: {args.manifest}")
    assets_dir = args.manifest.parent

    comments, header, rows = parse_manifest(args.manifest)
    col_idx = {name: i for i, name in enumerate(header)}

    # Locate columns. We're permissive about names.
    file_col = next(
        (col_idx[c] for c in
         ("dest_filename", "file", "filename", "path") if c in col_idx),
        None
    )
    if file_col is None:
        sys.exit(f"ERROR: no file column in MANIFEST. Header: {header}")
    md5_col = col_idx.get("md5") or col_idx.get("checksum") or col_idx.get("md5sum")
    size_col = col_idx.get("size_bytes")
    validation_col = col_idx.get("validation")
    mtime_col = col_idx.get("source_mtime_utc") or col_idx.get("mtime")

    changes = []
    for row in rows:
        # Pad short rows so column access is safe
        while len(row) < len(header):
            row.append("")
        fname = row[file_col]
        fpath = assets_dir / fname
        if not fpath.is_file():
            print(f"  WARN: {fname} not found in {assets_dir}/, skipping",
                  file=sys.stderr)
            continue

        # md5
        if md5_col is not None:
            new_md5 = md5_of(fpath)
            if row[md5_col] != new_md5:
                changes.append((fname, "md5", row[md5_col], new_md5))
                row[md5_col] = new_md5

        # size_bytes
        if size_col is not None:
            new_size = str(fpath.stat().st_size)
            if row[size_col] != new_size:
                changes.append((fname, "size_bytes", row[size_col], new_size))
                row[size_col] = new_size

        # source_mtime_utc — refresh to reflect the new state on disk
        if mtime_col is not None:
            mtime = time.strftime(
                "%Y-%m-%dT%H:%M:%S+00:00",
                time.gmtime(fpath.stat().st_mtime),
            )
            if row[mtime_col] != mtime:
                changes.append((fname, "source_mtime_utc",
                                row[mtime_col], mtime))
                row[mtime_col] = mtime

        # validation — only regenerate for known file types
        if validation_col is not None:
            new_val = None
            if fname.endswith(".cnn"):
                new_val = revalidate_cnn(fpath)
            elif fname.endswith(".bed"):
                new_val = revalidate_bed(fpath)
            if new_val is not None and row[validation_col] != new_val:
                changes.append((fname, "validation",
                                row[validation_col], new_val))
                row[validation_col] = new_val

    print(f"Manifest:   {args.manifest}")
    print(f"Assets:     {assets_dir}/")
    print(f"Data rows:  {len(rows)}")
    if not changes:
        print("\nAlready in sync. No changes.")
        return 0

    print(f"\n{len(changes)} change(s):")
    for fname, field, old, new in changes:
        def short(s):
            return (s[:40] + "...") if len(s) > 43 else s
        print(f"  {fname:32s}  {field:18s}  {short(old):45s}  ->  {short(new)}")

    if args.dry_run:
        print("\nDRY-RUN: nothing written.")
        return 0

    # Backup + write
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = args.manifest.with_name(
        args.manifest.name + f".bak_update_manifest_{ts}"
    )
    shutil.copy2(args.manifest, bak)
    print(f"\nBackup:     {bak}")

    with open(args.manifest, "w") as f:
        for c in comments:
            f.write(c + "\n")
        f.write("\t".join(header) + "\n")
        for r in rows:
            f.write("\t".join(r) + "\n")
    print(f"Wrote:      {args.manifest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
