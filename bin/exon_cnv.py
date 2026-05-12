#!/usr/bin/env python3
"""
12g_exon_cnv.py — Exon-level CNV detection for partial gene events.

Scans each gene using a sliding window of consecutive exons to detect
partial gains/losses that get diluted in whole-gene averages (genemetrics).

Critical for:
  - KMT2A-PTD (partial tandem duplication, early exons gained)
  - IKZF1 Ik6 deletions (various exon combinations lost)
  - Focal CDKN2A/CDKN2B deletions

Usage:
    python 12g_exon_cnv.py \
        -s SAMPLE \
        --cnr results/SAMPLE/cnvkit/SAMPLE.cnr \
        --bed bedfiles/MYOPOOL_240125_UBTF_hg38.bed \
        -o results/SAMPLE/cnv_calls
"""

import argparse
import logging
import os
import re
import sys

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

# --- Thresholds ---
WINDOW_MEAN_THRESH = 0.4       # |window_mean| must exceed this
SCORE_THRESH = 0.3              # |window_mean - outside_mean| must exceed this
SCORE_THRESH_LARGE = 0.4        # stricter score for genes with many exons
LARGE_GENE_EXON_CUTOFF = 15     # genes with >= this many exons use SCORE_THRESH_LARGE
OUTSIDE_NEUTRAL_THRESH = 0.7    # |outside_mean| must be below this for partial events
                                # Set at 0.7 because panel normalization can shift
                                # background exons; score threshold ensures contrast
WHOLE_GENE_THRESH = 0.4         # |gene_mean| for whole-gene events

# Sliding window sizes
WINDOW_SIZES = [3, 4, 5, 6, 7, 8]
MIN_EXONS_DEFAULT = 3   # minimum exons for sliding window scan

# Genes where even 1-2 exons are clinically significant
LOW_EXON_GENES = {"CDKN2A", "CDKN2B", "CEBPA"}
MIN_EXONS_LOW = 1


def parse_args():
    ap = argparse.ArgumentParser(
        description="Exon-level CNV detection for partial gene events.")
    ap.add_argument("-s", "--sample", required=True, help="Sample name")
    ap.add_argument("--cnr", required=True, help="CNVKit .cnr file")
    ap.add_argument("--bed", default=DEFAULT_BED, help="Panel BED file")
    ap.add_argument("-o", "--outdir", required=True, help="Output directory")
    return ap.parse_args()


# ---------------------------------------------------------------------------
# BED parsing -> gene -> ordered exon list
# ---------------------------------------------------------------------------

def _clean_exon_name(raw):
    """Normalize exon name: strip sub-probe suffixes like _1, _2 etc.

    Examples:
      'KMT2A_Ex_3' -> '3'
      '926537_53648242_KMT2A_Ex_1B_1' -> '1B'
      'Target=137;ProbeIdx=11;KMT2A_Ex_2' -> '2'
    """
    m = re.search(r'_Ex_(\d+[A-Za-z]?)(?:_\d+)?$', raw)
    if m:
        return m.group(1)
    m = re.search(r'_Ex_(\w+)', raw)
    if m:
        return m.group(1)
    return None


def _clean_gene_name(raw):
    """Extract gene name from BED name field."""
    m = re.search(r';([A-Za-z][A-Za-z0-9]+)_Ex_', raw)
    if m:
        return m.group(1)
    m = re.search(r'_([A-Z][A-Z0-9]+)_Ex_', raw, re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.match(r'([A-Za-z][A-Za-z0-9]+)_Ex_', raw)
    if m:
        return m.group(1)
    return None


def exon_sort_key(exon_str):
    """Sort exon names numerically: '1A' < '2' < '10'."""
    m = re.match(r'(\d+)(.*)', str(exon_str))
    if m:
        return (int(m.group(1)), m.group(2))
    return (9999, str(exon_str))


def exon_number(exon_str):
    """Extract numeric part of exon name."""
    m = re.match(r'(\d+)', str(exon_str))
    return int(m.group(1)) if m else 0


def parse_bed(bed_path):
    """Parse BED -> dict of gene -> ordered list of {exon, chrom, start, end}.

    Multiple BED rows mapping to the same gene+exon are merged into one entry
    with the min(start) and max(end).
    """
    gene_exon_coords = {}  # (gene, exon) -> {chrom, start, end}

    with open(bed_path) as f:
        for line in f:
            if line.startswith(("#", "track")):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 4:
                continue
            chrom, start, end, name = parts[0], int(parts[1]), int(parts[2]), parts[3]
            gene = _clean_gene_name(name)
            exon = _clean_exon_name(name)
            if not gene or not exon:
                continue

            key = (gene, exon)
            if key not in gene_exon_coords:
                gene_exon_coords[key] = {"chrom": chrom, "start": start, "end": end}
            else:
                gene_exon_coords[key]["start"] = min(gene_exon_coords[key]["start"], start)
                gene_exon_coords[key]["end"] = max(gene_exon_coords[key]["end"], end)

    # Build gene -> sorted exon list
    genes = {}
    for (gene, exon), coords in gene_exon_coords.items():
        if gene not in genes:
            genes[gene] = []
        genes[gene].append({
            "exon": exon,
            "chrom": coords["chrom"],
            "start": coords["start"],
            "end": coords["end"],
        })

    for gene in genes:
        genes[gene].sort(key=lambda e: exon_sort_key(e["exon"]))

    log.info("Parsed %d genes from BED (%d total exon entries)",
             len(genes), len(gene_exon_coords))
    return genes


# ---------------------------------------------------------------------------
# CNR loading and exon-level log2 extraction
# ---------------------------------------------------------------------------

def load_cnr(cnr_path):
    """Load CNR file, filter to target bins only."""
    df = pd.read_csv(cnr_path, sep="\t")
    df = df[df["gene"] != "Antitarget"].copy()
    return df


def extract_exon_log2(cnr, gene_exons):
    """For a gene's exon list, extract mean log2 per exon from CNR bins.

    Returns list of (exon_name, mean_log2) in exon order.
    """
    if not gene_exons:
        return []

    chrom = gene_exons[0]["chrom"]
    chrom_cnr = cnr[cnr["chromosome"] == chrom]
    if chrom_cnr.empty:
        return []

    results = []
    for exon_info in gene_exons:
        es, ee = exon_info["start"], exon_info["end"]
        overlap = chrom_cnr[(chrom_cnr["start"] < ee) & (chrom_cnr["end"] > es)]
        if not overlap.empty:
            mean_log2 = overlap["log2"].mean()
            results.append((exon_info["exon"], mean_log2))

    return results


# ---------------------------------------------------------------------------
# Sliding window scan
# ---------------------------------------------------------------------------

def sliding_window_scan(exon_log2s, gene_name):
    """Scan a gene's exon-level log2 values for partial and whole-gene events.

    Returns list of detected events (dicts).
    """
    n = len(exon_log2s)
    if n == 0:
        return []

    min_exons = MIN_EXONS_LOW if gene_name in LOW_EXON_GENES else MIN_EXONS_DEFAULT

    exon_names = [e[0] for e in exon_log2s]
    log2_vals = np.array([e[1] for e in exon_log2s])
    gene_mean = np.mean(log2_vals)

    # Score threshold: stricter for large genes to reduce noise
    score_thresh = SCORE_THRESH_LARGE if n >= LARGE_GENE_EXON_CUTOFF else SCORE_THRESH

    events = []

    # --- Check for whole-gene events (no minimum exon count) ---
    if abs(gene_mean) > WHOLE_GENE_THRESH:
        event_type = "whole_gene_gain" if gene_mean > 0 else "whole_gene_loss"
        events.append({
            "event_type": event_type,
            "exon_start": exon_names[0],
            "exon_end": exon_names[-1],
            "exon_range_log2": gene_mean,
            "background_log2": 0.0,
            "score": gene_mean,
            "n_affected": n,
            "n_total": n,
            "window_size": n,
        })

    # --- For genes with few exons in LOW_EXON_GENES, check each exon directly ---
    if n < MIN_EXONS_DEFAULT and gene_name in LOW_EXON_GENES:
        low_exon_events = []
        for i, (ename, elog2) in enumerate(exon_log2s):
            if abs(elog2) > WINDOW_MEAN_THRESH:
                event_type = "partial_gain" if elog2 > 0 else "partial_loss"
                low_exon_events.append({
                    "event_type": event_type,
                    "exon_start": ename,
                    "exon_end": ename,
                    "exon_range_log2": elog2,
                    "background_log2": 0.0,
                    "score": elog2,
                    "n_affected": 1,
                    "n_total": n,
                    "window_size": 1,
                })
        # Keep only best partial per direction
        events.extend(_best_partial_per_direction(low_exon_events))
        return events

    # --- Need enough exons for partial scanning ---
    if n < min_exons:
        return events  # may still have whole_gene event

    # --- Sliding window scan for partial events ---
    # Track best event per direction (gain vs loss)
    best_gain = None
    best_gain_score = 0
    best_loss = None
    best_loss_score = 0

    for w in WINDOW_SIZES:
        if w >= n:
            continue
        for start_idx in range(n - w + 1):
            end_idx = start_idx + w
            window_vals = log2_vals[start_idx:end_idx]
            outside_vals = np.concatenate([log2_vals[:start_idx], log2_vals[end_idx:]])

            window_mean = np.mean(window_vals)
            outside_mean = np.mean(outside_vals) if len(outside_vals) > 0 else 0.0
            score = window_mean - outside_mean

            # Check detection criteria
            if abs(window_mean) < WINDOW_MEAN_THRESH:
                continue
            if abs(score) < score_thresh:
                continue
            if abs(outside_mean) >= OUTSIDE_NEUTRAL_THRESH:
                continue

            event = {
                "event_type": "partial_gain" if score > 0 else "partial_loss",
                "exon_start": exon_names[start_idx],
                "exon_end": exon_names[end_idx - 1],
                "exon_range_log2": window_mean,
                "background_log2": outside_mean,
                "score": score,
                "n_affected": w,
                "n_total": n,
                "window_size": w,
            }

            if score > 0 and abs(score) > best_gain_score:
                best_gain_score = abs(score)
                best_gain = event
            elif score < 0 and abs(score) > best_loss_score:
                best_loss_score = abs(score)
                best_loss = event

    if best_gain is not None:
        events.append(best_gain)
    if best_loss is not None:
        events.append(best_loss)

    # --- Targeted clinical pattern scan ---
    # For known clinical genes, check specific exon ranges even if the
    # generic best-window didn't land on them (e.g., KMT2A exons 1A/1B
    # can be higher than the PTD region and steal the best window).
    # Clinical events are ALWAYS kept alongside generic events when they
    # represent a distinct clinical pattern (e.g., KMT2A-PTD exons 2-9
    # vs generic best window exons 1A-2).
    clinical_events = _targeted_clinical_scan(exon_names, log2_vals, n,
                                              score_thresh)
    for ce in clinical_events:
        # Don't add if we already have the exact same range
        direction = "gain" if "gain" in ce["event_type"] else "loss"
        existing = best_gain if direction == "gain" else best_loss
        if existing and existing["exon_start"] == ce["exon_start"] \
                and existing["exon_end"] == ce["exon_end"]:
            continue
        # Clinical patterns with different exon ranges are kept alongside
        # the generic best window (they represent different interpretations)
        events.append(ce)

    return events


def _best_partial_per_direction(partial_events):
    """Keep only the best partial event per direction (gain/loss)."""
    best = {}  # direction -> event
    for e in partial_events:
        direction = "gain" if "gain" in e["event_type"] else "loss"
        if direction not in best or abs(e["score"]) > abs(best[direction]["score"]):
            best[direction] = e
    return list(best.values())


def _targeted_clinical_scan(exon_names, log2_vals, n, score_thresh):
    """Check specific exon ranges for known clinical patterns.

    This catches cases where a non-clinical artifact window scores higher
    than the true clinical event.
    """
    events = []
    exon_nums = [exon_number(e) for e in exon_names]

    # --- KMT2A-PTD: check exons 2-9 region ---
    # Use relaxed score threshold based on base SCORE_THRESH (not the
    # tightened large-gene threshold) since clinical patterns have high
    # prior probability and clinical significance
    clinical_score_thresh = SCORE_THRESH * 0.8  # 0.24
    ptd_indices = [i for i, en in enumerate(exon_nums) if 2 <= en <= 9]
    if len(ptd_indices) >= 3:
        ptd_vals = log2_vals[ptd_indices]
        other_indices = [i for i in range(n) if i not in ptd_indices]
        if other_indices:
            other_vals = log2_vals[other_indices]
            ptd_mean = np.mean(ptd_vals)
            other_mean = np.mean(other_vals)
            score = ptd_mean - other_mean
            if ptd_mean > WINDOW_MEAN_THRESH and score > clinical_score_thresh:
                events.append({
                    "event_type": "partial_gain",
                    "exon_start": exon_names[ptd_indices[0]],
                    "exon_end": exon_names[ptd_indices[-1]],
                    "exon_range_log2": ptd_mean,
                    "background_log2": other_mean,
                    "score": score,
                    "n_affected": len(ptd_indices),
                    "n_total": n,
                    "window_size": len(ptd_indices),
                })

    return events


# ---------------------------------------------------------------------------
# Clinical flag assignment
# ---------------------------------------------------------------------------

def assign_clinical_flag(gene_name, event):
    """Check if an event matches a known clinical pattern."""
    event_type = event["event_type"]
    start_num = exon_number(event["exon_start"])
    end_num = exon_number(event["exon_end"])
    affected_nums = list(range(start_num, end_num + 1))
    n_total = event["n_total"]

    if gene_name == "KMT2A":
        # KMT2A-PTD: any contiguous gain block overlapping Ex_2-Ex_9
        if event_type == "partial_gain":
            ptd_exons = [e for e in affected_nums if 2 <= e <= 9]
            if len(ptd_exons) >= 2:
                return "KMT2A-PTD"

    elif gene_name == "IKZF1":
        if event_type == "partial_loss":
            return "IKZF1-Ik6"
        if event_type == "whole_gene_loss":
            return "IKZF1-del"

    elif gene_name == "CDKN2A":
        if "loss" in event_type:
            return "CDKN2A-del"

    elif gene_name == "CDKN2B":
        if "loss" in event_type:
            return "CDKN2B-del"

    return ""


def detect_co_deletions(results):
    """Check for CDKN2A/CDKN2B co-deletion and update flags."""
    cdkn2a_del = any(r["Clinical_Flag"] == "CDKN2A-del" for r in results)
    cdkn2b_del = any(r["Clinical_Flag"] == "CDKN2B-del" for r in results)

    if cdkn2a_del and cdkn2b_del:
        for r in results:
            if r["Clinical_Flag"] in ("CDKN2A-del", "CDKN2B-del"):
                r["Clinical_Flag"] = "CDKN2A/CDKN2B_co-deletion"


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def _deduplicate_results(results):
    """Keep one partial event per gene+direction, preferring clinical flags.

    Whole-gene and partial events for the same gene are both kept (different
    interpretations). But multiple partial events for the same gene in the
    same direction are collapsed to the best one.
    """
    from collections import defaultdict

    whole_gene = [r for r in results if "whole_gene" in r["Event_Type"]]
    partials = [r for r in results if "partial" in r["Event_Type"]]

    # Group partials by (gene, direction)
    groups = defaultdict(list)
    for r in partials:
        direction = "gain" if "gain" in r["Event_Type"] else "loss"
        groups[(r["Gene"], direction)].append(r)

    deduped_partials = []
    for key, events in groups.items():
        if len(events) == 1:
            deduped_partials.append(events[0])
            continue

        # Prefer events with clinical flags
        flagged = [e for e in events if e["Clinical_Flag"]]
        unflagged = [e for e in events if not e["Clinical_Flag"]]

        if flagged:
            # Keep the best flagged event
            best = max(flagged, key=lambda e: abs(e["Score"]))
            deduped_partials.append(best)
        else:
            # Keep the best by |score|
            best = max(unflagged, key=lambda e: abs(e["Score"]))
            deduped_partials.append(best)

    # Combine and sort by gene, then event type
    out = whole_gene + deduped_partials
    out.sort(key=lambda r: (r["Gene"], r["Event_Type"]))
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()
    sample = args.sample

    log.info("=== Exon-level CNV Detection (12g) ===")
    log.info("Sample: %s", sample)
    log.info("CNR:    %s", args.cnr)
    log.info("BED:    %s", args.bed)

    for f, label in [(args.cnr, "CNR"), (args.bed, "BED")]:
        if not os.path.isfile(f):
            log.error("%s not found: %s", label, f)
            sys.exit(1)

    os.makedirs(args.outdir, exist_ok=True)

    genes = parse_bed(args.bed)
    cnr = load_cnr(args.cnr)
    log.info("Loaded %d target bins from CNR", len(cnr))

    # Scan each gene
    results = []
    n_partial = 0
    n_whole = 0

    for gene_name in sorted(genes.keys()):
        exon_list = genes[gene_name]
        exon_log2s = extract_exon_log2(cnr, exon_list)

        if len(exon_log2s) == 0:
            continue

        events = sliding_window_scan(exon_log2s, gene_name)
        for event in events:
            clinical_flag = assign_clinical_flag(gene_name, event)
            exons_affected = (f"Ex_{event['exon_start']}-Ex_{event['exon_end']}"
                              if event["exon_start"] != event["exon_end"]
                              else f"Ex_{event['exon_start']}")

            results.append({
                "Sample": sample,
                "Gene": gene_name,
                "Event_Type": event["event_type"],
                "Exons_Affected": exons_affected,
                "Exon_Range_Log2": round(event["exon_range_log2"], 4),
                "Background_Log2": round(event["background_log2"], 4),
                "Score": round(event["score"], 4),
                "N_Exons_Affected": event["n_affected"],
                "N_Exons_Total": event["n_total"],
                "Clinical_Flag": clinical_flag,
            })

            if "partial" in event["event_type"]:
                n_partial += 1
            else:
                n_whole += 1

    # Deduplicate: one partial per gene+direction, prefer clinical flags
    results = _deduplicate_results(results)

    # Recount after dedup
    n_partial = sum(1 for r in results if "partial" in r["Event_Type"])
    n_whole = sum(1 for r in results if "whole_gene" in r["Event_Type"])

    # Check for co-deletions
    detect_co_deletions(results)

    # Write output
    out_path = os.path.join(args.outdir, f"{sample}_exon_cnv.tsv")
    if results:
        df = pd.DataFrame(results)
        df.to_csv(out_path, sep="\t", index=False)
    else:
        cols = ["Sample", "Gene", "Event_Type", "Exons_Affected",
                "Exon_Range_Log2", "Background_Log2", "Score",
                "N_Exons_Affected", "N_Exons_Total", "Clinical_Flag"]
        pd.DataFrame(columns=cols).to_csv(out_path, sep="\t", index=False)

    log.info("Detected %d partial events, %d whole-gene events", n_partial, n_whole)
    if results:
        for r in results:
            flag = f" [{r['Clinical_Flag']}]" if r["Clinical_Flag"] else ""
            log.info("  %s %s: %s log2=%.3f score=%.3f%s",
                     r["Gene"], r["Event_Type"], r["Exons_Affected"],
                     r["Exon_Range_Log2"], r["Score"], flag)
    log.info("Output: %s", out_path)


if __name__ == "__main__":
    main()
