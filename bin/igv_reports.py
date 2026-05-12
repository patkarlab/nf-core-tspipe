#!/usr/bin/env python3
"""
16_igv_reports.py - Generate self-contained IGV HTML reports for clinical variants.

Reads the clinical TSV, converts variants to a VCF, and generates an interactive
HTML report with embedded IGV views of each variant.

Usage:
    python scripts/16_igv_reports.py --sample 26CGH40
"""

import argparse
import gzip
import logging
import os
import subprocess
import sys
import tempfile

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

PIPELINE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate IGV HTML reports for clinical variants"
    )
    parser.add_argument("-s", "--sample", required=True, help="Sample name")
    parser.add_argument("-i", "--input", default=None,
                        help="Input clinical TSV (default: results/{sample}/annotation/{sample}.somaticseq.clinical.tsv)")
    parser.add_argument("--bam", default=None,
                        help="BAM file (default: results/{sample}/abra2/{sample}.final.bam)")
    parser.add_argument("-o", "--output", default=None,
                        help="Output HTML (default: results/{sample}/annotation/{sample}_igv_report.html)")
    parser.add_argument("--flanking", type=int, default=500,
                        help="Flanking region in bp (default: 500)")
    return parser.parse_args()


def tsv_to_vcf(df, vcf_path):
    """Convert clinical TSV rows to a minimal VCF file (bgzipped + tabix indexed)."""
    # Sort by chromosome and position
    chrom_order = [f"chr{i}" for i in range(1, 23)] + ["chrX", "chrY", "chrM"]
    df = df.copy()
    df["_chrom_sort"] = df["Chr"].apply(lambda x: chrom_order.index(x) if x in chrom_order else 99)
    df["_pos_sort"] = df["Start"].astype(int)
    df = df.sort_values(["_chrom_sort", "_pos_sort"]).drop(columns=["_chrom_sort", "_pos_sort"])

    vcf_lines = []
    vcf_lines.append("##fileformat=VCFv4.2")
    vcf_lines.append('##INFO=<ID=Gene,Number=1,Type=String,Description="Gene symbol">')
    vcf_lines.append('##INFO=<ID=Consequence,Number=1,Type=String,Description="Variant consequence">')
    vcf_lines.append('##INFO=<ID=HGVSp,Number=1,Type=String,Description="Protein HGVS">')
    vcf_lines.append('##INFO=<ID=VAF_pct,Number=1,Type=Float,Description="Variant allele frequency (%)">')
    vcf_lines.append('##INFO=<ID=Callers,Number=1,Type=String,Description="Variant callers">')
    vcf_lines.append("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO")

    for _, row in df.iterrows():
        chrom = str(row["Chr"])
        pos = str(int(row["Start"]))
        ref = str(row["Ref"])
        alt = str(row["Alt"])
        rsid = str(row.get("rsID", "."))
        if rsid in ("-1", "", "nan"):
            rsid = "."
        filt = str(row.get("Filter", "PASS"))
        if filt in ("-1", "", "nan"):
            filt = "PASS"

        # Build INFO field
        info_parts = []
        gene = str(row.get("Gene", ".")).replace(";", ",")
        consequence = str(row.get("Consequence", ".")).replace(";", ",")
        hgvsp = str(row.get("HGVSp", ".")).replace(";", ",")
        vaf = str(row.get("VAF_pct", "."))
        callers = str(row.get("Callers", ".")).replace(";", ",")

        for key, val in [("Gene", gene), ("Consequence", consequence),
                         ("HGVSp", hgvsp), ("VAF_pct", vaf), ("Callers", callers)]:
            if val not in ("-1", "", "nan", "."):
                info_parts.append(f"{key}={val}")

        info = ";".join(info_parts) if info_parts else "."

        vcf_lines.append(f"{chrom}\t{pos}\t{rsid}\t{ref}\t{alt}\t.\t{filt}\t{info}")

    # Write, bgzip, and tabix
    raw_vcf = vcf_path.replace(".gz", "")
    with open(raw_vcf, "w") as f:
        f.write("\n".join(vcf_lines) + "\n")

    subprocess.run(["bgzip", "-f", raw_vcf], check=True)
    subprocess.run(["tabix", "-p", "vcf", "-f", vcf_path], check=True)
    log.info(f"Created VCF: {vcf_path}")


def main():
    args = parse_args()
    sample = args.sample

    # Input paths — derive defaults from -o so batch runner's outdir is respected
    default_annot_dir = os.path.join(PIPELINE_DIR, "results", sample, "annotation")
    default_base_dir = os.path.join(PIPELINE_DIR, "results", sample)

    if args.output:
        output_html = args.output
        # Infer annotation dir from output path for input defaults
        annot_dir = os.path.dirname(output_html)
        base_dir = os.path.dirname(annot_dir)
    else:
        annot_dir = default_annot_dir
        base_dir = default_base_dir
        output_html = os.path.join(annot_dir, f"{sample}_igv_report.html")

    if args.input:
        input_tsv = args.input
    else:
        input_tsv = os.path.join(annot_dir, f"{sample}.somaticseq.clinical.final.tsv")

    if args.bam:
        bam_path = args.bam
    else:
        bam_path = os.path.join(base_dir, "abra2", f"{sample}.final.bam")

    # Validate inputs
    if not os.path.isfile(input_tsv):
        log.error(f"Input file not found: {input_tsv}")
        sys.exit(1)
    if not os.path.isfile(bam_path):
        log.error(f"BAM file not found: {bam_path}")
        sys.exit(1)

    # Read clinical TSV
    df = pd.read_csv(input_tsv, sep="\t", dtype=str)
    log.info(f"Read {len(df)} clinical variants from {input_tsv}")

    if len(df) == 0:
        log.warning("No variants found — skipping report generation")
        sys.exit(0)

    # Create VCF in the output directory
    outdir = os.path.dirname(output_html)
    os.makedirs(outdir, exist_ok=True)
    vcf_path = os.path.join(outdir, f"{sample}.clinical.vcf.gz")
    tsv_to_vcf(df, vcf_path)

    # Generate IGV report
    cmd = [
        "create_report",
        vcf_path,
        "--genome", "hg38",
        "--tracks", vcf_path, bam_path,
        "--info-columns", "Gene", "Consequence", "HGVSp", "VAF_pct", "Callers",
        "--flanking", str(args.flanking),
        "--title", f"{sample} Clinical Variant Review",
        "--output", output_html,
    ]

    log.info(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        log.error(f"create_report failed:\n{result.stderr}")
        sys.exit(1)

    if result.stdout.strip():
        log.info(result.stdout.strip())

    file_size = os.path.getsize(output_html) / (1024 * 1024)
    log.info(f"IGV report generated: {output_html} ({file_size:.1f} MB)")
    log.info(f"Open in browser to review {len(df)} clinical variants")


if __name__ == "__main__":
    main()
