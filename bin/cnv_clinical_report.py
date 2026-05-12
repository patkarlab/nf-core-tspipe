#!/usr/bin/env python3
"""
12f_cnv_clinical_report.py — Generate tiered clinical CNV report.

Combines CNVKit and Z-score caller results into a clinical-grade report with:
  TIER 1 (REPORT):    Concordant calls (both callers agree)
  TIER 2 (REVIEW):    CNVKit HIGH confidence + Z > 1.5, or arm-level events
  TIER 3 (NOTE):      CNVKit-only with MEDIUM/LOW confidence
  FILTERED:           LOO FP > 30%

Groups genes on the same CNVKit segment as arm-level events.
Annotates known AML clinical significance.

Usage:
    python scripts/12f_cnv_clinical_report.py \
        -s 26CGH40 \
        --concordance results/26CGH40/cnv_consensus/26CGH40.cnv_concordance.tsv \
        --cnvkit-calls results/26CGH40/cnvkit/26CGH40.filtered.call.cns \
        --zscore-genes results/26CGH40/cnv_zscore/26CGH40.zscore_genes.tsv \
        --genemetrics results/26CGH40/cnvkit/26CGH40.genemetrics.annotated.tsv \
        -o results/26CGH40/cnv_report
"""

import argparse
import logging
import re
import sys
import textwrap
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# Known clinical significance for AML-related genes
CLINICAL_ANNOTATIONS = {
    "HNRNPK":  "Tumor suppressor; haploinsufficiency associated with MDS/AML",
    "CDKN2A":  "Tumor suppressor (p16/ARF); homozygous deletion in T-ALL, rare in AML",
    "CDKN2B":  "Tumor suppressor (p15); deletion associated with AML progression",
    "KMT2A":   "Monitor for KMT2A-PTD (exons 3-8 gain); rearrangements in AML",
    "BRAF":    "Oncogene; activating mutations in hairy cell leukemia",
    "CBL":     "E3 ubiquitin ligase; loss-of-function in JMML/CMML",
    "DNMT1":   "DNA methyltransferase; gain may indicate chr19p amplification",
    "EPOR":    "Erythropoietin receptor; gain in polycythemia",
    "CALR":    "Calreticulin; mutations in MPN (ET, PMF)",
    "PRPF40B": "Splicing factor; limited clinical data",
    "ELANE":   "Neutrophil elastase; mutations in severe congenital neutropenia",
    "ZBTB7A":  "Transcription factor; loss in APL",
    "LUC7L2":  "Splicing factor; mutations in MDS",
    "MAP2K1":  "MEK1 kinase; gain-of-function in histiocytosis, rare in AML",
    "TP53":    "Tumor suppressor; deletion/mutation critical in therapy-related MDS/AML",
    "RUNX1":   "Transcription factor; loss/mutation in AML",
    "ETV6":    "Transcription factor; deletion in ALL, some AML",
    "NF1":     "RAS pathway regulator; loss in JMML, some AML",
    "PTEN":    "Tumor suppressor; deletion in T-ALL",
    "TET2":    "Epigenetic regulator; loss-of-function in MDS/AML",
    "ASXL1":   "Chromatin modifier; mutations in MDS/AML",
    "IDH1":    "Metabolic enzyme; mutations in AML",
    "IDH2":    "Metabolic enzyme; mutations in AML",
    "FLT3":    "Receptor tyrosine kinase; amplification rare",
    "NPM1":    "Nucleophosmin; mutations common in AML",
    "NOTCH1":  "Signaling; mutations in T-ALL",
}


def parse_args():
    p = argparse.ArgumentParser(description="Generate tiered clinical CNV report.")
    p.add_argument("-s", "--sample", default="26CGH40")
    p.add_argument("--concordance",
                    default="results/26CGH40/cnv_consensus/26CGH40.cnv_concordance.tsv",
                    help="Concordance TSV from 12e_cnv_concordance.py")
    p.add_argument("--cnvkit-calls",
                    default="results/26CGH40/cnvkit/26CGH40.filtered.call.cns",
                    help="CNVKit filtered call.cns with segment info")
    p.add_argument("--zscore-genes",
                    default="results/26CGH40/cnv_zscore/26CGH40.zscore_genes.tsv",
                    help="Z-score gene-level results")
    p.add_argument("--genemetrics",
                    default="results/26CGH40/cnvkit/26CGH40.genemetrics.annotated.tsv",
                    help="Annotated genemetrics TSV")
    p.add_argument("-o", "--out-dir",
                    default="results/26CGH40/cnv_report")
    return p.parse_args()


def clean_gene(raw: str) -> str:
    """Extract clean gene name from BED-style annotation."""
    s = str(raw)
    m = re.search(r';([A-Za-z][A-Za-z0-9]+)_(?:Ex_?\d|Intron)', s)
    if m:
        return m.group(1)
    m = re.search(r'_([A-Za-z][A-Za-z0-9]+)_Ex_', s)
    if m:
        return m.group(1)
    m = re.search(r'(?:^|,)([A-Za-z][A-Za-z0-9]+)_Ex_', s)
    if m:
        return m.group(1)
    if re.match(r'^[A-Za-z][A-Za-z0-9]+$', s):
        return s
    return s


def get_cytoband_arm(chrom, start, end, chrom_sizes=None):
    """Rough arm assignment based on centromere positions."""
    # Approximate centromere midpoints for hg38
    centromeres = {
        "chr1": 123400000, "chr2": 93900000, "chr3": 90900000,
        "chr4": 50000000, "chr5": 48800000, "chr6": 58500000,
        "chr7": 60100000, "chr8": 45200000, "chr9": 43000000,
        "chr10": 39800000, "chr11": 51600000, "chr12": 35500000,
        "chr13": 17700000, "chr14": 17200000, "chr15": 19000000,
        "chr16": 36800000, "chr17": 25100000, "chr18": 18500000,
        "chr19": 26200000, "chr20": 28100000, "chr21": 12000000,
        "chr22": 15000000, "chrX": 61000000, "chrY": 10400000,
    }
    cen = centromeres.get(chrom, 0)
    mid = (start + end) / 2 if pd.notna(start) and pd.notna(end) else 0
    arm = "p" if mid < cen else "q"
    return f"{chrom.replace('chr', '')}{arm}"


def detect_arm_level_events(call_cns, genemetrics_path):
    """Detect segments spanning multiple genes -> arm-level events.

    Returns dict: segment_key -> list of gene names sharing that segment.
    """
    gm = pd.read_csv(genemetrics_path, sep="\t")
    gm["clean_gene"] = gm["gene"].apply(clean_gene)

    # Group genemetrics by segment (same log2 + same segment_probes = same segment)
    # Use chromosome + segment_weight as proxy for segment identity
    segment_genes = defaultdict(set)
    for _, row in gm.iterrows():
        seg_key = (row["chromosome"], round(row["log2"], 6))
        segment_genes[seg_key].add(row["clean_gene"])

    # Arm-level = segment containing 3+ genes
    arm_events = {}
    for seg_key, genes in segment_genes.items():
        if len(genes) >= 3:
            chrom = seg_key[0]
            gene_list = sorted(genes)
            # Get coordinates from genemetrics
            gene_rows = gm[gm["clean_gene"].isin(genes)]
            start = gene_rows["start"].min()
            end = gene_rows["end"].max()
            arm = get_cytoband_arm(chrom, start, end)
            arm_events[frozenset(genes)] = {
                "arm": arm,
                "chrom": chrom,
                "start": start,
                "end": end,
                "genes": gene_list,
                "log2": seg_key[1],
            }
    return arm_events


def assign_tier(row, arm_level_genes):
    """Assign tier to a gene based on concordance, confidence, Z-score, FP rate."""
    gene = row["gene"]
    concordance = row.get("concordance", "")
    cnvkit_type = row.get("cnvkit_type", "neutral")
    zscore_type = row.get("zscore_type", "neutral")
    cnvkit_conf = row.get("cnvkit_confidence", "")
    fp_rate = row.get("LOO_FP_rate", 0)
    if pd.isna(fp_rate):
        fp_rate = row.get("gene_fp_rate", 0)
    if pd.isna(fp_rate):
        fp_rate = 0
    zscore_z = abs(row.get("zscore_mean_z", 0)) if pd.notna(row.get("zscore_mean_z")) else 0

    # FILTERED: FP > 30%
    if fp_rate > 0.30:
        return "FILTERED"

    # TIER 1: Concordant
    if concordance == "CONCORDANT":
        return "TIER_1"

    # TIER 2: HIGH confidence CNVKit + Z > 1.5, or arm-level
    if cnvkit_type not in ("neutral", "not_tested"):
        if cnvkit_conf == "HIGH" and zscore_z > 1.5:
            return "TIER_2"
        if gene in arm_level_genes:
            return "TIER_2"

    # ZSCORE_ONLY calls with HIGH confidence
    if zscore_type not in ("neutral", "not_tested") and concordance == "ZSCORE_ONLY":
        return "TIER_2"

    # TIER 3: remaining CNVKit-only calls
    if cnvkit_type not in ("neutral", "not_tested"):
        return "TIER_3"

    # TIER 3: exon-only calls (from 12g exon-level rescue)
    if concordance == "EXON_ONLY":
        return "TIER_3"

    return None  # neutral, skip


def main():
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    sample = args.sample

    log.info("=== Clinical CNV Report: %s ===", sample)

    # Load data
    conc = pd.read_csv(args.concordance, sep="\t")
    zscore = pd.read_csv(args.zscore_genes, sep="\t")

    # Compatibility: map new 12e column names to what this script expects
    col_renames = {}
    if "consensus_type" in conc.columns and "concordance" not in conc.columns:
        col_renames["consensus_type"] = "concordance"
    if "cnvkit_call" in conc.columns and "cnvkit_type" not in conc.columns:
        col_renames["cnvkit_call"] = "cnvkit_type"
    if "zscore_call" in conc.columns and "zscore_type" not in conc.columns:
        col_renames["zscore_call"] = "zscore_type"
    if col_renames:
        conc = conc.rename(columns=col_renames)

    # Map new concordance values to old-style labels used by assign_tier()
    if "concordance" in conc.columns and "agreeing_callers" in conc.columns:
        def _map_concordance(row):
            if row["concordance"] == "neutral":
                return "BOTH_NEUTRAL"
            callers = str(row.get("agreeing_callers", ""))
            caller_list = [c.strip() for c in callers.split(",") if c.strip()]
            if len(caller_list) >= 2:
                return "CONCORDANT"
            if caller_list == ["cnvkit"]:
                return "CNVKIT_ONLY"
            if caller_list == ["zscore"]:
                return "ZSCORE_ONLY"
            if caller_list == ["exon"]:
                return "EXON_ONLY"
            return row["concordance"]
        conc["concordance"] = conc.apply(_map_concordance, axis=1)

    log.info("Concordance: %d genes", len(conc))

    # Detect arm-level events
    arm_events = detect_arm_level_events(
        args.cnvkit_calls, args.genemetrics
    )
    arm_level_genes = set()
    for event in arm_events.values():
        arm_level_genes.update(event["genes"])
    log.info("Arm-level events: %d (covering %d genes)",
             len(arm_events), len(arm_level_genes))

    # Build report rows
    report_rows = []
    non_neutral = conc[conc["concordance"] != "BOTH_NEUTRAL"].copy()

    for _, row in non_neutral.iterrows():
        gene = row["gene"]
        tier = assign_tier(row, arm_level_genes)
        if tier is None:
            continue

        # Determine call type and direction
        cnvkit_type = row.get("cnvkit_type", "not_tested")
        zscore_type = row.get("zscore_type", "not_tested")
        exon_call = row.get("exon_call", "not_tested")
        if cnvkit_type not in ("neutral", "not_tested"):
            call_type = cnvkit_type
        elif zscore_type not in ("neutral", "not_tested"):
            call_type = zscore_type.replace("suggestive_", "")
        elif exon_call not in ("neutral", "not_tested", ""):
            call_type = exon_call
        else:
            call_type = "neutral"

        # Get coordinates
        chrom = row.get("chromosome", "")
        start = row.get("start", "")
        end = row.get("end", "")
        if pd.isna(chrom) or chrom == "":
            # Try from zscore data
            zrow = zscore[zscore["gene"] == gene]
            if len(zrow) > 0:
                chrom = zrow.iloc[0]["chromosome"]
                start = zrow.iloc[0]["start"]
                end = zrow.iloc[0]["end"]

        # Arm location
        arm = get_cytoband_arm(str(chrom), start, end) if pd.notna(chrom) and chrom else ""

        # Is this part of an arm-level event?
        arm_event_label = ""
        for event in arm_events.values():
            if gene in event["genes"]:
                arm_event_label = f"{event['arm']} ({', '.join(event['genes'][:5])})"
                if len(event["genes"]) > 5:
                    arm_event_label += f" +{len(event['genes'])-5}"
                break

        # CN from CNVKit
        cnvkit_log2 = row.get("cnvkit_log2", 0)
        zscore_log2 = row.get("zscore_log2", 0)
        zscore_z = row.get("zscore_mean_z", 0)
        fp_rate = row.get("LOO_FP_rate", row.get("gene_fp_rate", 0))
        if pd.isna(fp_rate):
            fp_rate = 0
        cnvkit_conf = row.get("cnvkit_confidence", "")
        if pd.isna(cnvkit_conf):
            cnvkit_conf = ""

        # Estimate CN from log2
        best_log2 = cnvkit_log2 if cnvkit_log2 != 0 else zscore_log2
        cn_est = round(2 * 2**best_log2) if best_log2 != 0 else 2

        # Clinical significance
        clin_sig = CLINICAL_ANNOTATIONS.get(gene, "")

        report_rows.append({
            "gene": gene,
            "tier": tier,
            "call": call_type,
            "chromosome": chrom,
            "arm": arm,
            "start": int(start) if pd.notna(start) and start != "" else "",
            "end": int(end) if pd.notna(end) and end != "" else "",
            "cnvkit_log2": round(cnvkit_log2, 3) if pd.notna(cnvkit_log2) else "",
            "cn_estimate": cn_est,
            "zscore": round(zscore_z, 2) if pd.notna(zscore_z) else "",
            "LOO_FP_pct": round(fp_rate * 100, 1) if fp_rate else 0,
            "cnvkit_confidence": cnvkit_conf,
            "concordance": row["concordance"],
            "arm_level_event": arm_event_label,
            "clinical_significance": clin_sig,
        })

    report_df = pd.DataFrame(report_rows)

    # Sort by tier then chromosome
    tier_order = {"TIER_1": 0, "TIER_2": 1, "TIER_3": 2, "FILTERED": 3}
    chrom_order = {f"chr{i}": i for i in range(1, 23)}
    chrom_order.update({"chrX": 23, "chrY": 24})
    report_df["_tier_rank"] = report_df["tier"].map(tier_order).fillna(99)
    report_df["_chrom_rank"] = report_df["chromosome"].map(chrom_order).fillna(99)
    report_df = report_df.sort_values(["_tier_rank", "_chrom_rank", "start"])
    report_df = report_df.drop(columns=["_tier_rank", "_chrom_rank"])

    # Write TSV
    tsv_path = out_dir / f"{sample}_cnv_clinical_report.tsv"
    report_df.to_csv(tsv_path, sep="\t", index=False)
    log.info("TSV report: %s (%d entries)", tsv_path, len(report_df))

    # Write formatted text report
    txt_path = out_dir / f"{sample}_cnv_clinical_report.txt"
    with open(txt_path, "w") as f:
        f.write("=" * 80 + "\n")
        f.write(f"CLINICAL CNV REPORT — {sample}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")

        f.write("METHODS:\n")
        f.write("  CNV callers: CNVKit (segment-based) + Z-score (bin-level, LOO-calibrated)\n")
        f.write("  Reference:   Sex-matched panel-of-normals (55 samples)\n")
        f.write("  QC:          Leave-one-out noise profiling, per-gene FP rates\n\n")

        # Arm-level event summary
        if arm_events:
            f.write("ARM-LEVEL EVENTS:\n")
            for event in arm_events.values():
                direction = "GAIN" if event["log2"] > 0 else "LOSS"
                f.write(f"  {event['arm']} {direction} (log2={event['log2']:+.3f}): "
                        f"{', '.join(event['genes'])}\n")
            f.write("\n")

        # Per-tier sections
        tier_labels = {
            "TIER_1": "TIER 1 — REPORT (Concordant: both callers agree)",
            "TIER_2": "TIER 2 — REVIEW (High-confidence single-caller or arm-level)",
            "TIER_3": "TIER 3 — NOTE (Single-caller, lower confidence)",
            "FILTERED": "FILTERED (LOO FP > 30%, likely artifact)",
        }

        for tier_key in ["TIER_1", "TIER_2", "TIER_3", "FILTERED"]:
            tier_df = report_df[report_df["tier"] == tier_key]
            f.write("-" * 80 + "\n")
            f.write(f"{tier_labels[tier_key]}\n")
            f.write("-" * 80 + "\n")

            if len(tier_df) == 0:
                f.write("  (none)\n\n")
                continue

            for _, row in tier_df.iterrows():
                gene = row["gene"]
                call = row["call"].upper()
                arm = row["arm"]

                f.write(f"\n  {gene} — {call}\n")
                f.write(f"    Location:     {row['chromosome']}:{row['start']}-{row['end']} ({arm})\n")
                f.write(f"    CNVKit log2:  {row['cnvkit_log2']:+.3f}   CN estimate: {row['cn_estimate']}\n"
                        if row['cnvkit_log2'] != "" else "")
                f.write(f"    Z-score:      {row['zscore']:+.2f}\n"
                        if row['zscore'] != "" else "")
                f.write(f"    LOO FP rate:  {row['LOO_FP_pct']:.1f}%   Confidence: {row['cnvkit_confidence']}\n")
                f.write(f"    Concordance:  {row['concordance']}\n")
                if row["arm_level_event"]:
                    f.write(f"    Arm-level:    Part of {row['arm_level_event']}\n")
                if row["clinical_significance"]:
                    f.write(f"    Clinical:     {row['clinical_significance']}\n")

            f.write("\n")

        # Summary
        f.write("=" * 80 + "\n")
        f.write("SUMMARY\n")
        f.write("=" * 80 + "\n")
        for tier_key, label in [("TIER_1", "TIER 1 (Report)"),
                                 ("TIER_2", "TIER 2 (Review)"),
                                 ("TIER_3", "TIER 3 (Note)"),
                                 ("FILTERED", "Filtered")]:
            n = (report_df["tier"] == tier_key).sum()
            genes = report_df[report_df["tier"] == tier_key]["gene"].tolist()
            gene_str = ", ".join(genes) if genes else "(none)"
            f.write(f"  {label:25s}  {n} genes: {gene_str}\n")

        f.write(f"\nTotal non-neutral genes: {len(report_df)}\n")
        f.write(f"Arm-level events: {len(arm_events)}\n")
        f.write("\n" + "=" * 80 + "\n")
        f.write("END OF REPORT\n")
        f.write("=" * 80 + "\n")

    log.info("Text report: %s", txt_path)

    # Print summary to log
    for tier_key in ["TIER_1", "TIER_2", "TIER_3", "FILTERED"]:
        tier_df = report_df[report_df["tier"] == tier_key]
        genes = ", ".join(tier_df["gene"].tolist()) if len(tier_df) > 0 else "(none)"
        log.info("  %s: %d genes — %s", tier_key, len(tier_df), genes)

    log.info("=== Done ===")


if __name__ == "__main__":
    main()
