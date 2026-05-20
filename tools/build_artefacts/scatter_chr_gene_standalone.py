#!/usr/bin/env python3
"""scatter_chr_gene_standalone.py — produce the resident-requested per-chromosome
exon-level scatter PDF from existing CNVKit outputs.

Port of patkarlab/MyOPool's custom_scatter_chrwise.py, restructured to:
  - Read .cnr and .cns once via pandas (5-10x faster than original line-by-line)
  - Use logging instead of print
  - Be importable as a function (so the same code can drop into 12b_cnv_plots.py)
  - Handle missing files gracefully

Visual output is intended to match the original byte-for-byte:
  - Gray scatter dots, size = weight * 50, alpha 0.5
  - Black horizontal line at y=0, red lines at y=+-0.5
  - Gray dashed vertical lines at region boundaries
  - Orange (darkorange, linewidth=3) overlay for CNS segments
  - Vertical x-tick labels at fontsize=7, format <band>_<probe_index>
  - Y-ticks every 0.5
  - Figure width: 7 (<=20 regions) / 15 (<=90) / 18 (<=150) / 24 (>150)

Usage:
  python3 scatter_chr_gene_standalone.py \\
      --sample 25NGS1307 \\
      --cnvkit-dir /goast/hemat_data/targeted-seq-pipeline/results/25NGS1307/cnvkit \\
      --regions    /home/hemat/targeted-seq-pipeline/references/myeloid/cnv_scatter_regions.txt \\
      --outdir     ~/inbox/from_claude/scatter_test
"""

import argparse
import logging
import os
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.backends.backend_pdf
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def _norm_chr(c):
    """Strip 'chr' prefix and lowercase X/Y. Matches the original's behavior."""
    c = str(c)
    c = re.sub(r"^chr", "", c, flags=re.IGNORECASE)
    c = re.sub(r"X", "x", c, flags=re.IGNORECASE)
    c = re.sub(r"Y", "y", c, flags=re.IGNORECASE)
    return c


def plot_chr_gene_scatter(cnr_path, cns_path, regions_path, output_pdf):
    """Generate the per-chromosome gene-scatter PDF.

    Each line of regions_path defines one PDF page:
      Col 1: comma-separated 'chrN:start-stop' regions
      Col 2: comma-separated 'GENE_Ex_N' band labels (one per region)
    """
    for path, label in [(cnr_path, "cnr"), (cns_path, "cns"),
                        (regions_path, "regions")]:
        if not os.path.isfile(path):
            log.error("%s file not found: %s", label, path)
            return False

    log.info("Reading %s", cnr_path)
    df_cnr = pd.read_csv(cnr_path, sep="\t")
    log.info("Reading %s", cns_path)
    df_cns = pd.read_csv(cns_path, sep="\t")

    # Drop Antitarget bins (matches the 'Antitarget' regex skip in the original)
    if "gene" in df_cnr.columns:
        df_cnr = df_cnr[
            ~df_cnr["gene"].astype(str).str.contains("Antitarget", case=False, na=False)
        ].copy()

    df_cnr["_chr_norm"] = df_cnr["chromosome"].map(_norm_chr)
    df_cns["_chr_norm"] = df_cns["chromosome"].map(_norm_chr)
    df_cnr["_midpoint"] = ((df_cnr["start"] + df_cnr["end"]) // 2).astype(int)

    pdf = matplotlib.backends.backend_pdf.PdfPages(output_pdf)
    page_count = 0

    with open(regions_path) as f:
        for raw_line in f:
            if raw_line.startswith("#") or not raw_line.strip():
                continue
            columns = raw_line.split()
            if len(columns) < 2:
                log.warning("Skipping malformed line: %.50s", raw_line)
                continue

            chr_start_stop_list = columns[0].split(",")
            band_list = columns[1].split(",")
            no_of_regions = len(chr_start_stop_list)

            if no_of_regions != len(band_list):
                log.warning(
                    "Region/band count mismatch on page %d: %d regions vs %d bands -- skipping",
                    page_count + 1, no_of_regions, len(band_list))
                continue

            # Per-page accumulators (variable names preserved from original for clarity)
            X_axis_list = []          # 1-based x indices for plotting
            X_axis_values = []        # genomic midpoints (for CNS overlay matching)
            Y_axis_list = []          # log2 values
            weights_list = []         # marker sizes (= cnr 'weight' * 50)
            color_list = []           # always 'gray'
            x_tick_list = []          # x positions for tick labels
            x_tick_labels_list = []   # tick label strings
            start_val_list = []       # region boundary x indices (start)
            stop_val_list = []        # region boundary x indices (stop)
            ci_chrstart_list = []     # CNS overlay start x indices
            ci_chrend_list = []       # CNS overlay end x indices
            cns_log2_list = []        # CNS overlay log2 levels

            x_index = 0
            chromosome = chr_start_stop_list[0].split(":")[0]  # for title

            for region_idx, region_str in enumerate(chr_start_stop_list):
                chr_part, pos_part = region_str.split(":")
                chr_name_norm = _norm_chr(chr_part)
                start_val, stop_val = map(int, pos_part.split("-"))
                band_name = band_list[region_idx]

                x_index_start = x_index

                # Vectorized filter for this region
                mask = (
                    (df_cnr["_chr_norm"] == chr_name_norm)
                    & (df_cnr["start"] >= start_val)
                    & (df_cnr["end"] <= stop_val)
                )
                sub = df_cnr.loc[mask].sort_values("start")

                tick_regions_list = []
                band_name_list_region = []
                for probe_idx, (_, row) in enumerate(sub.iterrows(), start=1):
                    x_index += 1
                    X_axis_values.append(int(row["_midpoint"]))
                    X_axis_list.append(x_index)
                    Y_axis_list.append(float(row["log2"]))
                    weights_list.append(float(row["weight"]) * 50.0)
                    color_list.append("gray")
                    tick_regions_list.append(x_index)
                    band_name_list_region.append(f"{band_name}_{probe_idx}")

                if x_index > x_index_start:
                    start_val_list.append(x_index_start + 1)
                    stop_val_list.append(x_index)
                    if no_of_regions > 1:
                        x_tick_list.extend(tick_regions_list)
                        x_tick_labels_list.extend(band_name_list_region)
                    else:
                        # Single-region page: one centered tick with the band name
                        x_tick_list.append((x_index_start + 1 + x_index) / 2)
                        x_tick_labels_list.append(band_name)

                # CNS overlay: for each segment on this chromosome, find which
                # X_axis_values midpoints fall inside it. One overlay bar per CNS row
                # that has any matching probes.
                cns_chr_mask = df_cns["_chr_norm"] == chr_name_norm
                for _, seg in df_cns.loc[cns_chr_mask].iterrows():
                    seg_start = int(seg["start"])
                    seg_end = int(seg["end"])
                    seg_log2 = float(seg["log2"])

                    matched = [
                        idx + 1
                        for idx, mid in enumerate(X_axis_values)
                        if seg_start <= mid <= seg_end
                    ]
                    if matched:
                        ci_chrstart_list.append(matched[0])
                        ci_chrend_list.append(matched[-1])
                        cns_log2_list.append(seg_log2)

            # Figure size by region count (matches original)
            if no_of_regions <= 20:
                plot_length = 7
            elif no_of_regions <= 90:
                plot_length = 15
            elif no_of_regions <= 150:
                plot_length = 18
            else:
                plot_length = 24

            fig = plt.figure(figsize=(plot_length, 5))
            plt.subplots_adjust(bottom=0.3)

            if no_of_regions == 1:
                title = f"{chromosome}:{' '.join(band_list)}"
            else:
                title = chromosome
            plt.title(title)

            if X_axis_list:
                plt.scatter(X_axis_list, Y_axis_list,
                            s=weights_list, alpha=0.5, color=color_list)

            # Y-limits clamp to +-3 but expand for outliers
            ylower, yupper = -3.0, 3.0
            for yv in Y_axis_list:
                if yv < ylower:
                    ylower = yv
                if yv > yupper:
                    yupper = yv
            plt.ylim(ylower, yupper)

            plt.axhline(y=0.0, color="black")
            plt.axhline(y=0.5, color="red")
            plt.axhline(y=-0.5, color="red")

            for sv in start_val_list:
                plt.axvline(x=sv, color="gray", linestyle="dashed")
            for sv in stop_val_list:
                plt.axvline(x=sv, color="gray", linestyle="dashed")

            for ci_s, ci_e, lv in zip(ci_chrstart_list, ci_chrend_list, cns_log2_list):
                plt.plot([ci_s, ci_e], [lv, lv],
                         color="darkorange", linewidth=3, solid_capstyle="round")

            plt.xticks(x_tick_list, x_tick_labels_list,
                       rotation="vertical", fontsize=7)
            plt.yticks(np.arange(ylower, yupper, 0.5))
            plt.ylabel("Copy ratio (log2)")

            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)
            page_count += 1

    pdf.close()
    log.info("chr-gene-scatter PDF written (%d pages): %s", page_count, output_pdf)
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample", required=True)
    ap.add_argument("--cnvkit-dir", required=True,
                    help="Directory containing <sample>.cnr and <sample>.cns")
    ap.add_argument("--regions",
                    default="/home/hemat/targeted-seq-pipeline/references/myeloid/cnv_scatter_regions.txt",
                    help="Path to the per-chromosome regions file")
    ap.add_argument("--outdir", required=True,
                    help="Directory to write <sample>_chr_gene_scatter.pdf")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    # Find inputs (prefer .final.cnr/.cns if present, fall back to .cnr/.cns)
    cnr = os.path.join(args.cnvkit_dir, f"{args.sample}.final.cnr")
    if not os.path.isfile(cnr):
        cnr = os.path.join(args.cnvkit_dir, f"{args.sample}.cnr")
    cns = os.path.join(args.cnvkit_dir, f"{args.sample}.final.cns")
    if not os.path.isfile(cns):
        cns = os.path.join(args.cnvkit_dir, f"{args.sample}.cns")

    output_pdf = os.path.join(args.outdir, f"{args.sample}_chr_gene_scatter.pdf")

    log.info("Sample:  %s", args.sample)
    log.info("CNR:     %s", cnr)
    log.info("CNS:     %s", cns)
    log.info("Regions: %s", args.regions)
    log.info("Output:  %s", output_pdf)

    ok = plot_chr_gene_scatter(cnr, cns, args.regions, output_pdf)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
