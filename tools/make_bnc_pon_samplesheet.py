#!/usr/bin/env python3
"""
Build a BUILD_PON samplesheet from a directory of BNC FASTQs.

Expected filename convention:
    BNC<N><F|M>-MYCNV_R<1|2>.fastq.gz
e.g., BNC1F-MYCNV_R1.fastq.gz, BNC10M-MYCNV_R2.fastq.gz.

Writes the schema documented in docs/usage_pon.md:
    sample,fastq_1,fastq_2,sex,exclude

Usage:
    python make_bnc_pon_samplesheet.py \
        --fastq-dir /goast/hemat_data/BNC_fastqs \
        --output /goast/hemat_data/nf-core-tspipe/pon_samplesheets/bnc_mycnv_25.csv

The script does NOT touch the filesystem outside the output CSV path,
and refuses to run if any expected R2 is missing for an R1 it finds.
"""

import argparse
import csv
import re
import sys
from pathlib import Path

# Strict sample-name regex. Captures the numeric ID and the sex letter.
# Examples it accepts:
#   BNC1F   -> id=1,  sex=F
#   BNC10M  -> id=10, sex=M
#   BNC25F  -> id=25, sex=F
# It rejects anything not matching exactly, so a typo in a new batch will
# fail loudly rather than be silently miscategorized.
SAMPLE_RE = re.compile(r"^(BNC\d+)([FM])$")

SEX_MAP = {"F": "female", "M": "male"}


def parse_sample_id_and_sex(filename: str) -> tuple[str, str]:
    """
    Given 'BNC10M-MYCNV_R1.fastq.gz', return ('BNC10M', 'male').

    Raises ValueError on anything that doesn't match the expected pattern.
    """
    # Strip the suffix '-MYCNV_R1.fastq.gz' or '-MYCNV_R2.fastq.gz'
    stem = filename
    for suffix in ("-MYCNV_R1.fastq.gz", "-MYCNV_R2.fastq.gz"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    else:
        raise ValueError(f"Unrecognized FASTQ suffix in {filename!r}")

    m = SAMPLE_RE.match(stem)
    if not m:
        raise ValueError(
            f"Sample name {stem!r} (from {filename!r}) does not match "
            f"the expected pattern BNC<N><F|M>"
        )
    sample_id, sex_letter = m.group(1) + m.group(2), m.group(2)
    return sample_id, SEX_MAP[sex_letter]


def build_rows(fastq_dir: Path) -> list[dict]:
    """
    Scan fastq_dir for *_R1.fastq.gz files, pair each with its matching _R2,
    parse sex from the sample name, and return a list of samplesheet rows.

    Aborts on the first missing R2 partner -- a half-paired sample silently
    flowing into BUILD_PON would corrupt the PoN.
    """
    if not fastq_dir.is_dir():
        sys.exit(f"ERROR: not a directory: {fastq_dir}")

    r1_files = sorted(fastq_dir.glob("*-MYCNV_R1.fastq.gz"))
    if not r1_files:
        sys.exit(
            f"ERROR: no files matching '*-MYCNV_R1.fastq.gz' in {fastq_dir}"
        )

    rows = []
    for r1 in r1_files:
        r2 = r1.with_name(r1.name.replace("_R1.fastq.gz", "_R2.fastq.gz"))
        if not r2.exists():
            sys.exit(f"ERROR: R2 missing for {r1.name} (expected {r2})")

        try:
            sample_id, sex = parse_sample_id_and_sex(r1.name)
        except ValueError as exc:
            sys.exit(f"ERROR: {exc}")

        rows.append(
            {
                "sample": sample_id,
                "fastq_1": str(r1.resolve()),
                "fastq_2": str(r2.resolve()),
                "sex": sex,
                # All current BNCs are real normals -- nothing to drop from
                # the PoN. Cell lines or known-aberrant normals would be
                # marked exclude=true here.
                "exclude": "false",
            }
        )

    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a BUILD_PON samplesheet from BNC FASTQ filenames."
    )
    parser.add_argument(
        "--fastq-dir",
        required=True,
        type=Path,
        help="Directory containing BNC*-MYCNV_R{1,2}.fastq.gz files.",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Output samplesheet CSV path.",
    )
    args = parser.parse_args()

    rows = build_rows(args.fastq_dir)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["sample", "fastq_1", "fastq_2", "sex", "exclude"]
    with args.output.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # Summary to stdout for the audit trail.
    n_total = len(rows)
    n_male = sum(1 for r in rows if r["sex"] == "male")
    n_female = sum(1 for r in rows if r["sex"] == "female")
    print(f"Wrote {n_total} samples to {args.output}")
    print(f"  male:   {n_male}")
    print(f"  female: {n_female}")
    if n_male < 10 or n_female < 10:
        print(
            "WARNING: at least one sex has <10 normals. The corresponding "
            "sex-specific PoN may be noisy; validate carefully.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
