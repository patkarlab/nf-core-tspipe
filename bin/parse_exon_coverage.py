#!/usr/bin/env python3
"""
parse_exon_coverage.py - Parse mosdepth outputs into per-exon coverage TSV.

This is the post-mosdepth half of what was previously
bin/exon_coverage.py (which combined mosdepth invocation + parsing in
one script). The split lets each Nextflow process use a container
that has the tools it actually needs: MOSDEPTH uses the mosdepth
biocontainer; PARSE_EXON_COVERAGE uses a Python-capable container.

Input (all pre-computed by an upstream mosdepth process):
  --regions     {prefix}.regions.bed.gz    per-region mean coverage
  --thresholds  {prefix}.thresholds.bed.gz per-region bases >= threshold
  --bed         panel BED file (4-column: chr, start, end, gene_exon
                label). Used to recover the original col4 gene/exon
                labels which mosdepth's output preserves but loses if
                the BED used a different label scheme.
  --sample      sample name (used for the output filename)
  --output-dir  directory to write {sample}_exon_coverage.tsv into

Output: {output-dir}/{sample}_exon_coverage.tsv -- TSV with columns
  Gene, Exon, Chr, Start, End, Length_bp, Mean_Coverage,
  Pct_100x, Pct_250x, Pct_500x, Flag.

Notes:
  - LOW_COVERAGE flag is set on rows with Mean_Coverage < 100x.
  - parse_gene_exon handles the panel BED label format
    'Target=1;ProbeIdx=12;GNB1_Ex_11' -- splits on ';', takes last
    field, matches GENE_Ex_N pattern.
  - Multiple BED rows may share an exon label (tiled probes); we
    emit one record per BED row to preserve the production behavior.

This script was extracted from bin/exon_coverage.py (which is kept
in bin/ for redundancy and standalone use). The parsing logic
(parse_gene_exon, parse_mosdepth_output, write_coverage_report) is
unchanged from the source. Only the mosdepth-invocation path and
the samtools fallback were removed.
"""

import argparse
import csv
import gzip
import logging
import re
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

COVERAGE_THRESHOLDS = [100, 250, 500]
LOW_COVERAGE_THRESHOLD = 100


def parse_gene_exon(label):
    """Extract gene and exon from BED name field.

    Handles formats:
      - Target=1;ProbeIdx=12;GNB1_Ex_11  (panel standard)
      - GENE_Ex_N, GENE_EX_N, GENE_ExN  (variants)
      - GENE_exonN                       (simple)
      - plain GENE                       (no exon info)
    """
    label = label.strip('"').strip("'")

    # Panel BED uses semicolons; take the last field which carries
    # the gene_exon label
    if ";" in label:
        label = label.rsplit(";", 1)[-1]

    # GENE_Ex_N / GENE_EX_N / GENE_ExN patterns
    m = re.match(r'^(.+?)_[Ee][Xx]_?(\d+)$', label)
    if m:
        return m.group(1), f"Ex_{m.group(2)}"

    # GENE_exonN pattern
    if "_exon" in label.lower():
        parts = re.split(r'_exon', label, flags=re.IGNORECASE)
        return parts[0], f"Ex_{parts[1]}"

    # No exon info recognized; return label as gene name, '-' for exon
    return label, "-"


def parse_mosdepth_output(regions_file, thresholds_file, bed_path):
    """Join mosdepth's regions + thresholds outputs with BED labels.

    The panel BED's col4 carries the gene/exon label. mosdepth
    preserves it in its regions.bed.gz output (col4), but to be
    robust against label-format edge cases we cross-reference back
    to the original BED via (chrom, start, end) key.

    Returns a list of dict records, one per BED region.
    """
    # Index the panel BED by region for label lookup.
    bed_labels = {}
    with open(bed_path) as fh:
        for line in fh:
            if line.startswith("#") or line.strip() == "":
                continue
            fields = line.strip().split("\t")
            chrom, start, end = fields[0], fields[1], fields[2]
            label = fields[3] if len(fields) > 3 else f"{chrom}:{start}-{end}"
            bed_labels[(chrom, start, end)] = label

    # Per-region mean coverage from mosdepth's regions.bed.gz.
    # Layout when --by BED has a name column: chrom start end name mean.
    # If no name column, the BED would be 3-column and mean is at col 3.
    region_coverage = {}
    with gzip.open(regions_file, "rt") as fh:
        for line in fh:
            fields = line.strip().split("\t")
            chrom, start, end = fields[0], fields[1], fields[2]
            mean_cov = float(fields[4]) if len(fields) > 4 else float(fields[3])
            region_coverage[(chrom, start, end)] = mean_cov

    # Per-region threshold-base counts from mosdepth's thresholds.bed.gz.
    # Header line is consumed and discarded; remaining lines are:
    # chrom start end region_name count_100x count_250x count_500x.
    threshold_data = {}
    with gzip.open(thresholds_file, "rt") as fh:
        _header = fh.readline()
        for line in fh:
            fields = line.strip().split("\t")
            chrom, start, end = fields[0], fields[1], fields[2]
            region_len = int(end) - int(start)
            counts = [float(x) for x in fields[4:]]
            fractions = [c / region_len if region_len > 0 else 0.0
                         for c in counts]
            threshold_data[(chrom, start, end)] = fractions

    # Join everything per region.
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


def write_coverage_report(records, output_path):
    """Write per-exon coverage TSV; log summary statistics."""
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

    # Summary log lines (useful for run-time debugging).
    total_regions = len(records)
    low_cov = sum(1 for r in records if r["Flag"] == "LOW_COVERAGE")
    mean_covs = [float(r["Mean_Coverage"]) for r in records]
    overall_mean = sum(mean_covs) / len(mean_covs) if mean_covs else 0

    logger.info("Coverage report written: %s", output_path)
    logger.info("  Total exon regions: %d", total_regions)
    logger.info("  Overall mean coverage: %.1fx", overall_mean)
    logger.info("  Low coverage regions (<%dx): %d",
                LOW_COVERAGE_THRESHOLD, low_cov)
    if low_cov > 0:
        logger.warning("Low coverage exons:")
        for r in records:
            if r["Flag"] == "LOW_COVERAGE":
                logger.warning(
                    "  %s %s (%s:%s-%s) = %sx",
                    r["Gene"], r["Exon"], r["Chr"], r["Start"], r["End"],
                    r["Mean_Coverage"],
                )


def main():
    p = argparse.ArgumentParser(
        description="Parse mosdepth outputs into per-exon coverage TSV.",
    )
    p.add_argument("--sample", required=True, help="Sample name")
    p.add_argument("--bed",    required=True,
                   help="Panel BED file (4-column: chr, start, end, label)")
    p.add_argument("--regions", required=True,
                   help="mosdepth {prefix}.regions.bed.gz")
    p.add_argument("--thresholds", required=True,
                   help="mosdepth {prefix}.thresholds.bed.gz")
    p.add_argument("--output-dir", required=True, help="Output directory")
    args = p.parse_args()

    bed_path        = Path(args.bed)
    regions_path    = Path(args.regions)
    thresholds_path = Path(args.thresholds)
    output_dir      = Path(args.output_dir)

    for path, label in [(bed_path, "BED"),
                        (regions_path, "regions.bed.gz"),
                        (thresholds_path, "thresholds.bed.gz")]:
        if not path.is_file():
            logger.error("%s file not found: %s", label, path)
            sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{args.sample}_exon_coverage.tsv"

    records = parse_mosdepth_output(regions_path, thresholds_path, bed_path)

    # Sort by chromosome, then start position (standard genome order).
    chrom_order = {f"chr{i}": i for i in range(1, 23)}
    chrom_order["chrX"] = 23
    chrom_order["chrY"] = 24
    records.sort(key=lambda r: (chrom_order.get(r["Chr"], 99),
                                int(r["Start"])))

    write_coverage_report(records, output_file)


if __name__ == "__main__":
    main()
