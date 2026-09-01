#!/usr/bin/env python3
"""Aggregate per-sample GATK CollectAllelicCounts output into the per-site
BAF background table for the Twist myeloid panel.

Cohort semantics (handoff decision 2, parameterised):
  --cohort male : samples with sex==male AND include_in_pon==true
  --cohort all  : every samplesheet row

Resolution is PER BASE POSITION, not per probe window: a het SNP shows
ALT fraction ~0.5 at its own coordinate but ~0.004 if diluted across a
120 bp window sum, which would make het detection impossible. The site
universe is every 1-based position inside the --snp-bed intervals
(374 x 120 bp probe windows -> ~45k positions), so positions with zero
coverage in every sample still appear with n_pass_depth=0.

Per-position statistics over cohort samples passing --min-depth:
  n_pass_depth, median_depth, median_alt_fraction, mad_alt_fraction,
  n_het_like (ALT fraction in [0.2, 0.8]), informative flag
  (n_het_like >= --min-het-samples). The informative subset is the
  empirically het-capable SNP catalog for downstream BAF work.

GATK allelicCounts format: '@' header lines, then a column header
starting with CONTIG, then rows CONTIG POSITION REF_COUNT ALT_COUNT
REF_NUCLEOTIDE ALT_NUCLEOTIDE.

Python 3.6 compatible.
"""

import argparse
import csv
import hashlib
import os
import statistics
import sys
from datetime import datetime

SUFFIX = ".allelicCounts.tsv"


def fail(msg):
    sys.stderr.write("[error] {0}\n".format(msg))
    sys.exit(1)


def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_sheet(path):
    info = {}
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            info[row["sample"]] = {
                "sex": row["sex"].strip().lower(),
                "include": row["include_in_pon"].strip().lower() == "true",
            }
    if not info:
        fail("no rows in samplesheet: {0}".format(path))
    return info


def read_sites(path):
    """Enumerate every 1-based position in the BED intervals.

    Returns (sites, index) where sites is an ordered, de-duplicated list
    of (contig, pos1) and index maps (contig, pos1) -> list offset.
    """
    sites = []
    index = {}
    n_intervals = 0
    with open(path) as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line or line.startswith(("#", "track", "browser")):
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                fail("malformed BED line in {0}: {1}".format(path, line))
            contig, start, end = parts[0], int(parts[1]), int(parts[2])
            if end <= start:
                fail("empty/negative interval in {0}: {1}".format(path, line))
            n_intervals += 1
            for pos1 in range(start + 1, end + 1):   # half-open BED -> 1-based
                key = (contig, pos1)
                if key not in index:
                    index[key] = len(sites)
                    sites.append(key)
    if not sites:
        fail("no intervals in {0}".format(path))
    return sites, index, n_intervals


def parse_allelic(path, index, n_sites):
    """Return (ref, alt, n_outside) count arrays over the site universe."""
    ref = [0] * n_sites
    alt = [0] * n_sites
    n_outside = 0
    header_seen = False
    with open(path) as fh:
        for line in fh:
            if line.startswith("@"):
                continue
            parts = line.rstrip("\n").split("\t")
            if not header_seen:
                if parts and parts[0] == "CONTIG":
                    header_seen = True
                    continue
                fail("unexpected pre-header line in {0}: {1}".format(path, line[:80]))
            if len(parts) < 4:
                continue
            try:
                pos = int(parts[1])
                r_n = int(parts[2])
                a_n = int(parts[3])
            except ValueError:
                fail("malformed record in {0}: {1}".format(path, line.rstrip()[:120]))
            idx = index.get((parts[0], pos))
            if idx is None:
                n_outside += 1
                continue
            ref[idx] += r_n
            alt[idx] += a_n
    if not header_seen:
        fail("no CONTIG header found in {0}".format(path))
    return ref, alt, n_outside


def mad(values, med):
    return statistics.median([abs(v - med) for v in values])


def main():
    ap = argparse.ArgumentParser(description="Aggregate BAF background table")
    ap.add_argument("--sheet", required=True, help="validated samplesheet CSV")
    ap.add_argument("--snp-bed", required=True, help="snp_sites.baf.bed")
    ap.add_argument("--cohort", required=True, choices=["male", "all"])
    ap.add_argument("--min-depth", type=int, default=20)
    ap.add_argument("--min-het-samples", type=int, default=3)
    ap.add_argument("--out", required=True)
    ap.add_argument("files", nargs="+", help="*.allelicCounts.tsv")
    args = ap.parse_args()

    sheet = read_sheet(args.sheet)
    sites, index, n_intervals = read_sites(args.snp_bed)
    n_sites = len(sites)
    print("[ok] site universe: {0} positions from {1} intervals".format(
        n_sites, n_intervals))

    cohort_files = []
    skipped = []
    for path in sorted(args.files):
        base = os.path.basename(path)
        if not base.endswith(SUFFIX):
            fail("unexpected filename (want *{0}): {1}".format(SUFFIX, base))
        sample = base[: -len(SUFFIX)]
        if sample not in sheet:
            fail("sample '{0}' (from {1}) not present in samplesheet".format(sample, base))
        rec = sheet[sample]
        if args.cohort == "male" and not (rec["sex"] == "male" and rec["include"]):
            skipped.append(sample)
            continue
        cohort_files.append((sample, path))

    if len(cohort_files) < 2:
        fail("cohort '{0}' resolved to {1} samples; need >= 2".format(
            args.cohort, len(cohort_files)))

    print("[ok] cohort={0}: {1} samples in, {2} skipped".format(
        args.cohort, len(cohort_files), len(skipped)))

    depth = [[] for _ in range(n_sites)]   # per position: depths passing min-depth
    afrac = [[] for _ in range(n_sites)]
    total_outside = 0
    for sample, path in cohort_files:
        ref, alt, n_outside = parse_allelic(path, index, n_sites)
        total_outside += n_outside
        for i in range(n_sites):
            d = ref[i] + alt[i]
            if d >= args.min_depth:
                depth[i].append(d)
                afrac[i].append(alt[i] / float(d))

    if total_outside:
        print("[warn] {0} allelic-count records fell outside the snp-bed "
              "catalog; check BED/interval conversion".format(total_outside))

    cohort_ids = [s for s, _ in cohort_files]
    with open(args.out, "w") as out:
        out.write("# baf_background.tsv -- Twist myeloid panel (TE-99430185)\n")
        out.write("# generated: {0}\n".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        out.write("# cohort: {0} (n={1}); min_depth={2}; min_het_samples={3}; het_band=0.20-0.80\n".format(
            args.cohort, len(cohort_ids), args.min_depth, args.min_het_samples))
        out.write("# snp_bed: {0} (md5 {1}; {2} intervals; {3} positions)\n".format(
            os.path.basename(args.snp_bed), md5_of(args.snp_bed), n_intervals, n_sites))
        out.write("# samples: {0}\n".format(",".join(cohort_ids)))
        out.write("contig\tposition\tn_cohort\tn_pass_depth\tmedian_depth\t"
                  "median_alt_fraction\tmad_alt_fraction\tn_het_like\tinformative\n")
        n_informative = 0
        n_covered = 0
        for i, (contig, pos1) in enumerate(sites):
            ds = depth[i]
            fs = afrac[i]
            if ds:
                n_covered += 1
                med_d = statistics.median(ds)
                med_f = statistics.median(fs)
                mad_f = mad(fs, med_f)
                n_het = sum(1 for f in fs if 0.2 <= f <= 0.8)
                med_d_s = "{0:.1f}".format(med_d)
                med_f_s = "{0:.4f}".format(med_f)
                mad_f_s = "{0:.4f}".format(mad_f)
            else:
                n_het = 0
                med_d_s, med_f_s, mad_f_s = "0", "NA", "NA"
            informative = n_het >= args.min_het_samples
            if informative:
                n_informative += 1
            out.write("{0}\t{1}\t{2}\t{3}\t{4}\t{5}\t{6}\t{7}\t{8}\n".format(
                contig, pos1, len(cohort_ids), len(ds),
                med_d_s, med_f_s, mad_f_s, n_het,
                "true" if informative else "false"))

    print("[ok] wrote {0}: {1} positions, {2} with coverage, {3} informative "
          "(>= {4} samples with ALT fraction 0.2-0.8)".format(
              args.out, n_sites, n_covered, n_informative, args.min_het_samples))


if __name__ == "__main__":
    main()
