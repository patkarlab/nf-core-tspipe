#!/usr/bin/env python3
"""
12c_cnv_loo_qc.py — Leave-One-Out CNV noise assessment.

For each normal in the PON:
  1. Build a temporary reference from the OTHER N-1 normals
  2. Run cnvkit.py fix + segment on the held-out normal
  3. Collect per-bin log2 ratios and segment calls (false positives in normals)

After all iterations, generate:
  - Per-bin noise profile (mean/stdev of log2; bins with stdev > 0.3 are noisy)
  - Per-gene false positive rate
  - Blacklist BED (bins called CNV in >10% of normals)
  - Summary heatmap (normals x genes, colored by log2)

Usage:
    python 12c_cnv_loo_qc.py \\
        --cov-dir results/cnvkit_pon_build \\
        --bed bedfiles/MYOPOOL_240125_UBTF_hg38.bed \\
        -o results/cnvkit_loo_qc \\
        -j 16
"""

import argparse
import glob
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
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
DEFAULT_COV_DIR = os.path.join(PIPELINE_DIR, "results", "cnvkit_pon_build")

# Thresholds matching 12_cnv_calling.py
CALL_THRESHOLDS = "-1.1,-0.25,0.2,0.7"
THRESH_GAIN = 0.40
THRESH_LOSS = -0.55
NOISE_STDEV_THRESH = 0.3
BLACKLIST_FP_RATE = 0.10  # 10% of normals

CHROM_ORDER = [f"chr{i}" for i in range(1, 23)] + ["chrX", "chrY"]
CHROM_RANK = {c: i for i, c in enumerate(CHROM_ORDER)}


def parse_args():
    ap = argparse.ArgumentParser(
        description="Leave-One-Out CNV noise assessment for PON QC.")
    ap.add_argument("--cov-dir", default=DEFAULT_COV_DIR,
                    help="Directory with *.targetcoverage.cnn and *.antitargetcoverage.cnn")
    ap.add_argument("--bed", default=DEFAULT_BED,
                    help="Panel BED file for gene annotation")
    ap.add_argument("-o", "--outdir", default="results/cnvkit_loo_qc",
                    help="Output directory")
    ap.add_argument("-j", "--jobs", type=int, default=8,
                    help="Parallel LOO iterations (default: 8)")
    ap.add_argument("--fasta", default=None,
                    help="Reference FASTA (optional; cnvkit reference works without it)")
    ap.add_argument("-y", "--male-reference", action="store_true",
                    help="Use male reference (haploid X) for CNVKit calls")
    return ap.parse_args()


# ---------------------------------------------------------------------------
# BED parsing (reused from 12b)
# ---------------------------------------------------------------------------

def parse_bed_gene_exon(name_field):
    m = re.search(r"([A-Za-z][A-Za-z0-9_-]+?)_Ex_?(\w+)", name_field)
    if m:
        return m.group(1), m.group(2)
    # Strip ..N suffix for tiling regions (BCL2..2 -> BCL2)
    gene = re.sub(r"\.\.\d+$", "", name_field.strip())
    return (gene, None) if gene else (None, None)


def load_bed_genes(bed_path):
    """Load panel BED -> dict gene -> {chrom, start, end}."""
    genes = defaultdict(lambda: {"chrom": None, "start": float("inf"), "end": 0})
    with open(bed_path) as f:
        for line in f:
            if line.startswith(("#", "track")):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 4:
                continue
            chrom, start, end = parts[0], int(parts[1]), int(parts[2])
            gene, exon = parse_bed_gene_exon(parts[3])
            if gene:
                g = genes[gene]
                g["chrom"] = chrom
                g["start"] = min(g["start"], start)
                g["end"] = max(g["end"], end)
    return dict(genes)


# ---------------------------------------------------------------------------
# Discover normals
# ---------------------------------------------------------------------------

def discover_normals(cov_dir):
    """Find all normals with both target and antitarget coverage files.

    Returns list of (sample_name, target_cnn_path, antitarget_cnn_path).
    """
    target_files = sorted(glob.glob(os.path.join(cov_dir, "*.targetcoverage.cnn")))
    normals = []
    for tf in target_files:
        basename = os.path.basename(tf)
        # Extract sample name: everything before .final.targetcoverage.cnn or .targetcoverage.cnn
        if ".final.targetcoverage.cnn" in basename:
            sample = basename.replace(".final.targetcoverage.cnn", "")
            at_file = tf.replace(".targetcoverage.cnn", ".antitargetcoverage.cnn")
        else:
            sample = basename.replace(".targetcoverage.cnn", "")
            at_file = tf.replace(".targetcoverage.cnn", ".antitargetcoverage.cnn")

        if os.path.isfile(at_file):
            normals.append((sample, tf, at_file))
        else:
            log.warning("Missing antitarget for %s, skipping", sample)
    return normals


# ---------------------------------------------------------------------------
# Single LOO iteration
# ---------------------------------------------------------------------------

def run_cmd(cmd, desc=""):
    """Run a shell command, return (returncode, stdout, stderr)."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return result.returncode, result.stdout, result.stderr
    return 0, result.stdout, result.stderr


def run_loo_iteration(held_out_idx, normals, tmpdir, male_reference=False):
    """Run one LOO iteration: build ref from N-1, fix+segment the held-out.

    Returns (sample_name, cnr_path, cns_path) or (sample_name, None, None) on failure.
    """
    sample, target_cnn, antitarget_cnn = normals[held_out_idx]
    iter_dir = os.path.join(tmpdir, sample)
    os.makedirs(iter_dir, exist_ok=True)

    # Gather the OTHER normals' coverage files
    other_covs = []
    for i, (s, tf, af) in enumerate(normals):
        if i != held_out_idx:
            other_covs.append(tf)
            other_covs.append(af)

    # Build LOO reference
    ref_path = os.path.join(iter_dir, "loo_reference.cnn")
    cmd_ref = ["cnvkit.py", "reference", "-o", ref_path] + other_covs
    if male_reference:
        cmd_ref.append("-y")
    rc, stdout, stderr = run_cmd(cmd_ref, f"LOO reference for {sample}")
    if rc != 0:
        log.error("LOO reference failed for %s: %s", sample, stderr[-500:] if stderr else "")
        return sample, None, None

    # Fix
    cnr_path = os.path.join(iter_dir, f"{sample}.cnr")
    cmd_fix = ["cnvkit.py", "fix", target_cnn, antitarget_cnn, ref_path,
               "-o", cnr_path]
    rc, stdout, stderr = run_cmd(cmd_fix, f"LOO fix for {sample}")
    if rc != 0:
        log.error("LOO fix failed for %s: %s", sample, stderr[-500:] if stderr else "")
        return sample, None, None

    # Segment
    cns_path = os.path.join(iter_dir, f"{sample}.cns")
    cmd_seg = ["cnvkit.py", "segment", cnr_path, "-o", cns_path]
    rc, stdout, stderr = run_cmd(cmd_seg, f"LOO segment for {sample}")
    if rc != 0:
        log.error("LOO segment failed for %s: %s", sample, stderr[-500:] if stderr else "")
        return sample, cnr_path, None

    return sample, cnr_path, cns_path


def _loo_worker(args):
    """Wrapper for ProcessPoolExecutor."""
    return run_loo_iteration(*args)


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def collect_results(normals, tmpdir):
    """Collect all CNR and CNS files from LOO iterations.

    Returns:
        all_cnr: dict sample -> DataFrame
        all_cns: dict sample -> DataFrame
    """
    all_cnr = {}
    all_cns = {}
    for sample, _, _ in normals:
        iter_dir = os.path.join(tmpdir, sample)
        cnr_path = os.path.join(iter_dir, f"{sample}.cnr")
        cns_path = os.path.join(iter_dir, f"{sample}.cns")
        if os.path.isfile(cnr_path):
            df = pd.read_csv(cnr_path, sep="\t")
            df = df[df["chromosome"].isin(CHROM_ORDER)].copy()
            all_cnr[sample] = df
        if os.path.isfile(cns_path):
            df = pd.read_csv(cns_path, sep="\t")
            df = df[df["chromosome"].isin(CHROM_ORDER)].copy()
            all_cns[sample] = df
    return all_cnr, all_cns


def build_bin_noise_profile(all_cnr):
    """Build per-bin noise profile across all LOO runs.

    Returns DataFrame with columns: chromosome, start, end, gene, mean_log2,
    stdev_log2, n_samples, is_noisy.
    """
    # Use first sample's bins as reference coordinates
    ref_sample = list(all_cnr.keys())[0]
    ref = all_cnr[ref_sample][["chromosome", "start", "end", "gene"]].copy()

    # Build bin key for merging
    ref["bin_key"] = ref["chromosome"] + ":" + ref["start"].astype(str) + "-" + ref["end"].astype(str)

    # Collect log2 values per bin across samples
    bin_log2s = defaultdict(list)
    for sample, df in all_cnr.items():
        df = df.copy()
        df["bin_key"] = df["chromosome"] + ":" + df["start"].astype(str) + "-" + df["end"].astype(str)
        for _, row in df.iterrows():
            bin_log2s[row["bin_key"]].append(row["log2"])

    # Compute stats
    stats = []
    for _, row in ref.iterrows():
        bk = row["bin_key"]
        vals = bin_log2s.get(bk, [])
        if vals:
            stats.append({
                "chromosome": row["chromosome"],
                "start": row["start"],
                "end": row["end"],
                "gene": row["gene"],
                "mean_log2": np.mean(vals),
                "stdev_log2": np.std(vals),
                "n_samples": len(vals),
            })

    result = pd.DataFrame(stats)
    result["is_noisy"] = result["stdev_log2"] > NOISE_STDEV_THRESH
    return result


def compute_bin_fp_rate(all_cnr, n_normals):
    """For each bin, count how many normals have |log2| above thresholds.

    Returns DataFrame with fp columns.
    """
    ref_sample = list(all_cnr.keys())[0]
    ref = all_cnr[ref_sample][["chromosome", "start", "end", "gene"]].copy()
    ref["bin_key"] = ref["chromosome"] + ":" + ref["start"].astype(str) + "-" + ref["end"].astype(str)

    fp_gain = defaultdict(int)
    fp_loss = defaultdict(int)

    for sample, df in all_cnr.items():
        df = df.copy()
        df["bin_key"] = df["chromosome"] + ":" + df["start"].astype(str) + "-" + df["end"].astype(str)
        for _, row in df.iterrows():
            bk = row["bin_key"]
            if row["log2"] > THRESH_GAIN:
                fp_gain[bk] += 1
            if row["log2"] < THRESH_LOSS:
                fp_loss[bk] += 1

    ref["fp_gain_count"] = ref["bin_key"].map(lambda k: fp_gain.get(k, 0))
    ref["fp_loss_count"] = ref["bin_key"].map(lambda k: fp_loss.get(k, 0))
    ref["fp_gain_rate"] = ref["fp_gain_count"] / n_normals
    ref["fp_loss_rate"] = ref["fp_loss_count"] / n_normals
    ref["fp_any_rate"] = (ref["fp_gain_count"] + ref["fp_loss_count"]) / n_normals
    ref["blacklist"] = ref["fp_any_rate"] > BLACKLIST_FP_RATE

    return ref.drop(columns=["bin_key"])


def compute_gene_fp_rate(all_cnr, genes, n_normals):
    """Per-gene false positive rate: how often each gene gets called as gain/loss."""
    gene_results = []
    for gene_name, ginfo in sorted(genes.items(),
                                     key=lambda x: (CHROM_RANK.get(x[1]["chrom"], 99),
                                                    x[1]["start"])):
        chrom = ginfo["chrom"]
        gs, ge = ginfo["start"], ginfo["end"]

        fp_gain = 0
        fp_loss = 0
        gene_log2s = []

        for sample, df in all_cnr.items():
            cdf = df[(df["chromosome"] == chrom) &
                     (df["start"] >= gs) & (df["end"] <= ge) &
                     (df["gene"] != "Antitarget")]
            if cdf.empty:
                continue
            mean_log2 = cdf["log2"].mean()
            gene_log2s.append(mean_log2)
            if mean_log2 > THRESH_GAIN:
                fp_gain += 1
            if mean_log2 < THRESH_LOSS:
                fp_loss += 1

        gene_results.append({
            "gene": gene_name,
            "chromosome": chrom,
            "start": gs,
            "end": ge,
            "mean_log2": np.mean(gene_log2s) if gene_log2s else np.nan,
            "stdev_log2": np.std(gene_log2s) if gene_log2s else np.nan,
            "fp_gain_count": fp_gain,
            "fp_loss_count": fp_loss,
            "fp_gain_rate": fp_gain / n_normals,
            "fp_loss_rate": fp_loss / n_normals,
            "fp_any_rate": (fp_gain + fp_loss) / n_normals,
            "n_samples": len(gene_log2s),
        })

    return pd.DataFrame(gene_results)


def build_gene_sample_matrix(all_cnr, genes):
    """Build matrix of mean log2 per gene per sample for heatmap."""
    sorted_genes = sorted(genes.keys(),
                          key=lambda g: (CHROM_RANK.get(genes[g]["chrom"], 99),
                                         genes[g]["start"]))
    sorted_samples = sorted(all_cnr.keys())

    matrix = np.full((len(sorted_samples), len(sorted_genes)), np.nan)

    for si, sample in enumerate(sorted_samples):
        df = all_cnr[sample]
        for gi, gene_name in enumerate(sorted_genes):
            ginfo = genes[gene_name]
            chrom = ginfo["chrom"]
            gs, ge = ginfo["start"], ginfo["end"]
            cdf = df[(df["chromosome"] == chrom) &
                     (df["start"] >= gs) & (df["end"] <= ge) &
                     (df["gene"] != "Antitarget")]
            if not cdf.empty:
                matrix[si, gi] = cdf["log2"].mean()

    return matrix, sorted_samples, sorted_genes


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------

def plot_summary_heatmap(matrix, sample_names, gene_names, genes, outdir):
    """Heatmap: normals (rows) x genes (columns), colored by log2."""
    n_samples, n_genes = matrix.shape

    fig_w = max(14, n_genes * 0.2 + 3)
    fig_h = max(6, n_samples * 0.15 + 2)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=200)

    cmap = mcolors.LinearSegmentedColormap.from_list(
        "cnv_loo",
        [(0.0, "#2471a3"), (0.35, "#aed6f1"),
         (0.5, "#ffffff"),
         (0.65, "#f5b7b1"), (1.0, "#c0392b")],
    )
    cmap.set_bad(color="#f0f0f0")
    vmax = max(0.8, np.nanmax(np.abs(matrix)))
    norm = mcolors.TwoSlopeNorm(vmin=-vmax, vcenter=0, vmax=vmax)

    im = ax.imshow(matrix, aspect="auto", cmap=cmap, norm=norm,
                   interpolation="nearest")

    ax.set_xticks(range(n_genes))
    ax.set_xticklabels(gene_names, rotation=90, fontsize=4, ha="center")
    ax.set_yticks(range(n_samples))
    ax.set_yticklabels(sample_names, fontsize=4)

    ax.set_title("LOO CNV QC — Normal samples x Panel genes (log2 ratio)",
                 fontsize=11, fontweight="bold", pad=10)

    # Chromosome grouping along top
    prev_chrom = None
    toggle = 0
    for gi, gn in enumerate(gene_names):
        gc = genes[gn]["chrom"]
        if gc != prev_chrom:
            if prev_chrom is not None:
                ax.axvline(gi - 0.5, color="#888888", linewidth=0.3, zorder=3)
            toggle = 1 - toggle
            prev_chrom = gc

    cbar = fig.colorbar(im, ax=ax, fraction=0.02, pad=0.01, shrink=0.8)
    cbar.set_label("log$_2$ ratio", fontsize=8)
    cbar.ax.tick_params(labelsize=6)

    out = os.path.join(outdir, "loo_summary_heatmap.png")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    log.info("Saved %s", out)


def plot_noise_profile(bin_noise, outdir):
    """Per-bin noise stdev histogram + genome-wide scatter."""
    fig, axes = plt.subplots(1, 2, figsize=(16, 5), dpi=200)

    # Histogram of stdev
    ax = axes[0]
    stdevs = bin_noise["stdev_log2"].dropna()
    ax.hist(stdevs, bins=80, color="#5b7fa5", edgecolor="white", linewidth=0.3)
    ax.axvline(NOISE_STDEV_THRESH, color="#c0392b", linewidth=1.5, linestyle="--",
               label=f"Noise threshold ({NOISE_STDEV_THRESH})")
    n_noisy = (stdevs > NOISE_STDEV_THRESH).sum()
    ax.set_xlabel("log2 stdev across LOO runs", fontsize=9)
    ax.set_ylabel("Number of bins", fontsize=9)
    ax.set_title(f"Per-bin noise distribution — {n_noisy} noisy bins (stdev > {NOISE_STDEV_THRESH})",
                 fontsize=10, fontweight="bold")
    ax.legend(fontsize=8)

    # Genome-wide stdev scatter
    ax2 = axes[1]
    chrom_offsets = {}
    cumul = 0
    chrom_sizes = {
        "chr1": 248956422, "chr2": 242193529, "chr3": 198295559,
        "chr4": 190214555, "chr5": 181538259, "chr6": 170805979,
        "chr7": 159345973, "chr8": 145138636, "chr9": 138394717,
        "chr10": 133797422, "chr11": 135086622, "chr12": 133275309,
        "chr13": 114364328, "chr14": 107043718, "chr15": 101991189,
        "chr16": 90338345, "chr17": 83257441, "chr18": 80373285,
        "chr19": 58617616, "chr20": 64444167, "chr21": 46709983,
        "chr22": 50818468, "chrX": 156040895, "chrY": 57227415,
    }
    for c in CHROM_ORDER:
        chrom_offsets[c] = cumul
        cumul += chrom_sizes.get(c, 0)

    for i, chrom in enumerate(CHROM_ORDER):
        mask = bin_noise["chromosome"] == chrom
        if not mask.any():
            continue
        subset = bin_noise[mask]
        gx = subset["start"] + chrom_offsets[chrom]
        color = "#5b7fa5" if i % 2 == 0 else "#999999"
        ax2.scatter(gx, subset["stdev_log2"], s=0.8, c=color, alpha=0.4,
                    rasterized=True, linewidths=0)

    ax2.axhline(NOISE_STDEV_THRESH, color="#c0392b", linewidth=1, linestyle="--", alpha=0.7)
    ax2.set_xlim(0, cumul)
    ax2.set_xticks([chrom_offsets[c] + chrom_sizes.get(c, 0) / 2 for c in CHROM_ORDER])
    ax2.set_xticklabels([c.replace("chr", "") for c in CHROM_ORDER], fontsize=6)
    ax2.set_ylabel("log2 stdev", fontsize=9)
    ax2.set_title("Genome-wide bin noise", fontsize=10, fontweight="bold")
    ax2.tick_params(axis="x", length=0)

    out = os.path.join(outdir, "loo_noise_profile.png")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    log.info("Saved %s", out)


def plot_gene_fp(gene_fp, outdir):
    """Bar plot of per-gene false positive rates."""
    n = len(gene_fp)
    fig, ax = plt.subplots(figsize=(max(10, n * 0.18), 4.5), dpi=200)

    x = np.arange(n)
    ax.bar(x - 0.15, gene_fp["fp_gain_rate"], width=0.3, color="#c0392b",
           alpha=0.7, label="FP gain rate")
    ax.bar(x + 0.15, gene_fp["fp_loss_rate"], width=0.3, color="#2471a3",
           alpha=0.7, label="FP loss rate")
    ax.axhline(BLACKLIST_FP_RATE, color="#888888", linewidth=1, linestyle="--",
               alpha=0.5, label=f"Blacklist threshold ({BLACKLIST_FP_RATE:.0%})")
    ax.set_xticks(x)
    ax.set_xticklabels(gene_fp["gene"], rotation=90, fontsize=5)
    ax.set_ylabel("False positive rate", fontsize=9)
    ax.set_title("Per-gene false positive rate in normals (LOO)", fontsize=11,
                 fontweight="bold")
    ax.legend(fontsize=7, loc="upper right")
    ax.set_xlim(-0.5, n - 0.5)

    out = os.path.join(outdir, "loo_gene_fp_rates.png")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    log.info("Saved %s", out)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    t0 = time.time()
    args = parse_args()

    log.info("=== LOO CNV Noise Assessment (12c) ===")

    # Discover normals
    normals = discover_normals(args.cov_dir)
    n_normals = len(normals)
    log.info("Found %d normals in %s", n_normals, args.cov_dir)
    if n_normals < 5:
        log.error("Need at least 5 normals for LOO analysis, found %d", n_normals)
        sys.exit(1)

    # Load panel genes
    genes = load_bed_genes(args.bed)
    log.info("Loaded %d panel genes from %s", len(genes), args.bed)

    # Create output directories
    os.makedirs(args.outdir, exist_ok=True)
    ref_dir = os.path.join(PIPELINE_DIR, "references")
    os.makedirs(ref_dir, exist_ok=True)

    # Use a persistent temp directory under outdir for LOO results
    loo_work_dir = os.path.join(args.outdir, "loo_iterations")
    os.makedirs(loo_work_dir, exist_ok=True)

    # Run LOO iterations in parallel
    log.info("Running %d LOO iterations with %d parallel jobs...", n_normals, args.jobs)

    worker_args = [(i, normals, loo_work_dir, args.male_reference) for i in range(n_normals)]
    completed = 0
    failed = 0

    with ProcessPoolExecutor(max_workers=args.jobs) as executor:
        futures = {executor.submit(_loo_worker, wa): wa[0] for wa in worker_args}
        for future in as_completed(futures):
            idx = futures[future]
            try:
                sample, cnr_path, cns_path = future.result()
                completed += 1
                status = "OK" if cnr_path else "FAILED"
                if not cnr_path:
                    failed += 1
                log.info("  [%d/%d] %s — %s", completed, n_normals, sample, status)
            except Exception as e:
                failed += 1
                completed += 1
                log.error("  [%d/%d] idx=%d — Exception: %s", completed, n_normals, idx, e)

    log.info("LOO iterations complete: %d succeeded, %d failed", completed - failed, failed)

    # Collect results
    log.info("Collecting LOO results...")
    all_cnr, all_cns = collect_results(normals, loo_work_dir)
    log.info("Collected CNR from %d samples, CNS from %d samples",
             len(all_cnr), len(all_cns))

    if len(all_cnr) < 5:
        log.error("Too few successful LOO runs (%d), cannot generate reliable QC", len(all_cnr))
        sys.exit(1)

    n_success = len(all_cnr)

    # --- Per-bin noise profile ---
    log.info("Computing per-bin noise profile...")
    bin_noise = build_bin_noise_profile(all_cnr)
    noise_path = os.path.join(args.outdir, "loo_bin_noise_profile.tsv")
    bin_noise.to_csv(noise_path, sep="\t", index=False, float_format="%.6f")
    log.info("  %d total bins, %d noisy (stdev > %.2f)",
             len(bin_noise), bin_noise["is_noisy"].sum(), NOISE_STDEV_THRESH)

    # --- Per-bin false positive rates + blacklist ---
    log.info("Computing per-bin false positive rates...")
    bin_fp = compute_bin_fp_rate(all_cnr, n_success)
    n_blacklist = bin_fp["blacklist"].sum()
    log.info("  %d bins blacklisted (FP rate > %.0f%%)", n_blacklist, BLACKLIST_FP_RATE * 100)

    # Write blacklist BED
    blacklist_bed = os.path.join(ref_dir, "cnvkit_noisy_bins.bed")
    bl = bin_fp[bin_fp["blacklist"]][["chromosome", "start", "end", "gene",
                                       "fp_any_rate"]].copy()
    bl["start"] = bl["start"].astype(int)
    bl["end"] = bl["end"].astype(int)
    bl.to_csv(blacklist_bed, sep="\t", index=False, header=False)
    log.info("  Blacklist BED: %s (%d bins)", blacklist_bed, len(bl))

    # Write full bin FP table
    bin_fp_path = os.path.join(args.outdir, "loo_bin_fp_rates.tsv")
    bin_fp.to_csv(bin_fp_path, sep="\t", index=False, float_format="%.6f")

    # --- Per-gene false positive rates ---
    log.info("Computing per-gene false positive rates...")
    gene_fp = compute_gene_fp_rate(all_cnr, genes, n_success)
    gene_fp_path = os.path.join(ref_dir, "cnvkit_loo_summary.tsv")
    gene_fp.to_csv(gene_fp_path, sep="\t", index=False, float_format="%.6f")
    log.info("  Gene FP summary: %s", gene_fp_path)

    # Also save to outdir
    gene_fp.to_csv(os.path.join(args.outdir, "loo_gene_fp_rates.tsv"),
                    sep="\t", index=False, float_format="%.6f")

    # Report problematic genes
    problem_genes = gene_fp[gene_fp["fp_any_rate"] > BLACKLIST_FP_RATE]
    if not problem_genes.empty:
        log.warning("  Genes with FP rate > %.0f%%:", BLACKLIST_FP_RATE * 100)
        for _, row in problem_genes.iterrows():
            log.warning("    %s: gain=%.1f%%, loss=%.1f%%, stdev=%.3f",
                        row["gene"], row["fp_gain_rate"] * 100,
                        row["fp_loss_rate"] * 100, row["stdev_log2"])
    else:
        log.info("  No genes exceed %.0f%% FP rate", BLACKLIST_FP_RATE * 100)

    # --- Plots ---
    plot_dir = os.path.join(args.outdir, "plots")
    os.makedirs(plot_dir, exist_ok=True)

    log.info("Generating plots...")
    matrix, sample_names, gene_names = build_gene_sample_matrix(all_cnr, genes)
    plot_summary_heatmap(matrix, sample_names, gene_names, genes, plot_dir)
    plot_noise_profile(bin_noise, plot_dir)
    plot_gene_fp(gene_fp, plot_dir)

    # --- Summary stats ---
    log.info("=" * 60)
    log.info("LOO QC Summary:")
    log.info("  Normals analyzed:   %d / %d", n_success, n_normals)
    log.info("  Total bins:         %d", len(bin_noise))
    log.info("  Noisy bins:         %d (stdev > %.2f)", bin_noise["is_noisy"].sum(), NOISE_STDEV_THRESH)
    log.info("  Blacklisted bins:   %d (FP > %.0f%%)", n_blacklist, BLACKLIST_FP_RATE * 100)
    log.info("  Problem genes:      %d (FP > %.0f%%)", len(problem_genes), BLACKLIST_FP_RATE * 100)
    log.info("  Median bin stdev:   %.4f", bin_noise["stdev_log2"].median())
    log.info("  Mean bin stdev:     %.4f", bin_noise["stdev_log2"].mean())
    log.info("=" * 60)
    log.info("Output directory: %s", args.outdir)
    log.info("Blacklist BED:    %s", blacklist_bed)
    log.info("Gene FP summary:  %s", gene_fp_path)

    elapsed = time.time() - t0
    log.info("Total time: %.0fs (%.1f min)", elapsed, elapsed / 60)


if __name__ == "__main__":
    main()
