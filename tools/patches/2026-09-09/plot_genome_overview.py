#!/usr/bin/env python3
"""bin/plot_genome_overview.py -- GENOME_V2 (2026-09-09; replaces the VIZ_V1b arm-median overview).

One genome-wide figure in genomic coordinates, three tracks sharing the x axis:
  1. depth   -- denoised log2 copy ratio per bin (consensus JSON tracks.denoised_bins) with one
                median line per chromosome arm from the BAF_V2 summary rows (baf_arms), coloured
                red at or below --cr-del, green at or above --cr-gain, dark otherwise.
  2. BAF     -- every catalog site (tracks.baf_sites): heterozygous sites coloured by the arm's
                BAF_V2 verdict (DEL red, CNLOH blue, GAIN green, IMBALANCE purple, balanced grey),
                homozygous sites light grey; legend.
  3. PURPLE  -- total (blue) and minor-allele (orange) copy number per segment from
                <purple-dir>/<sample>.purple.cnv.somatic.tsv; capped at --max-cn.
Centromeres shaded; chromosome labels on the bottom axis; arm calls in the title.

CLI matches the VIZ_V1b script (the CHROM_PAGES module calls it unchanged):
  --sample --consensus-json --allelic (accepted, unused: sites come from the JSON) --purple-dir --out
py3.6 / matplotlib 3.2 safe.
"""
import argparse
import csv
import json
import os
import statistics
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

CHROMS = ["chr%d" % i for i in range(1, 23)] + ["chrX"]
CHROM_LEN = {"chr1": 248956422, "chr2": 242193529, "chr3": 198295559, "chr4": 190214555, "chr5": 181538259,
             "chr6": 170805979, "chr7": 159345973, "chr8": 145138636, "chr9": 138394717, "chr10": 133797422,
             "chr11": 135086622, "chr12": 133275309, "chr13": 114364328, "chr14": 107043718, "chr15": 101991189,
             "chr16": 90338345, "chr17": 83257441, "chr18": 80373285, "chr19": 58617616, "chr20": 64444167,
             "chr21": 46709983, "chr22": 50818468, "chrX": 156040895}
CENTROMERE_HG38 = {
    "chr1": (121700000, 125100000), "chr2": (91800000, 96000000), "chr3": (87800000, 94000000),
    "chr4": (48200000, 51800000), "chr5": (46100000, 51400000), "chr6": (58500000, 62600000),
    "chr7": (58100000, 62100000), "chr8": (43200000, 47200000), "chr9": (42200000, 45500000),
    "chr10": (38000000, 41600000), "chr11": (51000000, 55800000), "chr12": (33200000, 37800000),
    "chr13": (16500000, 18900000), "chr14": (16100000, 18200000), "chr15": (17500000, 20500000),
    "chr16": (35300000, 38400000), "chr17": (22700000, 27400000), "chr18": (15400000, 21500000),
    "chr19": (24200000, 28100000), "chr20": (25700000, 30400000), "chr21": (10900000, 13000000),
    "chr22": (13700000, 17400000), "chrX": (58100000, 61000000)}
VERDICT_COLOUR = {"NEUTRAL": "#9e9e9e", "DEL": "#c0392b", "CNLOH": "#2471a3", "GAIN": "#1e8449",
                  "IMBALANCE": "#8e44ad", "INDETERMINATE": "#bdbdbd"}


def norm_chrom(c):
    c = str(c)
    return c if c.startswith("chr") else "chr" + c


def arm_of(chrom, pos):
    cen = CENTROMERE_HG38.get(chrom)
    if cen is None:
        return None
    return "p" if pos < cen[0] else ("q" if pos > cen[1] else None)


def read_purple(purple_dir, sample):
    """[(chrom, start, end, total_cn, minor_cn)] or []"""
    if not purple_dir:
        return []
    path = os.path.join(purple_dir, "%s.purple.cnv.somatic.tsv" % sample)
    if not os.path.isfile(path):
        return []
    segs = []
    with open(path) as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            try:
                mn = r.get("minorAlleleCopyNumber")
                segs.append((norm_chrom(r["chromosome"]), int(r["start"]), int(r["end"]), float(r["copyNumber"]),
                             float(mn) if mn not in (None, "", "NA") else None))
            except (KeyError, ValueError):
                continue
    return segs


def fmt(x, nd=2):
    try:
        return "{0:.{1}f}".format(float(x), nd)
    except (TypeError, ValueError):
        return "NA"


def main():
    ap = argparse.ArgumentParser(description="GENOME_V2 genome-wide depth / BAF / PURPLE overview")
    ap.add_argument("--sample", required=True)
    ap.add_argument("--consensus-json", required=True)
    ap.add_argument("--allelic", default=None, help="accepted for CLI compatibility; sites come from the consensus JSON")
    ap.add_argument("--purple-dir", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cr-del", type=float, default=-0.15)
    ap.add_argument("--cr-gain", type=float, default=0.15)
    ap.add_argument("--max-cn", type=float, default=6.0)
    args = ap.parse_args()

    with open(args.consensus_json) as fh:
        d = json.load(fh)
    tracks = d.get("tracks", {})
    bins = []
    for b in tracks.get("denoised_bins", []):
        try:
            bins.append((norm_chrom(b[0]), int(b[1]), int(b[2]), float(b[3])))
        except (ValueError, TypeError, IndexError):
            continue
    sites = []
    for s in tracks.get("baf_sites", []):
        try:
            sites.append((norm_chrom(s[0]), int(s[1]), float(s[3]), bool(s[5])))
        except (ValueError, TypeError, IndexError):
            continue
    arms = {}
    for r in d.get("baf_arms", []) or []:
        a = str(r.get("arm", ""))
        if not a:
            continue
        arms[("chr" + a[:-1], a[-1])] = r
    purple = read_purple(args.purple_dir, args.sample)

    chroms = [c for c in CHROMS if any(b[0] == c for b in bins) or any(s[0] == c for s in sites)]
    if not chroms:
        sys.stderr.write("[warn] no bins or sites in %s; no overview written\n" % args.consensus_json)
        return
    off, x = {}, 0.0
    for c in chroms:
        off[c] = x
        x += CHROM_LEN[c] / 1e6 + 4.0

    n_tracks = 3 if purple else 2
    ratios = [1.0, 1.1, 0.7][:n_tracks]
    fig, axes = plt.subplots(n_tracks, 1, figsize=(18, 3.0 * n_tracks), sharex=True,
                             gridspec_kw={"height_ratios": ratios, "hspace": 0.07})
    a0, a1 = axes[0], axes[1]
    a2 = axes[2] if purple else None

    # 1. depth
    for c, s, e, l in bins:
        if c in off:
            a0.scatter(off[c] + (s + e) / 2e6, l, s=3, c="#8c8c8c", linewidths=0)
    for (c, arm), r in arms.items():
        if c not in off:
            continue
        try:
            v = float(r.get("cr_median_log2"))
        except (TypeError, ValueError):
            continue
        cen = CENTROMERE_HG38[c]
        lo, hi = (0, cen[0]) if arm == "p" else (cen[1], CHROM_LEN[c])
        col = "#c0392b" if v <= args.cr_del else ("#1e8449" if v >= args.cr_gain else "#333333")
        a0.plot([off[c] + lo / 1e6, off[c] + hi / 1e6], [v, v], color=col, lw=2)
    a0.axhline(0.0, color="#555555", lw=0.6)
    a0.set_ylim(-1.5, 1.5)
    a0.set_ylabel("depth\nlog2 copy ratio")

    # 2. BAF
    for c, pos, af, het in sites:
        if c not in off:
            continue
        arm = arm_of(c, pos)
        v = arms.get((c, arm), {}).get("verdict", "NEUTRAL") if arm else "NEUTRAL"
        a1.scatter(off[c] + pos / 1e6, af, s=6, linewidths=0, c=VERDICT_COLOUR.get(v, "#9e9e9e") if het else "#e0e0e0")
    a1.axhline(0.5, color="#555555", lw=0.6)
    a1.set_ylim(0, 1)
    a1.set_ylabel("BAF\nALT allele fraction")
    a1.legend(handles=[Line2D([0], [0], marker="o", color="w", markerfacecolor=col, markersize=6, label=lab) for lab, col in [
        ("DEL", VERDICT_COLOUR["DEL"]), ("CNLOH", VERDICT_COLOUR["CNLOH"]), ("GAIN", VERDICT_COLOUR["GAIN"]),
        ("imbalance", VERDICT_COLOUR["IMBALANCE"]), ("balanced het", "#9e9e9e"), ("homozygous", "#e0e0e0")]],
        loc="upper right", ncol=6, fontsize=7, frameon=True, framealpha=0.9)

    # 3. PURPLE
    if a2 is not None:
        for c, s, e, cn, mn in purple:
            if c not in off:
                continue
            xs = [off[c] + s / 1e6, off[c] + e / 1e6]
            a2.plot(xs, [min(cn, args.max_cn)] * 2, color="#1f4e79", lw=2.5)
            if mn is not None:
                a2.plot(xs, [min(mn, args.max_cn)] * 2, color="#e67e22", lw=2.5)
        a2.set_ylim(-0.3, args.max_cn + 0.3)
        a2.set_yticks(range(0, int(args.max_cn) + 1))
        a2.set_ylabel("PURPLE\ncopy number")
        a2.legend(handles=[Line2D([0], [0], color="#1f4e79", lw=2.5, label="total CN"),
                           Line2D([0], [0], color="#e67e22", lw=2.5, label="minor allele CN")],
                  loc="upper right", ncol=2, fontsize=7, framealpha=0.9)

    last = axes[-1]
    for c in chroms:
        cen = CENTROMERE_HG38[c]
        for ax in axes:
            ax.axvline(off[c] - 2.0, color="#bbbbbb", lw=0.5)
            ax.axvspan(off[c] + cen[0] / 1e6, off[c] + cen[1] / 1e6, color="#f2f2f2", lw=0)
    last.set_xlim(-2, x)
    last.set_xticks([off[c] + CHROM_LEN[c] / 2e6 for c in chroms])
    last.set_xticklabels([c.replace("chr", "") for c in chroms], fontsize=8)
    last.tick_params(axis="x", length=0)
    last.set_xlabel("chromosome")

    calls = ["%s %s%s f=%s" % (r.get("arm"), r.get("verdict"), "?" if r.get("confidence") == "LOW" else "", fmt(r.get("f_estimate")))
             for (c, arm), r in sorted(arms.items(), key=lambda kv: (CHROMS.index(kv[0][0]) if kv[0][0] in CHROMS else 99, kv[0][1]))
             if r.get("verdict") not in ("NEUTRAL", "INDETERMINATE", None)]
    a0.set_title("%s -- genome-wide: depth, BAF by arm%s  |  arm calls: %s" % (
        args.sample, ", PURPLE copy number" if purple else "", ", ".join(calls) or "none"), fontsize=10, pad=12)
    fig.savefig(args.out, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print("[ok] %s: genome overview -> %s (%d bins, %d sites, %d PURPLE segments, %d arm rows)" % (
        args.sample, args.out, len(bins), len(sites), len(purple), len(arms)))


if __name__ == "__main__":
    main()
