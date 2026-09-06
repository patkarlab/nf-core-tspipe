#!/usr/bin/env python3
"""
bin/plot_exon_ratio.py  (EXONPLOT_V1.2; importable renderer + CLI)

Per-exon CNVkit copy-ratio plot for a set of genes, in genomic order: one
point per CNVkit bin (log2 vs the sex-matched PoN), dashed guide per bin,
gene blocks labelled below, red guides at +/-0.5 and +/-1.0 log2, y clipped
to +/-3. Point size follows bin weight; bins below the weight floor are
hollow. Reads either the CMX_V2 consensus JSON (tracks.cnr_bins) or a
CNVkit .cnr file. Optional DECoN calls table (*_all.txt or *_filtered.tsv)
draws each call as a bracket above the affected exons with its BF.

Examples:
  python3 tools/plot_exon_ratio.py --json <sample>.cnv_consensus4.json \
      --genes IKZF1,SAMD9,SAMD9L,CUX1,BPGM,LUC7L2,BRAF,EZH2 --out ikzf1.png
  python3 tools/plot_exon_ratio.py --cnr <sample>.cnr --genes CDKN2A,CDKN2B \
      --decon <sample>.decon_all.txt --out cdkn2.png

Python 3.6, matplotlib only (GATK container or targeted-seq env).
"""

import argparse
import csv
import gzip
import json
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CHROM_ORDER = dict((c, i) for i, c in enumerate(
    ["chr%d" % i for i in range(1, 23)] + ["chrX", "chrY", "chrM"]))


def bin_gene(name):
    """'IKZF1_exon_4' -> 'IKZF1'; 'bb.chr1.629966' -> None; 'Antitarget' -> None."""
    if not name or name.startswith("bb.") or name.lower() in ("antitarget", "-", "."):
        return None
    return re.split(r"_exon_|_Ex_|_ex", name)[0]


def read_json_bins(path):
    with open(path) as fh:
        d = json.load(fh)
    out = []
    for b in d["tracks"]["cnr_bins"]:
        chrom, start, end, name, log2 = b[0], int(b[1]), int(b[2]), b[3], float(b[4])
        depth = float(b[5]) if len(b) > 5 and b[5] is not None else None
        weight = float(b[6]) if len(b) > 6 and b[6] is not None else None
        out.append((chrom, start, end, name, log2, depth, weight))
    return out


def read_cnr_bins(path):
    opener = gzip.open if path.endswith(".gz") else open
    out = []
    with opener(path, "rt") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for r in reader:
            try:
                out.append((r["chromosome"], int(r["start"]), int(r["end"]), r.get("gene", ""),
                            float(r["log2"]),
                            float(r["depth"]) if r.get("depth") not in (None, "", "NA") else None,
                            float(r["weight"]) if r.get("weight") not in (None, "", "NA") else None))
            except (KeyError, ValueError):
                continue
    return out


def read_decon_calls(path):
    calls = []
    with open(path) as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for r in reader:
            try:
                calls.append({"chrom": "chr" + r["Chromosome"].replace("chr", ""),
                              "start": int(float(r["Start"])), "end": int(float(r["End"])),
                              "type": r["CNV.type"], "bf": float(r["BF"]),
                              "ratio": float(r["Reads.ratio"]), "gene": r["Gene"],
                              "decision": r.get("decision", "")})
            except (KeyError, ValueError):
                continue
    return calls



def render(bins, want, out, decon_calls=None, sample="", ymax=3.0, weight_floor=0.5):
    """Draw the per-exon plot for the genes in `want` (any order) from a list of
    (chrom, start, end, name, log2, depth, weight) bins. Returns (n_bins, missing_genes)."""
    sel = [b for b in bins if bin_gene(b[3]) in want]
    if not sel:
        return 0, list(want)
    sel.sort(key=lambda b: (CHROM_ORDER.get(b[0], 99), b[1]))
    present = set(bin_gene(b[3]) for b in sel)
    missing = [g for g in want if g not in present]

    xs = list(range(len(sel)))
    ys = [max(-ymax, min(ymax, b[4])) for b in sel]
    genes = [bin_gene(b[3]) for b in sel]
    labels = [b[3] for b in sel]
    weights = [b[6] for b in sel]
    have_w = any(w is not None for w in weights)

    fig_w = max(10.0, 0.22 * len(sel) + 2.5)
    fig, ax = plt.subplots(figsize=(fig_w, 4.6))
    for x in xs:
        ax.axvline(x, color="0.75", lw=0.6, ls="--", zorder=1)
    for y in (0.5, -0.5):
        ax.axhline(y, color="red", lw=1.0, zorder=2)
    for y in (1.0, -1.0):
        ax.axhline(y, color="red", lw=0.6, ls=":", zorder=2)
    ax.axhline(0, color="black", lw=1.0, zorder=2)

    for x, y, w in zip(xs, ys, weights):
        size = 42 if w is None else 12 + 40 * max(0.0, min(1.0, w)) ** 2
        hollow = w is not None and w < weight_floor
        ax.scatter([x], [y], s=size, facecolors="none" if hollow else "0.55",
                   edgecolors="0.35", linewidths=0.8, zorder=4)

    ymin = -ymax - 0.55
    i = 0
    while i < len(sel):
        j = i
        while j + 1 < len(sel) and genes[j + 1] == genes[i]:
            j += 1
        ax.axvspan(i - 0.5, j + 0.5, ymin=0, ymax=0.045, color="0.85", zorder=0)
        ax.text((i + j) / 2.0, ymin + 0.12, genes[i], ha="center", va="bottom", fontsize=8, zorder=5)
        if i > 0:
            ax.axvline(i - 0.5, color="0.2", lw=0.8, zorder=3)
        i = j + 1

    if decon_calls:
        merged = {}
        for c in decon_calls:
            if c["gene"] not in want:
                continue
            merged.setdefault((c["chrom"], c["start"], c["end"], c["type"]), c)
        drawn = 0
        for key in sorted(merged, key=lambda k: (CHROM_ORDER.get(k[0], 99), k[1])):
            c = merged[key]
            idx = [k for k, b in enumerate(sel) if b[0] == c["chrom"] and b[2] >= c["start"] and b[1] <= c["end"]]
            if not idx:
                continue
            x0, x1 = min(idx) - 0.4, max(idx) + 0.4
            ytop = ymax - 0.35 - 0.45 * (drawn % 2)
            colour = "firebrick" if c["type"].lower().startswith("del") else "darkorange"
            ax.plot([x0, x0, x1, x1], [ytop - 0.15, ytop, ytop, ytop - 0.15], color=colour, lw=1.4, zorder=6)
            ax.text((x0 + x1) / 2.0, ytop + 0.05, "DECoN %s BF %.1f ratio %.2f%s" % (
                c["type"], c["bf"], c["ratio"], (" " + c["decision"]) if c["decision"] else ""),
                ha="center", va="bottom", fontsize=7, color=colour, zorder=6)
            drawn += 1

    ax.set_xlim(-0.6, len(sel) - 0.4)
    ax.set_ylim(ymin, ymax + 0.6)
    ax.set_xticks(xs)
    ax.set_xticklabels(labels, rotation=90, fontsize=6)
    ax.set_ylabel("Copy ratio (log2)")
    chroms = sorted(set(b[0] for b in sel), key=lambda c: CHROM_ORDER.get(c, 99))
    shown = [g for g in want if g in present]
    ax.set_title("%s%s: %s" % ((sample + "  ") if sample else "", ",".join(chroms), " ".join(shown)), fontsize=10)
    if have_w:
        ax.text(0.995, 0.02, "point size = bin weight; hollow = weight < %.2f" % weight_floor,
                transform=ax.transAxes, ha="right", va="bottom", fontsize=6, color="0.4")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return len(sel), missing


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--json", help="CMX consensus JSON (tracks.cnr_bins)")
    src.add_argument("--cnr", help="CNVkit .cnr")
    ap.add_argument("--genes", required=True, help="comma-separated gene symbols, any order")
    ap.add_argument("--decon", default=None, help="DECoN *_all.txt or *_filtered.tsv (optional)")
    ap.add_argument("--sample", default="", help="label for the title")
    ap.add_argument("--out", required=True, help="PNG or PDF")
    ap.add_argument("--ymax", type=float, default=3.0)
    ap.add_argument("--weight-floor", type=float, default=0.5, help="bins below this weight are hollow")
    args = ap.parse_args()

    bins = read_json_bins(args.json) if args.json else read_cnr_bins(args.cnr)
    want = [g.strip() for g in args.genes.split(",") if g.strip()]
    calls = read_decon_calls(args.decon) if args.decon else None
    n, missing = render(bins, want, args.out, decon_calls=calls, sample=args.sample,
                        ymax=args.ymax, weight_floor=args.weight_floor)
    if n == 0:
        sys.exit("[error] no bins for genes %s" % ",".join(want))
    if missing:
        sys.stderr.write("[warn] no bins for: %s\n" % ", ".join(missing))
    print("[ok] %s: %d bins, %d genes -> %s" % (args.sample or "sample", n, len(want) - len(missing), args.out))


if __name__ == "__main__":
    main()
