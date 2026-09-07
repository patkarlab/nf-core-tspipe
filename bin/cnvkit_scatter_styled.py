#!/usr/bin/env python3
"""Render CNVkit's scatter (cnvlib.scatter.do_scatter, unchanged logic) with a
cleaner presentation: wide figure, thin muted points, no chart chrome, a
readable BAF panel. Python 3.6 compatible.

Usage:
    cnvkit_scatter_styled.py --cnr S.cnr --cns S.cns [--vcf hets.vcf]
        [--chrom chr8 | --genome] --out S.chr8.png [--title T]
"""

import argparse
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import cnvlib
from cnvlib import scatter as sc
from cnvlib.cmdutil import load_het_snps

STYLE = {
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans", "Helvetica", "Arial"],
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.titleweight": "semibold",
    "axes.labelsize": 10,
    "axes.edgecolor": "#8a96a3",
    "axes.linewidth": 0.8,
    "xtick.color": "#5f6b76",
    "ytick.color": "#5f6b76",
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "figure.facecolor": "white",
    "savefig.facecolor": "white",
}
POINT = "#6b7783"
SEG = "#d6641c"


def restyle(fig, point_scale, alpha):
    for ax in fig.axes:
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        ax.grid(False)
        ax.tick_params(length=3)
        for coll in ax.collections:
            sizes = coll.get_sizes()
            if len(sizes):
                coll.set_sizes(sizes * point_scale)
            coll.set_alpha(alpha)
            coll.set_edgecolor("none")
        for line in ax.lines:
            if line.get_color() in ("darkorange", SEG):
                line.set_linewidth(2.6)
                line.set_solid_capstyle("round")
        # CNVkit's thin black chromosome separators: keep, but soften
        for line in ax.lines:
            if line.get_color() in ("black", "k") and line.get_linewidth() >= 1:
                line.set_color("#c8ccd1")
                line.set_linewidth(0.8)


def render(cnarr, segs, variants, out, chrom=None, gene=None, title=None, args=None, width=14.0, height=None, trend=False, y_lim=None):
    height = height or (5.5 if chrom or gene else 4.6)
    y_min, y_max = (-y_lim, y_lim) if y_lim else (args.y_min, args.y_max)
    fig = sc.do_scatter(cnarr, segs, variants, show_range=chrom, show_gene=gene,
                        do_trend=trend, y_min=y_min, y_max=y_max,
                        fig_size=(width, height), segment_color=SEG, title=title)
    restyle(fig, args.point_scale, args.alpha)
    for ax in fig.axes:
        ax.set_facecolor("white")
        if ax.get_ylabel().startswith("Copy ratio"):
            ax.axhline(0, color="#1f2933", linewidth=0.8)
            for g in (0.5, -0.5):
                ax.axhline(g, color="#9aa3ad", linewidth=0.7, linestyle=(0, (2, 3)))
            for g in (1.0, -1.0):
                ax.axhline(g, color="#9aa3ad", linewidth=0.8, linestyle=(0, (6, 3)))
    fig.tight_layout()
    fig.savefig(out, dpi=args.dpi)
    plt.close(fig)


def batch(args):
    """Genome, per-chromosome (chromosomes with panel genes) and per-called-gene plots
    in the cnv_plots.py folder layout: overview/, per_chromosome/, per_gene/."""
    import os
    cnarr = cnvlib.read(args.cnr)
    segs = cnvlib.read(args.cns) if args.cns else None
    variants = load_het_snps(args.vcf, None, None, 0.0, 0) if args.vcf else None
    sample = args.sample or os.path.basename(args.cnr).split(".")[0]
    for sub in ("overview", "per_chromosome", "per_gene"):
        os.makedirs(os.path.join(args.outdir, sub), exist_ok=True)
    render(cnarr, segs, None, os.path.join(args.outdir, "overview", "%s_genome_scatter.png" % sample),
           title="%s  genome" % sample, args=args, trend=True)
    # chromosomes that carry panel genes (exonic bins), in karyotype order
    genes_by_chrom = {}
    df = cnarr.data
    for chrom, g in zip(df["chromosome"], df["gene"]):
        g = str(g)
        if g and g != "-" and not g.startswith(("bb.", "Antitarget", "Background")):
            genes_by_chrom.setdefault(chrom, set()).add(g.split("_")[0])
    order = ["chr%d" % i for i in range(1, 23)] + ["chrX", "chrY"]
    for chrom in order:
        if chrom not in genes_by_chrom:
            continue
        if chrom == "chrY" and args.sex.lower().startswith("f"):
            continue
        label = "_".join(sorted(genes_by_chrom[chrom])[:5]) + ("_+%d" % (len(genes_by_chrom[chrom]) - 5) if len(genes_by_chrom[chrom]) > 5 else "")
        render(cnarr, segs, variants, os.path.join(args.outdir, "per_chromosome", "%s_%s_%s.png" % (sample, chrom, label)),
               chrom=chrom, title="%s  %s" % (sample, chrom), args=args)
    # called genes: genemetrics (annotated) rows, or an explicit list
    called = []
    if args.genes_list:
        called = [g for g in args.genes_list.split(",") if g]
    elif args.genemetrics and os.path.isfile(args.genemetrics):
        with open(args.genemetrics) as fh:
            hdr = fh.readline().rstrip("\n").split("\t")
            gi = hdr.index("gene") if "gene" in hdr else 0
            for line in fh:
                called.append(line.split("\t")[gi].split("_")[0])
    # bins are named GENE_exon_N, so CNVkit's -g lookup by exact name misses; take the gene span from its bins instead
    for g in sorted(set(called)):
        rows = df[[str(x).split("_")[0] == g for x in df["gene"]]]
        if not len(rows):
            print("[warn] gene %s has no bins in the ratio file; skipped" % g); continue
        chrom = rows["chromosome"].iloc[0]; start, end = int(rows["start"].min()), int(rows["end"].max())
        pad = max(5000, int(0.15 * (end - start)))
        region = "%s:%d-%d" % (chrom, max(1, start - pad), end + pad)
        try:
            render(cnarr, segs, variants, os.path.join(args.outdir, "per_gene", "%s_%s.png" % (sample, g)),
                   chrom=region, title="%s  %s  (%s)" % (sample, g, region), args=args, width=12.0, height=5.0, y_lim=2.5)
        except Exception as exc:
            print("[warn] gene %s skipped: %s" % (g, exc))
    print("[ok] batch plots under %s (%d chromosomes, %d called genes)" % (args.outdir, len([c for c in order if c in genes_by_chrom]), len(set(called))))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cnr", required=True)
    ap.add_argument("--cns", default=None)
    ap.add_argument("--vcf", default=None, help="VCF with GT and AD for the BAF panel")
    ap.add_argument("--chrom", default=None, help="chromosome or region (chr8, chr8:1-50000000)")
    ap.add_argument("--gene", default=None)
    ap.add_argument("--out", default=None, help="single-plot output; omit in --batch mode")
    ap.add_argument("--batch", action="store_true", help="write overview/, per_chromosome/, per_gene/ under --outdir")
    ap.add_argument("--outdir", default="cnvkit_plots")
    ap.add_argument("--sample", default=None)
    ap.add_argument("--sex", default="unknown", help="female skips chrY in batch mode")
    ap.add_argument("--genemetrics", default=None, help="annotated genemetrics (called genes get per-gene plots)")
    ap.add_argument("--genes-list", default=None, help="comma-separated genes for per-gene plots (overrides genemetrics)")
    ap.add_argument("--title", default=None)
    ap.add_argument("--y-min", type=float, default=-1.5)
    ap.add_argument("--y-max", type=float, default=1.5)
    ap.add_argument("--point-scale", type=float, default=0.35)
    ap.add_argument("--alpha", type=float, default=0.45)
    ap.add_argument("--width", type=float, default=14.0)
    ap.add_argument("--height", type=float, default=None)
    ap.add_argument("--dpi", type=int, default=160)
    ap.add_argument("--trend", action="store_true")
    args = ap.parse_args()

    plt.rcParams.update(STYLE)
    if args.batch:
        return batch(args)
    if not args.out:
        sys.exit("[error] --out is required unless --batch")
    cnarr = cnvlib.read(args.cnr)
    segs = cnvlib.read(args.cns) if args.cns else None
    variants = load_het_snps(args.vcf, None, None, 0.0, 0) if args.vcf else None
    height = args.height or (5.5 if args.chrom else 4.6)
    fig = sc.do_scatter(cnarr, segs, variants, show_range=args.chrom, show_gene=args.gene,
                        do_trend=args.trend, y_min=args.y_min, y_max=args.y_max,
                        fig_size=(args.width, height), segment_color=SEG, title=args.title)
    restyle(fig, args.point_scale, args.alpha)
    for ax in fig.axes:
        ax.set_facecolor("white")
        if ax.get_ylabel().startswith("Copy ratio"):
            ax.axhline(0, color="#1f2933", linewidth=0.8)
            for g in (0.5, -0.5):
                ax.axhline(g, color="#9aa3ad", linewidth=0.7, linestyle=(0, (2, 3)))
            for g in (1.0, -1.0):
                ax.axhline(g, color="#9aa3ad", linewidth=0.8, linestyle=(0, (6, 3)))
    fig.tight_layout()
    fig.savefig(args.out, dpi=args.dpi)
    print("[ok] wrote", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
