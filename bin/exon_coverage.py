#!/usr/bin/env python3
"""
10b_exon_coverage.py - Per-exon coverage analysis for targeted sequencing QC.

Computes per-exon coverage metrics from the ABRA2-realigned BAM using mosdepth
(preferred) or samtools depth (fallback).

Input:  results/{sample}/abra2/{sample}.final.bam
        Panel BED file (4-column: chr, start, end, gene_exon)
Output: results/{sample}/{sample}_analysis/{sample}_exon_coverage.tsv

Dependencies: mosdepth (preferred) or samtools + bedtools
"""

import argparse
import csv
import logging
import os
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Coverage thresholds for clinical reporting
COVERAGE_THRESHOLDS = [100, 250, 500]
LOW_COVERAGE_THRESHOLD = 100  # Mean coverage below this triggers LOW_COVERAGE flag

import re

def parse_gene_exon(label):
    """Extract gene and exon from BED name field.

    Handles formats:
      - Target=1;ProbeIdx=12;GNB1_Ex_11  (panel standard)
      - GENE_Ex_N, GENE_EX_N, GENE_ExN  (variants)
      - GENE_exonN                        (simple)
      - plain GENE                        (no exon info)
    """
    # Strip quotes
    label = label.strip('"').strip("'")

    # If semicolon-delimited (panel BED), take the last field
    if ";" in label:
        label = label.rsplit(";", 1)[-1]

    # Match GENE_Ex_N or GENE_EX_N or GENE_ExN patterns
    m = re.match(r'^(.+?)_[Ee][Xx]_?(\d+)$', label)
    if m:
        return m.group(1), f"Ex_{m.group(2)}"

    # Match GENE_exonN
    if "_exon" in label.lower():
        parts = re.split(r'_exon', label, flags=re.IGNORECASE)
        return parts[0], f"Ex_{parts[1]}"

    return label, "-"


def check_tool(name):
    """Check if a command-line tool is available."""
    try:
        subprocess.run(
            [name, "--version"],
            capture_output=True,
            check=False,
        )
        return True
    except FileNotFoundError:
        return False


def run_mosdepth(bam_path, bed_path, output_prefix, threads=4):
    """
    Run mosdepth for per-base coverage within BED regions.

    mosdepth is significantly faster than samtools depth for targeted panels
    and produces per-region summary statistics directly.
    """
    logger.info("Running mosdepth for per-region coverage...")

    cmd = [
        "mosdepth",
        "--by", str(bed_path),
        "--threads", str(threads),
        "--no-per-base",          # We only need region summaries
        "--thresholds", ",".join(str(t) for t in COVERAGE_THRESHOLDS),
        str(output_prefix),
        str(bam_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("mosdepth failed: %s", result.stderr)
        raise RuntimeError(f"mosdepth failed with return code {result.returncode}")

    logger.info("mosdepth completed successfully.")
    return output_prefix


def parse_mosdepth_output(output_prefix, bed_path):
    """
    Parse mosdepth region and threshold outputs into per-exon coverage records.

    Files used:
      - {prefix}.regions.bed.gz: per-region mean coverage
      - {prefix}.thresholds.bed.gz: per-region fraction of bases above each threshold
    """
    import gzip

    regions_file = f"{output_prefix}.regions.bed.gz"
    thresholds_file = f"{output_prefix}.thresholds.bed.gz"

    # Parse the original BED to get gene/exon names (mosdepth uses col4 if present)
    bed_labels = {}
    with open(bed_path) as fh:
        for line in fh:
            if line.startswith("#") or line.strip() == "":
                continue
            fields = line.strip().split("\t")
            chrom, start, end = fields[0], fields[1], fields[2]
            label = fields[3] if len(fields) > 3 else f"{chrom}:{start}-{end}"
            key = (chrom, start, end)
            bed_labels[key] = label

    # Parse mean coverage per region
    region_coverage = {}
    with gzip.open(regions_file, "rt") as fh:
        for line in fh:
            fields = line.strip().split("\t")
            chrom, start, end = fields[0], fields[1], fields[2]
            mean_cov = float(fields[4]) if len(fields) > 4 else float(fields[3])
            key = (chrom, start, end)
            region_coverage[key] = mean_cov

    # Parse threshold base counts
    # Format: chr start end region_name count_100x count_250x count_500x
    threshold_data = {}
    with gzip.open(thresholds_file, "rt") as fh:
        header = fh.readline()  # #chrom start end region ...threshold columns
        for line in fh:
            fields = line.strip().split("\t")
            chrom, start, end = fields[0], fields[1], fields[2]
            key = (chrom, start, end)
            region_len = int(end) - int(start)
            # Col 3 is the region name; threshold counts start at col 4
            counts = [float(x) for x in fields[4:]]
            # Convert base counts to fractions
            fractions = [c / region_len if region_len > 0 else 0.0 for c in counts]
            threshold_data[key] = fractions

    # Merge into records
    records = []
    for key in region_coverage:
        chrom, start, end = key
        label = bed_labels.get(key, f"{chrom}:{start}-{end}")

        gene, exon = parse_gene_exon(label)

        mean_cov = region_coverage[key]
        fracs = threshold_data.get(key, [0.0] * len(COVERAGE_THRESHOLDS))

        region_len = int(end) - int(start)
        flag = "LOW_COVERAGE" if mean_cov < LOW_COVERAGE_THRESHOLD else ""

        record = {
            "Gene": gene,
            "Exon": exon,
            "Chr": chrom,
            "Start": start,
            "End": end,
            "Length_bp": region_len,
            "Mean_Coverage": f"{mean_cov:.1f}",
        }
        for i, thresh in enumerate(COVERAGE_THRESHOLDS):
            pct = fracs[i] * 100 if i < len(fracs) else 0.0
            record[f"Pct_{thresh}x"] = f"{pct:.1f}"

        record["Flag"] = flag
        records.append(record)

    return records


def run_samtools_depth(bam_path, bed_path, threads=4):
    """
    Fallback: Use samtools depth + manual aggregation for per-exon coverage.

    Slower than mosdepth but universally available.
    """
    logger.info("Running samtools depth (fallback mode)...")

    cmd = [
        "samtools", "depth",
        "-a",                     # Output all positions (including zero-coverage)
        "-b", str(bed_path),      # Restrict to BED regions
        "-@", str(threads),
        str(bam_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("samtools depth failed: %s", result.stderr)
        raise RuntimeError(f"samtools depth failed with return code {result.returncode}")

    # Parse BED regions
    regions = []
    with open(bed_path) as fh:
        for line in fh:
            if line.startswith("#") or line.strip() == "":
                continue
            fields = line.strip().split("\t")
            chrom, start, end = fields[0], int(fields[1]), int(fields[2])
            label = fields[3] if len(fields) > 3 else f"{chrom}:{start}-{end}"
            regions.append((chrom, start, end, label))

    # Accumulate per-position depth into region buckets
    # Build a lookup: (chrom, pos) -> depth
    logger.info("Parsing samtools depth output (%d regions)...", len(regions))
    pos_depth = defaultdict(lambda: defaultdict(int))
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        fields = line.split("\t")
        chrom, pos, depth = fields[0], int(fields[1]), int(fields[2])
        pos_depth[chrom][pos] = depth

    # Compute per-region metrics
    records = []
    for chrom, start, end, label in regions:
        depths = []
        for pos in range(start + 1, end + 1):  # samtools depth is 1-based
            depths.append(pos_depth[chrom].get(pos, 0))

        if not depths:
            continue

        region_len = end - start
        mean_cov = sum(depths) / len(depths)
        min_cov = min(depths)

        gene, exon = parse_gene_exon(label)

        flag = "LOW_COVERAGE" if mean_cov < LOW_COVERAGE_THRESHOLD else ""

        record = {
            "Gene": gene,
            "Exon": exon,
            "Chr": chrom,
            "Start": str(start),
            "End": str(end),
            "Length_bp": region_len,
            "Mean_Coverage": f"{mean_cov:.1f}",
        }
        for thresh in COVERAGE_THRESHOLDS:
            above = sum(1 for d in depths if d >= thresh)
            pct = (above / len(depths)) * 100
            record[f"Pct_{thresh}x"] = f"{pct:.1f}"

        record["Flag"] = flag
        records.append(record)

    return records


def write_coverage_report(records, output_path, sample_name):
    """Write per-exon coverage TSV with summary statistics at the end."""
    fieldnames = [
        "Gene", "Exon", "Chr", "Start", "End", "Length_bp", "Mean_Coverage",
    ]
    for thresh in COVERAGE_THRESHOLDS:
        fieldnames.append(f"Pct_{thresh}x")
    fieldnames.append("Flag")

    with open(output_path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for record in records:
            writer.writerow(record)

    # Compute and log summary
    total_regions = len(records)
    low_cov = sum(1 for r in records if r["Flag"] == "LOW_COVERAGE")
    mean_covs = [float(r["Mean_Coverage"]) for r in records]
    overall_mean = sum(mean_covs) / len(mean_covs) if mean_covs else 0

    logger.info("Coverage report written: %s", output_path)
    logger.info("  Total exon regions: %d", total_regions)
    logger.info("  Overall mean coverage: %.1fx", overall_mean)
    logger.info("  Low coverage regions (<%dx): %d", LOW_COVERAGE_THRESHOLD, low_cov)

    if low_cov > 0:
        logger.warning("Low coverage exons:")
        for r in records:
            if r["Flag"] == "LOW_COVERAGE":
                logger.warning(
                    "  %s %s (%s:%s-%s) = %sx",
                    r["Gene"], r["Exon"], r["Chr"], r["Start"], r["End"],
                    r["Mean_Coverage"],
                )

    return total_regions, low_cov, overall_mean


def main():
    parser = argparse.ArgumentParser(
        description="Per-exon coverage analysis for targeted sequencing QC"
    )
    parser.add_argument("--sample", required=True, help="Sample name")
    parser.add_argument("--bam", required=True, help="Path to ABRA2 BAM file")
    parser.add_argument("--bed", required=True, help="Path to panel BED file (4-column)")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument("--threads", type=int, default=4, help="Number of threads")

    args = parser.parse_args()

    bam_path = Path(args.bam)
    bed_path = Path(args.bed)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"{args.sample}_exon_coverage.tsv"

    if not bam_path.exists():
        logger.error("BAM file not found: %s", bam_path)
        sys.exit(1)
    if not bed_path.exists():
        logger.error("BED file not found: %s", bed_path)
        sys.exit(1)

    # Try mosdepth first, fall back to samtools
    if check_tool("mosdepth"):
        logger.info("Using mosdepth for coverage analysis")
        with tempfile.TemporaryDirectory() as tmpdir:
            prefix = os.path.join(tmpdir, args.sample)
            run_mosdepth(bam_path, bed_path, prefix, args.threads)
            records = parse_mosdepth_output(prefix, bed_path)
    elif check_tool("samtools"):
        logger.info("mosdepth not found, falling back to samtools depth")
        records = run_samtools_depth(bam_path, bed_path, args.threads)
    else:
        logger.error("Neither mosdepth nor samtools found. Install one.")
        sys.exit(1)

    # Sort by chromosome, then start position
    chrom_order = {f"chr{i}": i for i in range(1, 23)}
    chrom_order["chrX"] = 23
    chrom_order["chrY"] = 24

    records.sort(key=lambda r: (chrom_order.get(r["Chr"], 99), int(r["Start"])))

    write_coverage_report(records, output_file, args.sample)


if __name__ == "__main__":
    main()
