#!/usr/bin/env python3
"""
tools/plot_targets_trio.py  (TARGETS_TRIO_V2.2; default style interleaved; depth colour bar)

Target-space trio for one sample (depth, BAF, PURPLE) with three layouts:
  --style interleaved  targets in genomic order (exons, SNP windows, backbone tiles);
                       a shaded band per gene across all panels, gene names on top
  --style grouped      three blocks: gene exons | SNP windows | backbone tiles
                       (position order inside each block); dense and legible
  --style genes        one column per gene: its exons plus the SNP windows and
                       backbone tiles within --flank of it; small multiples
Panels: CNVkit log2 per target (triangles beyond +-log2-lim); BAF from our
allelic counts over the v2 catalog (large markers, colour by depth), optional
--mirror-baf folds BAF to 0.5..1; PURPLE copy number and minor allele per target.
Inputs as V1: --sample-dir <outdir>/<sample>, --targets BED (repeatable; later
BEDs are SNP probe windows), selection by --arm/--chrom/--region/--genes/--all.
"""

import argparse
import bisect
import csv
import gzip
import json
import os
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

CHROMS = ["chr%d" % i for i in range(1, 23)] + ["chrX", "chrY"]
CHROM_ORDER = dict((c, i) for i, c in enumerate(CHROMS))
CHROM_LEN = {"chr1": 248956422, "chr2": 242193529, "chr3": 198295559, "chr4": 190214555, "chr5": 181538259,
             "chr6": 170805979, "chr7": 159345973, "chr8": 145138636, "chr9": 138394717, "chr10": 133797422,
             "chr11": 135086622, "chr12": 133275309, "chr13": 114364328, "chr14": 107043718, "chr15": 101991189,
             "chr16": 90338345, "chr17": 83257441, "chr18": 80373285, "chr19": 58617616, "chr20": 64444167,
             "chr21": 46709983, "chr22": 50818468, "chrX": 156040895, "chrY": 57227415}
CENTROMERE = {"chr1": 123.4, "chr2": 93.9, "chr3": 90.9, "chr4": 50.0, "chr5": 48.8, "chr6": 59.8, "chr7": 60.1,
              "chr8": 45.2, "chr9": 43.0, "chr10": 39.8, "chr11": 53.4, "chr12": 35.5, "chr13": 17.7, "chr14": 17.2,
              "chr15": 19.0, "chr16": 36.8, "chr17": 25.1, "chr18": 18.5, "chr19": 26.2, "chr20": 28.1, "chr21": 12.0,
              "chr22": 15.0, "chrX": 60.6, "chrY": 10.4}
GENE_COLOURS = ["#dbe9f6", "#e8f4e0", "#fbe9d9", "#efe3f5", "#f6f0d5", "#ddf1f1"]


def norm_chrom(c):
    return c if c.startswith("chr") else "chr" + c


def opener(path):
    return gzip.open(path, "rt") if path.endswith(".gz") else open(path)


def target_kind(name):
    if name.startswith("bb.") or "backbone" in name.lower():
        return "backbone"
    if name.startswith("SNPWIN:") or "snp" in name.lower() or name.startswith("het_") or re.search(r"rs\d{3,}", name):
        return "snp"
    return "exon"


def target_gene(name):
    return name.split("_exon_")[0]


# ---------------------------------------------------------------- inputs
def read_targets(paths):
    by = {}
    for path in paths:
        added = 0
        with open(path) as fh:
            for line in fh:
                p = line.rstrip("\n").split("\t")
                if len(p) < 3 or line.startswith("#") or line.startswith("track"):
                    continue
                c = norm_chrom(p[0])
                if c not in CHROM_ORDER:
                    continue
                s, e = int(p[1]), int(p[2])
                if e - s <= 1 and path != paths[0]:
                    continue
                lst = by.setdefault(c, [])
                starts = [r[0] for r in lst]
                i = bisect.bisect_left(starts, s)
                if (i < len(lst) and lst[i][0] < e) or (i > 0 and lst[i - 1][1] > s):
                    continue
                nm = p[3] if len(p) > 3 else ""
                if path != paths[0]:
                    nm = "SNPWIN:" + nm
                lst.insert(i, (s, e, nm)); added += 1
        print("[ok] targets from %s: %d added" % (os.path.basename(path), added))
    return [(c, s, e, n) for c in sorted(by, key=lambda x: CHROM_ORDER[x]) for s, e, n in by[c]]


def read_bins(json_path):
    with open(json_path) as fh:
        d = json.load(fh)
    out = []
    for b in d.get("tracks", {}).get("cnr_bins", []):
        try:
            out.append((norm_chrom(b[0]), int(b[1]), int(b[2]), b[3], float(b[4]),
                        float(b[6]) if len(b) > 6 and b[6] is not None else 1.0))
        except (ValueError, TypeError, IndexError):
            continue
    return out


def read_allelic(path, min_depth, depth_at=None):
    """het-like sites (AF 0.05-0.95, depth >= min) plus, when depth_at is given, the
    sample depth at every catalog position in it (for SNP-window depth ratios)."""
    sites = []
    with opener(path) as fh:
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
            key = (norm_chrom(p[0]), int(p[1]))
            if depth_at is not None and key in depth_at:
                depth_at[key] = dp
            if dp < min_depth:
                continue
            af = alt / float(dp)
            if 0.05 <= af <= 0.95:
                sites.append((key[0], key[1], af, dp))
    return sites


def read_background(path):
    """baf_background.tsv -> {(chrom, pos): median_depth} for positions with a cohort depth."""
    med = {}
    if not path or not os.path.isfile(path):
        return med
    with open(path) as fh:
        header = None
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            p = line.rstrip("\n").split("\t")
            if header is None:
                header = p
                continue
            row = dict(zip(header, p))
            try:
                med[(norm_chrom(row["contig"]), int(row["position"]))] = float(row["median_depth"])
            except (KeyError, ValueError):
                continue
    return med


def read_segments(path):
    segs = []
    with open(path) as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            try:
                mn = r.get("minorAlleleCopyNumber")
                segs.append((norm_chrom(r["chromosome"]), int(r["start"]), int(r["end"]), float(r["copyNumber"]),
                             float(mn) if mn not in (None, "", "NA") else None))
            except (KeyError, ValueError):
                continue
    by = {}
    for c, s, e, cn, mn in segs:
        by.setdefault(c, []).append((s, e, cn, mn))
    for c in by:
        by[c].sort()
    starts = dict((c, [x[0] for x in v]) for c, v in by.items())

    def find(c, pos):
        if c not in by:
            return None
        i = bisect.bisect_right(starts[c], pos) - 1
        return by[c][i] if i >= 0 and by[c][i][0] <= pos <= by[c][i][1] else None
    return find


# ---------------------------------------------------------------- selection and layout
def select_targets(targets, args):
    sels = []
    for a in args.arm:
        c = norm_chrom(a[:-1]); mid = int(CENTROMERE[c] * 1e6)
        lo, hi = (1, mid) if a[-1].lower() == "p" else (mid, CHROM_LEN[c])
        sels.append((a, [t for t in targets if t[0] == c and t[2] >= lo and t[1] <= hi]))
    for c in args.chrom:
        c = norm_chrom(c); sels.append((c, [t for t in targets if t[0] == c]))
    for r in args.region:
        c, rest = r.split(":"); a, b = rest.replace(",", "").split("-"); c = norm_chrom(c)
        sels.append((r.replace(":", "_").replace("-", "_"), [t for t in targets if t[0] == c and t[2] >= int(a) and t[1] <= int(b)]))
    if args.genes:
        want = [x.strip() for x in args.genes.split(",") if x.strip()]
        sel = [t for t in targets if target_kind(t[3]) == "exon" and target_gene(t[3]) in want]
        if args.flank:
            spans = {}
            for c, s, e, n in sel:
                g = target_gene(n); cur = spans.get(g, (c, s, e)); spans[g] = (c, min(cur[1], s), max(cur[2], e))
            for c, lo, hi in spans.values():
                sel += [t for t in targets if t[0] == c and target_kind(t[3]) != "exon" and t[2] >= lo - args.flank and t[1] <= hi + args.flank]
            sel = sorted(set(sel), key=lambda t: (CHROM_ORDER[t[0]], t[1]))
        sels.append(("genes_" + "_".join(want), sel))
    if args.all:
        sels.append(("all_targets", list(targets)))
    return sels


def layout(sel, gap, group_gap, snp_width, exon_width):
    xs, x, prev_key = [], 0, None
    for c, s, e, name in sel:
        kind = target_kind(name)
        key = (c, kind, target_gene(name) if kind == "exon" else kind)
        if prev_key is not None:
            x += group_gap if key != prev_key else (gap if kind != "snp" else max(4, gap // 3))
        w = snp_width if kind == "snp" else (exon_width if kind == "exon" else 100)
        xs.append((x, x + w)); x += w; prev_key = key
    return xs, x


def groups_of(sel, xs):
    groups = []
    for (c, s, e, name), (x0, x1) in zip(sel, xs):
        kind = target_kind(name)
        key = (c, kind, target_gene(name) if kind == "exon" else kind)
        if groups and groups[-1][0] == key:
            groups[-1][2] = x1; groups[-1][3] += 1; groups[-1][5] = max(groups[-1][5], e)
        else:
            groups.append([key, x0, x1, 1, s, e])
    return groups


# ---------------------------------------------------------------- drawing
def draw_panels(axes, sel, xs, ctx, args, show_gene_bands=True, colorbar=True):
    bin_by, site_by, site_pos, find_seg = ctx["bin_by"], ctx["site_by"], ctx["site_pos"], ctx["find_seg"]
    L = args.log2_lim
    dx, dy, dw, clip_lo, clip_hi = [], [], [], [], []
    win_depth = ctx.get("win_depth", {})
    sx, sy = [], []
    for (c, s, e, name), (x0, x1) in zip(sel, xs):
        found = False
        for b in bin_by.get(c, []):
            if b[1] < e and b[2] > s:
                xm = (x0 + x1) / 2.0
                if b[4] < -L:
                    clip_lo.append(xm)
                elif b[4] > L:
                    clip_hi.append(xm)
                else:
                    dx.append(xm); dy.append(b[4]); dw.append(b[5])
                found = True
                break
        if not found and (c, s, e) in win_depth:
            v = win_depth[(c, s, e)]
            xm = (x0 + x1) / 2.0
            if v < -L:
                clip_lo.append(xm)
            elif v > L:
                clip_hi.append(xm)
            else:
                sx.append(xm); sy.append(v)
    bx, by_, bd = [], [], []
    for (c, s, e, name), (x0, x1) in zip(sel, xs):
        if c not in site_pos:
            continue
        i = bisect.bisect_left(site_pos[c], s)
        while i < len(site_pos[c]) and site_pos[c][i] <= e:
            p, af, dp = site_by[c][i]
            if args.mirror_baf:
                af = 0.5 + abs(af - 0.5)
            bx.append(x0 + (x1 - x0) * min(1.0, max(0.0, (p - s) / float(max(1, e - s))))); by_.append(af); bd.append(dp); i += 1
    px = []
    for (c, s, e, name), (x0, x1) in zip(sel, xs):
        sg = find_seg(c, (s + e) // 2)
        if sg:
            px.append((x0, x1, min(args.max_cn, sg[2]), None if sg[3] is None else min(args.max_cn, sg[3])))

    groups = groups_of(sel, xs)
    gene_i = 0
    if show_gene_bands:
        for key, g0, g1, n, gs, ge in groups:
            if key[1] == "exon":
                col = GENE_COLOURS[gene_i % len(GENE_COLOURS)]; gene_i += 1
                for a in axes[:3]:
                    a.axvspan(g0 - args.gap / 2.0, g1 + args.gap / 2.0, color=col, zorder=0)
                axes[0].text((g0 + g1) / 2.0, L + 0.02, key[2], ha="center", va="bottom", fontsize=9, fontweight="bold", clip_on=False)
    a0, a1, a2 = axes[0], axes[1], axes[2]
    a0.scatter(dx, dy, s=[16 + 34 * max(0, min(1, w)) ** 2 for w in dw], color="0.25", alpha=0.85, linewidths=0, zorder=3)
    if sx:
        a0.scatter(sx, sy, s=14, color="darkorange", alpha=0.85, linewidths=0, zorder=3)
    if clip_lo:
        a0.scatter(clip_lo, [-L] * len(clip_lo), marker="v", s=34, color="firebrick", linewidths=0, zorder=4)
    if clip_hi:
        a0.scatter(clip_hi, [L] * len(clip_hi), marker="^", s=34, color="firebrick", linewidths=0, zorder=4)
    a0.axhline(0, color="black", lw=0.8)
    for y in (0.5, -0.5):
        a0.axhline(y, color="red", lw=0.8, ls="--", zorder=1)
    for y in (1.0, -1.0):
        a0.axhline(y, color="red", lw=0.6, ls=":", zorder=1)
    a0.set_ylim(-L - 0.1, L + 0.1)
    a0.set_ylabel("log2 depth ratio\n(%d CNVkit bins; %d SNP windows in orange)" % (len(dx) + len(clip_lo) + len(clip_hi), len(sx)))
    if bx:
        vmax = max(400, max(bd))
        sc = a1.scatter(bx, by_, s=26, c=bd, cmap="YlOrRd", vmin=0, vmax=vmax, edgecolors="0.35", linewidths=0.4, zorder=3)
        if colorbar:
            cax = a1.inset_axes([1.006, 0.08, 0.008, 0.84])
            cb = a1.figure.colorbar(sc, cax=cax)
            cb.set_label("read depth at site", fontsize=7); cb.ax.tick_params(labelsize=6)
    a1.axhline(0.5, color="black", lw=0.8)
    if args.mirror_baf:
        a1.set_ylim(0.45, 1.02); a1.axhline(0.67, color="0.6", lw=0.6, ls=":"); a1.axhline(0.75, color="0.6", lw=0.6, ls=":")
        a1.set_ylabel("mirrored BAF\n(%d sites; 0.67 = 1:2, 0.75 = 1:3)" % len(bx))
    else:
        a1.set_ylim(0, 1); a1.set_ylabel("BAF (%d sites)\ncolour = depth" % len(bx))
    for x0, x1, cn, mn in px:
        a2.plot([x0, x1], [cn, cn], color="royalblue", lw=3, solid_capstyle="butt", zorder=3)
        if mn is not None:
            a2.plot([x0, x1], [mn, mn], color="firebrick", lw=2.2, solid_capstyle="butt", zorder=4)
    a2.axhline(2, color="0.6", lw=0.8, ls="--"); a2.axhline(1, color="0.8", lw=0.6, ls=":")
    a2.set_ylim(-0.2, args.max_cn + 0.3); a2.set_ylabel("PURPLE CN\n(blue total, red minor)")
    # target track
    t = axes[3]; t.set_ylim(0, 1.4); t.set_yticks([])
    for (c, s, e, name), (x0, x1) in zip(sel, xs):
        kind = target_kind(name)
        if kind == "backbone":
            t.plot([x0, x1], [0.15, 0.15], color="0.5", lw=3, solid_capstyle="butt")
        elif kind == "snp":
            t.add_patch(plt.Rectangle((x0, 0.3), x1 - x0, 0.22, color="darkorange", linewidth=0))
        else:
            t.add_patch(plt.Rectangle((x0, 0.55), x1 - x0, 0.3, color="navy", linewidth=0))
    big = 10
    total_w = max(x1 for _, x1 in xs) if xs else 1
    k = 0
    for key, g0, g1, n, gs, ge in groups:
        wide = (g1 - g0) >= 0.07 * total_w
        if key[1] == "snp":
            lab = ("SNP (n=%d)" % n) if (n >= big and wide) else ""
        elif key[1] == "backbone":
            lab = ("backbone (n=%d)" % n) if (n >= big and wide) else ""
        else:
            lab = key[2]
        if lab:
            t.text((g0 + g1) / 2.0, 0.9 + 0.16 * (k % 2), lab, ha="center", va="bottom", fontsize=7.5); k += 1
        if key[1] == "exon" or (n >= big and wide):
            t.text((g0 + g1) / 2.0, 0.02, "%.2f-%.2f Mb" % (gs / 1e6, ge / 1e6), ha="center", va="bottom", fontsize=5.5, color="0.35")
    t.set_ylabel("targets", fontsize=8)
    width = max(x1 for _, x1 in xs) if xs else 1
    for a in axes:
        a.set_xlim(-args.gap, width + args.gap); a.set_xticks([])
    return len(dx) + len(clip_lo) + len(clip_hi), len(bx), len(px)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample", required=True)
    ap.add_argument("--sample-dir", required=True)
    ap.add_argument("--targets", action="append", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--allelic", default=None)
    ap.add_argument("--min-depth", type=int, default=50)
    ap.add_argument("--max-cn", type=float, default=6.0)
    ap.add_argument("--log2-lim", type=float, default=1.5)
    ap.add_argument("--style", choices=["interleaved", "grouped", "genes"], default="interleaved")
    ap.add_argument("--background", default=None, help="baf_background.tsv: cohort median depth per catalog position -> depth points on SNP windows")
    ap.add_argument("--mirror-baf", action="store_true")
    ap.add_argument("--arm", action="append", default=[])
    ap.add_argument("--chrom", action="append", default=[])
    ap.add_argument("--region", action="append", default=[])
    ap.add_argument("--genes", default="")
    ap.add_argument("--flank", type=int, default=1000000, help="for --genes and --style genes: SNP/backbone within this of a gene")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--gap", type=int, default=60)
    ap.add_argument("--group-gap", type=int, default=800)
    ap.add_argument("--snp-width", type=int, default=40)
    ap.add_argument("--exon-width", type=int, default=160)
    args = ap.parse_args()

    sd = args.sample_dir
    targets = read_targets(args.targets)
    js = [f for f in os.listdir(os.path.join(sd, "cnv_consensus_multi")) if f.endswith(".cnv_consensus4.json")]
    bins = read_bins(os.path.join(sd, "cnv_consensus_multi", js[0])) if js else []
    bin_by = {}
    for b in bins:
        bin_by.setdefault(b[0], []).append(b)
    allelic = args.allelic
    if not allelic:
        gd = os.path.join(sd, "cnv_gatk")
        cands = [f for f in (os.listdir(gd) if os.path.isdir(gd) else []) if "allelicCounts" in f]
        allelic = os.path.join(gd, cands[0]) if cands else None
    bg_median = read_background(args.background)
    depth_at = dict((k, None) for k in bg_median) if bg_median else None
    sites = read_allelic(allelic, args.min_depth, depth_at) if allelic and os.path.isfile(allelic) else []
    # per-window depth ratio for SNP windows: median over the window's positions of log2(sample / cohort median)
    win_depth = {}
    if depth_at:
        by_c = {}
        for (c, pos), dp in depth_at.items():
            if dp is not None and bg_median.get((c, pos), 0) > 0:
                by_c.setdefault(c, []).append((pos, dp / bg_median[(c, pos)]))
        for c in by_c:
            by_c[c].sort()
        import math as _m
        for c, s, e, nm in targets:
            if target_kind(nm) != "snp" or c not in by_c:
                continue
            ps = [x[0] for x in by_c[c]]
            i = bisect.bisect_left(ps, s); vals = []
            while i < len(ps) and ps[i] <= e:
                vals.append(by_c[c][i][1]); i += 1
            if vals:
                vals.sort(); r = vals[len(vals) // 2]
                if r > 0:
                    win_depth[(c, s, e)] = _m.log2(r)
    if win_depth:
        print("[ok] SNP-window depth ratios from allelic counts vs cohort median: %d windows" % len(win_depth))
    site_by = {}
    for c, p, af, dp in sites:
        site_by.setdefault(c, []).append((p, af, dp))
    for c in site_by:
        site_by[c].sort()
    site_pos = dict((c, [x[0] for x in v]) for c, v in site_by.items())
    ps = os.path.join(sd, "cnv_hmftools", "purple", "%s.purple.cnv.somatic.tsv" % args.sample)
    find_seg = read_segments(ps) if os.path.isfile(ps) else (lambda c, p: None)
    pur = {}
    pp = os.path.join(sd, "cnv_hmftools", "purple", "%s.purple.purity.tsv" % args.sample)
    if os.path.isfile(pp):
        with open(pp) as fh:
            pur = list(csv.DictReader(fh, delimiter="\t"))[0]
    ctx = dict(bin_by=bin_by, site_by=site_by, site_pos=site_pos, find_seg=find_seg, win_depth=win_depth)
    head = "%s  |  PURPLE purity %s ploidy %s %s" % (args.sample, pur.get("purity", "NA"), pur.get("ploidy", "NA"), pur.get("gender", "NA"))

    for label, sel in select_targets(targets, args):
        if not sel:
            sys.stderr.write("[warn] %s: no targets\n" % label); continue
        chroms = sorted(set(c for c, _, _, _ in sel), key=lambda c: CHROM_ORDER[c])
        if args.style == "grouped":
            order = [t for t in sel if target_kind(t[3]) == "exon"] + [t for t in sel if target_kind(t[3]) == "snp"] + [t for t in sel if target_kind(t[3]) == "backbone"]
            xs, width = layout(order, args.gap, args.group_gap * 2, args.snp_width, args.exon_width)
            fig_w = max(14, min(36, 0.06 * len(order)))
            fig, axes = plt.subplots(4, 1, figsize=(fig_w, 10), sharex=True, gridspec_kw={"height_ratios": [1.1, 1.0, 1.1, 0.55], "hspace": 0.1})
            n = draw_panels(axes, order, xs, ctx, args)
            n_ex = len([t for t in order if target_kind(t[3]) == "exon"])
            if 0 < n_ex < len(order):
                for a in axes:
                    a.axvline(xs[n_ex][0] - args.group_gap, color="0.4", lw=1.2, ls="--")
            fig.suptitle("%s  |  %s: %d targets on %s  |  grouped: genes | SNP windows | backbone" % (head, label, len(sel), ",".join(chroms)), fontsize=11)
        elif args.style == "genes":
            genes = []
            for c, s, e, nm in sel:
                if target_kind(nm) == "exon" and target_gene(nm) not in genes:
                    genes.append(target_gene(nm))
            if not genes:
                sys.stderr.write("[warn] %s: no genes for style genes\n" % label); continue
            cols = len(genes)
            fig, axes = plt.subplots(4, cols, figsize=(max(6, 5.2 * cols), 10), sharey="row", squeeze=False,
                                     gridspec_kw={"height_ratios": [1.1, 1.0, 1.1, 0.55], "hspace": 0.1, "wspace": 0.08})
            tot = (0, 0, 0)
            for j, g in enumerate(genes):
                ex = [t for t in sel if target_kind(t[3]) == "exon" and target_gene(t[3]) == g]
                c, lo, hi = ex[0][0], min(t[1] for t in ex), max(t[2] for t in ex)
                near = [t for t in targets if t[0] == c and target_kind(t[3]) != "exon" and t[2] >= lo - args.flank and t[1] <= hi + args.flank]
                col_sel = sorted(ex + near, key=lambda t: t[1])
                xs, width = layout(col_sel, args.gap, args.group_gap, args.snp_width, args.exon_width)
                n = draw_panels([axes[i][j] for i in range(4)], col_sel, xs, ctx, args, colorbar=(j == cols - 1))
                tot = tuple(a + b for a, b in zip(tot, n))
                axes[0][j].set_title("%s  (%s:%.2f-%.2f Mb, +-%.1f Mb)" % (g, c, lo / 1e6, hi / 1e6, args.flank / 1e6), fontsize=9, pad=18)
                if j:
                    for i in range(4):
                        axes[i][j].set_ylabel("")
            n = tot
            fig.suptitle("%s  |  %s: per-gene columns" % (head, label), fontsize=11)
        else:
            xs, width = layout(sel, args.gap, args.group_gap, args.snp_width, args.exon_width)
            fig_w = max(14, min(36, 0.06 * len(sel)))
            fig, axes = plt.subplots(4, 1, figsize=(fig_w, 10), sharex=True, gridspec_kw={"height_ratios": [1.1, 1.0, 1.1, 0.55], "hspace": 0.1})
            n = draw_panels(axes, sel, xs, ctx, args)
            fig.suptitle("%s  |  %s: %d targets on %s  |  genomic order" % (head, label, len(sel), ",".join(chroms)), fontsize=11)
        out = "%s.%s.%s%s.png" % (args.out, label, args.style, ".mirror" if args.mirror_baf else "")
        fig.savefig(out, dpi=130, bbox_inches="tight"); plt.close(fig)
        print("[ok] %s [%s]: %d targets, %d depth bins, %d BAF sites, %d PURPLE-covered -> %s" % (label, args.style, len(sel), n[0], n[1], n[2], out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
