#!/usr/bin/env python3
"""
bin/cnvkit.py

CNV calling with CNVKit against a sex-matched panel-of-normals.

Ported from scripts/12_cnv_calling.py in the production targeted-seq-pipeline.
nf-core CNV wiring v1 (apply_nfcore_cnv_wiring_part2).

Differences from the production wrapper:
  - --pon, --blacklist, --loo-summary are required (no defaults). The
    modules/local/cnvkit.nf process supplies these as staged paths.
  - --sex is required and must be 'male', 'female', or 'unknown'. There is
    no 'auto' inference path here -- the sample sex is resolved upstream
    via meta.sex on the channel tuple, and the .nf module selects the
    matching PoN before invoking this script.
  - Only one cnvkit.py batch invocation. The production wrapper ran batch
    twice (default PoN -> infer sex -> re-run with sex-specific PoN) which
    is unnecessary when sex is known up front.

Workflow:
  1. cnvkit.py batch (segment against PoN; -y for male)
  2. cnvkit.py call (integer CN with AML thresholds; -y for male)
  3. cnvkit.py export seg (IGV)
  4. cnvkit.py export vcf (annotation)
  5. cnvkit.py genemetrics (gene-level gain/loss)
  6. cnvkit.py scatter (genome-wide)
  7. Per-chromosome scatter plots for panel genes
  8. Blacklist annotation (LOO QC)

Usage:
    cnvkit.py \
        --bam SAMPLE.final.bam \
        -s SAMPLE \
        -o . \
        --pon cnvkit_pon_female.cnn \
        --sex female \
        --blacklist cnvkit_noisy_bins.bed \
        --loo-summary cnvkit_loo_summary.tsv
"""

import argparse
import logging
import os
import re
import subprocess
import sys
import time

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# Myeloid AML panel: chromosome -> gene list for focused per-chromosome
# scatter plots. Hardcoded for the myeloid panel; future panels can override
# via a future --panel-gene-chroms argument.
PANEL_GENE_CHROMS = {
    "chr5":  ["NPM1"],
    "chr8":  ["RUNX1T1"],
    "chr13": ["FLT3"],
    "chr17": ["TP53", "UBTF"],
    "chr21": ["RUNX1"],
}

# CNVKit call thresholds: log2 cutoff -> integer copy number
# 0 = deep del (<-1.1), 1 = het loss (<-0.25), 2 = neutral (<0.2), 3+ = gain (>0.7)
CALL_THRESHOLDS = "-1.1,-0.25,0.2,0.7"


def parse_args():
    ap = argparse.ArgumentParser(
        description="CNV calling with CNVKit using a sex-matched PoN.",
    )
    ap.add_argument("--bam", required=True,
                    help="Input BAM (ABRA2-realigned)")
    ap.add_argument("-s", "--sample", required=True,
                    help="Sample name")
    ap.add_argument("-o", "--outdir", default=".",
                    help="Output directory (default: current dir, for nf-core staging)")
    ap.add_argument("--pon", required=True,
                    help="CNVKit PoN reference .cnn (sex-matched)")
    ap.add_argument("--sex", required=True,
                    choices=["male", "female", "unknown"],
                    help="Sample sex (controls -y on batch and call). "
                         "'unknown' is treated as female with a warning.")
    ap.add_argument("--blacklist", required=True,
                    help="Noisy bins BED from LOO QC")
    ap.add_argument("--loo-summary", required=True,
                    help="Gene-level LOO FP rate TSV")
    return ap.parse_args()


def cnvkit_batch_cmd(bam, pon_path, outdir, male_reference=False):
    """Build a cnvkit.py batch command.

    -y / --male-reference tells cnvkit the input BAM is from a male sample
    and chrX is haploid. Without -y on a male sample (against any PoN),
    chrX shows a systematic ~-1 log2 'loss'. Even with a male-specific
    PoN, -y is still required at batch time because the PoN .cnn file's
    log2 column does not carry sex information.
    """
    cmd = ["cnvkit.py", "batch", bam,
           "-r", pon_path,
           "-d", outdir,
           "--scatter", "--diagram"]
    if male_reference:
        cmd.append("-y")
    return cmd


def run(cmd, desc=None, shell=False):
    if desc:
        log.info("%s", desc)
    cmd_str = cmd if shell else " ".join(cmd)
    log.info("  cmd: %s", cmd_str)
    result = subprocess.run(cmd, capture_output=True, text=True, shell=shell)
    if result.returncode != 0:
        log.error("  FAILED (exit %d)", result.returncode)
        for line in (result.stderr or "").strip().splitlines()[-10:]:
            log.error("    %s", line.strip())
    return result.returncode, result.stdout, result.stderr


def check_prerequisites(args):
    missing = []
    for path, label in [(args.bam,        "BAM"),
                         (args.bam + ".bai", "BAM index"),
                         (args.pon,        "PoN reference"),
                         (args.blacklist,  "Blacklist BED"),
                         (args.loo_summary, "LOO summary TSV")]:
        if not os.path.isfile(path):
            log.error("%s not found: %s", label, path)
            missing.append(label)
    if missing:
        log.error("Missing prerequisites: %s", ", ".join(missing))
        sys.exit(1)


# ---------------------------------------------------------------------------
# Blacklist annotation
# ---------------------------------------------------------------------------

def load_blacklist(blacklist_path):
    """Load noisy bins BED -> list of (chrom, start, end)."""
    bins = []
    with open(blacklist_path) as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 3:
                bins.append((parts[0], int(parts[1]), int(parts[2])))
    log.info("Loaded %d blacklisted bins from %s", len(bins), blacklist_path)
    return bins


def load_loo_fp(loo_summary_path):
    """Load gene-level LOO FP rates -> dict gene_name -> fp info."""
    df = pd.read_csv(loo_summary_path, sep="\t")
    fp_map = {}
    for _, row in df.iterrows():
        fp_map[row["gene"]] = {
            "fp_gain_rate": row.get("fp_gain_rate", 0),
            "fp_loss_rate": row.get("fp_loss_rate", 0),
            "fp_any_rate":  row.get("fp_any_rate", 0),
            "loo_stdev":    row.get("stdev_log2", 0),
        }
    log.info("Loaded LOO FP rates for %d genes", len(fp_map))
    return fp_map


def parse_gene_from_field(gene_field):
    """Extract gene name from CNVKit gene field
    (e.g. 'Target=1;ProbeIdx=12;GNB1_Ex_11')."""
    m = re.search(r"([A-Za-z][A-Za-z0-9]+)_Ex_", gene_field)
    return m.group(1) if m else None


def compute_blacklist_overlap(chrom, start, end, blacklist_bins):
    """Compute fraction of a segment overlapping blacklisted bins."""
    seg_len = end - start
    if seg_len <= 0:
        return 0.0
    overlap = 0
    for bc, bs, be in blacklist_bins:
        if bc != chrom:
            continue
        ov_start = max(start, bs)
        ov_end = min(end, be)
        if ov_start < ov_end:
            overlap += ov_end - ov_start
    return min(overlap / seg_len, 1.0)


def annotate_genemetrics(genemetrics_path, blacklist_bins, loo_fp_map, output_path):
    """Add confidence, LOO_FP_rate, blacklist_frac columns to aggregated
    genemetrics TSV.

    Confidence:
      HIGH    -- no overlap with noisy bins
      MEDIUM  -- partial overlap (<= 50%)
      LOW     -- > 50% overlap with noisy bins
    """
    if not os.path.isfile(genemetrics_path):
        log.warning("Genemetrics file not found: %s", genemetrics_path)
        return
    df = pd.read_csv(genemetrics_path, sep="\t")
    if df.empty:
        log.warning("Genemetrics file is empty")
        return

    bl_by_chrom = {}
    for bc, bs, be in blacklist_bins:
        bl_by_chrom.setdefault(bc, []).append((bc, bs, be))

    confidences, fp_rates, blacklist_fracs = [], [], []
    for _, row in df.iterrows():
        chrom = row["chromosome"]
        start = int(row["start"])
        end   = int(row["end"])
        ol_frac = compute_blacklist_overlap(chrom, start, end,
                                            bl_by_chrom.get(chrom, []))
        blacklist_fracs.append(ol_frac)
        if ol_frac == 0:
            conf = "HIGH"
        elif ol_frac <= 0.5:
            conf = "MEDIUM"
        else:
            conf = "LOW"
        confidences.append(conf)
        gene_name = str(row["gene"])
        if gene_name in loo_fp_map:
            fp_rates.append(loo_fp_map[gene_name]["fp_any_rate"])
        else:
            fp_rates.append(None)

    df["LOO_FP_rate"]    = fp_rates
    df["confidence"]     = confidences
    df["blacklist_frac"] = blacklist_fracs
    df.to_csv(output_path, sep="\t", index=False, float_format="%.6f")
    log.info("  Annotated genemetrics: %s", output_path)
    log.info("  Confidence: HIGH=%d, MEDIUM=%d, LOW=%d",
             confidences.count("HIGH"),
             confidences.count("MEDIUM"),
             confidences.count("LOW"))


def aggregate_genemetrics(raw_path, out_path):
    """Aggregate raw CNVKit genemetrics (one row per probe) to one row per gene."""
    df = pd.read_csv(raw_path, sep="\t")
    if df.empty:
        df.to_csv(out_path, sep="\t", index=False)
        return
    df["clean_gene"] = df["gene"].apply(parse_gene_from_field)
    df = df[df["clean_gene"].notna()].copy()
    agg = df.groupby("clean_gene").agg(
        chromosome=("chromosome", "first"),
        start=("start", "min"),
        end=("end", "max"),
        log2=("log2", "mean"),
        depth=("depth", "mean"),
        weight=("weight", "sum"),
        ci_lo=("ci_lo", "min"),
        ci_hi=("ci_hi", "max"),
        n_probes=("gene", "count"),
    ).reset_index()
    agg.rename(columns={"clean_gene": "gene"}, inplace=True)
    chrom_order = {f"chr{i}": i for i in range(1, 23)}
    chrom_order.update({"chrX": 23, "chrY": 24})
    agg["_chrom_idx"] = agg["chromosome"].map(chrom_order).fillna(99)
    agg = agg.sort_values(["_chrom_idx", "start"]).drop(columns=["_chrom_idx"])
    agg.to_csv(out_path, sep="\t", index=False, float_format="%.6f")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    t0 = time.time()
    args = parse_args()
    sample = args.sample

    log.info("=== CNV Calling with CNVKit (bin/cnvkit.py) ===")
    log.info("Sample: %s", sample)
    log.info("BAM:    %s", args.bam)
    log.info("PoN:    %s", args.pon)
    log.info("Sex:    %s", args.sex)
    log.info("Output: %s", args.outdir)

    if args.sex == "unknown":
        log.warning("Sample sex is 'unknown'; treating as female (no -y). "
                    "If the sample is male, chrX will show a systematic ~-1 "
                    "log2 loss in the CNR file.")

    os.makedirs(args.outdir, exist_ok=True)
    check_prerequisites(args)

    male_reference = (args.sex == "male")
    bam_stem = os.path.splitext(os.path.basename(args.bam))[0]

    # Output paths (everything sample-named)
    batch_cnr = os.path.join(args.outdir, f"{bam_stem}.cnr")
    batch_cns = os.path.join(args.outdir, f"{bam_stem}.cns")
    cnr  = os.path.join(args.outdir, f"{sample}.cnr")
    cns  = os.path.join(args.outdir, f"{sample}.cns")
    call_cns = os.path.join(args.outdir, f"{sample}.call.cns")
    seg     = os.path.join(args.outdir, f"{sample}.seg")
    cnv_vcf = os.path.join(args.outdir, f"{sample}.cnv.vcf")
    genemetrics_raw       = os.path.join(args.outdir, f"{sample}.genemetrics.raw.tsv")
    genemetrics_tsv       = os.path.join(args.outdir, f"{sample}.genemetrics.tsv")
    genemetrics_annotated = os.path.join(args.outdir, f"{sample}.genemetrics.annotated.tsv")
    scatter_png = os.path.join(args.outdir, f"{sample}.scatter.png")

    # --- Step 1: CNVKit batch (one pass; PoN already sex-matched) ---
    rc, _, _ = run(
        cnvkit_batch_cmd(args.bam, args.pon, args.outdir,
                         male_reference=male_reference),
        desc="Step 1: cnvkit.py batch (segmentation vs %s PoN%s)" % (
            args.sex, ", -y" if male_reference else ""),
    )
    if rc != 0:
        log.error("cnvkit.py batch failed"); sys.exit(1)

    for f, label in [(batch_cnr, "CNR"), (batch_cns, "CNS")]:
        if not os.path.isfile(f):
            log.error("Expected %s not found: %s", label, f); sys.exit(1)

    if bam_stem != sample:
        for src, dst in [(batch_cnr, cnr), (batch_cns, cns)]:
            os.rename(src, dst)
            log.info("  Renamed %s -> %s",
                     os.path.basename(src), os.path.basename(dst))
    else:
        cnr, cns = batch_cnr, batch_cns

    # --- Step 2: CNVKit call (integer CN with AML thresholds) ---
    call_cmd = ["cnvkit.py", "call", cns,
                f"-t={CALL_THRESHOLDS}",
                "-o", call_cns]
    if male_reference:
        call_cmd.append("-y")
    rc, _, _ = run(
        call_cmd,
        desc="Step 2: cnvkit.py call (integer CN%s)" % (
            ", -y" if male_reference else ""),
    )
    if rc != 0:
        log.error("cnvkit.py call failed"); sys.exit(1)

    # --- Step 3: Export SEG (IGV) ---
    rc, _, _ = run(["cnvkit.py", "export", "seg", cns, "-o", seg],
                   desc="Step 3: cnvkit.py export seg (IGV)")
    if rc != 0:
        log.warning("cnvkit.py export seg failed -- continuing")

    # --- Step 4: Export VCF (annotation) ---
    rc, _, _ = run(["cnvkit.py", "export", "vcf", call_cns, "-o", cnv_vcf],
                   desc="Step 4: cnvkit.py export vcf")
    if rc != 0:
        log.warning("cnvkit.py export vcf failed -- continuing")

    # --- Step 5: Gene metrics ---
    rc, _, _ = run(
        ["cnvkit.py", "genemetrics", cnr,
         "-s", cns,
         "--threshold", "0",
         "-o", genemetrics_raw],
        desc="Step 5: cnvkit.py genemetrics (all genes, threshold=0)",
    )
    if rc != 0:
        log.warning("cnvkit.py genemetrics failed -- continuing")
    else:
        aggregate_genemetrics(genemetrics_raw, genemetrics_tsv)
        with open(genemetrics_raw) as f:
            n_probes = sum(1 for _ in f) - 1
        log.info("  Aggregated: %d probes -> %s", n_probes, genemetrics_tsv)

    # --- Step 6: Genome-wide scatter ---
    rc, _, _ = run(["cnvkit.py", "scatter", cnr, "-s", cns, "-o", scatter_png],
                   desc="Step 6: cnvkit.py scatter (genome-wide)")
    if rc != 0:
        log.warning("cnvkit.py scatter failed -- continuing")

    # --- Step 7: Per-chromosome scatter for panel genes ---
    log.info("Step 7: Per-chromosome scatter plots for panel genes")
    for chrom, genes in PANEL_GENE_CHROMS.items():
        gene_label = "_".join(genes)
        chrom_png = os.path.join(
            args.outdir, f"{sample}.scatter.{chrom}_{gene_label}.png")
        rc, _, _ = run(
            ["cnvkit.py", "scatter", cnr, "-s", cns, "-c", chrom, "-o", chrom_png],
            desc="  Scatter: %s (%s)" % (chrom, ", ".join(genes)),
        )
        if rc != 0:
            log.warning("  Scatter for %s failed -- continuing", chrom)

    # --- Step 8: Blacklist annotation ---
    log.info("Step 8: Blacklist annotation (LOO QC)")
    blacklist_bins = load_blacklist(args.blacklist)
    loo_fp_map     = load_loo_fp(args.loo_summary)
    annotate_genemetrics(genemetrics_tsv, blacklist_bins, loo_fp_map,
                         genemetrics_annotated)

    elapsed = time.time() - t0
    log.info("")
    log.info("=== CNVKit Complete ===")
    log.info("Outputs:")
    for f, label in [(cnr, "Bin-level ratios (CNR)"),
                      (cns, "Segments (CNS)"),
                      (call_cns, "Called segments"),
                      (seg, "SEG (IGV)"),
                      (cnv_vcf, "VCF (annotation)"),
                      (genemetrics_tsv, "Gene metrics"),
                      (genemetrics_annotated, "Gene metrics (annotated)"),
                      (scatter_png, "Genome scatter")]:
        status = "OK" if os.path.isfile(f) else "MISSING"
        log.info("  [%s] %s: %s", status, label, f)
    log.info("Total time: %.0fs", elapsed)


if __name__ == "__main__":
    main()
