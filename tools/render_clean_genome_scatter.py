#!/usr/bin/env python3
"""
render_clean_genome_scatter.py

Render a clean genome-wide CNV scatter plot from a CNVkit .cnr file.

Why
---
CNVkit's default `cnvkit.py scatter` output (e.g. <sample>.final-scatter.png)
includes alt/decoy contigs and chrM in the x-axis layout. With the myeloid_cnv
panel BED, one alt-contig record (chr1_KI270706v1_random) is included for
sort-order reasons, and it carries a single bin that occasionally drops to
log2 ~ -5 in real samples. That single outlier forces matplotlib to extend
the y-axis to -7, compressing the entire clinically-relevant [-1, +1] range
into a sliver at the top of the plot.

This tool re-renders the genome-wide scatter from the same .cnr data with:
  - alt/decoy/chrM contigs dropped
  - y-axis hard-clipped to a clinical range (default +/- 2.5)
  - both target and backbone (Antitarget) bins shown, with slightly different
    styling so the gene-resolution data is visually distinguishable from the
    backbone tile-resolution data
  - segment overlay from the .call.cns (orange line at segment log2)
  - chromosome boundaries shown as vertical dividers, with chromosome labels

This is a strictly post-processing tool: it reads existing pipeline outputs
and writes a new PNG. It does not modify the .cnr, .cns, or any pipeline
artifact. No rerun required.

Usage
-----
    # Single sample
    python3 tools/render_clean_genome_scatter.py \\
        --cnr <outdir>/<sample>/cnv/cnvkit/<sample>.cnr \\
        --cns <outdir>/<sample>/cnv/cnvkit/<sample>.call.cns \\
        --sample <sample> \\
        --output /path/to/output.png

    # All samples in an outdir
    python3 tools/render_clean_genome_scatter.py \\
        --outdir <outdir>

    # Override y-axis clip (default 2.5)
    python3 tools/render_clean_genome_scatter.py \\
        --outdir <outdir> \\
        --ylim 3.0

Output
------
For each sample, writes:
    <outdir>/<sample>/clinical/cnvkit_plots/<sample>_genome_scatter_clean.png
"""

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# Canonical autosomes plus sex chromosomes in genomic order. Anything not in
# this list (alt contigs, decoys, chrM, unplaced) is dropped from the plot.
CANONICAL_CHROMS = (
    [f"chr{i}" for i in range(1, 23)] + ["chrX", "chrY"]
)

# Approximate hg38 chromosome lengths (bp). Used to lay out the x-axis so
# each chromosome occupies space proportional to its physical size, which is
# how cnvkit's native scatter does it. Values from UCSC hg38.
# Trimming to canonical chroms only.
HG38_LENGTHS = {
    "chr1": 248_956_422, "chr2": 242_193_529, "chr3": 198_295_559,
    "chr4": 190_214_555, "chr5": 181_538_259, "chr6": 170_805_979,
    "chr7": 159_345_973, "chr8": 145_138_636, "chr9": 138_394_717,
    "chr10": 133_797_422, "chr11": 135_086_622, "chr12": 133_275_309,
    "chr13": 114_364_328, "chr14": 107_043_718, "chr15": 101_991_189,
    "chr16": 90_338_345, "chr17": 83_257_441, "chr18": 80_373_285,
    "chr19": 58_617_616, "chr20": 64_444_167, "chr21": 46_709_983,
    "chr22": 50_818_468, "chrX": 156_040_895, "chrY": 57_227_415,
}

# Visual styling
COLOR_TARGET = "#404040"        # darker grey for gene-resolution bins
COLOR_BACKBONE = "#a0a0a0"      # lighter grey for backbone tiles
COLOR_GAIN_SEG = "#c0392b"      # red for gain segments
COLOR_LOSS_SEG = "#2471a3"      # blue for loss segments
COLOR_NEUT_SEG = "#e67e22"      # orange for neutral segments (cnvkit default)
THRESH_GAIN_SOFT = 0.20
THRESH_LOSS_SOFT = -0.25


def build_chrom_offsets(chroms_in_data):
    """
    Compute cumulative x-axis offset for each chromosome so they're laid
    out in canonical order, with width proportional to chromosome length.
    Only includes chromosomes actually present in the data.
    Returns (offsets_dict, total_genome_length, ordered_chroms_present).
    """
    ordered = [c for c in CANONICAL_CHROMS if c in chroms_in_data]
    offsets = {}
    cur = 0
    for c in ordered:
        offsets[c] = cur
        cur += HG38_LENGTHS.get(c, 0)
    return offsets, cur, ordered


def load_cnr(cnr_path):
    """Read a CNVkit .cnr file, drop non-canonical contigs, return DataFrame."""
    df = pd.read_csv(cnr_path, sep="\t")
    expected = {"chromosome", "start", "end", "gene", "log2"}
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(
            f"Missing columns in {cnr_path}: {missing}. "
            f"Got columns: {list(df.columns)}"
        )
    # Drop alt/decoy/chrM and anything not in canonical set
    n_before = len(df)
    df = df[df["chromosome"].isin(CANONICAL_CHROMS)].copy()
    n_after = len(df)
    if n_before > n_after:
        print(f"    Dropped {n_before - n_after} bins on alt/decoy/chrM contigs",
              file=sys.stderr)
    # Add an 'is_backbone' flag from the gene column
    df["is_backbone"] = df["gene"].astype(str).str.contains(
        "Antitarget", case=False, na=False
    )
    return df


def load_cns(cns_path):
    """Read a CNVkit .cns or .call.cns file, drop non-canonical contigs."""
    if cns_path is None or not Path(cns_path).is_file():
        return None
    df = pd.read_csv(cns_path, sep="\t")
    df = df[df["chromosome"].isin(CANONICAL_CHROMS)].copy()
    return df


def render_scatter(cnr_df, cns_df, sample, output_path, ylim=2.5):
    """Render the clean genome-wide scatter and save to output_path."""
    chroms_in_data = set(cnr_df["chromosome"].unique())
    offsets, total_len, ordered = build_chrom_offsets(chroms_in_data)

    # Compute genomic x-coordinate for each bin (midpoint + chromosome offset)
    cnr_df = cnr_df.copy()
    cnr_df["x"] = cnr_df.apply(
        lambda r: offsets[r["chromosome"]] + (r["start"] + r["end"]) // 2,
        axis=1,
    )
    # Clip y for plotting (we still want to see outliers, but not at the
    # cost of compressing real signal; use clipping not dropping)
    cnr_df["y_plot"] = cnr_df["log2"].clip(-ylim, ylim)

    fig, ax = plt.subplots(figsize=(16, 5))

    # Plot backbone bins first (so they sit behind target bins visually)
    backbone = cnr_df[cnr_df["is_backbone"]]
    targets = cnr_df[~cnr_df["is_backbone"]]
    ax.scatter(
        backbone["x"], backbone["y_plot"],
        s=2, c=COLOR_BACKBONE, alpha=0.35, linewidths=0,
        rasterized=True, label=f"Backbone bins (n={len(backbone):,})",
    )
    ax.scatter(
        targets["x"], targets["y_plot"],
        s=6, c=COLOR_TARGET, alpha=0.7, linewidths=0,
        rasterized=True, label=f"Target bins (n={len(targets):,})",
    )

    # Segment overlay from .call.cns
    if cns_df is not None and len(cns_df) > 0:
        for _, seg in cns_df.iterrows():
            chrom = seg["chromosome"]
            if chrom not in offsets:
                continue
            x_start = offsets[chrom] + seg["start"]
            x_end = offsets[chrom] + seg["end"]
            y = max(min(seg["log2"], ylim), -ylim)
            if seg["log2"] >= THRESH_GAIN_SOFT:
                color = COLOR_GAIN_SEG
            elif seg["log2"] <= THRESH_LOSS_SOFT:
                color = COLOR_LOSS_SEG
            else:
                color = COLOR_NEUT_SEG
            ax.plot(
                [x_start, x_end], [y, y],
                color=color, linewidth=2.0, solid_capstyle="butt",
            )

    # Chromosome dividers and labels
    for c in ordered:
        x = offsets[c] + HG38_LENGTHS[c]
        ax.axvline(x, color="black", linewidth=0.4, alpha=0.6)
    # Reference lines at y=0 and clinical thresholds
    ax.axhline(0.0, color="black", linewidth=0.6, alpha=0.8)
    ax.axhline(THRESH_GAIN_SOFT, color=COLOR_GAIN_SEG,
               linewidth=0.5, alpha=0.4, linestyle="--")
    ax.axhline(THRESH_LOSS_SOFT, color=COLOR_LOSS_SEG,
               linewidth=0.5, alpha=0.4, linestyle="--")

    # Chromosome labels at midpoints
    label_positions = [offsets[c] + HG38_LENGTHS[c] // 2 for c in ordered]
    label_texts = [c.replace("chr", "") for c in ordered]
    ax.set_xticks(label_positions)
    ax.set_xticklabels(label_texts, fontsize=9)

    ax.set_xlim(0, total_len)
    ax.set_ylim(-ylim, ylim)
    ax.set_ylabel("Copy ratio (log2)", fontsize=10)
    ax.set_xlabel("Chromosome", fontsize=10)
    ax.set_title(f"{sample} — genome-wide CNV (target + backbone bins)",
                 fontsize=11)

    # Legend
    ax.legend(loc="upper right", fontsize=8, framealpha=0.9,
              markerscale=2.5)

    # Tighten
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def process_one(cnr_path, cns_path, sample, output_path, ylim):
    """Process a single sample and return summary."""
    cnr_df = load_cnr(cnr_path)
    cns_df = load_cns(cns_path)
    render_scatter(cnr_df, cns_df, sample, output_path, ylim=ylim)
    return {
        "sample": sample,
        "n_bins": len(cnr_df),
        "n_backbone": int(cnr_df["is_backbone"].sum()),
        "n_targets": int((~cnr_df["is_backbone"]).sum()),
        "n_segments": len(cns_df) if cns_df is not None else 0,
        "output": output_path,
    }


def main():
    ap = argparse.ArgumentParser(
        description="Render a clean genome-wide CNV scatter from CNVkit .cnr.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--cnr", type=Path,
                   help="Path to a single sample's .cnr file")
    g.add_argument("--outdir", type=Path,
                   help="TSPIPE outdir; process all <sample>/cnv/cnvkit/*.cnr")
    ap.add_argument("--cns", type=Path, default=None,
                   help="Path to the matching .call.cns "
                        "(single-sample mode only). Optional.")
    ap.add_argument("--sample", type=str, default=None,
                   help="Sample name (single-sample mode; "
                        "auto-detected from filename if omitted)")
    ap.add_argument("--output", type=Path, default=None,
                   help="Output PNG path (single-sample mode). "
                        "Default: <sample>_genome_scatter_clean.png "
                        "in clinical/cnvkit_plots/")
    ap.add_argument("--ylim", type=float, default=2.5,
                   help="Y-axis clip range (symmetric). Default 2.5")
    args = ap.parse_args()

    if args.cnr:
        sample = args.sample or args.cnr.stem
        output = args.output or args.cnr.with_name(
            f"{sample}_genome_scatter_clean.png"
        )
        stats = process_one(args.cnr, args.cns, sample, output, args.ylim)
        print(f"{stats['sample']}: {stats['n_targets']} target + "
              f"{stats['n_backbone']} backbone bins, "
              f"{stats['n_segments']} segments -> {stats['output']}")
        return 0

    # --outdir mode
    if not args.outdir.is_dir():
        sys.exit(f"ERROR: not a directory: {args.outdir}")
    cnrs = sorted(args.outdir.glob("*/cnv/cnvkit/*.cnr"))
    if not cnrs:
        sys.exit(f"ERROR: no .cnr files found under "
                 f"{args.outdir}/*/cnv/cnvkit/")
    print(f"Processing {len(cnrs)} sample(s)\n")
    for cnr_path in cnrs:
        sample = cnr_path.stem
        cns_path = cnr_path.parent / f"{sample}.call.cns"
        if not cns_path.is_file():
            cns_path = None
        # Output goes into <sample>/clinical/cnvkit_plots/
        sample_root = cnr_path.parent.parent.parent  # up from cnv/cnvkit/
        output = (sample_root / "clinical" / "cnvkit_plots" /
                  f"{sample}_genome_scatter_clean.png")
        try:
            stats = process_one(cnr_path, cns_path, sample, output, args.ylim)
            print(f"  {sample}: {stats['n_targets']:,} target + "
                  f"{stats['n_backbone']:,} backbone bins, "
                  f"{stats['n_segments']} segments")
            print(f"    -> {stats['output']}")
        except Exception as e:
            print(f"  {sample}: FAILED ({e})", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main() or 0)
