#!/usr/bin/env python3
"""
tools/verify_s3_archived.py

Decide, file by file, whether a local file may be deleted because an
identical-looking object (same basename, same byte size) exists in the S3
archive. Input is an `s3cmd ls -r <prefix>` listing captured to a file, so
S3 is queried once and the check is repeatable offline.

Statuses:
  ARCHIVED        basename and size match at least one S3 object
  SIZE_MISMATCH   basename found on S3 but no object with the same size
  NOT_FOUND       basename not on S3 at all
  SKIPPED         extension not in --ext

Only ARCHIVED files are written to --safe-list. Nothing is deleted here.

Example:
  python3 tools/verify_s3_archived.py \
      --inventory /goast/hemat_data/s3_fastqarchival_inventory_20260906.txt \
      --dirs sequences sample_fastqs cnv_negatives \
      --report /tmp/prod_tree_archive_check.tsv \
      --safe-list /tmp/prod_tree_safe_to_delete.txt

Python 3.6-safe, stdlib only.
"""
import argparse
import collections
import os
import sys


def load_inventory(path):
    """s3cmd ls -r lines: '2026-08-31 15:06   2099422706   s3://bucket/key'."""
    by_name = collections.defaultdict(list)
    n = 0
    with open(path) as fh:
        for line in fh:
            parts = line.split()
            if len(parts) < 4 or not parts[-1].startswith("s3://"):
                continue
            if parts[2] == "DIR" or parts[2] == "DIROBJ":
                continue
            try:
                size = int(parts[2])
            except ValueError:
                continue
            key = parts[-1]
            by_name[os.path.basename(key)].append((size, key))
            n += 1
    return by_name, n


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--inventory", required=True, help="output of s3cmd ls -r <prefix>")
    p.add_argument("--dirs", nargs="+", required=True, help="local directories to scan (recursive)")
    p.add_argument("--ext", nargs="+", default=[".fastq.gz", ".fq.gz"],
                   help="extensions to check; others are SKIPPED")
    p.add_argument("--report", required=True, help="TSV with one row per file")
    p.add_argument("--safe-list", required=True, help="paths with status ARCHIVED, one per line")
    args = p.parse_args()

    if not os.path.isfile(args.inventory):
        raise SystemExit("[error] missing inventory: {}".format(args.inventory))
    inv, n_obj = load_inventory(args.inventory)
    if n_obj == 0:
        raise SystemExit("[error] inventory has no objects; was s3cmd ls -r complete?")
    print("[ok] inventory: {} objects, {} distinct basenames".format(n_obj, len(inv)))

    counts = collections.Counter()
    bytes_safe = 0
    rows = []
    safe = []
    for d in args.dirs:
        if not os.path.isdir(d):
            print("[warn] not a directory, skipped: {}".format(d))
            continue
        for root, _, files in os.walk(d):
            for f in sorted(files):
                path = os.path.join(root, f)
                if os.path.islink(path):
                    continue
                size = os.path.getsize(path)
                if not any(f.endswith(e) for e in args.ext):
                    status, match = "SKIPPED", ""
                else:
                    hits = inv.get(f, [])
                    same = [k for s, k in hits if s == size]
                    if same:
                        status, match = "ARCHIVED", same[0]
                        safe.append(path)
                        bytes_safe += size
                    elif hits:
                        status, match = "SIZE_MISMATCH", "{} (s3 sizes: {})".format(
                            hits[0][1], ",".join(str(s) for s, _ in hits))
                    else:
                        status, match = "NOT_FOUND", ""
                counts[status] += 1
                rows.append((path, size, status, match))

    with open(args.report, "w") as fh:
        fh.write("path\tsize\tstatus\ts3_match\n")
        for r in rows:
            fh.write("\t".join(str(x) for x in r) + "\n")
    with open(args.safe_list, "w") as fh:
        for s in safe:
            fh.write(s + "\n")

    print("[done] ARCHIVED={} SIZE_MISMATCH={} NOT_FOUND={} SKIPPED={}".format(
        counts["ARCHIVED"], counts["SIZE_MISMATCH"], counts["NOT_FOUND"], counts["SKIPPED"]))
    print("[done] safe to delete: {} files, {:.1f} GB -> {}".format(
        len(safe), bytes_safe / 1e9, args.safe_list))
    for path, size, status, match in rows:
        if status in ("SIZE_MISMATCH", "NOT_FOUND"):
            print("[hold] {:<14s} {}  ({} bytes) {}".format(status, path, size, match))
    return 0


if __name__ == "__main__":
    sys.exit(main())
