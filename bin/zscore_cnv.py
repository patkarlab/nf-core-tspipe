#!/usr/bin/env python3
"""
12d_zscore_cnv.py — Z-score somatic CNV caller calibrated to panel noise.

For each bin/gene in the tumor, computes:
    Z = (tumor_log2 - mean_normal_log2) / stdev_normal_log2

Uses the LOO per-bin noise profile as the null distribution.
Calls significant if |Z| > threshold AND LOO FP rate < cutoff.

Usage:
    python scripts/12d_zscore_cnv.py \
        -s 26CGH40 \
        --cnr results/26CGH40/cnvkit/26CGH40.final.cnr \
        --noise-profile results/cnvkit_loo_qc/loo_bin_noise_profile.tsv \
        --loo-summary references/cnvkit_loo_summary.tsv \
        -o results/26CGH40/cnv_zscore
"""

import argparse
import logging
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def parse_args():
    p = argparse.ArgumentParser(description="Z-score somatic CNV caller.")
    p.add_argument("-s", "--sample", default="26CGH40")
    p.add_argument("--cnr", default="results/26CGH40/cnvkit/26CGH40.final.cnr",
                    help="Tumor CNR file from CNVKit")
    p.add_argument("--noise-profile",
                    default="results/cnvkit_loo_qc/loo_bin_noise_profile.tsv",
                    help="LOO per-bin noise profile TSV")
    p.add_argument("--loo-summary", default="references/cnvkit_loo_summary.tsv",
                    help="LOO per-gene FP summary TSV")
    p.add_argument("-o", "--out-dir", default="results/26CGH40/cnv_zscore")
    p.add_argument("--z-thresh", type=float, default=2.5,
                    help="Z-score threshold for calling (default: 2.5)")
    p.add_argument("--fp-cutoff", type=float, default=0.20,
                    help="Max LOO FP rate to retain call (default: 0.20)")
    p.add_argument("--z-suggestive", type=float, default=1.5,
                    help="Z-score threshold for suggestive tier (default: 1.5)")
    p.add_argument("--fp-suggestive", type=float, default=0.10,
                    help="Max LOO FP rate for suggestive tier (default: 0.10)")
    p.add_argument("--min-stdev", type=float, default=0.05,
                    help="Minimum stdev to avoid division issues (default: 0.05)")
    return p.parse_args()


def clean_gene(raw: str) -> str:
    """Extract clean gene name from BED-style annotation."""
    s = str(raw)
    # Try: ;GENE_Ex_N or ;GENE_ExN or ;GENE_Intron_
    m = re.search(r';([A-Za-z][A-Za-z0-9]+)_(?:Ex_?\d|Intron)', s)
    if m:
        return m.group(1)
    # Try with _ prefix: _GENE_Ex_N
    m = re.search(r'_([A-Za-z][A-Za-z0-9]+)_Ex_', s)
    if m:
        return m.group(1)
    # Try standalone: GENE_Ex_N at start or after comma
    m = re.search(r'(?:^|,)([A-Za-z][A-Za-z0-9]+)_Ex_', s)
    if m:
        return m.group(1)
    # Already a clean gene name
    if re.match(r'^[A-Za-z][A-Za-z0-9]+$', s):
        return s
    return s


def main():
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    log.info("=== Z-score Somatic CNV Caller: %s ===", args.sample)

    # Load tumor CNR
    cnr = pd.read_csv(args.cnr, sep="\t")
    cnr_target = cnr[cnr["gene"] != "Antitarget"].copy()
    log.info("Tumor CNR: %d bins (%d target)", len(cnr), len(cnr_target))

    # Load LOO noise profile
    noise = pd.read_csv(args.noise_profile, sep="\t")
    noise_target = noise[noise["gene"] != "Antitarget"].copy()
    log.info("LOO noise profile: %d bins (%d target)", len(noise), len(noise_target))

    # Load LOO gene summary
    loo_genes = pd.read_csv(args.loo_summary, sep="\t")
    gene_fp = dict(zip(loo_genes["gene"], loo_genes["fp_any_rate"]))
    log.info("LOO gene summary: %d genes", len(loo_genes))

    # --- BIN-LEVEL Z-SCORES ---
    # Match tumor bins to noise profile by coordinates
    merged = pd.merge(
        cnr_target[["chromosome", "start", "end", "gene", "log2", "depth", "weight"]],
        noise_target[["chromosome", "start", "end", "mean_log2", "stdev_log2", "is_noisy"]],
        on=["chromosome", "start", "end"],
        how="inner",
        suffixes=("", "_loo")
    )
    log.info("Matched bins: %d", len(merged))

    # Compute Z-score
    stdev_clipped = merged["stdev_log2"].clip(lower=args.min_stdev)
    merged["zscore"] = (merged["log2"] - merged["mean_log2"]) / stdev_clipped
    merged["abs_zscore"] = merged["zscore"].abs()

    # Extract clean gene name
    merged["clean_gene"] = merged["gene"].apply(clean_gene)

    # Add gene-level FP rate
    merged["gene_fp_rate"] = merged["clean_gene"].map(gene_fp).fillna(0.0)

    # Call bins — significant tier
    merged["is_significant"] = (
        (merged["abs_zscore"] >= args.z_thresh) &
        (merged["gene_fp_rate"] < args.fp_cutoff) &
        (~merged["is_noisy"])
    )
    # Suggestive tier — lower Z threshold but stricter FP
    merged["is_suggestive"] = (
        (merged["abs_zscore"] >= args.z_suggestive) &
        (merged["abs_zscore"] < args.z_thresh) &
        (merged["gene_fp_rate"] < args.fp_suggestive) &
        (~merged["is_noisy"])
    )
    merged["call"] = "neutral"
    merged.loc[merged["is_significant"] & (merged["zscore"] > 0), "call"] = "gain"
    merged.loc[merged["is_significant"] & (merged["zscore"] < 0), "call"] = "loss"
    merged.loc[merged["is_suggestive"] & (merged["zscore"] > 0) & (merged["call"] == "neutral"), "call"] = "suggestive_gain"
    merged.loc[merged["is_suggestive"] & (merged["zscore"] < 0) & (merged["call"] == "neutral"), "call"] = "suggestive_loss"

    # Write bin-level results
    bin_tsv = out_dir / f"{args.sample}.zscore_bins.tsv"
    merged.to_csv(bin_tsv, sep="\t", index=False)
    log.info("Bin-level results: %s (%d bins, %d significant)",
             bin_tsv, len(merged), merged["is_significant"].sum())

    # --- GENE-LEVEL AGGREGATION ---
    gene_groups = merged.groupby("clean_gene")

    gene_results = []
    for gene_name, gdf in gene_groups:
        n_bins = len(gdf)
        n_sig = gdf["is_significant"].sum()
        n_sug = gdf["is_suggestive"].sum()
        mean_log2 = gdf["log2"].mean()
        mean_zscore = gdf["zscore"].mean()
        median_zscore = gdf["zscore"].median()
        max_abs_z = gdf["abs_zscore"].max()
        fp_rate = gdf["gene_fp_rate"].iloc[0]
        chrom = gdf["chromosome"].iloc[0]
        start = gdf["start"].min()
        end = gdf["end"].max()

        frac_sig = n_sig / n_bins if n_bins > 0 else 0
        frac_sig_or_sug = (n_sig + n_sug) / n_bins if n_bins > 0 else 0

        # Gene-level significance: mean |Z| > threshold*0.8 AND enough sig bins
        gene_significant = (
            (abs(mean_zscore) >= args.z_thresh * 0.8) and
            (frac_sig >= 0.25) and
            (fp_rate < args.fp_cutoff)
        )

        # Gene-level suggestive: mean |Z| > suggestive*0.8 AND enough sig+sug bins AND low FP
        gene_suggestive = (
            not gene_significant and
            (abs(mean_zscore) >= args.z_suggestive * 0.8) and
            (frac_sig_or_sug >= 0.2) and
            (fp_rate < args.fp_suggestive)
        )

        if gene_significant:
            gene_call = "gain" if mean_zscore > 0 else "loss"
        elif gene_suggestive:
            gene_call = "suggestive_gain" if mean_zscore > 0 else "suggestive_loss"
        else:
            gene_call = "neutral"

        # Confidence
        if fp_rate < 0.05:
            confidence = "HIGH"
        elif fp_rate <= 0.20:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        gene_results.append({
            "gene": gene_name,
            "chromosome": chrom,
            "start": start,
            "end": end,
            "n_bins": n_bins,
            "n_significant_bins": n_sig,
            "n_suggestive_bins": n_sug,
            "frac_significant": round(frac_sig, 4),
            "mean_log2": round(mean_log2, 4),
            "mean_zscore": round(mean_zscore, 4),
            "median_zscore": round(median_zscore, 4),
            "max_abs_zscore": round(max_abs_z, 4),
            "gene_fp_rate": round(fp_rate, 4),
            "call": gene_call,
            "confidence": confidence,
        })

    gene_df = pd.DataFrame(gene_results)

    # Sort by chromosome and position
    chrom_order = {f"chr{i}": i for i in range(1, 23)}
    chrom_order.update({"chrX": 23, "chrY": 24})
    gene_df["_chrom_rank"] = gene_df["chromosome"].map(chrom_order).fillna(99)
    gene_df = gene_df.sort_values(["_chrom_rank", "start"]).drop(columns=["_chrom_rank"])

    gene_tsv = out_dir / f"{args.sample}.zscore_genes.tsv"
    gene_df.to_csv(gene_tsv, sep="\t", index=False)
    log.info("Gene-level results: %s (%d genes)", gene_tsv, len(gene_df))

    # --- CNV CALLS ONLY (significant + suggestive) ---
    cnv_genes = gene_df[gene_df["call"] != "neutral"].copy()
    cnv_tsv = out_dir / f"{args.sample}.zscore_calls.tsv"
    cnv_genes.to_csv(cnv_tsv, sep="\t", index=False)
    log.info("Gene CNV calls: %s (%d genes)", cnv_tsv, len(cnv_genes))

    # --- EXON-LEVEL RESULTS ---
    # Group bins by gene+exon for more granular view
    merged["exon"] = merged["gene"].apply(
        lambda x: re.search(r'_Ex_(\d+)', str(x)).group(1)
        if re.search(r'_Ex_(\d+)', str(x)) else "?"
    )
    exon_groups = merged.groupby(["clean_gene", "exon"])
    exon_results = []
    for (gene_name, exon_num), edf in exon_groups:
        exon_results.append({
            "gene": gene_name,
            "exon": exon_num,
            "chromosome": edf["chromosome"].iloc[0],
            "start": edf["start"].min(),
            "end": edf["end"].max(),
            "n_probes": len(edf),
            "mean_log2": round(edf["log2"].mean(), 4),
            "mean_zscore": round(edf["zscore"].mean(), 4),
            "is_significant": bool(edf["is_significant"].any()),
            "call": "gain" if edf["zscore"].mean() > args.z_thresh else
                    ("loss" if edf["zscore"].mean() < -args.z_thresh else "neutral"),
        })
    exon_df = pd.DataFrame(exon_results)
    exon_tsv = out_dir / f"{args.sample}.zscore_exons.tsv"
    exon_df.to_csv(exon_tsv, sep="\t", index=False)
    log.info("Exon-level results: %s (%d exons)", exon_tsv, len(exon_df))

    # --- SUMMARY ---
    log.info("")
    log.info("=" * 60)
    log.info("Z-score CNV Summary for %s:", args.sample)
    log.info("  Z threshold:     %.1f (suggestive: %.1f)", args.z_thresh, args.z_suggestive)
    log.info("  FP cutoff:       %.0f%% (suggestive: %.0f%%)", args.fp_cutoff * 100, args.fp_suggestive * 100)
    log.info("  Bins analyzed:   %d", len(merged))
    log.info("  Significant bins: %d (%.1f%%)",
             merged["is_significant"].sum(),
             100 * merged["is_significant"].mean())
    log.info("  Suggestive bins:  %d (%.1f%%)",
             merged["is_suggestive"].sum(),
             100 * merged["is_suggestive"].mean())
    log.info("  Genes analyzed:  %d", len(gene_df))

    sig_genes = cnv_genes[cnv_genes["call"].isin(["gain", "loss"])]
    sug_genes = cnv_genes[cnv_genes["call"].isin(["suggestive_gain", "suggestive_loss"])]
    log.info("  Significant calls: %d (%d gain, %d loss)",
             len(sig_genes),
             (sig_genes["call"] == "gain").sum() if len(sig_genes) > 0 else 0,
             (sig_genes["call"] == "loss").sum() if len(sig_genes) > 0 else 0)
    log.info("  Suggestive calls:  %d (%d gain, %d loss)",
             len(sug_genes),
             (sug_genes["call"] == "suggestive_gain").sum() if len(sug_genes) > 0 else 0,
             (sug_genes["call"] == "suggestive_loss").sum() if len(sug_genes) > 0 else 0)

    for label, subset_df in [("SIGNIFICANT", sig_genes), ("SUGGESTIVE", sug_genes)]:
        if len(subset_df) > 0:
            log.info("  --- %s ---", label)
            for _, r in subset_df.iterrows():
                log.info("    %-15s %-18s log2=%+.3f  Z=%+.2f  FP=%.3f  [%s]",
                         r["gene"], r["call"], r["mean_log2"],
                         r["mean_zscore"], r["gene_fp_rate"], r["confidence"])
    log.info("=" * 60)
    log.info("Output: %s", out_dir)
    log.info("Done.")


if __name__ == "__main__":
    main()
