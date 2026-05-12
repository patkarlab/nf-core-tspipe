#!/usr/bin/env python3
"""
12e_cnv_concordance.py — Multi-caller CNV concordance analysis.

Core callers: CNVKit + Z-score (always required).
Optional caller: panelcn.MOPS (--cnmops-genes).

Produces tiered consensus report:
  TIER 1 (HIGH):   All available callers agree (2/2 or 3/3),
                    OR CNVKit + Z-score concordant with LOO FP < 10%
  TIER 2 (MEDIUM): 2 callers agree, LOO FP < 20%
  TIER 3 (LOW):    single caller only, or LOO FP > 20%
  FILTERED:        LOO FP > 30%

Usage:
    python scripts/12e_cnv_concordance.py \
        -s 26CGH40 \
        --cnvkit-genemetrics results/26CGH40/cnvkit/26CGH40.genemetrics.annotated.tsv \
        --zscore-genes results/26CGH40/cnv_zscore/26CGH40.zscore_genes.tsv \
        -o results/26CGH40/cnv_consensus
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
    p = argparse.ArgumentParser(
        description="Multi-caller CNV concordance analysis."
    )
    p.add_argument("-s", "--sample", required=True)
    p.add_argument("--cnvkit-genemetrics", required=True)
    p.add_argument("--zscore-genes", required=True)
    p.add_argument("--cnmops-genes", default=None,
                   help="Optional: panelcn.MOPS gene summary (adds 3rd caller)")
    p.add_argument("--exon-cnv", default=None,
                   help="Optional: exon-level CNV events from 12g (rescues partial events)")
    p.add_argument("--ifcnv-genes", default=None,
                   help="Optional: ifCNV gene summary (deprecated, ignored with warning)")
    p.add_argument("-o", "--out-dir", required=True)
    p.add_argument("--log2-threshold", type=float, default=0.2,
                   help="Minimum |log2| for CNVKit gene call (default: 0.2)")
    return p.parse_args()


def clean_gene(raw: str) -> str:
    """Extract clean gene name from BED-style annotation."""
    s = str(raw).strip('"')
    m = re.search(r';([A-Za-z][A-Za-z0-9]+)_(?:Ex_?\d|Intron)', s)
    if m:
        return m.group(1)
    m = re.search(r'_([A-Za-z][A-Za-z0-9]+)_Ex_', s)
    if m:
        return m.group(1)
    m = re.search(r'_([A-Za-z][A-Za-z0-9]+)_EX_', s)
    if m:
        return m.group(1)
    m = re.search(r'_([A-Za-z][A-Za-z0-9]+)_Ex\d', s)
    if m:
        return m.group(1)
    m = re.search(r'(?:^|,)([A-Za-z][A-Za-z0-9]+)_Ex_', s)
    if m:
        return m.group(1)
    m = re.search(r';([A-Za-z][A-Za-z0-9]+)_Ex_intr', s)
    if m:
        return m.group(1)
    if re.match(r'^[A-Za-z][A-Za-z0-9]+$', s):
        return s
    return s


# ---------------------------------------------------------------------------
# Loader functions for each caller
# ---------------------------------------------------------------------------

def load_cnvkit_genes(path: Path, log2_thresh: float) -> pd.DataFrame:
    """Load CNVKit annotated genemetrics -> gene-level calls."""
    df = pd.read_csv(path, sep="\t")
    df["clean_gene"] = df["gene"].apply(clean_gene)

    gene_agg = df.groupby("clean_gene").agg(
        chromosome=("chromosome", "first"),
        start=("start", "min"),
        end=("end", "max"),
        cnvkit_log2=("log2", "mean"),
        cnvkit_n_exons=("gene", "count"),
        cnvkit_confidence=("confidence", lambda x: x.mode().iloc[0] if len(x) > 0 else "LOW"),
        LOO_FP_rate=("LOO_FP_rate", "first"),
        blacklist_frac=("blacklist_frac", "mean"),
    ).reset_index()
    gene_agg.rename(columns={"clean_gene": "gene"}, inplace=True)

    gene_agg["cnvkit_call"] = gene_agg["cnvkit_log2"].apply(
        lambda x: "gain" if x > log2_thresh else ("loss" if x < -log2_thresh else "neutral")
    )
    return gene_agg


def load_zscore_genes(path: Path) -> pd.DataFrame:
    """Load Z-score gene-level results."""
    df = pd.read_csv(path, sep="\t")
    df["gene"] = df["gene"].apply(clean_gene)
    rename_map = {
        "call": "zscore_call",
        "mean_log2": "zscore_log2",
        "mean_zscore": "zscore_mean_z",
        "median_zscore": "zscore_median_z",
        "max_abs_zscore": "zscore_max_abs_z",
        "confidence": "zscore_confidence",
        "n_bins": "zscore_n_bins",
        "n_significant_bins": "zscore_n_sig_bins",
        "frac_significant": "zscore_frac_sig",
    }
    df = df.rename(columns=rename_map)
    cols = ["gene", "zscore_call", "zscore_log2", "zscore_mean_z",
            "zscore_median_z", "zscore_max_abs_z", "zscore_confidence",
            "zscore_n_bins", "zscore_n_sig_bins", "zscore_frac_sig",
            "gene_fp_rate"]
    return df[[c for c in cols if c in df.columns]]


def load_cnmops_genes(path: Path) -> pd.DataFrame:
    """Load cn.mops gene-level summary."""
    df = pd.read_csv(path, sep="\t")
    df["gene"] = df["gene"].apply(clean_gene)
    rename_map = {
        "type": "cnmops_call",
        "median_CN": "cnmops_cn",
        "mean_log2": "cnmops_log2",
        "n_loss": "cnmops_n_loss",
        "n_gain": "cnmops_n_gain",
    }
    df = df.rename(columns=rename_map)
    cols = ["gene", "cnmops_call", "cnmops_cn", "cnmops_log2",
            "cnmops_n_loss", "cnmops_n_gain"]
    return df[[c for c in cols if c in df.columns]]


def load_ifcnv_genes(path: Path) -> pd.DataFrame:
    """Load ifCNV gene-level summary."""
    df = pd.read_csv(path, sep="\t")
    rename_map = {
        "ifcnv_type": "ifcnv_call",
        "ifcnv_ratio": "ifcnv_ratio",
        "ifcnv_score": "ifcnv_score",
    }
    df = df.rename(columns=rename_map)
    cols = ["gene", "ifcnv_call", "ifcnv_ratio", "ifcnv_score"]
    return df[[c for c in cols if c in df.columns]]


def load_exon_cnv(path: Path) -> pd.DataFrame:
    """Load exon-level CNV events from 12g_exon_cnv.py.

    Collapses to one call per gene: if any event is a gain -> gain,
    if any event is a loss -> loss. If both, use the stronger one.
    Also captures clinical flags and best event details.
    """
    df = pd.read_csv(path, sep="\t")
    if df.empty:
        return pd.DataFrame(columns=["gene", "exon_call", "exon_log2",
                                      "exon_score", "exon_event_type",
                                      "exon_clinical_flag"])

    results = []
    for gene, gdf in df.groupby("Gene"):
        # Best event by |Score|
        best_idx = gdf["Score"].abs().idxmax()
        best = gdf.loc[best_idx]
        event_type = best["Event_Type"]

        if "gain" in event_type:
            call = "gain"
        elif "loss" in event_type:
            call = "loss"
        else:
            call = "neutral"

        # Collect clinical flags
        flags = gdf["Clinical_Flag"].dropna()
        flags = flags[flags != ""]
        clinical_flag = flags.iloc[0] if len(flags) > 0 else ""

        results.append({
            "gene": gene,
            "exon_call": call,
            "exon_log2": best["Exon_Range_Log2"],
            "exon_score": best["Score"],
            "exon_event_type": event_type,
            "exon_clinical_flag": clinical_flag,
        })

    return pd.DataFrame(results)


# ---------------------------------------------------------------------------
# Concordance and tiering
# ---------------------------------------------------------------------------

def count_callers(row, active_callers):
    """Count how many callers agree on a non-neutral call, and what they agree on."""
    calls = {}
    for caller in active_callers:
        val = row.get(caller, "neutral")
        if pd.isna(val):
            val = "not_tested"
        if val not in ("neutral", "not_tested"):
            calls[caller] = val

    if not calls:
        return 0, "neutral", [], len(active_callers)

    # Count gain vs loss
    gain_callers = [c for c, v in calls.items() if v in ("gain", "suggestive_gain")]
    loss_callers = [c for c, v in calls.items() if v in ("loss", "suggestive_loss")]

    if len(gain_callers) >= len(loss_callers) and gain_callers:
        return len(gain_callers), "gain", gain_callers, len(active_callers)
    elif loss_callers:
        return len(loss_callers), "loss", loss_callers, len(active_callers)
    else:
        # Mixed or suggestive only
        return len(calls), list(calls.values())[0], list(calls.keys()), len(active_callers)


def assign_tier(row):
    """Assign tier based on caller concordance and LOO FP rate.

    Concordance adapts to the number of active callers:
      2 callers: TIER_1 = 2/2, TIER_2 = not possible, TIER_3 = 1/2
      3 callers: TIER_1 = 3/3 or 2/3 with FP<10%, TIER_2 = 2/3, TIER_3 = 1/3
    """
    n_callers = row["n_callers_agree"]
    n_total = row["n_total_callers"]
    fp_rate = row.get("LOO_FP_pct", 0)
    if pd.isna(fp_rate):
        fp_rate = 0

    cnvkit_call = row.get("cnvkit_call", "neutral")
    zscore_call = row.get("zscore_call", "neutral")
    if pd.isna(cnvkit_call):
        cnvkit_call = "not_tested"
    if pd.isna(zscore_call):
        zscore_call = "not_tested"

    # Both neutral = not a CNV
    if n_callers == 0:
        return "NEUTRAL", "none"

    # FILTERED: LOO FP > 30%
    if fp_rate > 30:
        return "FILTERED", "high_fp"

    # CNVKit + Z-score concordance check
    cnvkit_cnv = cnvkit_call not in ("neutral", "not_tested")
    zscore_cnv = zscore_call not in ("neutral", "not_tested")
    cnvkit_zscore_concordant = (cnvkit_cnv and zscore_cnv and
                                 cnvkit_call.replace("suggestive_", "") ==
                                 zscore_call.replace("suggestive_", ""))

    # TIER 1: all callers agree, OR CNVKit + Z-score concordant with FP < 10%
    if n_callers >= n_total:
        return "TIER_1", f"{n_callers}/{n_total}_callers"
    if cnvkit_zscore_concordant and fp_rate < 10:
        return "TIER_1", "cnvkit_zscore_fp<10"

    # TIER 2: 2+ callers agree (only meaningful with 3 callers), FP < 20%
    if n_callers >= 2 and fp_rate < 20:
        return "TIER_2", f"{n_callers}/{n_total}_callers_fp<20"

    # TIER 3: single caller, or FP > 20%
    return "TIER_3", "single_or_high_fp"


def determine_confidence(row):
    """Determine confidence from LOO FP rate."""
    fp = row.get("LOO_FP_pct", 0)
    if pd.isna(fp):
        return "UNKNOWN"
    if fp < 5:
        return "HIGH"
    if fp <= 20:
        return "MEDIUM"
    return "LOW"


def main():
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    sample = args.sample

    # Determine active callers
    active_callers = ["cnvkit_call", "zscore_call"]
    caller_labels = ["CNVKit", "Zscore"]

    has_cnmops = False
    if args.cnmops_genes:
        cnmops_path = Path(args.cnmops_genes)
        if cnmops_path.is_file():
            has_cnmops = True
            active_callers.append("cnmops_call")
            caller_labels.append("cnmops")

    has_exon_cnv = False
    if args.exon_cnv:
        exon_cnv_path = Path(args.exon_cnv)
        if exon_cnv_path.is_file():
            has_exon_cnv = True
            active_callers.append("exon_call")
            caller_labels.append("ExonCNV")

    if args.ifcnv_genes:
        log.warning("--ifcnv-genes is deprecated and will be ignored. "
                    "ifCNV has been removed from the pipeline.")

    n_callers_label = len(active_callers)
    log.info("=== %d-Caller CNV Concordance: %s ===", n_callers_label, sample)

    # Load core caller results
    cnvkit = load_cnvkit_genes(Path(args.cnvkit_genemetrics), args.log2_threshold)
    log.info("CNVKit: %d genes, %d with CNV calls",
             len(cnvkit), (cnvkit["cnvkit_call"] != "neutral").sum())

    zscore = load_zscore_genes(Path(args.zscore_genes))
    log.info("Z-score: %d genes, %d with CNV calls",
             len(zscore), (zscore["zscore_call"] != "neutral").sum())

    if has_cnmops:
        cnmops = load_cnmops_genes(cnmops_path)
        log.info("cn.mops: %d genes, %d with CNV calls",
                 len(cnmops), (cnmops["cnmops_call"] != "neutral").sum())

    if has_exon_cnv:
        exon_cnv = load_exon_cnv(exon_cnv_path)
        log.info("ExonCNV: %d genes, %d with CNV calls",
                 len(exon_cnv), (exon_cnv["exon_call"] != "neutral").sum())

    # Merge callers on gene name
    merged = cnvkit[["gene", "chromosome", "start", "end",
                     "cnvkit_call", "cnvkit_log2", "cnvkit_n_exons",
                     "cnvkit_confidence", "LOO_FP_rate", "blacklist_frac"]].copy()

    merged = merged.merge(zscore, on="gene", how="outer")
    if has_cnmops:
        merged = merged.merge(cnmops, on="gene", how="outer")
    if has_exon_cnv:
        merged = merged.merge(exon_cnv, on="gene", how="outer")

    # Fill NAs for active callers
    for col in active_callers:
        if col in merged.columns:
            merged[col] = merged[col].fillna("not_tested")
        else:
            merged[col] = "not_tested"

    merged["cnvkit_log2"] = merged["cnvkit_log2"].fillna(0.0)
    merged["zscore_log2"] = merged.get("zscore_log2", pd.Series(0.0)).fillna(0.0)
    merged["zscore_mean_z"] = merged.get("zscore_mean_z", pd.Series(0.0)).fillna(0.0)

    # Count callers and determine consensus
    caller_results = merged.apply(
        lambda row: count_callers(row, active_callers), axis=1)
    merged["n_callers_agree"] = [r[0] for r in caller_results]
    merged["consensus_type"] = [r[1] for r in caller_results]
    merged["agreeing_callers"] = [",".join(c.replace("_call", "") for c in r[2])
                                   for r in caller_results]
    merged["n_total_callers"] = [r[3] for r in caller_results]

    # LOO FP as percentage for display
    merged["LOO_FP_pct"] = merged["LOO_FP_rate"].fillna(0) * 100

    # Assign tier and confidence
    tier_results = merged.apply(assign_tier, axis=1)
    merged["tier"] = [r[0] for r in tier_results]
    merged["tier_reason"] = [r[1] for r in tier_results]
    merged["confidence"] = merged.apply(determine_confidence, axis=1)

    # Sort by chromosome and position
    chrom_order = [f"chr{i}" for i in range(1, 23)] + ["chrX", "chrY"]
    merged["chrom_idx"] = merged["chromosome"].map(
        {c: i for i, c in enumerate(chrom_order)}
    ).fillna(99)
    merged = merged.sort_values(["chrom_idx", "start"]).drop(columns=["chrom_idx"])

    # Select output columns
    out_cols = [
        "gene", "chromosome", "start", "end",
        "cnvkit_call", "zscore_call",
    ]
    if has_cnmops:
        out_cols.append("cnmops_call")
    if has_exon_cnv:
        out_cols.append("exon_call")
    out_cols += [
        "n_callers_agree", "n_total_callers", "tier", "LOO_FP_pct", "confidence",
        "consensus_type", "agreeing_callers", "tier_reason",
        "cnvkit_log2", "zscore_log2", "zscore_mean_z",
    ]
    if has_cnmops:
        out_cols += ["cnmops_cn", "cnmops_log2"]
    if has_exon_cnv:
        out_cols += ["exon_log2", "exon_score", "exon_event_type",
                     "exon_clinical_flag"]
    out_cols += ["cnvkit_confidence", "LOO_FP_rate", "blacklist_frac"]
    out_cols = [c for c in out_cols if c in merged.columns]

    # Write full concordance
    full_path = out_dir / f"{sample}_cnv_concordance.tsv"
    merged[out_cols].to_csv(full_path, sep="\t", index=False)
    log.info("Full concordance: %s (%d genes)", full_path, len(merged))

    # Summary by tier
    log.info("")
    log.info("=== Tier Summary ===")
    for tier in ["TIER_1", "TIER_2", "TIER_3", "FILTERED", "NEUTRAL"]:
        tier_genes = merged[merged["tier"] == tier]
        n = len(tier_genes)
        if n > 0:
            gene_list = ", ".join(tier_genes["gene"].tolist())
            log.info("  %-12s  %d genes: %s", tier, n, gene_list)
        else:
            log.info("  %-12s  %d genes", tier, n)

    # Detailed per-caller breakdown for non-neutral genes
    non_neutral = merged[merged["tier"] != "NEUTRAL"].copy()
    if len(non_neutral) > 0:
        log.info("")
        log.info("=== Detailed Calls ===")
        header_parts = ["%-12s %-7s  %-8s %-8s" % ("Gene", "Type", "CNVKit", "Zscore")]
        if has_cnmops:
            header_parts.append("%-8s" % "cnmops")
        if has_exon_cnv:
            header_parts.append("%-8s" % "ExonCNV")
        header_parts.append("n_cal  tier      FP%%    confidence")
        log.info("  " + " ".join(header_parts))
        log.info("  " + "-" * 95)
        for _, row in non_neutral.iterrows():
            parts = ["%-12s %-7s  %-8s %-8s" % (
                row["gene"], row["consensus_type"],
                row["cnvkit_call"], row["zscore_call"])]
            if has_cnmops:
                parts.append("%-8s" % row.get("cnmops_call", "n/a"))
            if has_exon_cnv:
                exon_val = row.get("exon_call", "n/a")
                flag = row.get("exon_clinical_flag", "")
                label = f"{exon_val}" if not flag else f"{exon_val}*"
                parts.append("%-8s" % label)
            parts.append("%d/%d    %-9s %.1f%%   %s" % (
                row["n_callers_agree"], row["n_total_callers"],
                row["tier"], row["LOO_FP_pct"], row["confidence"]))
            log.info("  " + " ".join(parts))

    log.info("")
    log.info("=== Done ===")


if __name__ == "__main__":
    main()
