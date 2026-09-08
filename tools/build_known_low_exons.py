#!/usr/bin/env python3
"""tools/build_known_low_exons.py -- KNOWN_LOW_V1

Build assets/<panel>/known_low_exons.tsv from the normal cohort's per-exon
coverage tables (<sample>_exon_coverage.tsv from PARSE_EXON_COVERAGE).

An exon is a known low-capture exon of the panel when its coverage is below
--threshold in at least --min-frac of the included normals. Such exons are
panel-design facts (GC-rich first exons, mostly) and the sample report lists
them as known panel limitations rather than downgrading every sample for them.

Inputs
  --coverage DIR/GLOB   repeatable; every *_exon_coverage.tsv found is a candidate
  --normals CSV         normals_twist.csv (sample, ..., exclude); only rows with
                        exclude == false are used. Sample ids are matched by
                        prefix so 'Female1-TwistMy' matches 'Female1-TwistMyRun2'.
                        Without --normals every table found is used.
Outputs
  --out FILE            the asset (provenance header + one row per known low exon)
  --stats FILE          optional: cohort statistics for every exon

Pure stdlib; python >= 3.6.
"""

import argparse
import csv
import glob
import hashlib
import os
import statistics
import sys
import time


def read_normals(path):
    keep = []
    with open(path) as fh:
        for r in csv.DictReader(fh):
            if (r.get("exclude", "false") or "false").strip().lower() in ("false", "0", "no", ""):
                keep.append(r["sample"].strip())
    return keep


def sample_id(path):
    return os.path.basename(path).replace("_exon_coverage.tsv", "")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--coverage", action="append", required=True, help="directory or glob; repeatable")
    ap.add_argument("--normals", default=None, help="normals CSV with an exclude column")
    ap.add_argument("--threshold", type=float, default=100.0, help="exon is low below this coverage")
    ap.add_argument("--min-frac", type=float, default=0.5, help="fraction of normals below threshold to call the exon known-low")
    ap.add_argument("--out", required=True)
    ap.add_argument("--stats", default=None)
    args = ap.parse_args()

    files = []
    for c in args.coverage:
        pattern = os.path.join(c, "**", "*_exon_coverage.tsv") if os.path.isdir(c) else c
        files += glob.glob(pattern, recursive=True)
    files = sorted(set(files))
    if not files:
        sys.exit("no *_exon_coverage.tsv found under: %s" % ", ".join(args.coverage))

    if args.normals:
        wanted = read_normals(args.normals)
        chosen = {}
        for f in files:
            sid = sample_id(f)
            for w in wanted:
                if sid == w or sid.startswith(w):
                    chosen.setdefault(w, f)
        missing = [w for w in wanted if w not in chosen]
        if missing:
            print("[warn] no coverage table for %d included normal(s): %s" % (len(missing), ", ".join(missing)))
        files = [chosen[w] for w in wanted if w in chosen]
    print("[ok] %d normal coverage tables" % len(files))

    cov = {}   # (gene, exon, chr, start, end) -> [values]
    order = []
    for f in files:
        with open(f) as fh:
            for r in csv.DictReader(fh, delimiter="\t"):
                key = (r["Gene"], r["Exon"], r["Chr"], r["Start"], r["End"])
                try:
                    v = float(r["Mean_Coverage"])
                except (KeyError, ValueError):
                    continue
                if key not in cov:
                    cov[key] = []
                    order.append(key)
                cov[key].append(v)

    n = len(files)
    rows = []
    for key in order:
        vals = cov[key]
        n_low = sum(1 for v in vals if v < args.threshold)
        rows.append({
            "gene": key[0], "exon": key[1], "chr": key[2], "start": key[3], "end": key[4],
            "n_normals": len(vals), "n_below": n_low, "frac_below": round(n_low / float(len(vals)), 3),
            "median_cov": round(statistics.median(vals), 1), "min_cov": round(min(vals), 1), "max_cov": round(max(vals), 1),
        })
    known = [r for r in rows if r["frac_below"] >= args.min_frac]

    digest = hashlib.md5()
    for f in files:
        digest.update(open(f, "rb").read())
    header = [
        "# known_low_exons.tsv -- KNOWN_LOW_V1",
        "# built %s by tools/build_known_low_exons.py" % time.strftime("%Y-%m-%d %H:%M"),
        "# rule: exon coverage < %.0fx in >= %.0f%% of included normals" % (args.threshold, args.min_frac * 100),
        "# normals: %d (%s)" % (n, ", ".join(sample_id(f) for f in files)),
        "# normals md5: %s" % digest.hexdigest(),
    ]
    cols = ["gene", "exon", "chr", "start", "end", "n_normals", "n_below", "frac_below", "median_cov", "min_cov", "max_cov"]
    with open(args.out, "w") as out:
        out.write("\n".join(header) + "\n")
        out.write("\t".join(cols) + "\n")
        for r in known:
            out.write("\t".join(str(r[c]) for c in cols) + "\n")
    print("[ok] %d known low-capture exon(s) -> %s" % (len(known), args.out))
    for r in known:
        print("     %-10s %-8s median %6.0fx  below in %d/%d" % (r["gene"], r["exon"], r["median_cov"], r["n_below"], r["n_normals"]))

    if args.stats:
        with open(args.stats, "w") as out:
            out.write("\t".join(cols) + "\n")
            for r in rows:
                out.write("\t".join(str(r[c]) for c in cols) + "\n")
        print("[ok] cohort statistics for %d exons -> %s" % (len(rows), args.stats))

    # borderline report: exons low in some normals but under the fraction
    border = [r for r in rows if 0 < r["frac_below"] < args.min_frac]
    if border:
        print("[info] %d exon(s) below %.0fx in some normals but under the %.0f%% rule:" % (len(border), args.threshold, args.min_frac * 100))
        for r in sorted(border, key=lambda x: -x["frac_below"])[:15]:
            print("     %-10s %-8s median %6.0fx  below in %d/%d" % (r["gene"], r["exon"], r["median_cov"], r["n_below"], r["n_normals"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
