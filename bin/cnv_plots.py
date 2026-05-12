#!/usr/bin/env python3
"""
12b_cnv_plots.py — Clinical-grade CNV visualization.

Generates four plot types from CNVKit output:
  1. Per-chromosome plots with log2 scatter, gene/exon annotation, and ideogram
  2. Per-gene exon-level VisCap/MLPA-style plots (critical for partial events)
  3. Genome-wide scatter with panel gene labels
  4. Gene-level summary heatmap with per-exon mini-strip

Usage:
    python 12b_cnv_plots.py \
        -s 26CGH40 \
        -o results/26CGH40/cnvkit \
        --bed bedfiles/MYOPOOL_240125_UBTF_hg38.bed \
        --cytoband references/cytoBand_hg38.txt
"""

import argparse
import logging
import os
import re
import sys
import time
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PIPELINE_DIR = os.path.dirname(SCRIPT_DIR)
DEFAULT_BED = os.path.join(PIPELINE_DIR, "bedfiles", "MYOPOOL_240125_UBTF_hg38.bed")
DEFAULT_CYTOBAND = os.path.join(PIPELINE_DIR, "references", "cytoBand_hg38.txt")

# --- Thresholds ---
THRESH_GAIN = 0.55
THRESH_LOSS = -0.55
THRESH_GAIN_SOFT = 0.20   # segment color threshold
THRESH_LOSS_SOFT = -0.25  # segment color threshold
THEO_1COPY_GAIN = 0.58
THEO_1COPY_LOSS = -1.0

# --- Colors ---
COLOR_GAIN = "#c0392b"
COLOR_LOSS = "#2471a3"
COLOR_NEUTRAL = "#2c2c2c"
COLOR_GAIN_LIGHT = "#fadbd8"
COLOR_LOSS_LIGHT = "#d4e6f1"
COLOR_NEUTRAL_LIGHT = "#d5f5e3"
COLOR_BIN = "#aaaaaa"

# Cytoband stain colors
STAIN_COLORS = {
    "gneg":    "#f5f5f5",
    "gpos25":  "#c0c0c0",
    "gpos50":  "#909090",
    "gpos75":  "#505050",
    "gpos100": "#202020",
    "acen":    "#cc3333",
    "gvar":    "#888899",
    "stalk":   "#aaaacc",
}

CHROM_ORDER = [f"chr{i}" for i in range(1, 23)] + ["chrX", "chrY"]
CHROM_RANK = {c: i for i, c in enumerate(CHROM_ORDER)}
CHROM_SIZES = {
    "chr1": 248956422, "chr2": 242193529, "chr3": 198295559,
    "chr4": 190214555, "chr5": 181538259, "chr6": 170805979,
    "chr7": 159345973, "chr8": 145138636, "chr9": 138394717,
    "chr10": 133797422, "chr11": 135086622, "chr12": 133275309,
    "chr13": 114364328, "chr14": 107043718, "chr15": 101991189,
    "chr16": 90338345, "chr17": 83257441, "chr18": 80373285,
    "chr19": 58617616, "chr20": 64444167, "chr21": 46709983,
    "chr22": 50818468, "chrX": 156040895, "chrY": 57227415,
}


def parse_args():
    ap = argparse.ArgumentParser(description="Clinical-grade CNV plots.")
    ap.add_argument("-s", "--sample", required=True)
    ap.add_argument("-o", "--outdir", required=True,
                    help="CNVKit output directory")
    ap.add_argument("--bed", default=DEFAULT_BED)
    ap.add_argument("--cytoband", default=DEFAULT_CYTOBAND,
                    help="UCSC cytoBand.txt file")
    ap.add_argument("--loo-summary", default=None,
                    help="LOO per-gene FP summary TSV (references/cnvkit_loo_summary.tsv)")
    ap.add_argument("--genemetrics", default=None,
                    help="Annotated genemetrics TSV with LOO_FP_rate and confidence")
    return ap.parse_args()


# ---------------------------------------------------------------------------
# BED parsing
# ---------------------------------------------------------------------------

def parse_bed_gene_exon(name_field):
    """Extract (gene, exon_str) from BED name column."""
    m = re.search(r"([A-Za-z][A-Za-z0-9]+)_Ex_(\w+)", name_field)
    if m:
        return m.group(1), m.group(2)
    return None, None


def exon_sort_key(exon_str):
    """Natural sort key for exon labels like 1, 1A, 1B, 1_5, 10_12, 11B_3.

    Returns tuple: (exon_number, letter_suffix, probe_sub_index)
    so Ex_1 < Ex_1_1 < Ex_1_30 < Ex_1A < Ex_1B < Ex_2 < Ex_10.
    Probes without a letter suffix sort before lettered exons.
    """
    m = re.match(r"(\d+)([A-Za-z]?)(?:_(\d+))?$", str(exon_str))
    if m:
        num = int(m.group(1))
        letter = m.group(2) if m.group(2) else ""
        sub = int(m.group(3)) if m.group(3) else -1
        # Sort: (exon_num, 0 for no-letter then sub-idx, 1 for lettered then sub-idx)
        has_letter = 1 if letter else 0
        return (num, has_letter, letter, sub)
    return (9999, 2, "", -1)


def load_bed(bed_path):
    """Load panel BED -> genes dict + bed_df."""
    rows = []
    with open(bed_path) as f:
        for line in f:
            if line.startswith(("#", "track")):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 4:
                continue
            chrom, start, end, name = parts[0], int(parts[1]), int(parts[2]), parts[3]
            gene, exon = parse_bed_gene_exon(name)
            if gene:
                rows.append({"chrom": chrom, "start": start, "end": end,
                             "gene": gene, "exon": exon})
    bed_df = pd.DataFrame(rows)
    if bed_df.empty:
        log.error("No genes parsed from BED file")
        sys.exit(1)

    genes = {}
    for gene_name, gdf in bed_df.groupby("gene"):
        chrom = gdf["chrom"].iloc[0]
        exons = defaultdict(list)
        for _, row in gdf.iterrows():
            exons[row["exon"]].append((row["start"], row["end"]))
        genes[gene_name] = {
            "chrom": chrom,
            "start": gdf["start"].min(),
            "end": gdf["end"].max(),
            "exons": dict(exons),
        }
    log.info("Parsed %d genes with %d exon targets from BED", len(genes), len(bed_df))
    return genes, bed_df


# ---------------------------------------------------------------------------
# Cytoband loading
# ---------------------------------------------------------------------------

def load_cytobands(cytoband_path):
    """Load UCSC cytoBand.txt -> dict chrom -> list of (start, end, name, stain)."""
    bands = defaultdict(list)
    with open(cytoband_path) as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) < 5:
                continue
            chrom, start, end, name, stain = parts[0], int(parts[1]), int(parts[2]), parts[3], parts[4]
            bands[chrom].append((start, end, name, stain))
    return dict(bands)


def get_cytoband_at(bands, chrom, pos):
    """Return cytoband name at a genomic position."""
    if chrom not in bands:
        return ""
    for start, end, name, stain in bands[chrom]:
        if start <= pos < end:
            return f"{chrom.replace('chr', '')}{name}"
    return ""


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_tsv(path):
    df = pd.read_csv(path, sep="\t")
    df = df[df["chromosome"].isin(CHROM_ORDER)].copy()
    df["chrom_rank"] = df["chromosome"].map(CHROM_RANK)
    df.sort_values(["chrom_rank", "start"], inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def load_cnr(path):
    return _load_tsv(path)


def load_cns(path):
    return _load_tsv(path)


def compute_genome_offsets():
    offsets = {}
    cumul = 0
    for c in CHROM_ORDER:
        offsets[c] = cumul
        cumul += CHROM_SIZES.get(c, 0)
    return offsets, cumul


def genome_x(chrom, pos, offsets):
    return offsets.get(chrom, 0) + pos


def seg_color(log2):
    """Color for segment lines (uses soft thresholds)."""
    if log2 > THRESH_GAIN_SOFT:
        return COLOR_GAIN
    if log2 < THRESH_LOSS_SOFT:
        return COLOR_LOSS
    return COLOR_NEUTRAL


def gene_shading_color(log2):
    if log2 > THRESH_GAIN_SOFT:
        return COLOR_GAIN_LIGHT
    if log2 < THRESH_LOSS_SOFT:
        return COLOR_LOSS_LIGHT
    return COLOR_NEUTRAL_LIGHT


def gene_label_color(log2):
    if log2 > THRESH_GAIN_SOFT:
        return COLOR_GAIN
    if log2 < THRESH_LOSS_SOFT:
        return COLOR_LOSS
    return "#555555"


def get_gene_segment_log2(gene_info, cns):
    chrom = gene_info["chrom"]
    mid = (gene_info["start"] + gene_info["end"]) / 2
    seg = cns[(cns["chromosome"] == chrom) &
              (cns["start"] <= mid) & (cns["end"] >= mid)]
    if not seg.empty:
        return seg.iloc[0]["log2"]
    return 0.0


def get_gene_segment_cn(gene_info, call_cns):
    chrom = gene_info["chrom"]
    mid = (gene_info["start"] + gene_info["end"]) / 2
    seg = call_cns[(call_cns["chromosome"] == chrom) &
                    (call_cns["start"] <= mid) & (call_cns["end"] >= mid)]
    if not seg.empty and "cn" in seg.columns:
        return int(seg.iloc[0]["cn"])
    return None


def load_gene_annotations(genemetrics_path=None, loo_summary_path=None):
    """Load per-gene LOO FP rate and confidence annotations.

    Returns dict: gene_name -> {fp_rate, confidence, is_noisy}
    """
    annotations = {}

    if genemetrics_path and os.path.isfile(genemetrics_path):
        df = pd.read_csv(genemetrics_path, sep="\t")
        if "clean_gene" in df.columns and "LOO_FP_rate" in df.columns:
            for gene_name, gdf in df.groupby("clean_gene"):
                fp_rate = gdf["LOO_FP_rate"].iloc[0]
                confidence = gdf["confidence"].iloc[0] if "confidence" in gdf.columns else "LOW"
                annotations[gene_name] = {
                    "fp_rate": fp_rate,
                    "confidence": confidence,
                    "is_noisy": fp_rate > 0.20,
                }
            log.info("Loaded LOO annotations for %d genes from genemetrics", len(annotations))

    if loo_summary_path and os.path.isfile(loo_summary_path):
        loo = pd.read_csv(loo_summary_path, sep="\t")
        for _, row in loo.iterrows():
            gene_name = row["gene"]
            if gene_name not in annotations:
                fp_rate = row.get("fp_any_rate", 0)
                annotations[gene_name] = {
                    "fp_rate": fp_rate,
                    "confidence": "HIGH" if fp_rate < 0.05 else ("MEDIUM" if fp_rate <= 0.20 else "LOW"),
                    "is_noisy": fp_rate > 0.20,
                }
        log.info("Total LOO annotations: %d genes", len(annotations))

    return annotations


# Confidence colors for genome-wide labels
CONF_COLORS = {
    "HIGH": "#27ae60",     # green
    "MEDIUM": "#e67e22",   # orange
    "LOW": "#e74c3c",      # red
}


def match_cnr_to_gene(cnr_target, gene_name, gene_info):
    """Find CNR bins overlapping this gene's exon intervals."""
    chrom = gene_info["chrom"]
    chrom_cnr = cnr_target[cnr_target["chromosome"] == chrom]
    if chrom_cnr.empty:
        return pd.DataFrame()

    matched = []
    for _, row in chrom_cnr.iterrows():
        bs, be = row["start"], row["end"]
        for exon_str, intervals in gene_info["exons"].items():
            for (es, ee) in intervals:
                if bs < ee and be > es:
                    matched.append({"start": bs, "end": be,
                                    "log2": row["log2"],
                                    "depth": row.get("depth", 0),
                                    "exon": exon_str})
                    break
            else:
                continue
            break
    if not matched:
        return pd.DataFrame()
    return pd.DataFrame(matched)


# ---------------------------------------------------------------------------
# Ideogram drawing helper (matplotlib-native)
# ---------------------------------------------------------------------------

def draw_ideogram(ax, chrom, bands_dict, highlight_start=None, highlight_end=None):
    """Draw a chromosome ideogram on the given axes using cytobands.

    Args:
        ax: matplotlib axes
        chrom: chromosome name (e.g. 'chr1')
        bands_dict: output of load_cytobands()
        highlight_start/end: optional region to highlight with red bracket
    """
    if chrom not in bands_dict:
        ax.set_visible(False)
        return

    band_list = bands_dict[chrom]
    chrom_end = max(e for _, e, _, _ in band_list)

    # Find centromere position
    acen_positions = [(s, e) for s, e, _, st in band_list if st == "acen"]

    # Draw bands
    MB = 1e6
    bar_height = 0.6
    y_center = 0.5

    for start, end, name, stain in band_list:
        color = STAIN_COLORS.get(stain, "#f0f0f0")
        width = (end - start) / MB
        x = start / MB

        if stain == "acen":
            # Draw centromere as triangle
            ax.add_patch(mpatches.FancyBboxPatch(
                (x, y_center - bar_height / 2), width, bar_height,
                boxstyle="round,pad=0",
                facecolor=color, edgecolor="#666666", linewidth=0.4,
                zorder=2))
        else:
            ax.add_patch(mpatches.Rectangle(
                (x, y_center - bar_height / 2), width, bar_height,
                facecolor=color, edgecolor="#999999", linewidth=0.15,
                zorder=1))

    # Chromosome outline with rounded ends
    ax.add_patch(mpatches.FancyBboxPatch(
        (0, y_center - bar_height / 2), chrom_end / MB, bar_height,
        boxstyle=mpatches.BoxStyle.Round(pad=0, rounding_size=chrom_end / MB * 0.008),
        facecolor="none", edgecolor="#333333", linewidth=0.8,
        zorder=3))

    # p/q arm labels
    if acen_positions:
        cen_mid = (acen_positions[0][0] + acen_positions[-1][1]) / 2 / MB
        ax.text(cen_mid * 0.4, y_center, "p", ha="center", va="center",
                fontsize=6, color="#666666", fontstyle="italic", zorder=4)
        ax.text(cen_mid + (chrom_end / MB - cen_mid) * 0.5, y_center, "q",
                ha="center", va="center",
                fontsize=6, color="#666666", fontstyle="italic", zorder=4)

    # Highlight region
    if highlight_start is not None and highlight_end is not None:
        hs = highlight_start / MB
        he = highlight_end / MB
        ax.axvspan(hs, he, ymin=0.05, ymax=0.95,
                   facecolor="#ff000015", edgecolor=COLOR_GAIN,
                   linewidth=1.5, linestyle="-", zorder=5)

    ax.set_xlim(0, chrom_end / MB)
    ax.set_ylim(0, 1)
    ax.set_yticks([])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.tick_params(axis="x", length=0, labelbottom=False)


# ---------------------------------------------------------------------------
# PLOT 1: Per-chromosome (3-row GridSpec: scatter + gene track + ideogram)
# ---------------------------------------------------------------------------

def plot_per_chromosome(cnr, cns, genes, sample, plot_dir, bands_dict, gene_annot=None):
    log.info("Plotting per-chromosome views...")
    chroms_with_genes = sorted(
        set(g["chrom"] for g in genes.values()),
        key=lambda c: CHROM_RANK.get(c, 99),
    )

    MB = 1e6

    for chrom in chroms_with_genes:
        chrom_cnr = cnr[cnr["chromosome"] == chrom].copy()
        chrom_cns = cns[cns["chromosome"] == chrom].copy()
        chrom_genes = {g: info for g, info in genes.items()
                       if info["chrom"] == chrom}
        if chrom_cnr.empty:
            continue

        gene_names_sorted = sorted(chrom_genes.keys(),
                                   key=lambda g: chrom_genes[g]["start"])
        gene_tag = "_".join(gene_names_sorted[:5])
        if len(gene_names_sorted) > 5:
            gene_tag += f"_+{len(gene_names_sorted) - 5}"

        # --- Figure with GridSpec: scatter (80%), gene track (12%), ideogram (8%) ---
        fig = plt.figure(figsize=(18, 8), dpi=300)
        gs = gridspec.GridSpec(3, 1, height_ratios=[8, 1.2, 0.8],
                               hspace=0.05, figure=fig)
        ax_scatter = fig.add_subplot(gs[0])
        ax_genes = fig.add_subplot(gs[1], sharex=ax_scatter)
        ax_ideo = fig.add_subplot(gs[2], sharex=ax_scatter)

        # ===== Row 1: Log2 ratio scatter =====
        cnr_mid_mb = ((chrom_cnr["start"] + chrom_cnr["end"]) / 2) / MB

        # Gray dots for all bins
        ax_scatter.scatter(cnr_mid_mb, chrom_cnr["log2"],
                           s=4, c="#b0b0b0", alpha=0.3, rasterized=True,
                           zorder=1, linewidths=0)

        # Segment means as thick colored lines
        for _, seg in chrom_cns.iterrows():
            sc = seg_color(seg["log2"])
            lw = 3.5 if abs(seg["log2"]) > THRESH_GAIN_SOFT else 2.0
            ax_scatter.plot([seg["start"] / MB, seg["end"] / MB],
                            [seg["log2"], seg["log2"]],
                            color=sc, linewidth=lw, solid_capstyle="butt", zorder=4)

        # Threshold lines
        ax_scatter.axhline(THRESH_LOSS, color=COLOR_LOSS, linewidth=1.0,
                           linestyle="--", alpha=0.7, zorder=2,
                           label=f"Het deletion ({THRESH_LOSS})")
        ax_scatter.axhline(THRESH_GAIN, color=COLOR_GAIN, linewidth=1.0,
                           linestyle="--", alpha=0.7, zorder=2,
                           label=f"Gain ({THRESH_GAIN})")
        ax_scatter.axhline(THEO_1COPY_LOSS, color="#aaaaaa", linewidth=0.6,
                           linestyle="--", alpha=0.5, zorder=2)
        ax_scatter.axhline(THEO_1COPY_GAIN, color="#aaaaaa", linewidth=0.6,
                           linestyle="--", alpha=0.5, zorder=2)
        ax_scatter.axhline(0, color="#888888", linewidth=0.4, alpha=0.4, zorder=2)

        ax_scatter.set_ylim(-2, 3)
        ax_scatter.set_ylabel("log$_2$ ratio", fontsize=10)
        ax_scatter.legend(fontsize=7, loc="upper right", framealpha=0.8)
        ax_scatter.spines["top"].set_visible(False)
        ax_scatter.spines["right"].set_visible(False)

        # Right-side threshold labels
        trans = ax_scatter.get_yaxis_transform()
        ax_scatter.text(1.01, THRESH_GAIN, f"+{THRESH_GAIN}", transform=trans,
                        fontsize=6, color=COLOR_GAIN, va="center", clip_on=False)
        ax_scatter.text(1.01, THRESH_LOSS, str(THRESH_LOSS), transform=trans,
                        fontsize=6, color=COLOR_LOSS, va="center", clip_on=False)
        ax_scatter.text(1.01, THEO_1COPY_LOSS, "hom del", transform=trans,
                        fontsize=5, color="#999999", va="center", clip_on=False)
        ax_scatter.text(1.01, THEO_1COPY_GAIN, "1-copy", transform=trans,
                        fontsize=5, color="#999999", va="center", clip_on=False)

        # Cytogenetic band info for title
        all_gene_starts = [chrom_genes[g]["start"] for g in gene_names_sorted]
        all_gene_ends = [chrom_genes[g]["end"] for g in gene_names_sorted]
        region_start = min(all_gene_starts) if all_gene_starts else 0
        region_end = max(all_gene_ends) if all_gene_ends else CHROM_SIZES.get(chrom, 0)
        band_start = get_cytoband_at(bands_dict, chrom, region_start)
        band_end = get_cytoband_at(bands_dict, chrom, region_end)
        band_info = band_start if band_start == band_end else f"{band_start}-{band_end}"

        ax_scatter.set_title(
            f"{sample} \u2014 {chrom} ({band_info})",
            fontsize=13, fontweight="bold", pad=8)

        # ===== Row 2: Gene/exon annotation track =====
        ax_genes.set_ylim(0, 1)
        ax_genes.set_yticks([])
        ax_genes.spines["top"].set_visible(False)
        ax_genes.spines["right"].set_visible(False)
        ax_genes.spines["left"].set_visible(False)

        # Stagger genes if they overlap
        n_genes = len(gene_names_sorted)
        gene_y_slots = []  # assigned y-slot for each gene
        gene_extents = []  # (start_mb, end_mb) for overlap checking
        n_rows = 1

        for gi, gene_name in enumerate(gene_names_sorted):
            ginfo = chrom_genes[gene_name]
            gs_mb = ginfo["start"] / MB
            ge_mb = ginfo["end"] / MB
            # Pad for label space
            pad = max((ge_mb - gs_mb) * 0.3, 0.5)
            gs_padded = gs_mb - pad
            ge_padded = ge_mb + pad

            # Find lowest row without overlap
            slot = 0
            for prev_gi, (ps, pe) in enumerate(gene_extents):
                if gene_y_slots[prev_gi] == slot:
                    if gs_padded < pe and ge_padded > ps:
                        slot += 1
            gene_y_slots.append(slot)
            gene_extents.append((gs_padded, ge_padded))
            n_rows = max(n_rows, slot + 1)

        # Scale y positions based on number of rows
        row_height = 1.0 / max(n_rows, 1)

        for gi, gene_name in enumerate(gene_names_sorted):
            ginfo = chrom_genes[gene_name]
            gene_log2 = get_gene_segment_log2(ginfo, cns)
            shade = gene_shading_color(gene_log2)
            lbl_c = gene_label_color(gene_log2)

            # Check LOO annotation
            annot = (gene_annot or {}).get(gene_name, {})
            is_noisy = annot.get("is_noisy", False)
            fp_rate = annot.get("fp_rate", None)

            gs_mb = ginfo["start"] / MB
            ge_mb = ginfo["end"] / MB
            slot = gene_y_slots[gi]
            y_base = 1.0 - (slot + 1) * row_height
            rect_h = row_height * 0.55
            rect_y = y_base + rect_h * 0.2

            # --- Gene rectangle with exon barcode ---
            if is_noisy:
                ax_genes.add_patch(mpatches.Rectangle(
                    (gs_mb, rect_y), ge_mb - gs_mb, rect_h,
                    facecolor="#e0e0e0", edgecolor="#999999", linewidth=0.6,
                    alpha=0.7, hatch="///", zorder=2))
            else:
                # Draw base rectangle
                ax_genes.add_patch(mpatches.Rectangle(
                    (gs_mb, rect_y), ge_mb - gs_mb, rect_h,
                    facecolor=shade, edgecolor=lbl_c, linewidth=0.6,
                    alpha=0.7, zorder=2))

            # Draw exon barcode bands inside the rectangle
            exon_sorted = sorted(ginfo["exons"].keys(), key=exon_sort_key)
            n_exons = len(exon_sorted)
            for ei, exon_str in enumerate(exon_sorted):
                intervals = ginfo["exons"][exon_str]
                for (es, ee) in intervals:
                    ex_s_mb = es / MB
                    ex_e_mb = ee / MB
                    # Alternate between darker and lighter bands
                    bar_alpha = 0.35 if ei % 2 == 0 else 0.15
                    bar_c = lbl_c if not is_noisy else "#888888"
                    ax_genes.add_patch(mpatches.Rectangle(
                        (ex_s_mb, rect_y), max(ex_e_mb - ex_s_mb, 0.02),
                        rect_h,
                        facecolor=bar_c, edgecolor="none",
                        alpha=bar_alpha, zorder=3))

            # Gene name above rectangle
            gene_mid_mb = (gs_mb + ge_mb) / 2
            label_text = gene_name
            if is_noisy:
                label_text += " NOISY"
                lbl_c = "#999999"
            ax_genes.text(gene_mid_mb, y_base + rect_h * 1.3, label_text,
                          ha="center", va="bottom",
                          fontsize=6, fontweight="bold", color=lbl_c,
                          zorder=5)

            # Exon count subscript below gene name
            exon_count_text = f"{n_exons} ex"
            ax_genes.text(gene_mid_mb, y_base + rect_h * 1.15, exon_count_text,
                          ha="center", va="bottom",
                          fontsize=3.5, color="#888888", fontstyle="italic",
                          zorder=5)

        ax_genes.tick_params(axis="x", labelbottom=False)

        # ===== Row 3: Chromosome ideogram =====
        draw_ideogram(ax_ideo, chrom, bands_dict,
                       highlight_start=region_start, highlight_end=region_end)
        ax_ideo.set_xlabel("Position (Mb)", fontsize=9)
        ax_ideo.tick_params(axis="x", labelbottom=True, labelsize=7)

        # Set x limits to full chromosome
        chrom_size_mb = CHROM_SIZES.get(chrom, 0) / MB
        ax_scatter.set_xlim(0, chrom_size_mb)

        out = os.path.join(plot_dir, f"{sample}_{chrom}_{gene_tag}.png")
        fig.savefig(out, bbox_inches="tight")
        plt.close(fig)
        log.info("  Saved %s", out)


# ---------------------------------------------------------------------------
# PLOT 2: Per-gene exon-level (VisCap/MLPA style)
# ---------------------------------------------------------------------------

def plot_per_gene(cnr_target, cns, call_cns, genes, sample, plot_dir, gene_annot=None):
    log.info("Plotting per-gene exon-level views...")

    for gene_name in sorted(genes.keys()):
        ginfo = genes[gene_name]
        gene_cnr = match_cnr_to_gene(cnr_target, gene_name, ginfo)
        if gene_cnr.empty:
            continue

        gene_log2 = get_gene_segment_log2(ginfo, cns)
        seg_cn = get_gene_segment_cn(ginfo, call_cns)

        # Sort exons and assign evenly-spaced x positions
        exon_order = sorted(gene_cnr["exon"].unique(), key=exon_sort_key)
        exon_to_idx = {e: i for i, e in enumerate(exon_order)}
        gene_cnr = gene_cnr.copy()
        gene_cnr["exon_idx"] = gene_cnr["exon"].map(exon_to_idx)
        n_exons = len(exon_order)

        fig_w = max(6, n_exons * 0.55 + 2)
        fig, ax = plt.subplots(figsize=(fig_w, 5), dpi=300)

        # Neutral zone band
        ax.axhspan(-0.2, 0.2, color="#f0f0f0", zorder=0)

        # Threshold lines
        ax.axhline(THRESH_GAIN, color=COLOR_GAIN, linewidth=1,
                   linestyle="--", alpha=0.6, zorder=2, label=f"Gain ({THRESH_GAIN})")
        ax.axhline(THRESH_LOSS, color=COLOR_LOSS, linewidth=1,
                   linestyle="--", alpha=0.6, zorder=2, label=f"Loss ({THRESH_LOSS})")
        ax.axhline(0, color="#aaaaaa", linewidth=0.5, linestyle="-",
                   alpha=0.5, zorder=2)

        # Segment mean line spanning entire gene
        ax.axhline(gene_log2, color=seg_color(gene_log2), linewidth=2.0,
                   linestyle=":", alpha=0.8, zorder=6,
                   label=f"Segment mean: {gene_log2:.3f}")

        # Individual probe dots (jittered)
        rng = np.random.default_rng(42)
        jitter = rng.uniform(-0.18, 0.18, len(gene_cnr))
        probe_colors = [COLOR_GAIN if v > THRESH_GAIN else
                        COLOR_LOSS if v < THRESH_LOSS else "#b0b0b0"
                        for v in gene_cnr["log2"].values]
        ax.scatter(gene_cnr["exon_idx"].values + jitter,
                   gene_cnr["log2"].values,
                   s=18, c=probe_colors, alpha=0.5, zorder=3, linewidths=0.3,
                   edgecolors="#888888")

        # Exon means as diamond markers connected by line
        exon_stats = gene_cnr.groupby("exon_idx")["log2"].agg(["mean", "std"])
        exon_stats = exon_stats.reindex(range(n_exons))

        # Color each diamond by its own value
        for eidx, row in exon_stats.iterrows():
            emean = row["mean"]
            if np.isnan(emean):
                continue
            if emean > THRESH_GAIN:
                mc = COLOR_GAIN
            elif emean < THRESH_LOSS:
                mc = COLOR_LOSS
            else:
                mc = "#555555"
            ax.plot(eidx, emean, "D", color=mc, markersize=8,
                    markeredgecolor="black", markeredgewidth=0.7, zorder=5)

        # Connect exon means with lines
        valid = exon_stats.dropna(subset=["mean"])
        if len(valid) > 1:
            ax.plot(valid.index, valid["mean"], "-", color="#333333",
                    linewidth=1.2, zorder=4)

        # Highlight outlier exons (|exon_mean - segment_mean| > 0.3)
        for eidx, row in exon_stats.iterrows():
            emean = row["mean"]
            if np.isnan(emean):
                continue
            if abs(emean - gene_log2) > 0.3:
                oc = COLOR_GAIN if emean > gene_log2 else COLOR_LOSS
                ax.scatter([eidx], [emean], s=140, facecolors="none",
                           edgecolors=oc, linewidths=2.5, zorder=7)
                delta = emean - gene_log2
                ax.annotate(f"\u0394{delta:+.2f}",
                            (eidx, emean),
                            textcoords="offset points",
                            xytext=(10, 8 if delta > 0 else -12),
                            fontsize=6, color=oc, fontweight="bold", zorder=7)

        # Axis formatting
        ax.set_xticks(range(n_exons))
        ax.set_xticklabels([f"Ex {e}" for e in exon_order],
                           rotation=45, ha="right", fontsize=7)
        ax.set_xlim(-0.5, n_exons - 0.5)

        data_lo = min(gene_cnr["log2"].min(), THEO_1COPY_LOSS)
        data_hi = max(gene_cnr["log2"].max(), THEO_1COPY_GAIN)
        ax.set_ylim(min(data_lo - 0.2, -1.2), max(data_hi + 0.2, 1.0))

        ax.set_ylabel("log$_2$ ratio", fontsize=10)

        # Title with gene name, coordinates, CN call, log2, FP rate
        annot = (gene_annot or {}).get(gene_name, {})
        fp_rate = annot.get("fp_rate", None)
        confidence = annot.get("confidence", None)
        is_noisy = annot.get("is_noisy", False)

        coords = f"{ginfo['chrom']}:{ginfo['start']:,}-{ginfo['end']:,}"
        title = f"{gene_name} \u2014 {coords}"
        if seg_cn is not None:
            title += f" \u2014 Segment CN={seg_cn}"
        title += f" \u2014 log2={gene_log2:.3f}"
        if fp_rate is not None:
            title += f" \u2014 LOO FP={fp_rate:.1%}"
        if confidence:
            title += f" [{confidence}]"
        if is_noisy:
            title += " \u26a0 NOISY"

        title_color = "#999999" if is_noisy else "black"
        ax.set_title(title, fontsize=11, fontweight="bold", color=title_color)

        ax.legend(fontsize=7, loc="upper right", framealpha=0.85, edgecolor="#cccccc")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        # Right-side threshold labels
        trans = ax.get_yaxis_transform()
        ax.text(1.01, THRESH_GAIN, "gain", transform=trans,
                fontsize=6, color=COLOR_GAIN, va="center", clip_on=False)
        ax.text(1.01, THRESH_LOSS, "loss", transform=trans,
                fontsize=6, color=COLOR_LOSS, va="center", clip_on=False)

        out = os.path.join(plot_dir, f"{sample}_gene_{gene_name}.png")
        fig.savefig(out, bbox_inches="tight")
        plt.close(fig)

    log.info("  Saved per-gene plots to %s/", plot_dir)


# ---------------------------------------------------------------------------
# PLOT 3: Genome-wide scatter
# ---------------------------------------------------------------------------

def plot_genome_wide(cnr, cns, genes, sample, plot_dir, bands_dict, gene_annot=None):
    log.info("Plotting genome-wide scatter...")
    offsets, total_genome = compute_genome_offsets()

    MB = 1e6

    # Pre-compute genome_x for all bins
    cnr_gx = cnr.apply(
        lambda r: genome_x(r["chromosome"], (r["start"] + r["end"]) / 2, offsets),
        axis=1,
    )

    fig = plt.figure(figsize=(22, 7), dpi=300)
    gs = gridspec.GridSpec(2, 1, height_ratios=[6, 0.6], hspace=0.02, figure=fig)
    ax = fig.add_subplot(gs[0])
    ax_ideo = fig.add_subplot(gs[1], sharex=ax)

    # Alternating chromosome bands
    for i, chrom in enumerate(CHROM_ORDER):
        if chrom not in CHROM_SIZES:
            continue
        x0 = offsets[chrom]
        x1 = x0 + CHROM_SIZES[chrom]
        color = "#e8f0fe" if i % 2 == 0 else "#f5f5f5"
        ax.axvspan(x0, x1, color=color, zorder=0)

    # Bin-level dots
    for i, chrom in enumerate(CHROM_ORDER):
        mask = cnr["chromosome"] == chrom
        if not mask.any():
            continue
        color = "#5b7fa5" if i % 2 == 0 else "#999999"
        ax.scatter(cnr_gx[mask], cnr.loc[mask, "log2"],
                   s=1.2, c=color, alpha=0.25, rasterized=True, zorder=1,
                   linewidths=0)

    # Segment overlay
    for _, seg in cns.iterrows():
        sx0 = genome_x(seg["chromosome"], seg["start"], offsets)
        sx1 = genome_x(seg["chromosome"], seg["end"], offsets)
        sc = seg_color(seg["log2"])
        ax.plot([sx0, sx1], [seg["log2"], seg["log2"]],
                color=sc, linewidth=2.5, solid_capstyle="butt", zorder=3)

    # Threshold lines
    ax.axhline(THRESH_GAIN, color=COLOR_GAIN, linewidth=0.9,
               linestyle="--", alpha=0.7, zorder=2)
    ax.axhline(THRESH_LOSS, color=COLOR_LOSS, linewidth=0.9,
               linestyle="--", alpha=0.7, zorder=2)
    ax.axhline(THEO_1COPY_GAIN, color="#aaaaaa", linewidth=0.6,
               linestyle="--", alpha=0.5, zorder=2)
    ax.axhline(THEO_1COPY_LOSS, color="#aaaaaa", linewidth=0.6,
               linestyle="--", alpha=0.5, zorder=2)
    ax.axhline(0, color="#888888", linewidth=0.4, alpha=0.4, zorder=2)

    ax.set_ylim(-2.5, 2.8)

    # Gene labels along top — colored by LOO confidence
    sorted_genes = sorted(genes.items(),
                          key=lambda x: (CHROM_RANK.get(x[1]["chrom"], 99),
                                         x[1]["start"]))
    y_label_base = 2.15
    prev_x = -np.inf
    level = 0
    for gene_name, ginfo in sorted_genes:
        gx = genome_x(ginfo["chrom"],
                       (ginfo["start"] + ginfo["end"]) / 2, offsets)
        gene_log2 = get_gene_segment_log2(ginfo, cns)

        if gx - prev_x < total_genome * 0.008:
            level = (level + 1) % 3
        else:
            level = 0
        y_pos = y_label_base + level * 0.18
        prev_x = gx

        # Use confidence color if LOO annotations available
        annot = (gene_annot or {}).get(gene_name, {})
        confidence = annot.get("confidence", None)
        if confidence and confidence in CONF_COLORS:
            lbl_color = CONF_COLORS[confidence]
        else:
            lbl_color = gene_label_color(gene_log2)
        weight = "bold" if abs(gene_log2) > THRESH_GAIN_SOFT else "normal"
        ax.text(gx, y_pos, gene_name, ha="center", va="bottom",
                fontsize=3.2, rotation=90, color=lbl_color,
                fontweight=weight, clip_on=False)

    # Legend for confidence colors if annotations available
    if gene_annot:
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], marker='o', color='w', markerfacecolor=CONF_COLORS["HIGH"],
                   label='HIGH confidence', markersize=6),
            Line2D([0], [0], marker='o', color='w', markerfacecolor=CONF_COLORS["MEDIUM"],
                   label='MEDIUM confidence', markersize=6),
            Line2D([0], [0], marker='o', color='w', markerfacecolor=CONF_COLORS["LOW"],
                   label='LOW confidence', markersize=6),
        ]
        ax.legend(handles=legend_elements, fontsize=6, loc="upper left",
                  framealpha=0.8, edgecolor="#cccccc")

    # Chromosome dividers and labels
    for chrom in CHROM_ORDER:
        if chrom in offsets:
            ax.axvline(offsets[chrom], color="#cccccc", linewidth=0.3, zorder=0)

    ax.set_xticks([offsets[c] + CHROM_SIZES[c] / 2
                   for c in CHROM_ORDER if c in CHROM_SIZES])
    ax.set_xticklabels([c.replace("chr", "") for c in CHROM_ORDER
                        if c in CHROM_SIZES], fontsize=7)
    ax.set_xlim(0, total_genome)
    ax.set_ylabel("log$_2$ ratio", fontsize=10)
    ax.set_title(f"{sample} \u2014 Genome-wide CNV Profile",
                 fontsize=13, fontweight="bold", pad=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="x", length=0)

    # Ideogram strip below
    ax_ideo.set_yticks([])
    ax_ideo.spines["top"].set_visible(False)
    ax_ideo.spines["right"].set_visible(False)
    ax_ideo.spines["left"].set_visible(False)

    bar_h = 0.6
    y_c = 0.5
    for chrom in CHROM_ORDER:
        if chrom not in bands_dict:
            continue
        off = offsets[chrom]
        for start, end, name, stain in bands_dict[chrom]:
            color = STAIN_COLORS.get(stain, "#f0f0f0")
            ax_ideo.add_patch(mpatches.Rectangle(
                (off + start, y_c - bar_h / 2), end - start, bar_h,
                facecolor=color, edgecolor="none", linewidth=0, zorder=1))
        # Chromosome outline
        csize = CHROM_SIZES.get(chrom, 0)
        ax_ideo.add_patch(mpatches.Rectangle(
            (off, y_c - bar_h / 2), csize, bar_h,
            facecolor="none", edgecolor="#888888", linewidth=0.3, zorder=2))

    ax_ideo.set_xlim(0, total_genome)
    ax_ideo.set_ylim(0, 1)
    ax_ideo.tick_params(axis="x", labelbottom=False, length=0)

    out = os.path.join(plot_dir, f"{sample}_genome_wide.png")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    log.info("  Saved %s", out)


# ---------------------------------------------------------------------------
# PLOT 4: Gene summary heatmap
# ---------------------------------------------------------------------------

def plot_gene_summary_heatmap(cnr_target, cns, call_cns, genes, sample, plot_dir):
    log.info("Plotting gene summary heatmap...")

    sorted_gene_names = sorted(
        genes.keys(),
        key=lambda g: (CHROM_RANK.get(genes[g]["chrom"], 99), genes[g]["start"]),
    )

    gene_log2s = []
    gene_cns = []
    gene_exon_means = []
    max_exons = 0

    for gene_name in sorted_gene_names:
        ginfo = genes[gene_name]
        gene_cnr = match_cnr_to_gene(cnr_target, gene_name, ginfo)
        if gene_cnr.empty:
            mean_log2 = get_gene_segment_log2(ginfo, cns)
        else:
            mean_log2 = gene_cnr["log2"].mean()
        gene_log2s.append(mean_log2)

        cn = get_gene_segment_cn(ginfo, call_cns)
        gene_cns.append(cn)

        exon_means = []
        if not gene_cnr.empty:
            exon_sorted = sorted(ginfo["exons"].keys(), key=exon_sort_key)
            for ex in exon_sorted:
                ex_data = gene_cnr[gene_cnr["exon"] == ex]
                if not ex_data.empty:
                    exon_means.append(ex_data["log2"].mean())
        gene_exon_means.append(exon_means)
        max_exons = max(max_exons, len(exon_means))

    n_genes = len(sorted_gene_names)
    gene_log2_arr = np.array(gene_log2s)

    # Exon mini-strip matrix (padded with NaN)
    exon_matrix = np.full((max(max_exons, 1), n_genes), np.nan)
    for j, emeans in enumerate(gene_exon_means):
        for i, v in enumerate(emeans):
            exon_matrix[i, j] = v

    # Figure
    fig_w = max(14, n_genes * 0.24)
    fig, (ax_gene, ax_exon) = plt.subplots(
        2, 1, figsize=(fig_w, 3.8), dpi=300,
        gridspec_kw={"height_ratios": [1, 1.5], "hspace": 0.08},
        sharex=True,
    )

    # Diverging colormap blue -> white -> red
    cmap = mcolors.LinearSegmentedColormap.from_list(
        "cnv_clinical",
        [(0.0, "#2471a3"), (0.3, "#aed6f1"),
         (0.5, "#ffffff"),
         (0.7, "#f5b7b1"), (1.0, "#c0392b")],
    )
    vmax = max(1.0, np.nanmax(np.abs(gene_log2_arr)))
    norm = mcolors.TwoSlopeNorm(vmin=-vmax, vcenter=0, vmax=vmax)

    # Row 1: Gene-level heatmap
    gene_vals = gene_log2_arr.reshape(1, -1)
    im = ax_gene.imshow(gene_vals, aspect="auto", cmap=cmap, norm=norm,
                        interpolation="nearest")
    ax_gene.set_yticks([0])
    ax_gene.set_yticklabels(["Gene\nmean"], fontsize=7)

    # CN annotations inside cells
    for j in range(n_genes):
        cn = gene_cns[j]
        if cn is not None:
            bg = gene_log2_arr[j]
            tc = "white" if abs(bg) > 0.7 else "black"
            ax_gene.text(j, 0, str(cn), ha="center", va="center",
                         fontsize=5.5, fontweight="bold", color=tc)

    # Chromosome grouping indicators
    prev_chrom = None
    toggle = 0
    chrom_spans = []
    span_start = 0
    for j, gn in enumerate(sorted_gene_names):
        gc = genes[gn]["chrom"]
        if gc != prev_chrom:
            if prev_chrom is not None:
                chrom_spans.append((span_start, j - 1, prev_chrom, toggle))
            span_start = j
            toggle = 1 - toggle
            prev_chrom = gc
    chrom_spans.append((span_start, n_genes - 1, prev_chrom, toggle))

    for s, e, chrname, tog in chrom_spans:
        color = "#d5dbdb" if tog else "#ebedef"
        rect = mpatches.Rectangle(
            (s - 0.5, -0.8), e - s + 1, 0.3,
            transform=ax_gene.transData, color=color, clip_on=False)
        ax_gene.add_patch(rect)
        mid = (s + e) / 2
        ax_gene.text(mid, -0.65, chrname.replace("chr", ""),
                     ha="center", va="center", fontsize=4, color="#555555",
                     clip_on=False)

    ax_gene.set_title(f"{sample} \u2014 Gene-level CNV Summary",
                      fontsize=12, fontweight="bold", pad=14)

    # Row 2: Per-exon mini-heatmap
    cmap_exon = cmap.copy()
    cmap_exon.set_bad(color="#f8f8f8")
    vmax_ex = max(1.0, np.nanmax(np.abs(exon_matrix[np.isfinite(exon_matrix)])) if np.any(np.isfinite(exon_matrix)) else 1.0)
    norm_ex = mcolors.TwoSlopeNorm(vmin=-vmax_ex, vcenter=0, vmax=vmax_ex)

    ax_exon.imshow(exon_matrix, aspect="auto", cmap=cmap_exon, norm=norm_ex,
                   interpolation="nearest")
    if max_exons > 0:
        ax_exon.set_yticks([0, max_exons // 2, max_exons - 1])
        ax_exon.set_yticklabels(["Ex 1", f"Ex {max_exons // 2 + 1}",
                                  f"Ex {max_exons}"], fontsize=6)
    ax_exon.set_ylabel("Exon", fontsize=7, labelpad=2)

    ax_exon.set_xticks(range(n_genes))
    ax_exon.set_xticklabels(sorted_gene_names, rotation=90, fontsize=4.5,
                            ha="center")

    cbar = fig.colorbar(im, ax=[ax_gene, ax_exon], orientation="vertical",
                        fraction=0.015, pad=0.015, shrink=0.8)
    cbar.set_label("log$_2$ ratio", fontsize=8)
    cbar.ax.tick_params(labelsize=7)

    out = os.path.join(plot_dir, f"{sample}_gene_summary_heatmap.png")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    log.info("  Saved %s", out)


# ---------------------------------------------------------------------------
# PLOT 5: Combined chromosome + gene (top: chromosome scatter, bottom: gene panels)
# ---------------------------------------------------------------------------

def plot_combined_chromosome(cnr, cnr_target, cns, call_cns, genes, sample,
                             plot_dir, bands_dict, gene_annot=None):
    """Combined chromosome + gene plot: top row shows full-chromosome scatter,
    bottom row(s) show per-gene exon-level panels with connecting lines."""
    log.info("Plotting combined chromosome+gene views...")

    MB = 1e6
    MAX_GENES_PER_ROW = 6

    chroms_with_genes = sorted(
        set(g["chrom"] for g in genes.values()),
        key=lambda c: CHROM_RANK.get(c, 99),
    )

    for chrom in chroms_with_genes:
        chrom_cnr = cnr[cnr["chromosome"] == chrom].copy()
        chrom_cns = cns[cns["chromosome"] == chrom].copy()
        chrom_genes = {g: info for g, info in genes.items()
                       if info["chrom"] == chrom}
        if chrom_cnr.empty or not chrom_genes:
            continue

        gene_names_sorted = sorted(chrom_genes.keys(),
                                   key=lambda g: chrom_genes[g]["start"])
        n_genes = len(gene_names_sorted)

        # Layout: 1 or 2 rows of gene panels
        if n_genes <= MAX_GENES_PER_ROW:
            gene_rows = [gene_names_sorted]
        else:
            mid = (n_genes + 1) // 2
            gene_rows = [gene_names_sorted[:mid], gene_names_sorted[mid:]]

        n_gene_rows = len(gene_rows)
        max_cols = max(len(r) for r in gene_rows)

        # Figure height: 40% top (scatter+gene track+ideogram), 60% bottom (gene panels)
        # Top section needs ~5 inches, each gene row needs ~4 inches
        top_height = 5.0
        gene_row_height = 4.0
        bottom_height = gene_row_height * n_gene_rows
        fig_height = top_height + bottom_height + 1.0  # +1 for connecting lines gap
        fig_height = max(12, min(16, fig_height))

        fig = plt.figure(figsize=(20, fig_height), dpi=300)

        # Master GridSpec: top section (40%), gap, bottom section (60%)
        # Top section: scatter(80%) + gene_track(12%) + ideogram(8%)
        # Bottom section: gene_rows x max_cols
        top_frac = 0.40
        bottom_frac = 0.55
        gap_frac = 0.05

        master_gs = gridspec.GridSpec(
            2, 1,
            height_ratios=[top_frac, bottom_frac + gap_frac],
            hspace=0.12,
            figure=fig,
            top=0.95, bottom=0.05,
        )

        # Top section: scatter + gene track + ideogram
        top_gs = gridspec.GridSpecFromSubplotSpec(
            3, 1, subplot_spec=master_gs[0],
            height_ratios=[8, 1.2, 0.8], hspace=0.05,
        )
        ax_scatter = fig.add_subplot(top_gs[0])
        ax_genes_track = fig.add_subplot(top_gs[1], sharex=ax_scatter)
        ax_ideo = fig.add_subplot(top_gs[2], sharex=ax_scatter)

        # Bottom section: gene panels
        bottom_gs = gridspec.GridSpecFromSubplotSpec(
            n_gene_rows, max_cols,
            subplot_spec=master_gs[1],
            hspace=0.35, wspace=0.08,
        )

        # ===== TOP: Chromosome scatter (reuse plot_per_chromosome logic) =====
        cnr_mid_mb = ((chrom_cnr["start"] + chrom_cnr["end"]) / 2) / MB

        ax_scatter.scatter(cnr_mid_mb, chrom_cnr["log2"],
                           s=4, c="#b0b0b0", alpha=0.3, rasterized=True,
                           zorder=1, linewidths=0)

        for _, seg in chrom_cns.iterrows():
            sc = seg_color(seg["log2"])
            lw = 3.5 if abs(seg["log2"]) > THRESH_GAIN_SOFT else 2.0
            ax_scatter.plot([seg["start"] / MB, seg["end"] / MB],
                            [seg["log2"], seg["log2"]],
                            color=sc, linewidth=lw, solid_capstyle="butt", zorder=4)

        ax_scatter.axhline(THRESH_LOSS, color=COLOR_LOSS, linewidth=1.0,
                           linestyle="--", alpha=0.7, zorder=2)
        ax_scatter.axhline(THRESH_GAIN, color=COLOR_GAIN, linewidth=1.0,
                           linestyle="--", alpha=0.7, zorder=2)
        ax_scatter.axhline(THEO_1COPY_LOSS, color="#aaaaaa", linewidth=0.6,
                           linestyle="--", alpha=0.5, zorder=2)
        ax_scatter.axhline(THEO_1COPY_GAIN, color="#aaaaaa", linewidth=0.6,
                           linestyle="--", alpha=0.5, zorder=2)
        ax_scatter.axhline(0, color="#888888", linewidth=0.4, alpha=0.4, zorder=2)

        ax_scatter.set_ylim(-2, 3)
        ax_scatter.set_ylabel("log$_2$ ratio", fontsize=10)
        ax_scatter.spines["top"].set_visible(False)
        ax_scatter.spines["right"].set_visible(False)

        # Right-side threshold labels
        trans = ax_scatter.get_yaxis_transform()
        ax_scatter.text(1.01, THRESH_GAIN, f"+{THRESH_GAIN}", transform=trans,
                        fontsize=6, color=COLOR_GAIN, va="center", clip_on=False)
        ax_scatter.text(1.01, THRESH_LOSS, str(THRESH_LOSS), transform=trans,
                        fontsize=6, color=COLOR_LOSS, va="center", clip_on=False)

        # Cytogenetic band info for title
        all_gene_starts = [chrom_genes[g]["start"] for g in gene_names_sorted]
        all_gene_ends = [chrom_genes[g]["end"] for g in gene_names_sorted]
        region_start = min(all_gene_starts)
        region_end = max(all_gene_ends)
        band_start = get_cytoband_at(bands_dict, chrom, region_start)
        band_end = get_cytoband_at(bands_dict, chrom, region_end)
        band_info = band_start if band_start == band_end else f"{band_start}-{band_end}"

        ax_scatter.set_title(
            f"{sample} \u2014 {chrom} ({band_info}) \u2014 Combined View",
            fontsize=13, fontweight="bold", pad=8)

        # ===== Gene track (same as per_chromosome) =====
        ax_genes_track.set_ylim(0, 1)
        ax_genes_track.set_yticks([])
        ax_genes_track.spines["top"].set_visible(False)
        ax_genes_track.spines["right"].set_visible(False)
        ax_genes_track.spines["left"].set_visible(False)

        gene_y_slots = []
        gene_extents = []
        n_rows_track = 1
        for gi, gene_name in enumerate(gene_names_sorted):
            ginfo = chrom_genes[gene_name]
            gs_mb = ginfo["start"] / MB
            ge_mb = ginfo["end"] / MB
            pad = max((ge_mb - gs_mb) * 0.3, 0.5)
            gs_padded = gs_mb - pad
            ge_padded = ge_mb + pad
            slot = 0
            for prev_gi, (ps, pe) in enumerate(gene_extents):
                if gene_y_slots[prev_gi] == slot:
                    if gs_padded < pe and ge_padded > ps:
                        slot += 1
            gene_y_slots.append(slot)
            gene_extents.append((gs_padded, ge_padded))
            n_rows_track = max(n_rows_track, slot + 1)

        row_height = 1.0 / max(n_rows_track, 1)
        # Store gene midpoints for connecting lines
        gene_mid_mbs = {}

        for gi, gene_name in enumerate(gene_names_sorted):
            ginfo = chrom_genes[gene_name]
            gene_log2 = get_gene_segment_log2(ginfo, cns)
            shade = gene_shading_color(gene_log2)
            lbl_c = gene_label_color(gene_log2)
            annot = (gene_annot or {}).get(gene_name, {})
            is_noisy = annot.get("is_noisy", False)

            gs_mb = ginfo["start"] / MB
            ge_mb = ginfo["end"] / MB
            slot = gene_y_slots[gi]
            y_base = 1.0 - (slot + 1) * row_height
            rect_h = row_height * 0.55
            rect_y = y_base + rect_h * 0.2

            gene_mid_mb = (gs_mb + ge_mb) / 2
            gene_mid_mbs[gene_name] = gene_mid_mb

            if is_noisy:
                ax_genes_track.add_patch(mpatches.Rectangle(
                    (gs_mb, rect_y), ge_mb - gs_mb, rect_h,
                    facecolor="#e0e0e0", edgecolor="#999999", linewidth=0.6,
                    alpha=0.7, hatch="///", zorder=2))
            else:
                ax_genes_track.add_patch(mpatches.Rectangle(
                    (gs_mb, rect_y), ge_mb - gs_mb, rect_h,
                    facecolor=shade, edgecolor=lbl_c, linewidth=0.6,
                    alpha=0.7, zorder=2))

            exon_sorted = sorted(ginfo["exons"].keys(), key=exon_sort_key)
            n_exons_gene = len(exon_sorted)
            for ei, exon_str in enumerate(exon_sorted):
                intervals = ginfo["exons"][exon_str]
                for (es, ee) in intervals:
                    ex_s_mb = es / MB
                    ex_e_mb = ee / MB
                    bar_alpha = 0.35 if ei % 2 == 0 else 0.15
                    bar_c = lbl_c if not is_noisy else "#888888"
                    ax_genes_track.add_patch(mpatches.Rectangle(
                        (ex_s_mb, rect_y), max(ex_e_mb - ex_s_mb, 0.02),
                        rect_h,
                        facecolor=bar_c, edgecolor="none",
                        alpha=bar_alpha, zorder=3))

            label_text = gene_name
            if is_noisy:
                label_text += " NOISY"
                lbl_c = "#999999"
            ax_genes_track.text(gene_mid_mb, y_base + rect_h * 1.3, label_text,
                                ha="center", va="bottom",
                                fontsize=6, fontweight="bold", color=lbl_c,
                                zorder=5)
            ax_genes_track.text(gene_mid_mb, y_base + rect_h * 1.15,
                                f"{n_exons_gene} ex",
                                ha="center", va="bottom",
                                fontsize=3.5, color="#888888", fontstyle="italic",
                                zorder=5)

        ax_genes_track.tick_params(axis="x", labelbottom=False)

        # ===== Ideogram =====
        draw_ideogram(ax_ideo, chrom, bands_dict,
                       highlight_start=region_start, highlight_end=region_end)
        ax_ideo.set_xlabel("Position (Mb)", fontsize=9)
        ax_ideo.tick_params(axis="x", labelbottom=True, labelsize=7)

        chrom_size_mb = CHROM_SIZES.get(chrom, 0) / MB
        ax_scatter.set_xlim(0, chrom_size_mb)

        # ===== BOTTOM: Per-gene exon-level panels =====
        # Compute shared y-axis limits across all gene panels
        all_log2_vals = []
        gene_panel_data = {}  # cache gene data for reuse
        for gene_name in gene_names_sorted:
            ginfo = chrom_genes[gene_name]
            gene_cnr = match_cnr_to_gene(cnr_target, gene_name, ginfo)
            gene_log2 = get_gene_segment_log2(ginfo, cns)
            seg_cn = get_gene_segment_cn(ginfo, call_cns)
            gene_panel_data[gene_name] = {
                "gene_cnr": gene_cnr,
                "gene_log2": gene_log2,
                "seg_cn": seg_cn,
            }
            if not gene_cnr.empty:
                all_log2_vals.extend(gene_cnr["log2"].tolist())
            all_log2_vals.append(gene_log2)

        if all_log2_vals:
            shared_ymin = min(min(all_log2_vals), THEO_1COPY_LOSS) - 0.2
            shared_ymax = max(max(all_log2_vals), THEO_1COPY_GAIN) + 0.2
            shared_ymin = min(shared_ymin, -1.2)
            shared_ymax = max(shared_ymax, 1.0)
        else:
            shared_ymin, shared_ymax = -1.5, 1.5

        gene_axes = {}  # gene_name -> ax for connecting lines
        rng = np.random.default_rng(42)

        for row_idx, row_genes in enumerate(gene_rows):
            for col_idx, gene_name in enumerate(row_genes):
                ax_gene = fig.add_subplot(bottom_gs[row_idx, col_idx])
                gene_axes[gene_name] = ax_gene

                ginfo = chrom_genes[gene_name]
                pdata = gene_panel_data[gene_name]
                gene_cnr = pdata["gene_cnr"]
                gene_log2 = pdata["gene_log2"]
                seg_cn = pdata["seg_cn"]

                if gene_cnr.empty:
                    ax_gene.text(0.5, 0.5, "No data", transform=ax_gene.transAxes,
                                 ha="center", va="center", fontsize=9, color="#999999")
                    ax_gene.set_title(gene_name, fontsize=9, fontweight="bold")
                    continue

                exon_order = sorted(gene_cnr["exon"].unique(), key=exon_sort_key)
                exon_to_idx = {e: i for i, e in enumerate(exon_order)}
                gene_cnr = gene_cnr.copy()
                gene_cnr["exon_idx"] = gene_cnr["exon"].map(exon_to_idx)
                n_exons = len(exon_order)

                # Neutral zone
                ax_gene.axhspan(-0.2, 0.2, color="#f0f0f0", zorder=0)

                # Threshold lines
                ax_gene.axhline(THRESH_GAIN, color=COLOR_GAIN, linewidth=0.8,
                                linestyle="--", alpha=0.5, zorder=2)
                ax_gene.axhline(THRESH_LOSS, color=COLOR_LOSS, linewidth=0.8,
                                linestyle="--", alpha=0.5, zorder=2)
                ax_gene.axhline(0, color="#aaaaaa", linewidth=0.4, alpha=0.4, zorder=2)

                # Segment mean line
                ax_gene.axhline(gene_log2, color=seg_color(gene_log2), linewidth=1.5,
                                linestyle=":", alpha=0.7, zorder=6)

                # Probe dots
                jitter = rng.uniform(-0.18, 0.18, len(gene_cnr))
                probe_colors = [COLOR_GAIN if v > THRESH_GAIN else
                                COLOR_LOSS if v < THRESH_LOSS else "#b0b0b0"
                                for v in gene_cnr["log2"].values]
                ax_gene.scatter(gene_cnr["exon_idx"].values + jitter,
                                gene_cnr["log2"].values,
                                s=12, c=probe_colors, alpha=0.4, zorder=3,
                                linewidths=0.2, edgecolors="#888888")

                # Exon means as diamonds
                exon_stats = gene_cnr.groupby("exon_idx")["log2"].agg(["mean", "std"])
                exon_stats = exon_stats.reindex(range(n_exons))

                for eidx, erow in exon_stats.iterrows():
                    emean = erow["mean"]
                    if np.isnan(emean):
                        continue
                    mc = COLOR_GAIN if emean > THRESH_GAIN else \
                         COLOR_LOSS if emean < THRESH_LOSS else "#555555"
                    ax_gene.plot(eidx, emean, "D", color=mc, markersize=6,
                                 markeredgecolor="black", markeredgewidth=0.5, zorder=5)

                # Connect exon means
                valid = exon_stats.dropna(subset=["mean"])
                if len(valid) > 1:
                    ax_gene.plot(valid.index, valid["mean"], "-", color="#333333",
                                 linewidth=0.9, zorder=4)

                # Outlier exons
                for eidx, erow in exon_stats.iterrows():
                    emean = erow["mean"]
                    if np.isnan(emean):
                        continue
                    if abs(emean - gene_log2) > 0.3:
                        oc = COLOR_GAIN if emean > gene_log2 else COLOR_LOSS
                        ax_gene.scatter([eidx], [emean], s=100, facecolors="none",
                                        edgecolors=oc, linewidths=2.0, zorder=7)

                # Axis formatting
                ax_gene.set_xticks(range(n_exons))
                ax_gene.set_xticklabels([f"Ex{e}" for e in exon_order],
                                        rotation=45, ha="right", fontsize=5)
                ax_gene.set_xlim(-0.5, n_exons - 0.5)
                ax_gene.set_ylim(shared_ymin, shared_ymax)
                ax_gene.spines["top"].set_visible(False)
                ax_gene.spines["right"].set_visible(False)

                # Only show y-label on leftmost panel
                if col_idx == 0:
                    ax_gene.set_ylabel("log$_2$", fontsize=8)
                else:
                    ax_gene.tick_params(axis="y", labelleft=False)

                ax_gene.tick_params(axis="y", labelsize=6)

                # Title: gene name + key info
                annot = (gene_annot or {}).get(gene_name, {})
                fp_rate = annot.get("fp_rate", None)
                title = f"{gene_name}  log2={gene_log2:.2f}"
                if seg_cn is not None:
                    title += f"  CN={seg_cn}"
                if fp_rate is not None:
                    title += f"  FP={fp_rate:.0%}"
                ax_gene.set_title(title, fontsize=8, fontweight="bold", pad=4)

            # Hide empty subplots in the last row
            for col_idx in range(len(row_genes), max_cols):
                ax_empty = fig.add_subplot(bottom_gs[row_idx, col_idx])
                ax_empty.set_visible(False)

        # ===== CONNECTING LINES: from gene position in top plot to gene panel =====
        fig.canvas.draw()  # needed to get accurate coordinate transforms

        for gene_name in gene_names_sorted:
            if gene_name not in gene_axes:
                continue
            ax_gene_panel = gene_axes[gene_name]
            if not ax_gene_panel.get_visible():
                continue

            gene_mid_mb = gene_mid_mbs[gene_name]

            # Get position in figure coordinates
            # Top: bottom of gene track at the gene's x position
            top_point_data = ax_genes_track.transData.transform((gene_mid_mb, 0.0))
            top_point_fig = fig.transFigure.inverted().transform(top_point_data)

            # Bottom: top-center of the gene panel
            bbox = ax_gene_panel.get_position()
            bottom_x = bbox.x0 + bbox.width / 2
            bottom_y = bbox.y1

            fig.add_artist(plt.Line2D(
                [top_point_fig[0], bottom_x],
                [top_point_fig[1], bottom_y],
                transform=fig.transFigure,
                color="#aaaaaa", linewidth=0.7, linestyle="--",
                alpha=0.5, zorder=0, clip_on=False,
            ))

        chrom_num = chrom.replace("chr", "")
        out = os.path.join(plot_dir, f"{sample}_combined_chr{chrom_num}.png")
        fig.savefig(out, bbox_inches="tight")
        plt.close(fig)
        log.info("  Saved %s", out)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    t0 = time.time()
    args = parse_args()
    sample = args.sample

    # Prefer .final.cnr/.final.cns (LOO-filtered) if available
    cnr_final = os.path.join(args.outdir, f"{sample}.final.cnr")
    cns_final = os.path.join(args.outdir, f"{sample}.final.cns")
    cnr_path = cnr_final if os.path.isfile(cnr_final) else os.path.join(args.outdir, f"{sample}.cnr")
    cns_path = cns_final if os.path.isfile(cns_final) else os.path.join(args.outdir, f"{sample}.cns")
    call_final = os.path.join(args.outdir, f"{sample}.final.call.cns")
    call_cns_path = call_final if os.path.isfile(call_final) else os.path.join(args.outdir, f"{sample}.call.cns")

    log.info("=== Clinical CNV Plots (12b) ===")
    log.info("Sample: %s", sample)
    log.info("CNR:    %s", cnr_path)
    log.info("CNS:    %s", cns_path)
    log.info("BED:    %s", args.bed)
    log.info("Cytoband: %s", args.cytoband)

    for f, label in [(cnr_path, "CNR"), (cns_path, "CNS"),
                     (args.bed, "BED"), (args.cytoband, "Cytoband")]:
        if not os.path.isfile(f):
            log.error("%s not found: %s", label, f)
            sys.exit(1)

    genes, bed_df = load_bed(args.bed)
    bands_dict = load_cytobands(args.cytoband)
    cnr = load_cnr(cnr_path)
    cns = load_cns(cns_path)
    call_cns = load_cns(call_cns_path) if os.path.isfile(call_cns_path) else cns
    cnr_target = cnr[cnr["gene"] != "Antitarget"].copy()

    # Load LOO annotations if available
    gene_annot = load_gene_annotations(
        genemetrics_path=args.genemetrics,
        loo_summary_path=args.loo_summary,
    )
    if gene_annot:
        log.info("LOO annotations loaded for %d genes", len(gene_annot))

    plot_dir = os.path.join(args.outdir, "plots")
    chr_dir = os.path.join(plot_dir, "per_chromosome")
    gene_dir = os.path.join(plot_dir, "per_gene")
    overview_dir = os.path.join(plot_dir, "overview")
    combined_dir = os.path.join(plot_dir, "combined")
    for d in [plot_dir, chr_dir, gene_dir, overview_dir, combined_dir]:
        os.makedirs(d, exist_ok=True)

    plot_per_chromosome(cnr, cns, genes, sample, chr_dir, bands_dict, gene_annot)
    plot_per_gene(cnr_target, cns, call_cns, genes, sample, gene_dir, gene_annot)
    plot_genome_wide(cnr, cns, genes, sample, overview_dir, bands_dict, gene_annot)
    plot_gene_summary_heatmap(cnr_target, cns, call_cns, genes, sample, overview_dir)
    plot_combined_chromosome(cnr, cnr_target, cns, call_cns, genes, sample,
                             combined_dir, bands_dict, gene_annot)

    elapsed = time.time() - t0
    log.info("All plots generated in %.0fs", elapsed)
    log.info("Output directory: %s", plot_dir)


if __name__ == "__main__":
    main()
