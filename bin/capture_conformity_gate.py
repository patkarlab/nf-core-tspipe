#!/usr/bin/env python3
"""Capture-conformity gate for Twist myeloid PoN normals. REPORT-ONLY in
v1: no sample is dropped; the merge report is a review artifact.

Sentinels (2026-09-01 survey): NPM1_exon_11 and JAK2_exon_15 mean depth
separate conforming 8-plex/16 hr captures (>= ~300x) from the failed
12-plex arm (~47x); BAM-wide mean insert size flags degraded libraries
(watch item Male12 at 131.8 bp).

--mode sample:
    Extracts the two sentinel exons from targets.exonwise.bed (exact
    match on column 4), runs mosdepth with --flag 772 (duplicates
    INCLUDED, lab convention; never 1796) over them, pulls mean insert
    size from samtools stats, writes a one-row TSV.

--mode merge:
    Joins per-sample rows with the validated samplesheet, applies
    thresholds, writes conformity_report.tsv with PASS/WARN status.

Python 3.6 compatible (subprocess.run with stdout/stderr=PIPE and
universal_newlines=True; no capture_output).
"""

import argparse
import csv
import gzip
import os
import re
import subprocess
import sys
from datetime import datetime

LABELS = ["NPM1_exon_11", "JAK2_exon_15"]
ROW_COLS = ["sample", "npm1_exon_11_mean", "jak2_exon_15_mean", "insert_size_mean"]


def fail(msg):
    sys.stderr.write("[error] {0}\n".format(msg))
    sys.exit(1)


def run(cmd):
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True)
    if proc.returncode != 0:
        fail("command failed ({0}): {1}\n{2}".format(
            proc.returncode, " ".join(cmd), proc.stderr.strip()[-2000:]))
    return proc.stdout


# ---------------------------------------------------------------- sample --

def build_gate_bed(exonwise, out_bed):
    found = {label: 0 for label in LABELS}
    with open(exonwise) as fh, open(out_bed, "w") as out:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 4 and parts[3] in found:
                out.write(line if line.endswith("\n") else line + "\n")
                found[parts[3]] += 1
    missing = [label for label, n in found.items() if n == 0]
    if missing:
        fail("labels not found in {0}: {1}".format(exonwise, ",".join(missing)))
    return found


def parse_regions(prefix):
    """Length-weighted mean depth per sentinel label from mosdepth output."""
    path = prefix + ".regions.bed.gz"
    if not os.path.isfile(path):
        fail("mosdepth output missing: {0}".format(path))
    acc = {label: [0.0, 0] for label in LABELS}   # label -> [sum(mean*len), sum(len)]
    with gzip.open(path, "rt") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 5:
                continue
            label = parts[3]
            if label in acc:
                length = int(parts[2]) - int(parts[1])
                acc[label][0] += float(parts[4]) * length
                acc[label][1] += length
    means = {}
    for label in LABELS:
        wsum, lsum = acc[label]
        if lsum == 0:
            fail("no mosdepth rows for {0}".format(label))
        means[label] = wsum / lsum
    return means


def insert_size_mean(bam, threads):
    stdout = run(["samtools", "stats", "-@", str(threads), bam])
    for line in stdout.splitlines():
        if line.startswith("SN\tinsert size average:"):
            return float(line.split("\t")[2])
    fail("insert size average not found in samtools stats output for {0}".format(bam))


def mode_sample(args):
    gate_bed = "gate_{0}.bed".format(args.sample)
    found = build_gate_bed(args.exonwise, gate_bed)
    print("[ok] {0}: gate BED rows {1}".format(
        args.sample, ", ".join("{0}={1}".format(k, found[k]) for k in LABELS)))

    prefix = "gate_{0}".format(args.sample)
    run(["mosdepth", "-t", str(args.threads), "--flag", "772", "--no-per-base",
         "--by", gate_bed, prefix, args.bam])
    means = parse_regions(prefix)
    ins = insert_size_mean(args.bam, args.threads)

    with open(args.out, "w") as out:
        out.write("\t".join(ROW_COLS) + "\n")
        out.write("{0}\t{1:.1f}\t{2:.1f}\t{3:.1f}\n".format(
            args.sample, means["NPM1_exon_11"], means["JAK2_exon_15"], ins))
    print("[ok] {0}: NPM1_exon_11={1:.1f}x JAK2_exon_15={2:.1f}x insert={3:.1f}bp".format(
        args.sample, means["NPM1_exon_11"], means["JAK2_exon_15"], ins))


# ----------------------------------------------------------------- merge --

def natural_key(sample):
    m = re.match(r"([A-Za-z]+)(\d+)", sample)
    if m:
        return (m.group(1), int(m.group(2)), sample)
    return (sample, 0, sample)


def mode_merge(args):
    sheet = {}
    with open(args.sheet, newline="") as fh:
        for row in csv.DictReader(fh):
            sheet[row["sample"]] = row
    if not sheet:
        fail("no rows in samplesheet: {0}".format(args.sheet))

    rows = {}
    for path in args.files:
        with open(path) as fh:
            reader = csv.DictReader(fh, delimiter="\t")
            for r in reader:
                rows[r["sample"]] = r
    missing = sorted(set(sheet) - set(rows))
    if missing:
        fail("conformity rows missing for: {0}".format(",".join(missing)))
    extra = sorted(set(rows) - set(sheet))
    if extra:
        fail("conformity rows for samples not in sheet: {0}".format(",".join(extra)))

    def sort_key(sample):
        sex = sheet[sample]["sex"]
        return (0 if sex == "male" else 1,) + natural_key(sample)

    n_pass = 0
    n_warn = 0
    with open(args.out, "w") as out:
        out.write("# conformity_report.tsv -- REPORT-ONLY (no samples dropped)\n")
        out.write("# generated: {0}\n".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        out.write("# thresholds: npm1_min={0} jak2_min={1} insert_min={2}\n".format(
            args.npm1_min, args.jak2_min, args.insert_min))
        out.write("sample\tsex\tinclude_in_pon\tnpm1_exon_11_mean\tjak2_exon_15_mean\t"
                  "insert_size_mean\tstatus\tnote\n")
        for sample in sorted(rows, key=sort_key):
            r = rows[sample]
            s = sheet[sample]
            npm1 = float(r["npm1_exon_11_mean"])
            jak2 = float(r["jak2_exon_15_mean"])
            ins = float(r["insert_size_mean"])
            reasons = []
            if npm1 < args.npm1_min:
                reasons.append("npm1_exon_11 {0:.1f}<{1}".format(npm1, args.npm1_min))
            if jak2 < args.jak2_min:
                reasons.append("jak2_exon_15 {0:.1f}<{1}".format(jak2, args.jak2_min))
            if ins < args.insert_min:
                reasons.append("insert {0:.1f}<{1}".format(ins, args.insert_min))
            status = "PASS" if not reasons else "WARN:" + ";".join(reasons)
            if reasons:
                n_warn += 1
            else:
                n_pass += 1
            out.write("{0}\t{1}\t{2}\t{3:.1f}\t{4:.1f}\t{5:.1f}\t{6}\t{7}\n".format(
                sample, s["sex"], s["include_in_pon"], npm1, jak2, ins,
                status, s.get("note", "")))

    print("[ok] conformity report: {0} PASS, {1} WARN -> {2}".format(
        n_pass, n_warn, args.out))
    if n_warn:
        print("[warn] WARN status is informational in v1; review before any exclusion decision")


def main():
    ap = argparse.ArgumentParser(description="Capture conformity gate (report-only v1)")
    ap.add_argument("--mode", required=True, choices=["sample", "merge"])
    # sample mode
    ap.add_argument("--bam")
    ap.add_argument("--sample")
    ap.add_argument("--exonwise")
    ap.add_argument("--threads", type=int, default=4)
    # merge mode
    ap.add_argument("--sheet")
    ap.add_argument("--npm1-min", type=float, default=100)
    ap.add_argument("--jak2-min", type=float, default=100)
    ap.add_argument("--insert-min", type=float, default=150)
    ap.add_argument("--out", required=True)
    ap.add_argument("files", nargs="*", help="merge mode: per-sample *.conformity.tsv")
    args = ap.parse_args()

    if args.mode == "sample":
        for name in ("bam", "sample", "exonwise"):
            if not getattr(args, name):
                fail("--{0} is required in sample mode".format(name))
        if not os.path.isfile(args.bam):
            fail("bam not found: {0}".format(args.bam))
        mode_sample(args)
    else:
        if not args.sheet:
            fail("--sheet is required in merge mode")
        if not args.files:
            fail("merge mode needs at least one *.conformity.tsv")
        mode_merge(args)


if __name__ == "__main__":
    main()
