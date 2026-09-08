#!/usr/bin/env python3
"""
Fetch a CAVA transcript catalog into assets/cava/<catalog_name>/ without git-lfs.

The sicotteh/CAVA repository publishes catalogs as Git LFS objects. Its own
`cava_data install` needs the git-lfs client, which gandalf does not have.
GitHub serves LFS payloads over plain HTTPS at media.githubusercontent.com,
so this script downloads the four files of a catalog directly and verifies
each against the sha256 recorded in cava_catalogs.tsv at a pinned commit.

Usage:
    python3 tools/fetch_cava_catalog.py --catalog mane-1.5-grch38-refseq \
        --dest assets/cava

Writes:
    assets/cava/<catalog_name>/<file_name>{,.tbi,.txt,.cesis}
    assets/cava/<catalog_name>/PROVENANCE.txt
"""

import argparse
import csv
import hashlib
import io
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = "sicotteh/CAVA"
COMMIT = "398eb1d6ff635925fedb7dcd88a9a6617d1a7c3b"
CATALOG_TSV = f"https://raw.githubusercontent.com/{REPO}/{COMMIT}/cava_catalogs.tsv"
MEDIA = f"https://media.githubusercontent.com/media/{REPO}/{COMMIT}/"

# (file column, sha256 column)
FILE_COLUMNS = [
    ("file_name", "sha256"),
    ("index_file_name", "index_sha256"),
    ("transcript_map_file_name", "transcript_map_sha256"),
    ("selenocysteine_file_name", "selenocysteine_sha256"),
]


def fetch(url: str, attempts: int = 5) -> bytes:
    """GET with retries; GitHub's media endpoint occasionally resets the connection."""
    req = urllib.request.Request(url, headers={"User-Agent": "tspipe-fetch-cava-catalog"})
    last_err: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.read()
        except (urllib.error.URLError, ConnectionError, TimeoutError) as err:
            last_err = err
            wait = 5 * attempt
            print(f"attempt {attempt}/{attempts} failed for {url.rsplit('/', 1)[-1]}: {err}; retrying in {wait}s")
            time.sleep(wait)
    raise SystemExit(f"giving up on {url}: {last_err}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--catalog", default="mane-1.5-grch38-refseq")
    ap.add_argument("--dest", default="assets/cava")
    ap.add_argument("--force", action="store_true", help="re-download files that already verify")
    args = ap.parse_args()

    rows = {r["catalog_name"]: r for r in csv.DictReader(io.StringIO(fetch(CATALOG_TSV).decode()), delimiter="\t")}
    if args.catalog not in rows:
        sys.exit(f"catalog {args.catalog!r} not in cava_catalogs.tsv; available: {', '.join(rows)}")
    row = rows[args.catalog]
    if row["status"] != "published":
        sys.exit(f"catalog {args.catalog!r} has status {row['status']!r}, refusing")

    out_dir = Path(args.dest) / args.catalog
    out_dir.mkdir(parents=True, exist_ok=True)

    for name_col, sha_col in FILE_COLUMNS:
        fname, expected = row[name_col], row[sha_col]
        target = out_dir / fname
        if target.exists() and not args.force:
            if hashlib.sha256(target.read_bytes()).hexdigest() == expected:
                print(f"ok (cached)  {target}")
                continue
            print(f"stale        {target}; re-downloading")
        data = fetch(MEDIA + "catalogs/files/" + fname)
        got = hashlib.sha256(data).hexdigest()
        if got != expected:
            sys.exit(f"sha256 mismatch for {fname}: expected {expected}, got {got}")
        target.write_bytes(data)
        print(f"ok           {target}  ({len(data):,} bytes)")

    prov = out_dir / "PROVENANCE.txt"
    prov.write_text(
        "\n".join(
            [
                f"catalog_name      {row['catalog_name']}",
                f"build             {row['Build']}",
                f"source            {row['source']} {row['source_version']}",
                f"transcript_ids    {row['transcript_ID_type']}",
                f"cava_version_spec {row['cava_version_spec']}",
                f"repository        https://github.com/{REPO}",
                f"commit            {COMMIT}",
                f"notes             {row['notes']}",
                "",
            ]
        )
    )
    print(f"wrote        {prov}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
