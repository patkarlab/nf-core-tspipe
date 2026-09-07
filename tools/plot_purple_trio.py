#!/usr/bin/env python3
"""
tools/plot_purple_trio.py  (TRIO_PLOT_V1.1)

Genome-wide figure from the hmftools trio for one sample, plus zoomed
region views (--region chr:start-end, --arm 17p, --chrom chr17, --genes
TP53,KDM6B) with a gene track from the target BED:
  panel 1  COBALT tumour GC ratio per on-target 1 kb window (log2)
  panel 2  AMBER BAF points
  panel 3  PURPLE copy number and minor-allele copy number per segment (steps)
plus a purity/ploidy 'sunrise' from purple.purity.range.tsv. Reads the files
published under <sample>/cnv_hmftools/. Run with the targeted-seq python
(matplotlib):
  plot_purple_trio.py --sample ID --dir <sample>/cnv_hmftools --out prefix \
      [--targets panel.combined.filtered.bed] [--region chr17:1-24000000] [--arm 17p] [--genes TP53,NF1]
Region views are written as <prefix>.<label>.png. Log2 guides at 0, +-0.5, +-1.
"""

import argparse
import csv
import gzip
import math
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


# hg38 centromere midpoints (Mb) for --arm; p = 1..centromere, q = centromere..end
CENTROMERE = {"chr1": 123.4, "chr2": 93.9, "chr3": 90.9, "chr4": 50.0, "chr5": 48.8, "chr6": 59.8, "chr7": 60.1,
              "chr8": 45.2, "chr9": 43.0, "chr10": 39.8, "chr11": 53.4, "chr12": 35.5, "chr13": 17.7, "chr14": 17.2,
              "chr15": 19.0, "chr16": 36.8, "chr17": 25.1, "chr18": 18.5, "chr19": 26.2, "chr20": 28.1, "chr21": 12.0,
              "chr22": 15.0, "chrX": 60.6, "chrY": 10.4}


def parse_region(text):
    c, rest = text.split(":")
    a, b = rest.replace(",", "").split("-")
    return norm_chrom(c), int(a), int(b)


def arm_region(arm):
    c = norm_chrom(arm[:-1]); p = arm[-1].lower()
    mid = int(CENTROMERE[c] * 1e6)
    return (c, 1, mid) if p == "p" else (c, mid, CHROM_LEN[c])


def read_targets(path):
    """target BED -> list of (chrom, start, end, name) and gene -> (chrom, min, max)."""
    rows, genes = [], {}
    with open(path) as fh:
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if len(p) < 3 or line.startswith("#"):
                continue
            c, s, e = norm_chrom(p[0]), int(p[1]), int(p[2])
            name = p[3] if len(p) > 3 else ""
            rows.append((c, s, e, name))
            if name and not name.startswith("bb.") and "_SNP_" not in name and not name.startswith("het_"):
                g = name.split("_exon_")[0]
                g = g.rsplit("_", 1)[0] if g[-1:].isdigit() and "_" in g and g.split("_")[-1].isdigit() else g
                lo, hi = genes.get(g, (c, s, e))[1:]
                genes[g] = (c, min(lo, s), max(hi, e))
    return rows, genes


def offsets():
    off, x = {}, 0
    for c in CHROMS:
        off[c] = x
        x += CHROM_LEN[c]
    return off, x


def opener(path):
    return gzip.open(path, "rt") if path.endswith(".gz") else open(path)


def read_tsv(path):
    with opener(path) as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def pick(row, *names):
    for n in names:
        if n in row and row[n] not in ("", "NA", "NaN"):
            return row[n]
    return None


def norm_chrom(c):
    return c if c.startswith("chr") else "chr" + c


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample", required=True)
    ap.add_argument("--dir", required=True, help="<sample>/cnv_hmftools")
    ap.add_argument("--out", required=True, help="output prefix (writes <prefix>.trio.png and <prefix>.sunrise.png)")
    ap.add_argument("--max-cn", type=float, default=6.0)
    ap.add_argument("--targets", default=None, help="target BED for the gene track in region views")
    ap.add_argument("--region", action="append", default=[], help="chr:start-end (repeatable)")
    ap.add_argument("--arm", action="append", default=[], help="e.g. 17p (repeatable)")
    ap.add_argument("--chrom", action="append", default=[], help="whole chromosome (repeatable)")
    ap.add_argument("--genes", default="", help="comma-separated genes; one view spanning them per chromosome, +- --flank")
    ap.add_argument("--flank", type=int, default=300000, help="bp flank around --genes views (default 300 kb)")
    args = ap.parse_args()

    d, s = args.dir, args.sample
    cobalt = read_tsv(os.path.join(d, "cobalt", "%s.cobalt.ratio.tsv.gz" % s))
    amber = read_tsv(os.path.join(d, "amber", "%s.amber.baf.tsv.gz" % s))
    segs = read_tsv(os.path.join(d, "purple", "%s.purple.cnv.somatic.tsv" % s))
    rng_path = os.path.join(d, "purple", "%s.purple.purity.range.tsv" % s)
    pur = read_tsv(os.path.join(d, "purple", "%s.purple.purity.tsv" % s))[0]
    off, total = offsets()

    # COBALT: tumour GC ratio, on-target windows only (ratio >= 0)
    cx, cy = [], []
    for r in cobalt:
        c = norm_chrom(r["chromosome"])
        if c not in off:
            continue
        v = pick(r, "tumorGCRatio", "tumorGcRatio", "tumorGCDiploidRatio")
        try:
            v = float(v)
        except (TypeError, ValueError):
            continue
        if v <= 0:
            continue
        cx.append(off[c] + int(r["position"]))
        cy.append(math.log2(v))
    # AMBER: BAF points
    ax_, ay_ = [], []
    for r in amber:
        c = norm_chrom(r["chromosome"])
        if c not in off:
            continue
        v = pick(r, "tumorBAF", "TumorBAF", "baf")
        try:
            v = float(v)
        except (TypeError, ValueError):
            continue
        ax_.append(off[c] + int(r["position"]))
        ay_.append(v)

    fig, axes = plt.subplots(3, 1, figsize=(18, 9), sharex=True,
                             gridspec_kw={"height_ratios": [1.1, 1.0, 1.2], "hspace": 0.08})
    for a in axes:
        for c in CHROMS:
            a.axvline(off[c], color="0.85", lw=0.6, zorder=0)
    axes[0].scatter(cx, cy, s=3, color="0.35", alpha=0.6, linewidths=0, zorder=2)
    axes[0].axhline(0, color="black", lw=0.8); axes[0].set_ylim(-2.2, 2.2)
    for y in (0.5, -0.5):
        axes[0].axhline(y, color="red", lw=0.8, ls="--", zorder=1)
    for y in (1.0, -1.0):
        axes[0].axhline(y, color="red", lw=0.6, ls=":", zorder=1)
    axes[0].set_ylabel("COBALT log2 ratio\n(on-target 1 kb)")
    axes[1].scatter(ax_, ay_, s=4, color="darkorange", alpha=0.7, linewidths=0, zorder=2)
    axes[1].axhline(0.5, color="black", lw=0.8); axes[1].set_ylim(0, 1)
    axes[1].set_ylabel("AMBER BAF\n(%d points)" % len(ay_))
    for r in segs:
        c = norm_chrom(r["chromosome"])
        if c not in off:
            continue
        x0, x1 = off[c] + int(r["start"]), off[c] + int(r["end"])
        cn = min(args.max_cn, float(r["copyNumber"]))
        mn = min(args.max_cn, float(pick(r, "minorAlleleCopyNumber") or "nan")) if pick(r, "minorAlleleCopyNumber") else None
        axes[2].plot([x0, x1], [cn, cn], color="royalblue", lw=2.2, solid_capstyle="butt", zorder=3)
        if mn is not None and mn == mn:
            axes[2].plot([x0, x1], [mn, mn], color="firebrick", lw=1.6, solid_capstyle="butt", zorder=4)
    axes[2].axhline(2, color="0.6", lw=0.8, ls="--"); axes[2].axhline(1, color="0.8", lw=0.6, ls=":")
    axes[2].set_ylim(-0.2, args.max_cn + 0.3)
    axes[2].set_ylabel("PURPLE copy number\n(blue total, red minor allele)")
    axes[2].set_xticks([off[c] + CHROM_LEN[c] / 2.0 for c in CHROMS])
    axes[2].set_xticklabels([c.replace("chr", "") for c in CHROMS], fontsize=8)
    axes[2].set_xlim(0, total)
    fig.suptitle("%s  |  PURPLE purity %s  ploidy %s  gender %s  status %s  |  AMBER/COBALT/PURPLE" % (
        s, pur.get("purity", "NA"), pur.get("ploidy", "NA"), pur.get("gender", "NA"), pur.get("status", "NA")), fontsize=11)
    fig.savefig(args.out + ".trio.png", dpi=140, bbox_inches="tight")
    plt.close(fig)
    print("[ok] %s: trio figure (%d COBALT windows, %d AMBER points, %d PURPLE segments) -> %s.trio.png" % (
        s, len(cx), len(ay_), len(segs), args.out))

    # ---- region views -------------------------------------------------------
    regions = [(parse_region(r), r.replace(":", "_").replace("-", "_")) for r in args.region]
    regions += [(arm_region(a), a) for a in args.arm]
    regions += [((norm_chrom(c), 1, CHROM_LEN[norm_chrom(c)]), norm_chrom(c)) for c in args.chrom]
    targets, gene_span = ([], {})
    if args.targets and os.path.isfile(args.targets):
        targets, gene_span = read_targets(args.targets)
    if args.genes:
        by_chrom = {}
        for g in [x.strip() for x in args.genes.split(",") if x.strip()]:
            if g not in gene_span:
                sys.stderr.write("[warn] gene not in targets: %s\n" % g); continue
            c, lo, hi = gene_span[g]
            cur = by_chrom.get(c, [lo, hi, []])
            cur[0], cur[1] = min(cur[0], lo), max(cur[1], hi); cur[2].append(g); by_chrom[c] = cur
        for c, (lo, hi, gs) in by_chrom.items():
            regions.append(((c, max(1, lo - args.flank), min(CHROM_LEN[c], hi + args.flank)), "genes_" + "_".join(gs)))
    for (rc, rs, re_), label in regions:
        rx = [x for x, _ in zip(cx, cy) if off[rc] + rs <= x <= off[rc] + re_]
        ry = [y for x, y in zip(cx, cy) if off[rc] + rs <= x <= off[rc] + re_]
        bx = [x for x, _ in zip(ax_, ay_) if off[rc] + rs <= x <= off[rc] + re_]
        by = [y for x, y in zip(ax_, ay_) if off[rc] + rs <= x <= off[rc] + re_]
        n_tr = 4 if targets else 3
        heights = [1.1, 1.0, 1.2] + ([0.45] if targets else [])
        fig, axr = plt.subplots(n_tr, 1, figsize=(16, 9.5 if targets else 8.5), sharex=True,
                                gridspec_kw={"height_ratios": heights, "hspace": 0.08})
        to_mb = lambda x: (x - off[rc]) / 1e6
        axr[0].scatter([to_mb(x) for x in rx], ry, s=9, color="0.3", alpha=0.8, linewidths=0, zorder=2)
        axr[0].axhline(0, color="black", lw=0.8); axr[0].set_ylim(-2.2, 2.2)
        for y in (0.5, -0.5):
            axr[0].axhline(y, color="red", lw=0.8, ls="--", zorder=1)
        for y in (1.0, -1.0):
            axr[0].axhline(y, color="red", lw=0.6, ls=":", zorder=1)
        axr[0].set_ylabel("COBALT log2 ratio\n(%d windows)" % len(rx))
        axr[1].scatter([to_mb(x) for x in bx], by, s=10, color="darkorange", alpha=0.8, linewidths=0, zorder=2)
        axr[1].axhline(0.5, color="black", lw=0.8); axr[1].set_ylim(0, 1)
        axr[1].set_ylabel("AMBER BAF\n(%d points)" % len(bx))
        for r in segs:
            if norm_chrom(r["chromosome"]) != rc:
                continue
            s0, s1 = max(int(r["start"]), rs), min(int(r["end"]), re_)
            if s1 <= s0:
                continue
            cn = min(args.max_cn, float(r["copyNumber"]))
            axr[2].plot([s0 / 1e6, s1 / 1e6], [cn, cn], color="royalblue", lw=2.4, solid_capstyle="butt", zorder=3)
            mn = pick(r, "minorAlleleCopyNumber")
            if mn is not None:
                mn = min(args.max_cn, float(mn))
                axr[2].plot([s0 / 1e6, s1 / 1e6], [mn, mn], color="firebrick", lw=1.8, solid_capstyle="butt", zorder=4)
        axr[2].axhline(2, color="0.6", lw=0.8, ls="--"); axr[2].axhline(1, color="0.8", lw=0.6, ls=":")
        axr[2].set_ylim(-0.2, args.max_cn + 0.3); axr[2].set_ylabel("PURPLE copy number\n(blue total, red minor)")
        if targets:
            ax4 = axr[3]; ax4.set_ylim(0, 1); ax4.set_yticks([])
            drawn = {}
            for tc, ts, te, name in targets:
                if tc != rc or te < rs or ts > re_:
                    continue
                if name.startswith("bb."):
                    ax4.plot([ts / 1e6, te / 1e6], [0.12, 0.12], color="0.6", lw=2, solid_capstyle="butt")
                elif "_SNP_" in name or name.startswith("het_"):
                    ax4.plot([(ts + te) / 2e6], [0.3], marker="|", color="darkorange", ms=6, mew=0.8)
                else:
                    ax4.add_patch(plt.Rectangle((ts / 1e6, 0.45), max((te - ts) / 1e6, (re_ - rs) / 1e6 * 0.0015), 0.22, color="navy"))
                    g = name.split("_exon_")[0]
                    drawn.setdefault(g, [ts, te]); drawn[g][0] = min(drawn[g][0], ts); drawn[g][1] = max(drawn[g][1], te)
            for i, (g, (gs_, ge_)) in enumerate(sorted(drawn.items(), key=lambda kv: kv[1][0])):
                ax4.text((gs_ + ge_) / 2e6, 0.72 + 0.14 * (i % 2), g, ha="center", va="bottom", fontsize=6.5)
            ax4.set_ylim(0, 1.15)
            ax4.set_ylabel("targets\n(exons, SNPs, backbone)", fontsize=8)
        axr[-1].set_xlim(rs / 1e6, re_ / 1e6); axr[-1].set_xlabel("%s position (Mb)" % rc)
        fig.suptitle("%s  |  %s:%s-%s  |  purity %s ploidy %s %s" % (
            s, rc, "{:,}".format(rs), "{:,}".format(re_), pur.get("purity", "NA"), pur.get("ploidy", "NA"), pur.get("gender", "NA")), fontsize=11)
        out = "%s.%s.png" % (args.out, label)
        fig.savefig(out, dpi=140, bbox_inches="tight"); plt.close(fig)
        print("[ok] region %s: %d windows, %d BAF points -> %s" % (label, len(rx), len(bx), out))

    if os.path.isfile(rng_path):
        rows = read_tsv(rng_path)
        px = [float(r["purity"]) for r in rows]
        py = [float(r["ploidy"]) for r in rows]
        sc = [float(r["score"]) for r in rows]
        fig, a = plt.subplots(figsize=(7, 5))
        h = a.scatter(px, py, c=sc, s=14, cmap="viridis_r", linewidths=0)
        best = min(range(len(sc)), key=lambda i: sc[i])
        a.scatter([px[best]], [py[best]], s=120, facecolors="none", edgecolors="red", linewidths=1.5, zorder=5)
        a.set_xlabel("purity"); a.set_ylabel("ploidy"); a.set_title("%s: PURPLE fit score by purity/ploidy (best circled)" % s, fontsize=10)
        fig.colorbar(h, label="fit score (lower is better)")
        fig.savefig(args.out + ".sunrise.png", dpi=140, bbox_inches="tight")
        plt.close(fig)
        print("[ok] sunrise -> %s.sunrise.png (best: purity %.2f ploidy %.2f score %.4f)" % (args.out, px[best], py[best], sc[best]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
