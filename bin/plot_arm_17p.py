#!/usr/bin/env python3
"""Dedicated 17p figure (ARM17P_V1): depth, BAF and PURPLE copy number along 17p in genomic
coordinates, with the panel genes and, when a clinical table is given, the TP53 variant VAF(s).

Inputs (all pipeline outputs; nothing recomputed)
  --consensus-json   cnv/consensus/<S>.cnv_consensus4.json  (tracks.denoised_bins, tracks.baf_sites,
                     baf_arms, segments.cnvkit, purple summary)
  --genes            cnv/consensus/<S>.cnv_consensus4.genes.tsv (panel genes on the arm) [optional; default:
                     the "genes" list inside the consensus JSON, which carries the same columns]
  --purple-somatic   <S>.purple.cnv.somatic.tsv (copyNumber, minorAlleleCopyNumber)  [optional]
  --purple-dir       PURPLE output directory; the *.purple.cnv.somatic.tsv inside it is used [optional]
  --snp-bed          catalog BED (site class by interval width: > 1 bp = SNP window, 1 bp = backbone) [optional]
  --clinical         clinical/<S>.somaticseq.clinical.final.tsv (TP53 rows -> VAF markers)     [optional]
Output: --out PNG. Python 3.6 / matplotlib 3.2 compatible (GATK container).

Tracks (top to bottom): denoised log2 copy ratio per bin with the arm median and CNVkit
segments; raw ALT fraction of every catalog site (heterozygous sites coloured by the BAF_V2
arm verdict, circles = 17p SNP windows, triangles = backbone sites) with the 0.5 +/- f/2
band; PURPLE total and minor-allele copy number; gene strip. The centromere is shaded.
"""

import argparse
import csv
import json
import sys

CEN = {"chr17": (22700000, 27400000)}
VERDICT_COLOUR = {"NEUTRAL": "#7f7f7f", "DEL": "#c0392b", "CNLOH": "#2471a3", "GAIN": "#1e8449",
                  "IMBALANCE": "#8e44ad", "INDETERMINATE": "#bdbdbd"}


def read_tsv(path):
    with open(path) as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def num(x, default=None):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def arm_bounds(arm):
    chrom, letter = "chr" + arm[:-1], arm[-1]
    c0, c1 = CEN[chrom]
    return chrom, letter, ((0, c0) if letter == "p" else (c1, 10 ** 9))


def site_classes(bed_path, chrom):
    """From the catalog BED: 1-bp intervals are backbone sites, wider intervals are SNP windows."""
    if not bed_path:
        return [], {}
    windows, backbone = [], {}
    with open(bed_path) as fh:
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if len(p) < 4 or p[0] != chrom:
                continue
            s, e = int(p[1]), int(p[2])
            if e - s == 1:
                backbone[e] = p[3]
            else:
                windows.append((s, e, p[3]))
    return windows, backbone


def classify(pos, windows, backbone):
    if pos in backbone:
        return "backbone"
    for s, e, _ in windows:
        if s < pos <= e:
            return "window"
    return "other"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--consensus-json", required=True)
    ap.add_argument("--genes", default=None)
    ap.add_argument("--purple-somatic", default=None)
    ap.add_argument("--purple-dir", default=None)
    ap.add_argument("--snp-bed", default=None)
    ap.add_argument("--clinical", default=None)
    ap.add_argument("--sample", required=True)
    ap.add_argument("--arm", default="17p")
    ap.add_argument("--gene", default="TP53", help="gene whose consensus row and variants are highlighted")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    chrom, letter, (lo, hi) = arm_bounds(args.arm)
    with open(args.consensus_json) as fh:
        cj = json.load(fh)
    tracks = cj.get("tracks", {})
    bins = [b for b in tracks.get("denoised_bins", []) if b[0] == chrom and b[2] > lo and b[1] < hi]
    sites = [s for s in tracks.get("baf_sites", []) if s[0] == chrom and lo <= s[1] < hi]
    arm_row = None
    for r in cj.get("baf_arms", []):
        if r.get("arm") == args.arm:
            arm_row = r
    if arm_row is None and cj.get("baf17p") and args.arm == "17p":
        arm_row = cj["baf17p"]
    verdict = (arm_row or {}).get("verdict", "NA")
    conf = (arm_row or {}).get("confidence", "NA")
    f_est = num((arm_row or {}).get("f_estimate"))
    n_het = (arm_row or {}).get("n_het", "?")
    cr_med = num((arm_row or {}).get("cr_median_log2"))
    colour = VERDICT_COLOUR.get(verdict, "#7f7f7f")

    gene_rows = read_tsv(args.genes) if args.genes else [dict((k, "" if v is None else str(v)) for k, v in g.items())
                                                          for g in cj.get("genes", [])]
    genes = [g for g in gene_rows if g.get("chrom") == chrom and lo <= int(float(g["start"])) < hi]
    focus = [g for g in genes if g.get("gene") == args.gene]
    focus = focus[0] if focus else None

    cnvkit_segs = [s for s in cj.get("segments", {}).get("cnvkit", []) if s.get("chromosome") == chrom]
    purple_segs = []
    purple_somatic = args.purple_somatic
    if not purple_somatic and args.purple_dir:
        import glob
        hits = sorted(glob.glob(args.purple_dir.rstrip("/") + "/*.purple.cnv.somatic.tsv")) or \
               sorted(glob.glob(args.purple_dir.rstrip("/") + "/purple/*.purple.cnv.somatic.tsv"))
        purple_somatic = hits[0] if hits else None
    if purple_somatic:
        for r in read_tsv(purple_somatic):
            if r.get("chromosome") == chrom and int(r["end"]) > lo and int(r["start"]) < hi:
                purple_segs.append((int(r["start"]), int(r["end"]), num(r.get("copyNumber")),
                                    num(r.get("minorAlleleCopyNumber"))))
    purity = (cj.get("purple") or {}).get("purity", "")
    pstatus = (cj.get("purple") or {}).get("status", "")

    variants = []
    if args.clinical:
        for r in read_tsv(args.clinical):
            if r.get("Gene") == args.gene and r.get("Chr") == chrom:
                lab = ""
                for col in ("VV_HGVSp", "CAVA_HGVSp", "HGVSp"):
                    v = r.get(col, "")
                    if v and v != "-1":
                        lab = v.split(":")[-1]
                        break
                variants.append((int(r["Start"]), num(r.get("VAF_pct"), 0.0), lab, r.get("SomaticSeq_Verdict", "")))

    windows, backbone = site_classes(args.snp_bed, chrom)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    x_max = (hi if hi < 10 ** 9 else max([b[2] for b in bins] + [s[1] for s in sites] + [1])) / 1e6
    x_lo = lo / 1e6
    fig, axes = plt.subplots(4, 1, figsize=(11, 7.2), sharex=True,
                             gridspec_kw={"height_ratios": [1.1, 1.3, 0.8, 0.28], "hspace": 0.10})
    ax_cr, ax_baf, ax_cn, ax_gene = axes

    # ---- depth ----
    if bins:
        ax_cr.scatter([(b[1] + b[2]) / 2e6 for b in bins], [b[3] for b in bins], s=7, c="#8c8c8c", linewidths=0, zorder=2)
    for s in cnvkit_segs:
        s0, s1 = max(s["start"], lo), min(s["end"], hi if hi < 10 ** 9 else s["end"])
        if s1 > s0:
            ax_cr.plot([s0 / 1e6, s1 / 1e6], [s["log2"], s["log2"]], color="#1f4e79", lw=2, zorder=3)
    if cr_med is not None:
        ax_cr.axhline(cr_med, color=colour if verdict in ("DEL", "GAIN") else "#555555", lw=1, ls="-", zorder=1)
    for y in (-0.15, 0.15):
        ax_cr.axhline(y, color="#bbbbbb", lw=0.7, ls=":", zorder=0)
    ax_cr.axhline(0, color="#999999", lw=0.7, zorder=0)
    ax_cr.set_ylabel("denoised log2 CR")
    if genes:
        ax_cr.text(0.01, 0.05, "depth bins exist only at the panel genes on this arm (%s); the SNP windows carry no depth bin" %
                   ", ".join(g["gene"] for g in genes), transform=ax_cr.transAxes, fontsize=7, color="#777777", va="bottom")
    ymax = max([abs(b[3]) for b in bins] + [0.5])
    ax_cr.set_ylim(-min(ymax * 1.15, 2.5), min(ymax * 1.15, 2.5))
    ax_cr.legend(handles=[Line2D([0], [0], marker="o", color="w", markerfacecolor="#8c8c8c", markersize=5, label="bins"),
                          Line2D([0], [0], color="#1f4e79", lw=2, label="CNVkit segments"),
                          Line2D([0], [0], color="#555555", lw=1, label="arm median %s" % ("%.2f" % cr_med if cr_med is not None else "NA"))],
                 fontsize=7, loc="upper right", ncol=3, frameon=False)

    # ---- BAF ----
    het_x, het_y, het_m, hom_x, hom_y = [], [], [], [], []
    for s in sites:
        pos, af, is_het = s[1], s[3], bool(s[5])
        if is_het:
            het_x.append(pos / 1e6); het_y.append(af)
            het_m.append("o" if classify(pos, windows, backbone) == "window" else "^")
        else:
            hom_x.append(pos / 1e6); hom_y.append(af)
    ax_baf.scatter(hom_x, hom_y, s=5, c="#d9d9d9", linewidths=0, zorder=1)
    for m in ("o", "^"):
        xs = [x for x, mm in zip(het_x, het_m) if mm == m]
        ys = [y for y, mm in zip(het_y, het_m) if mm == m]
        if xs:
            ax_baf.scatter(xs, ys, s=16 if m == "o" else 22, c=colour, marker=m, linewidths=0.3, edgecolors="white", zorder=3)
    if f_est is not None and f_est == f_est and verdict not in ("NEUTRAL", "INDETERMINATE", "NA"):
        ax_baf.axhspan(0.5 - f_est / 2, 0.5 + f_est / 2, color=colour, alpha=0.12, zorder=0)
        ax_baf.axhline(0.5 - f_est / 2, color=colour, lw=0.8, ls="--", zorder=2)
        ax_baf.axhline(0.5 + f_est / 2, color=colour, lw=0.8, ls="--", zorder=2)
    ax_baf.axhline(0.5, color="#999999", lw=0.7, zorder=0)
    for pos, vaf, lab, verd in variants:
        ax_baf.scatter([pos / 1e6], [vaf / 100.0], marker="D", s=46, c="#e60000", edgecolors="black", linewidths=0.6, zorder=5)
        ax_baf.annotate("%s %s VAF %.1f%%%s" % (args.gene, lab, vaf, "" if verd == "PASS" else " (%s)" % verd),
                        (pos / 1e6, vaf / 100.0), xytext=(6, 6), textcoords="offset points", fontsize=7.5, color="#b30000",
                        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#e60000", lw=0.6, alpha=0.9))
    ax_baf.set_ylim(-0.02, 1.02)
    ax_baf.set_ylabel("ALT fraction")
    baf_label = "BAF_V2 %s: %s%s" % (args.arm, verdict, ("?" if conf == "LOW" else ""))
    if f_est is not None and f_est == f_est:
        baf_label += "  f=%.2f" % f_est
    baf_label += "  (%s het sites, %s)" % (n_het, conf)
    handles = [Line2D([0], [0], marker="o", color="w", markerfacecolor=colour, markersize=6, label="het, 17p SNP window"),
               Line2D([0], [0], marker="^", color="w", markerfacecolor=colour, markersize=6, label="het, backbone site"),
               Line2D([0], [0], marker="o", color="w", markerfacecolor="#d9d9d9", markersize=5, label="homozygous")]
    if verdict not in ("NEUTRAL", "INDETERMINATE", "NA") and f_est is not None:
        handles.append(Patch(facecolor=colour, alpha=0.2, label="0.5 +/- f/2"))
    if variants:
        handles.append(Line2D([0], [0], marker="D", color="w", markerfacecolor="#e60000", markeredgecolor="black", markersize=6,
                              label="%s variant VAF" % args.gene))
    ax_baf.legend(handles=handles, fontsize=7, loc="upper right", ncol=len(handles), frameon=False)
    ax_baf.text(0.01, 0.97, baf_label, transform=ax_baf.transAxes, fontsize=8, va="top", ha="left", color=colour,
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=colour, lw=0.6))

    # ---- PURPLE ----
    if purple_segs:
        for s0, s1, tot, minor in purple_segs:
            s0, s1 = max(s0, lo), min(s1, hi if hi < 10 ** 9 else s1)
            if tot is not None:
                ax_cn.plot([s0 / 1e6, s1 / 1e6], [tot, tot], color="#1f77b4", lw=2.2, zorder=3)
            if minor is not None:
                ax_cn.plot([s0 / 1e6, s1 / 1e6], [minor, minor], color="#ff7f0e", lw=2.2, zorder=3)
        top = max([t for _, _, t, _ in purple_segs if t is not None] + [3.0])
        ax_cn.set_ylim(-0.15, top + 0.6)
        for y in (1, 2, 3):
            ax_cn.axhline(y, color="#dddddd", lw=0.6, zorder=0)
        ax_cn.legend(handles=[Line2D([0], [0], color="#1f77b4", lw=2.2, label="PURPLE total CN"),
                              Line2D([0], [0], color="#ff7f0e", lw=2.2, label="minor-allele CN")],
                     fontsize=7, loc="upper right", ncol=2, frameon=False)
    else:
        ax_cn.text(0.5, 0.5, "PURPLE segments not available", transform=ax_cn.transAxes, ha="center", va="center", fontsize=8, color="#888888")
    ax_cn.set_ylabel("copy number")

    # ---- genes ----
    ax_gene.set_ylim(0, 1.4)
    ax_gene.set_yticks([])
    genes.sort(key=lambda g: int(float(g["start"])))
    last_x, level = -10.0, 0
    for g in genes:
        gs, ge = int(float(g["start"])) / 1e6, int(float(g["end"])) / 1e6
        call = g.get("consensus_call", "")
        gcol = {"GAIN": "#1e8449", "LOSS": "#c0392b", "CNLOH": "#2471a3"}.get(call, "#555555")
        ax_gene.axvspan(gs, ge, ymin=0.30, ymax=0.55, color=gcol, alpha=0.9)
        mid = (gs + ge) / 2
        level = (level + 1) % 2 if mid - last_x < 0.9 else 0     # stagger neighbouring labels
        last_x = mid
        ax_gene.text(mid, 0.62 + 0.36 * level, g["gene"], ha="center", va="bottom", fontsize=7.5,
                     fontweight="bold" if g.get("gene") == args.gene else "normal", color=gcol)
        for ax in (ax_cr, ax_baf, ax_cn):
            ax.axvline((gs + ge) / 2, color=gcol, lw=0.6, ls=":", alpha=0.7, zorder=0)
    # centromere
    for ax in (ax_cr, ax_baf, ax_cn, ax_gene):
        ax.axvspan(CEN[chrom][0] / 1e6, x_max + 0.5, color="#000000", alpha=0.06, zorder=0)
    ax_gene.set_xlim(x_lo - 0.2, x_max + 0.4)
    ax_gene.set_xlabel("%s position (Mb, hg38)" % chrom)
    ax_gene.text(CEN[chrom][0] / 1e6 + 0.05, 0.5, "cen", fontsize=7, va="center", color="#666666")

    # ---- title ----
    bits = ["%s  |  %s" % (args.sample, args.arm)]
    if focus:
        bits.append("%s consensus %s%s [%s]" % (args.gene, focus.get("consensus_call", ""),
                                                 (" " + focus["tier"]) if focus.get("tier") not in ("", "NA") else "",
                                                 focus.get("flags", "")))
        if focus.get("h_cn_min"):
            bits.append("PURPLE %s / minor %s" % (focus.get("h_cn_min"), focus.get("h_macn_min")))
    if purity:
        bits.append("purity %s (%s)" % (purity, pstatus))
    fig.suptitle("   |   ".join(bits), fontsize=10, y=0.985)
    fig.subplots_adjust(top=0.94, bottom=0.07, left=0.07, right=0.98)
    fig.savefig(args.out, dpi=140, bbox_inches="tight")
    print("[ok] %s: %s figure -> %s (%d bins, %d sites, %d het, %d genes, %d %s variant(s))" % (
        args.sample, args.arm, args.out, len(bins), len(sites), len(het_x), len(genes), len(variants), args.gene))


if __name__ == "__main__":
    sys.exit(main())
