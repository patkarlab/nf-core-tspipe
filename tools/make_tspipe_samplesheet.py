#!/usr/bin/env python3
"""
make_tspipe_samplesheet.py

Build a TSPIPE samplesheet from a directory of paired FASTQs. Generic
counterpart to make_bnc_pon_samplesheet.py: the BNC script encodes sex in
filenames, this one doesn't.

Expected filename convention
----------------------------
    <sample_id>-<assay_tag>_R<1|2>.fastq.gz

Example: 26ARC1019-MYCNV_R1.fastq.gz, 26CGH796-MYCNV_R2.fastq.gz, etc.

The <sample_id> is everything before the first hyphen; <assay_tag> is the
short panel/assay code. Sample IDs may NOT contain whitespace or the
characters `,` `"` `\\` `/`.

Output schema
-------------
Writes the TSPIPE samplesheet schema:
    sample,fastq_1,fastq_2,sex,exclude

(Verify this matches the splitCsv block in workflows/tspipe.nf before
running. Add or rename columns via --extra-columns if your TSPIPE
expects something else.)

Sex
---
Three precedence levels (highest first):
    1. --sex-map TSV (2 cols: sample_id, sex)
    2. --default-sex (defaults to 'unknown')
    3. Falls back to 'unknown'

Samples with sex=unknown will hit the female PoN at TSPIPE inference time
per the 2026-05-16 wire-up.

Exclude pattern
---------------
By default skips any FASTQ whose sample_id matches glob `BNC*`. This is
because BNC normals and clinical samples often coexist in the same FASTQ
directory but should never be analyzed as tumor samples. Override with
--exclude-pattern or pass `--exclude-pattern ''` to disable.

Safety
------
- Aborts if any R1 has no paired R2.
- Aborts on malformed sample IDs.
- Warns about sex-map entries that don't match any FASTQ in the dir.
- Does NOT touch the filesystem outside the output CSV path.

Usage
-----
    # Simple case: all samples sex=unknown (warns)
    python3 tools/make_tspipe_samplesheet.py \\
        --fastq-dir /goast/hemat_data/targeted-seq-pipeline/sample_fastqs \\
        --output    /goast/hemat_data/nf-core-tspipe/tspipe_samplesheets/clinical_test_2026-05-24.csv

    # With a sex map
    python3 tools/make_tspipe_samplesheet.py \\
        --fastq-dir /goast/hemat_data/targeted-seq-pipeline/sample_fastqs \\
        --sex-map   /goast/hemat_data/nf-core-tspipe/tspipe_samplesheets/clinical_sex_map.tsv \\
        --output    /goast/hemat_data/nf-core-tspipe/tspipe_samplesheets/clinical_test_2026-05-24.csv

    # Sex-map format (2 cols, tab-separated, header optional):
    # 26ARC1019    female
    # 26ARC1020    male
    # ...
"""

import argparse
import csv
import fnmatch
import re
import sys
from pathlib import Path

# Sample IDs we accept: alphanumeric, underscores. Tight enough to catch
# typos but loose enough for any reasonable LIMS scheme. Adjust the
# character class if your IDs need hyphens or dots.
SAMPLE_ID_RE = re.compile(r"^[A-Za-z0-9_]+$")

VALID_SEX = {"male", "female", "unknown"}


def parse_filename(filename: str) -> tuple[str, str]:
    """
    Given '26ARC1019-MYCNV_R1.fastq.gz', return ('26ARC1019', 'R1').
    Raises ValueError on anything that doesn't fit the expected pattern.
    """
    for r_token in ("_R1.fastq.gz", "_R2.fastq.gz"):
        if filename.endswith(r_token):
            stem = filename[: -len(r_token)]
            mate = r_token.replace("_", "").replace(".fastq.gz", "")
            break
    else:
        raise ValueError(f"Unrecognized FASTQ suffix in {filename!r}")

    if "-" not in stem:
        raise ValueError(
            f"Sample stem {stem!r} (from {filename!r}) has no hyphen; "
            f"expected <sample_id>-<assay_tag>"
        )
    sample_id = stem.split("-", 1)[0]

    if not SAMPLE_ID_RE.match(sample_id):
        raise ValueError(
            f"Sample ID {sample_id!r} (from {filename!r}) has invalid "
            f"characters; allowed: [A-Za-z0-9_]"
        )
    return sample_id, mate


def load_sex_map(path: Path) -> dict[str, str]:
    """
    Load a 2-column TSV mapping sample_id -> sex.
    Tolerates a header row (first line ignored if its 2nd col isn't a valid sex).
    """
    mapping: dict[str, str] = {}
    with path.open() as f:
        for line_num, raw in enumerate(f, start=1):
            line = raw.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            cols = line.split("\t")
            if len(cols) < 2:
                sys.exit(f"ERROR: {path}:{line_num}: expected at least 2 tab-separated columns")
            sample_id, sex = cols[0].strip(), cols[1].strip().lower()
            if line_num == 1 and sex not in VALID_SEX:
                # Header row -- skip
                continue
            if sex not in VALID_SEX:
                sys.exit(
                    f"ERROR: {path}:{line_num}: sex {sex!r} not in {sorted(VALID_SEX)}"
                )
            if sample_id in mapping:
                sys.exit(f"ERROR: {path}:{line_num}: duplicate sample_id {sample_id!r}")
            mapping[sample_id] = sex
    return mapping


def build_rows(
    fastq_dir: Path,
    exclude_pattern: str,
    sex_map: dict[str, str],
    default_sex: str,
) -> tuple[list[dict], list[str]]:
    """
    Scan fastq_dir, pair R1/R2, apply sex map and exclude pattern.
    Returns (rows, excluded_sample_ids).
    """
    if not fastq_dir.is_dir():
        sys.exit(f"ERROR: not a directory: {fastq_dir}")

    r1_files = sorted(fastq_dir.glob("*_R1.fastq.gz"))
    if not r1_files:
        sys.exit(f"ERROR: no *_R1.fastq.gz files in {fastq_dir}")

    rows: list[dict] = []
    excluded: list[str] = []

    for r1 in r1_files:
        try:
            sample_id, _ = parse_filename(r1.name)
        except ValueError as exc:
            sys.exit(f"ERROR: {exc}")

        if exclude_pattern and fnmatch.fnmatch(sample_id, exclude_pattern):
            excluded.append(sample_id)
            continue

        r2 = r1.with_name(r1.name.replace("_R1.fastq.gz", "_R2.fastq.gz"))
        if not r2.exists():
            sys.exit(f"ERROR: R2 missing for {r1.name} (expected {r2})")

        sex = sex_map.get(sample_id, default_sex)
        rows.append({
            "sample":  sample_id,
            "fastq_1": str(r1.resolve()),
            "fastq_2": str(r2.resolve()),
            "sex":     sex,
            # All samples included by default; exclude=true is for
            # known-aberrant samples that shouldn't enter analysis.
            "exclude": "false",
        })

    return rows, excluded


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Generate a TSPIPE samplesheet from a FASTQ directory.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--fastq-dir", required=True, type=Path,
                    help="Directory of paired *_R{1,2}.fastq.gz files")
    ap.add_argument("--output", required=True, type=Path,
                    help="Output samplesheet CSV path")
    ap.add_argument("--sex-map", type=Path, default=None,
                    help="Optional 2-col TSV: sample_id<TAB>sex (header optional)")
    ap.add_argument("--default-sex", default="unknown", choices=sorted(VALID_SEX),
                    help="Sex value for samples not in --sex-map (default: unknown)")
    ap.add_argument("--exclude-pattern", default="BNC*",
                    help="fnmatch glob applied to sample_id; matching samples skipped "
                         "(default: BNC*; pass '' to disable)")
    args = ap.parse_args()

    sex_map: dict[str, str] = {}
    if args.sex_map:
        if not args.sex_map.is_file():
            sys.exit(f"ERROR: --sex-map not a file: {args.sex_map}")
        sex_map = load_sex_map(args.sex_map)

    rows, excluded = build_rows(
        args.fastq_dir,
        args.exclude_pattern,
        sex_map,
        args.default_sex,
    )

    if not rows:
        sys.exit(f"ERROR: no samples to write after exclusions")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["sample", "fastq_1", "fastq_2", "sex", "exclude"])
        writer.writeheader()
        writer.writerows(rows)

    # ---- Summary ----
    n_total = len(rows)
    n_male   = sum(1 for r in rows if r["sex"] == "male")
    n_female = sum(1 for r in rows if r["sex"] == "female")
    n_unknown = sum(1 for r in rows if r["sex"] == "unknown")
    n_excluded_listed = sum(1 for r in rows if r["exclude"] == "true")

    print(f"Wrote {n_total} samples to {args.output}")
    print(f"  by sex:        male={n_male}  female={n_female}  unknown={n_unknown}")
    print(f"  exclude=true:  {n_excluded_listed}")

    if excluded:
        print(f"  skipped (matched --exclude-pattern {args.exclude_pattern!r}):")
        for s in excluded:
            print(f"    - {s}")

    # Sex-map sanity check
    if sex_map:
        unmatched = [s for s in sex_map if s not in {r["sample"] for r in rows}]
        if unmatched:
            print(
                "\nWARNING: sex-map entries that didn't match any FASTQ in the dir:",
                file=sys.stderr,
            )
            for s in unmatched:
                print(f"  - {s} ({sex_map[s]})", file=sys.stderr)

    if n_unknown:
        print(
            f"\nNOTE: {n_unknown} sample(s) have sex='unknown'. Per the 2026-05-16 "
            f"wire-up, these will use the female PoN at TSPIPE CNV inference time. "
            f"chrX/chrY calls may be inaccurate for samples that are actually male.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
