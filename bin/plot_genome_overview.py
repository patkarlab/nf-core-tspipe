#!/usr/bin/env python3
"""
bin/plot_genome_overview.py  (GENOME_OVERVIEW_V1)

Genome-wide figure from the same inputs as the chromosome pages:
  panel 1  per-bin log2 (consensus JSON tracks.cnr_bins) as faint points and
           one median line per chromosome ARM (p | q at the centromere): red when the median is below
           --loss (-0.25), green above --gain (+0.20), dark grey otherwise;
           the chromosome's median value printed under its label
  panel 2  BAF from the allelic counts (grey balanced, green deviated)
  panel 3  PURPLE copy number and minor allele per segment (when present)
Python 3.6 / matplotlib 3.2 safe. Writes --out (PNG).
"""

import argparse
import bisect
import csv
import gzip
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

CHROMS = ["chr%d" % i for i in range(1, 23)] + ["chrX", "chrY"]
CHROM_LEN = {"chr1": 248956422, "chr2": 242193529, "chr3": 198295559, "chr4": 190214555, "chr5": 181538259,
             "chr6": 170805979, "chr7": 159345973, "chr8": 145138636, "chr9": 138394717, "chr10": 133797422,
             "chr11": 135086622, "chr12": 133275309, "chr13": 114364328, "chr14": 107043718, "chr15": 101991189,
             "chr16": 90338345, "chr17": 83257441, "chr18": 80373285, "chr19": 58617616, "chr20": 64444167,
             "chr21": 46709983, "chr22": 50818468, "chrX": 156040895, "chrY": 57227415}
CENTROMERE = {"chr1": 123.4, "chr2": 93.9, "chr3": 90.9, "chr4": 50.0, "chr5": 48.8, "chr6": 59.8, "chr7": 60.1,
              "chr8": 45.2, "chr9": 43.0, "chr10": 39.8, "chr11": 53.4, "chr12": 35.5, "chr13": 17.7, "chr14": 17.2,
              "chr15": 19.0, "chr16": 36.8, "chr17": 25.1, "chr18": 18.5, "chr19": 26.2, "chr20": 28.1, "chr21": 12.0,
              "chr22": 15.0, "chrX": 60.6, "chrY": 10.4}
C_NEUT, C_LOSS, C_GAIN = "#2f2f2f", "#c0392b", "#2e8b57"
C_HET, C_DEV = "0.55", "#2e8b57"


def norm_chrom(c):
    return c if c.startswith("chr") else "chr" + c


def opener(p):
    return gzip.open(p, "rt") if p.endswith(".gz") else open(p)


def offsets():
    off, x = {}, 0
    for c in CHROMS:
        off[c] = x
        x += CHROM_LEN[c]
    return off, x


def median(v):
    v = sorted(v)
    n = len(v)
    return v[n // 2] if n % 2 else 0.5 * (v[n // 2 - 1] + v[n // 2])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample", required=True)
    ap.add_argument("--consensus-json", required=True)
    ap.add_argument("--allelic", default=None)
    ap.add_argument("--purple-dir", default=None)
    ap.add_argument("--min-depth", type=int, default=100)
    ap.add_argument("--loss", type=float, default=-0.25)
    ap.add_argument("--gain", type=float, default=0.20)
    ap.add_argument("--baf-band", type=float, default=0.15)
    ap.add_argument("--log2-lim", type=float, default=1.5)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    off, total = offsets()
    L = args.log2_lim

    with open(args.consensus_json) as fh:
        d = json.load(fh)
    bins = {}
    for b in d.get("tracks", {}).get("cnr_bins", []):
        c = norm_chrom(b[0])
        if c in off:
            try:
                bins.setdefault(c, []).append((int(b[1]), float(b[4])))
            except (ValueError, TypeError):
                pass
    sites = {}
    if args.allelic and os.path.isfile(args.allelic):
        with opener(args.allelic) as fh:
            for line in fh:
                if line.startswith("@") or line.startswith("CONTIG"):
                    continue
                p = line.rstrip("\n").split("\t")
                if len(p) < 4:
                    continue
                try:
                    ref, alt = int(p[2]), int(p[3])
                except ValueError:
                    continue
                dp = ref + alt
                if dp < args.min_depth:
                    continue
                af = alt / float(dp)
                if 0.10 <= af <= 0.90:
                    c = norm_chrom(p[0])
                    if c in off:
                        sites.setdefault(c, []).append((int(p[1]), af))
    segs = []
    pur = {}
    if args.purple_dir and os.path.isdir(args.purple_dir):
        ps = os.path.join(args.purple_dir, "%s.purple.cnv.somatic.tsv" % args.sample)
        if os.path.isfile(ps):
            with open(ps) as fh:
                for r in csv.DictReader(fh, delimiter="\t"):
                    try:
                        mn = r.get("minorAlleleCopyNumber")
                        segs.append((norm_chrom(r["chromosome"]), int(r["start"]), int(r["end"]), float(r["copyNumber"]),
                                     float(mn) if mn not in (None, "", "NA") else None))
                    except (KeyError, ValueError):
                        pass
        pp = os.path.join(args.purple_dir, "%s.purple.purity.tsv" % args.sample)
        if os.path.isfile(pp):
            with open(pp) as fh:
                rows = list(csv.DictReader(fh, delimiter="\t"))
                pur = rows[0] if rows else {}

    n_pan = 3 if segs else 2
    fig, axes = plt.subplots(n_pan, 1, figsize=(18, 7.5 if segs else 5.5), sharex=True,
                             gridspec_kw={"height_ratios": [1.3, 1.0, 1.0][:n_pan], "hspace": 0.08})
    a0, a1 = axes[0], axes[1]
    for c in CHROMS:
        for a in axes:
            a.axvline(off[c], color="0.85", lw=0.6, zorder=0)
    # bins as faint points, one median line per chromosome ARM (p | q at the centromere)
    medians = {}
    for c in CHROMS:
        pts = bins.get(c, [])
        if not pts:
            continue
        xs = [off[c] + p for p, _ in pts]
        ys = [max(-L, min(L, v)) for _, v in pts]
        a0.scatter(xs, ys, s=4, color="0.6", alpha=0.45, linewidths=0, zorder=2)
        cen = int(CENTROMERE[c] * 1e6)
        for arm, lo, hi in (("p", 0, cen), ("q", cen, CHROM_LEN[c])):
            vals = [v for p, v in pts if lo <= p < hi]
            if len(vals) < 3:
                continue
            m = median(vals)
            medians[c + arm] = m
            col = C_LOSS if m < args.loss else (C_GAIN if m > args.gain else C_NEUT)
            a0.plot([off[c] + lo, off[c] + hi], [max(-L, min(L, m))] * 2, color=col, lw=2.6, solid_capstyle="butt", zorder=4)
        a0.axvline(off[c] + cen, color="0.8", lw=0.5, ls=":", zorder=1)
    a0.axhline(0, color="black", lw=0.7)
    for y in (0.5, -0.5):
        a0.axhline(y, color="red", lw=0.7, ls="--", zorder=1)
    a0.set_ylim(-L - 0.1, L + 0.1)
    a0.set_ylabel("log2 ratio per bin\narm median (p|q): red < %.2f, green > %.2f" % (args.loss, args.gain))
    # BAF
    bx, by, bc = [], [], []
    for c in CHROMS:
        for p, af in sites.get(c, []):
            bx.append(off[c] + p); by.append(af); bc.append(C_HET if abs(af - 0.5) < args.baf_band else C_DEV)
    a1.scatter(bx, by, s=6, c=bc, alpha=0.8, linewidths=0, zorder=2)
    a1.axhline(0.5, color="black", lw=0.7); a1.set_ylim(0, 1)
    a1.set_ylabel("BAF (%d sites)\ngrey balanced, green deviated" % len(bx))
    if segs:
        a2 = axes[2]
        for c, s, e, cn, mn in segs:
            if c not in off:
                continue
            a2.plot([off[c] + s, off[c] + e], [min(6, cn)] * 2, color="royalblue", lw=2.2, solid_capstyle="butt", zorder=3)
            if mn is not None:
                a2.plot([off[c] + s, off[c] + e], [min(6, mn)] * 2, color="firebrick", lw=1.6, solid_capstyle="butt", zorder=4)
        a2.axhline(2, color="0.6", lw=0.7, ls="--"); a2.set_ylim(-0.2, 6.3)
        a2.set_ylabel("PURPLE CN\n(blue total, red minor)")
    axes[-1].set_xticks([off[c] + CHROM_LEN[c] / 2.0 for c in CHROMS])
    def lab(c):
        p, q = medians.get(c + "p"), medians.get(c + "q")
        return "%s\n%s|%s" % (c.replace("chr", ""), ("%+.2f" % p) if p is not None else "-", ("%+.2f" % q) if q is not None else "-")
    axes[-1].set_xticklabels([lab(c) for c in CHROMS], fontsize=6.5)
    axes[-1].set_xlim(0, total)
    fig.suptitle("%s  |  genome-wide  |  PURPLE purity %s ploidy %s %s %s" % (
        args.sample, pur.get("purity", "NA"), pur.get("ploidy", "NA"), pur.get("gender", ""), pur.get("status", "")), fontsize=11)
    fig.savefig(args.out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print("[ok] %s: genome overview, %d arm medians, %d BAF sites, %d PURPLE segments -> %s" % (
        args.sample, len(medians), len(bx), len(segs), args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
