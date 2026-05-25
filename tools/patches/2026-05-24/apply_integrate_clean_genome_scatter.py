#!/usr/bin/env python3
"""
apply_integrate_clean_genome_scatter.py

Integrate the clean genome-wide CNV scatter (originally a post-processing
tool at tools/render_clean_genome_scatter.py) into the CNV_PLOTS pipeline
step, so it is produced automatically on every TSPIPE run.

What it does
------------
Patches bin/cnv_plots.py to:
  1. Add plot_genome_wide_clean() function definition just before main().
  2. Add a single call line in main() right after the existing
     plot_genome_wide(...) call, writing into overview_dir alongside the
     existing <sample>_genome_wide.png.

The new plot lives at:
  plots/overview/<sample>_genome_scatter_clean.png

ORGANIZE_OUTPUT already globs *.png from the overview directory into
clinical/cnvkit_plots/overview/, so the new file propagates to the
clinical deliverable folder automatically.

Why a separate function
-----------------------
plot_genome_wide() (the existing one) is gene-clustered: it labels panel
genes and the visual emphasis is on gene-resolution events. That has its
place. plot_genome_wide_clean() is bin-level genome-wide signal with
target + backbone bins visible in different styles, y-axis clipped to a
clinical range so chromosome-arm events read clearly. Both plots are
useful in different ways; they are siblings, not replacements.

Existing already-completed runs
-------------------------------
For runs completed before this patch, regenerate the clean scatter
without re-running the pipeline:

    python3 tools/render_clean_genome_scatter.py --outdir <RUN_DIR>

Safety
------
- Backup with timestamp.
- Idempotent: re-running after a successful apply prints "already
  applied" and exits 0.
- Dry-run via --dry-run.
- Anchor strings are exact-match; if cnv_plots.py changes shape in the
  future (e.g., main() body refactored), the script exits with a clear
  error instead of corrupting the file.

Usage
-----
    python3 tools/patches/2026-05-24/apply_integrate_clean_genome_scatter.py --dry-run
    python3 tools/patches/2026-05-24/apply_integrate_clean_genome_scatter.py
"""

import argparse
import shutil
import sys
import time
from pathlib import Path


CNV_PLOTS_PY = Path("/goast/hemat_data/nf-core-tspipe/bin/cnv_plots.py")
SENTINEL = "def plot_genome_wide_clean"


# The new function. Uses module-level imports already present in
# cnv_plots.py: os, matplotlib.pyplot as plt, pandas as pd, numpy as np,
# log = logging.getLogger(__name__), THRESH_GAIN_SOFT, THRESH_LOSS_SOFT,
# COLOR_GAIN, COLOR_LOSS.
FUNCTION_BLOCK = '''
# ----------------------------------------------------------------------
# Clean genome-wide scatter (added 2026-05-24)
#
# Renders a genome-wide log2 scatter that:
#   - excludes alt/decoy/chrM contigs (defensive; the current panel BED
#     no longer contains any, but the function would also tolerate a
#     future panel that did)
#   - clips the y-axis to a clinical range (default +/- 2.5) so the
#     [-1, +1] region is fully readable
#   - shows target bins (gene-resolution) and backbone bins (Antitarget)
#     in different styles, so the genome-wide coverage from the backbone
#     PoN is visible without overwhelming the gene-level signal
#   - overlays segment calls from the .call.cns
#
# Output: <plot_dir>/<sample>_genome_scatter_clean.png
# ----------------------------------------------------------------------

GENOME_CLEAN_CANONICAL_CHROMS = (
    ["chr%d" % i for i in range(1, 23)] + ["chrX", "chrY"]
)

# Approximate hg38 chromosome lengths from UCSC (bp). Used to lay out
# the x-axis with chromosomes sized by physical length.
GENOME_CLEAN_HG38_LENGTHS = {
    "chr1": 248956422, "chr2": 242193529, "chr3": 198295559,
    "chr4": 190214555, "chr5": 181538259, "chr6": 170805979,
    "chr7": 159345973, "chr8": 145138636, "chr9": 138394717,
    "chr10": 133797422, "chr11": 135086622, "chr12": 133275309,
    "chr13": 114364328, "chr14": 107043718, "chr15": 101991189,
    "chr16": 90338345, "chr17": 83257441, "chr18": 80373285,
    "chr19": 58617616, "chr20": 64444167, "chr21": 46709983,
    "chr22": 50818468, "chrX": 156040895, "chrY": 57227415,
}


def plot_genome_wide_clean(cnr, cns, sample, plot_dir, ylim=2.5):
    """
    Render a clinically-useful genome-wide scatter: target + backbone
    bins, y-axis clipped to a clinical range, segment overlay.

    Parameters
    ----------
    cnr : pandas.DataFrame
        CNVkit .cnr (must have columns chromosome, start, end, gene, log2).
    cns : pandas.DataFrame
        Segment calls (.call.cns preferred). May be None.
    sample : str
        Sample id, used in filename and title.
    plot_dir : str
        Output directory.
    ylim : float
        Symmetric y-axis range. Bins outside [-ylim, +ylim] are clipped
        to the chart edge (not dropped), so true outliers are still
        visible without compressing the rest of the data.
    """
    log.info("Plotting clean genome-wide scatter (target + backbone)...")

    df = cnr[cnr["chromosome"].isin(GENOME_CLEAN_CANONICAL_CHROMS)].copy()
    n_dropped = len(cnr) - len(df)
    if n_dropped > 0:
        log.info("  Dropped %d bins on non-canonical contigs", n_dropped)

    df["is_backbone"] = df["gene"].astype(str).str.contains(
        "Antitarget", case=False, na=False
    )

    chroms_present = set(df["chromosome"].unique())
    ordered = [c for c in GENOME_CLEAN_CANONICAL_CHROMS if c in chroms_present]
    offsets = {}
    cur = 0
    for c in ordered:
        offsets[c] = cur
        cur += GENOME_CLEAN_HG38_LENGTHS.get(c, 0)
    total_len = cur

    df["x"] = df.apply(
        lambda r: offsets[r["chromosome"]] + (r["start"] + r["end"]) // 2,
        axis=1,
    )
    df["y_plot"] = df["log2"].clip(-ylim, ylim)

    fig, ax = plt.subplots(figsize=(16, 5))

    backbone = df[df["is_backbone"]]
    targets = df[~df["is_backbone"]]
    ax.scatter(
        backbone["x"], backbone["y_plot"],
        s=2, c="#a0a0a0", alpha=0.35, linewidths=0,
        rasterized=True,
        label="Backbone bins (n=%d)" % len(backbone),
    )
    ax.scatter(
        targets["x"], targets["y_plot"],
        s=6, c="#404040", alpha=0.7, linewidths=0,
        rasterized=True,
        label="Target bins (n=%d)" % len(targets),
    )

    if cns is not None and len(cns) > 0:
        for _, seg in cns.iterrows():
            chrom = seg["chromosome"]
            if chrom not in offsets:
                continue
            x_start = offsets[chrom] + seg["start"]
            x_end = offsets[chrom] + seg["end"]
            y = max(min(seg["log2"], ylim), -ylim)
            if seg["log2"] >= THRESH_GAIN_SOFT:
                color = COLOR_GAIN
            elif seg["log2"] <= THRESH_LOSS_SOFT:
                color = COLOR_LOSS
            else:
                color = "#e67e22"
            ax.plot([x_start, x_end], [y, y],
                    color=color, linewidth=2.0, solid_capstyle="butt")

    for c in ordered:
        x = offsets[c] + GENOME_CLEAN_HG38_LENGTHS[c]
        ax.axvline(x, color="black", linewidth=0.4, alpha=0.6)
    ax.axhline(0.0, color="black", linewidth=0.6, alpha=0.8)
    ax.axhline(THRESH_GAIN_SOFT, color=COLOR_GAIN,
               linewidth=0.5, alpha=0.4, linestyle="--")
    ax.axhline(THRESH_LOSS_SOFT, color=COLOR_LOSS,
               linewidth=0.5, alpha=0.4, linestyle="--")

    label_positions = [
        offsets[c] + GENOME_CLEAN_HG38_LENGTHS[c] // 2 for c in ordered
    ]
    label_texts = [c.replace("chr", "") for c in ordered]
    ax.set_xticks(label_positions)
    ax.set_xticklabels(label_texts, fontsize=9)

    ax.set_xlim(0, total_len)
    ax.set_ylim(-ylim, ylim)
    ax.set_ylabel("Copy ratio (log2)", fontsize=10)
    ax.set_xlabel("Chromosome", fontsize=10)
    ax.set_title("%s - genome-wide CNV (target + backbone bins)" % sample,
                 fontsize=11)
    ax.legend(loc="upper right", fontsize=8, framealpha=0.9, markerscale=2.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    out = os.path.join(plot_dir, "%s_genome_scatter_clean.png" % sample)
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    log.info("  Saved: %s", out)


'''


# One line added in main() right after the existing plot_genome_wide(...)
# call. Indented with 4 spaces to match the surrounding code.
CALL_BLOCK = "    plot_genome_wide_clean(cnr, cns, sample, overview_dir)\n"

ANCHOR_FUNCTION = "\ndef main():\n"
ANCHOR_CALL = (
    "    plot_genome_wide(cnr, cns, genes, sample, "
    "overview_dir, bands_dict, gene_annot)\n"
)


def main():
    ap = argparse.ArgumentParser(
        description=(
            "Patch bin/cnv_plots.py to add plot_genome_wide_clean() "
            "and wire it into main()."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--dry-run", action="store_true",
                    help="Print what would change without writing.")
    args = ap.parse_args()

    if not CNV_PLOTS_PY.is_file():
        sys.exit("ERROR: not found: %s" % CNV_PLOTS_PY)

    text = CNV_PLOTS_PY.read_text()

    if SENTINEL in text:
        print("Patch already applied (sentinel '%s' present in %s)."
              % (SENTINEL, CNV_PLOTS_PY.name))
        print("Nothing to do.")
        return 0

    # Verify anchors before modifying anything
    if ANCHOR_FUNCTION not in text:
        sys.exit("ERROR: could not find anchor '\\ndef main():\\n' in %s. "
                 "File structure may have changed." % CNV_PLOTS_PY.name)
    if ANCHOR_CALL not in text:
        sys.exit("ERROR: could not find anchor for plot_genome_wide() call. "
                 "main() body may have been refactored.")

    # Perform substitution
    new_text = text.replace(
        ANCHOR_FUNCTION,
        FUNCTION_BLOCK + ANCHOR_FUNCTION,
    )
    new_text = new_text.replace(
        ANCHOR_CALL,
        ANCHOR_CALL + CALL_BLOCK,
    )

    # Sanity check: SENTINEL should now be present
    if SENTINEL not in new_text:
        sys.exit("ERROR: post-substitution text does not contain sentinel. "
                 "Something went wrong; not writing.")
    # Sanity check: the call line should be present exactly once
    if new_text.count(CALL_BLOCK) != 1:
        sys.exit("ERROR: call block appears %d times after substitution "
                 "(expected 1). Not writing."
                 % new_text.count(CALL_BLOCK))

    print("File:        %s" % CNV_PLOTS_PY)
    print("Size before: %d bytes" % len(text))
    print("Size after:  %d bytes" % len(new_text))
    print("Delta:       +%d bytes" % (len(new_text) - len(text)))

    if args.dry_run:
        print("\nDRY-RUN: nothing written. Use without --dry-run to apply.")
        return 0

    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = CNV_PLOTS_PY.with_name(
        CNV_PLOTS_PY.name + ".bak_apply_clean_scatter_%s" % ts
    )
    shutil.copy2(CNV_PLOTS_PY, bak)
    CNV_PLOTS_PY.write_text(new_text)

    print()
    print("Backup:      %s" % bak)
    print("Patched:     %s" % CNV_PLOTS_PY)
    print()
    print("Next steps:")
    print("  - For the existing run (no re-run needed):")
    print("      python3 tools/render_clean_genome_scatter.py --outdir <RUN_DIR>")
    print("  - For future TSPIPE runs: just run the pipeline. The new plot")
    print("    will land at:")
    print("      <outdir>/<sample>/clinical/cnvkit_plots/overview/")
    print("        <sample>_genome_scatter_clean.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
