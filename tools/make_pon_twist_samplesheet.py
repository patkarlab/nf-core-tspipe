#!/usr/bin/env python3
"""Generate the BUILD_PON_TWIST samplesheet from the staged normal BAMs.

Scans --bam-dir for *.final.bam, derives sample id (basename minus
.final.bam) and sex (Male/Female filename prefix), and writes the
7-column sheet consumed by bpt_check_samplesheet.py.

Females are written with include_in_pon=false and an explanatory note:
the 24 female normals were captured at 12-plex against the male 8-plex
arm and are excluded from reference construction until re-hybridised
(2026-09-01 audit memo). Per-sample steps still run on them.

Usage (from the repo root on gandalf):
    python tools/make_pon_twist_samplesheet.py \
        --out pon_samplesheets/twist_normals_48.csv
"""

import argparse
import csv
import glob
import os
import re
import sys

FEMALE_NOTE = "excluded_12plex_nonconforming_capture_2026-09-01"
COLS = ["sample", "sex", "bam", "fastq_1", "fastq_2", "include_in_pon", "note"]


def fail(msg):
    sys.stderr.write("[error] {0}\n".format(msg))
    sys.exit(1)


def natural_key(sample):
    m = re.match(r"(Male|Female)(\d+)", sample)
    if not m:
        return (2, 0, sample)
    return (0 if m.group(1) == "Male" else 1, int(m.group(2)), sample)


def main():
    ap = argparse.ArgumentParser(description="Generate BUILD_PON_TWIST samplesheet")
    ap.add_argument("--bam-dir", default="/goast/hemat_data/pon_twist/bams")
    ap.add_argument("--out", required=True)
    ap.add_argument("--expect-male", type=int, default=24)
    ap.add_argument("--expect-female", type=int, default=24)
    args = ap.parse_args()

    if not os.path.isdir(args.bam_dir):
        fail("bam dir not found: {0}".format(args.bam_dir))

    bams = sorted(glob.glob(os.path.join(args.bam_dir, "*.final.bam")))
    if not bams:
        fail("no *.final.bam files under {0}".format(args.bam_dir))

    rows = []
    n_male = 0
    n_female = 0
    for bam in bams:
        sample = os.path.basename(bam)[: -len(".final.bam")]
        if sample.startswith("Male"):
            sex = "male"
            n_male += 1
            include = "true"
            note = ""
        elif sample.startswith("Female"):
            sex = "female"
            n_female += 1
            include = "false"
            note = FEMALE_NOTE
        else:
            fail("cannot infer sex from filename: {0}".format(os.path.basename(bam)))
        rows.append({
            "sample": sample, "sex": sex, "bam": os.path.abspath(bam),
            "fastq_1": "", "fastq_2": "", "include_in_pon": include, "note": note,
        })

    if n_male != args.expect_male:
        fail("expected {0} male BAMs, found {1} (override with --expect-male)".format(
            args.expect_male, n_male))
    if n_female != args.expect_female:
        fail("expected {0} female BAMs, found {1} (override with --expect-female)".format(
            args.expect_female, n_female))

    rows.sort(key=lambda r: natural_key(r["sample"]))

    out_dir = os.path.dirname(args.out)
    if out_dir and not os.path.isdir(out_dir):
        fail("output directory does not exist: {0}".format(out_dir))

    with open(args.out, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLS, lineterminator="\n")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print("[ok] wrote {0}: {1} rows ({2} male included, {3} female excluded)".format(
        args.out, len(rows), n_male, n_female))
    print("[ok] first rows:")
    for r in rows[:3]:
        print("       {0},{1},...,{2}".format(r["sample"], r["sex"], r["include_in_pon"]))


if __name__ == "__main__":
    main()
