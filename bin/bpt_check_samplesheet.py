#!/usr/bin/env python3
"""Validate the BUILD_PON_TWIST samplesheet and emit a normalised copy.

Input columns : sample,sex,bam,fastq_1,fastq_2,include_in_pon,note
Output columns: sample,sex,bam,bai,include_in_pon,note

Rules (v1):
  - sample ids unique, non-empty
  - sex in {male, female}
  - bam must exist, be non-empty, end in .bam; index resolved as
    <bam>.bai or <bam minus .bam>.bai
  - fastq_1 / fastq_2 must be EMPTY (FASTQ rows are not wired in
    scaffold v1; hard error, not a warning)
  - include_in_pon in {true, false, ''}; empty defaults to true
  - duplicate bam paths rejected

Prints per-sex / per-include counts so stratum population is visible at
validation time (a selected stratum with 0 included samples will also
fail loudly at runtime inside the workflow).
"""

import argparse
import csv
import os
import re
import sys

REQUIRED = ["sample", "sex", "bam", "fastq_1", "fastq_2", "include_in_pon", "note"]
OUT_COLS = ["sample", "sex", "bam", "bai", "include_in_pon", "note"]


def fail(msg):
    sys.stderr.write("[error] {0}\n".format(msg))
    sys.exit(1)


def resolve_bai(bam):
    cand1 = bam + ".bai"
    cand2 = re.sub(r"\.bam$", ".bai", bam)
    if os.path.isfile(cand1):
        return cand1
    if os.path.isfile(cand2):
        return cand2
    return None


def main():
    ap = argparse.ArgumentParser(description="Validate BUILD_PON_TWIST samplesheet")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    if not os.path.isfile(args.input):
        fail("samplesheet not found: {0}".format(args.input))

    with open(args.input, newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            fail("samplesheet is empty: {0}".format(args.input))
        header = [c.strip() for c in reader.fieldnames]
        missing = [c for c in REQUIRED if c not in header]
        if missing:
            fail("missing required columns: {0} (header: {1})".format(
                ",".join(missing), ",".join(header)))
        extra = [c for c in header if c not in REQUIRED]
        if extra:
            fail("unexpected columns: {0}".format(",".join(extra)))
        rows = list(reader)

    if not rows:
        fail("samplesheet has a header but no rows")

    seen_ids = set()
    seen_bams = set()
    out_rows = []
    counts = {}   # (sex, include) -> n

    for i, row in enumerate(rows, start=2):   # line numbers incl. header
        sample = (row.get("sample") or "").strip()
        sex = (row.get("sex") or "").strip().lower()
        bam = (row.get("bam") or "").strip()
        fq1 = (row.get("fastq_1") or "").strip()
        fq2 = (row.get("fastq_2") or "").strip()
        inc = (row.get("include_in_pon") or "").strip().lower()
        note = (row.get("note") or "").strip()

        if not sample:
            fail("line {0}: empty sample id".format(i))
        if sample in seen_ids:
            fail("line {0}: duplicate sample id '{1}'".format(i, sample))
        seen_ids.add(sample)

        if sex not in ("male", "female"):
            fail("line {0} ({1}): sex must be male or female, got '{2}'".format(i, sample, sex))

        if fq1 or fq2:
            fail("line {0} ({1}): FASTQ rows are not wired in scaffold v1; "
                 "supply an aligned BAM instead".format(i, sample))

        if not bam:
            fail("line {0} ({1}): bam column is empty".format(i, sample))
        if not bam.endswith(".bam"):
            fail("line {0} ({1}): bam does not end in .bam: {2}".format(i, sample, bam))
        if not os.path.isfile(bam):
            fail("line {0} ({1}): bam not found: {2}".format(i, sample, bam))
        if os.path.getsize(bam) == 0:
            fail("line {0} ({1}): bam is zero-length: {2}".format(i, sample, bam))
        if bam in seen_bams:
            fail("line {0} ({1}): duplicate bam path: {2}".format(i, sample, bam))
        seen_bams.add(bam)

        bai = resolve_bai(bam)
        if bai is None:
            fail("line {0} ({1}): no index found ({2}.bai or .bai twin)".format(i, sample, bam))

        if inc == "":
            inc = "true"
        if inc not in ("true", "false"):
            fail("line {0} ({1}): include_in_pon must be true/false/empty, got '{2}'".format(
                i, sample, inc))

        key = (sex, inc)
        counts[key] = counts.get(key, 0) + 1
        out_rows.append({
            "sample": sample, "sex": sex, "bam": bam, "bai": bai,
            "include_in_pon": inc, "note": note,
        })

    with open(args.output, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=OUT_COLS, lineterminator="\n")
        writer.writeheader()
        for r in out_rows:
            writer.writerow(r)

    n_m_inc = counts.get(("male", "true"), 0)
    n_m_exc = counts.get(("male", "false"), 0)
    n_f_inc = counts.get(("female", "true"), 0)
    n_f_exc = counts.get(("female", "false"), 0)
    print("[ok] samplesheet valid: {0} rows -> {1}".format(len(out_rows), args.output))
    print("[ok]   male:   {0} included in PoN, {1} excluded".format(n_m_inc, n_m_exc))
    print("[ok]   female: {0} included in PoN, {1} excluded".format(n_f_inc, n_f_exc))
    if n_f_inc == 0:
        print("[ok]   female stratum has no included samples "
              "(expected until re-hybridised female normals land)")


if __name__ == "__main__":
    main()
