#!/usr/bin/env python3
"""
igv_reports.py - Generate self-contained IGV HTML reports for clinical variants.

Reads the clinical TSV, converts variants to a VCF, and generates an interactive
HTML report with embedded IGV views of each variant.

Ported from production scripts/16_igv_reports.py (2026-05-12) with two
behavior-preserving changes for the nf-core container environment:

  1. pandas.read_csv -> csv.DictReader  (pandas is not in the igv-reports
     biocontainer; csv is stdlib).
  2. subprocess bgzip/tabix -> pysam.tabix_compress/tabix_index  (bgzip and
     tabix binaries are not in the igv-reports biocontainer; pysam is, and
     its APIs produce byte-equivalent output).

Other than dependency surface, the VCF generated and the create_report
invocation are identical to production. Output HTML is byte-equivalent
modulo timestamps embedded by create_report.

Usage:
    python igv_reports.py \\
        --sample 25NGS1307 \\
        --input 25NGS1307.somaticseq.clinical.final.tsv \\
        --bam 25NGS1307.final.bam \\
        --fasta hg38.fa \\
        --output 25NGS1307_igv_report.html
"""

import argparse
import csv
import logging
import os
import sys

import pysam

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate IGV HTML reports for clinical variants"
    )
    parser.add_argument("-s", "--sample", required=True, help="Sample name")
    parser.add_argument("-i", "--input", required=True,
                        help="Input clinical TSV")
    parser.add_argument("--bam", required=True, help="BAM file (post-ABRA2)")
    parser.add_argument("--fasta", required=True,
                        help="Reference FASTA (must be indexed; .fai sibling required)")
    parser.add_argument("-o", "--output", required=True,
                        help="Output HTML")
    parser.add_argument("--flanking", type=int, default=500,
                        help="Flanking region in bp (default: 500, matches production)")
    return parser.parse_args()


def read_clinical_tsv(path):
    """Read clinical TSV as a list of dicts with all values as strings.

    Equivalent to pandas.read_csv(path, sep='\\t', dtype=str) for our use case.
    """
    with open(path) as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        return list(reader)


# Chromosome sort order: chr1..22, chrX, chrY, chrM, everything else last.
CHROM_ORDER = {chrom: i for i, chrom in enumerate(
    [f"chr{i}" for i in range(1, 23)] + ["chrX", "chrY", "chrM"]
)}


def _chrom_sort_key(row):
    return (CHROM_ORDER.get(row["Chr"], 99), int(row["Start"]))


def _clean(value):
    """Production's missing-value sentinel handling: blanks, -1, nan, '.' all
    collapse to '.' for VCF info fields."""
    v = str(value) if value is not None else "."
    return "." if v in ("-1", "", "nan") else v


def tsv_to_vcf(rows, vcf_gz_path):
    """Write the clinical rows as a bgzipped + tabix-indexed VCF at vcf_gz_path.

    rows: list of dicts from read_clinical_tsv().
    vcf_gz_path: output path ending in .vcf.gz. The .tbi sibling will be
        created next to it.

    Behavior mirrors production scripts/16_igv_reports.py:tsv_to_vcf except
    that compression and indexing are done via pysam instead of shelling out
    to bgzip and tabix.
    """
    rows_sorted = sorted(rows, key=_chrom_sort_key)

    raw_vcf = vcf_gz_path[:-3] if vcf_gz_path.endswith(".gz") else vcf_gz_path + ".raw"

    header_lines = [
        "##fileformat=VCFv4.2",
        '##INFO=<ID=Gene,Number=1,Type=String,Description="Gene symbol">',
        '##INFO=<ID=Consequence,Number=1,Type=String,Description="Variant consequence">',
        '##INFO=<ID=HGVSp,Number=1,Type=String,Description="Protein HGVS">',
        '##INFO=<ID=VAF_pct,Number=1,Type=Float,Description="Variant allele frequency (%)">',
        '##INFO=<ID=Callers,Number=1,Type=String,Description="Variant callers">',
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO",
    ]

    with open(raw_vcf, "w") as fh:
        fh.write("\n".join(header_lines) + "\n")
        for row in rows_sorted:
            chrom = row["Chr"]
            pos = str(int(row["Start"]))
            ref = row["Ref"]
            alt = row["Alt"]
            rsid = _clean(row.get("rsID"))
            filt = _clean(row.get("Filter")) or "PASS"
            if filt == ".":
                filt = "PASS"

            info_parts = []
            for key, raw_val in [
                ("Gene", row.get("Gene")),
                ("Consequence", row.get("Consequence")),
                ("HGVSp", row.get("HGVSp")),
                ("VAF_pct", row.get("VAF_pct")),
                ("Callers", row.get("Callers")),
            ]:
                val = _clean(raw_val)
                if val != ".":
                    # Mirror production: replace ';' with ',' since ';' is the
                    # INFO field separator.
                    info_parts.append(f"{key}={val.replace(';', ',')}")
            info = ";".join(info_parts) if info_parts else "."

            fh.write(f"{chrom}\t{pos}\t{rsid}\t{ref}\t{alt}\t.\t{filt}\t{info}\n")

    # Compress with pysam (bgzip-compatible) and tabix-index.
    pysam.tabix_compress(raw_vcf, vcf_gz_path, force=True)
    os.remove(raw_vcf)
    pysam.tabix_index(vcf_gz_path, preset="vcf", force=True)
    log.info("Created VCF: %s (.tbi sibling indexed)", vcf_gz_path)


def main():
    args = parse_args()

    for path, label in [
        (args.input, "Clinical TSV"),
        (args.bam, "BAM"),
        (args.bam + ".bai", "BAM index"),
        (args.fasta, "Reference FASTA"),
        (args.fasta + ".fai", "Reference FASTA index"),
    ]:
        if not os.path.isfile(path):
            log.error("%s not found: %s", label, path)
            sys.exit(1)

    rows = read_clinical_tsv(args.input)
    log.info("Read %d clinical variants from %s", len(rows), args.input)

    if not rows:
        log.warning("No variants found -- skipping report generation")
        # Touch an empty output so downstream channels do not break.
        with open(args.output, "w") as fh:
            fh.write("<html><body><p>No clinical variants for this sample.</p></body></html>\n")
        sys.exit(0)

    outdir = os.path.dirname(os.path.abspath(args.output)) or "."
    os.makedirs(outdir, exist_ok=True)
    vcf_path = os.path.join(outdir, f"{args.sample}.clinical.vcf.gz")
    tsv_to_vcf(rows, vcf_path)

    # Build create_report invocation. Match production's args exactly,
    # except --genome (production cloud-fetched hg38; we provide a local FASTA).
    import subprocess
    cmd = [
        "create_report",
        vcf_path,
        "--fasta", args.fasta,
        "--tracks", vcf_path, args.bam,
        "--info-columns", "Gene", "Consequence", "HGVSp", "VAF_pct", "Callers",
        "--flanking", str(args.flanking),
        "--title", f"{args.sample} Clinical Variant Review",
        "--output", args.output,
    ]
    log.info("Running: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log.error("create_report failed:\n%s", result.stderr)
        sys.exit(1)
    if result.stdout.strip():
        log.info(result.stdout.strip())

    size_mb = os.path.getsize(args.output) / (1024 * 1024)
    log.info("IGV report generated: %s (%.1f MB, %d variants)",
             args.output, size_mb, len(rows))


if __name__ == "__main__":
    main()
