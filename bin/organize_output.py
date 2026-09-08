#!/usr/bin/env python3
"""
organize_output.py - Build the clinical/ deliverable tree via hardlinks.

Option 2 (slim) variant: clinical/ contains only the
pathologist-facing artifacts plus CNVkit subdirectory plots. The full
per-tool FLT3-ITD audit trail (FLT3_ITD_EXT VCF + summary, filt3r
VCF + JSON, getitd tree) is intentionally NOT published here -- it
remains accessible in Nextflow's work/ directory if a REVIEW_REQUIRED
case ever needs deep inspection. The headline FLT3 result
(flt3_consensus.tsv) is kept at top level.

Optional inputs use a sentinel filename prefix 'NO_FILE_'. When the
upstream channel emitted nothing, Nextflow stages a placeholder with
that prefix; this script skips it.

Python 3.6 compatible (GATK 4.5 container constraint). Stdlib only.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

SENTINEL_PREFIX = "NO_FILE_"
MIN_U2AF1_RESCUE_SIZE = 100  # bytes; production 20_organize_output.py convention


def is_sentinel(path):
    if path is None:
        return True
    return Path(path).name.startswith(SENTINEL_PREFIX)


def hardlink(src, dst, description=""):
    """
    Hardlink src -> dst. Idempotent (overwrites existing dst), verified
    via inode equality, fails loud on cross-device.
    """
    if is_sentinel(src):
        logger.info("  skip:    %s (no file emitted upstream)", description or dst)
        return False
    src_p = Path(src)
    dst_p = Path(dst)
    if not src_p.exists():
        logger.warning("  MISSING: %s -- %s", src_p, description)
        return False
    dst_p.parent.mkdir(parents=True, exist_ok=True)
    if dst_p.exists() or dst_p.is_symlink():
        dst_p.unlink()
    try:
        os.link(str(src_p), str(dst_p))
    except OSError as e:
        logger.error("  HARDLINK FAILED: %s -> %s: %s", src_p, dst_p, e)
        raise
    if src_p.stat().st_ino != dst_p.stat().st_ino:
        logger.error("  INODE MISMATCH after link: %s vs %s", src_p, dst_p)
        raise RuntimeError("hardlink verification failed: " + str(dst_p))
    size_mb = src_p.stat().st_size / (1024 * 1024)
    logger.info("  link:    %s (%.1f MB) -- %s", dst_p.name, size_mb, description)
    return True


def hardlink_dir(src_dir, dst_dir, description="", exclude_substrings=None):
    """Recreate src_dir under dst_dir with hardlinked leaves. Excludes by substring."""
    if is_sentinel(src_dir):
        logger.info("  skip:    %s (no directory emitted upstream)", description or dst_dir)
        return 0
    src_p = Path(src_dir)
    dst_p = Path(dst_dir)
    if not src_p.exists():
        logger.warning("  MISSING DIR: %s -- %s", src_p, description)
        return 0
    exclude_substrings = exclude_substrings or []
    dst_p.mkdir(parents=True, exist_ok=True)
    count = 0
    for item in sorted(src_p.iterdir()):
        if any(s in item.name for s in exclude_substrings):
            logger.info("  exclude: %s/%s", src_p.name, item.name)
            continue
        if item.is_file():
            if hardlink(item, dst_p / item.name, description):
                count += 1
        elif item.is_dir():
            count += hardlink_dir(item, dst_p / item.name, description, exclude_substrings)
    return count


def disk_usage_dedup(root):
    seen_inodes = set()
    total = 0
    for path in Path(root).rglob("*"):
        if not path.is_file():
            continue
        st = path.stat()
        if st.st_ino in seen_inodes:
            continue
        seen_inodes.add(st.st_ino)
        total += st.st_size
    return total, len(seen_inodes)


def main():
    parser = argparse.ArgumentParser(
        description="Build clinical/ deliverable tree via hardlinks (Option 2)"
    )
    parser.add_argument("--sample", required=True)
    parser.add_argument("--outdir", required=True,
                        help="clinical/ subdirectory will be created under this")
    # Always-present inputs
    parser.add_argument("--bam", required=True)
    parser.add_argument("--bai", required=True)
    parser.add_argument("--clinical-tsv", required=True)
    parser.add_argument("--filtered-tsv", required=True)
    parser.add_argument("--flt3-consensus", required=True)
    parser.add_argument("--exon-coverage", required=True)
    parser.add_argument("--hsmetrics", required=True)
    parser.add_argument("--dashboard", required=True)
    parser.add_argument("--fastp-html", required=True)
    parser.add_argument("--fastp-json", default=None, help="fastp JSON metrics (optional; DASH_QC_V2)")
    parser.add_argument("--igv-report", required=True,
                        help="IGV HTML report from create_report")
    # MARKER CNV_RETIRE_7B: legacy CNV arguments (clinical/annotated tables, CNVkit plots) removed
    parser.add_argument("--cnv-consensus-genes", default=None, help="CMX consensus per-gene table (optional; ORG_CNV_V1)")
    parser.add_argument("--cnv-consensus-segments", default=None, help="CMX consensus segment intersection (optional; ORG_CNV_V1)")
    parser.add_argument("--cnv-consensus-json", default=None, help="CMX consensus JSON (tracks for figures) (optional; ORG_CNV_V1)")
    parser.add_argument("--exon-plots-dir", default=None, help="EXON_PLOTS directory (per-chromosome exon figures + index) (optional; ORG_CNV_V1)")
    parser.add_argument("--chrom-pages-dir", default=None, help="CHROM_PAGES directory (per-chromosome pages + index) (optional; ORG_CNV_V1)")
    parser.add_argument("--decon-filtered", default=None, help="DECoN filtered calls (optional; ORG_CNV_V1)")
    parser.add_argument("--decon-genes", default=None, help="DECoN per-gene table (arm E contract) (optional; ORG_CNV_V1)")
    parser.add_argument("--purple-summary", default=None, help="PURPLE arm H summary (optional; ORG_CNV_V1)")
    parser.add_argument("--purple-genes", default=None, help="PURPLE arm H gene table (optional; ORG_CNV_V1)")
    parser.add_argument("--purple-dir", default=None, help="PURPLE output directory (optional; ORG_CNV_V1)")
    parser.add_argument("--sex-check", default=None, help="SEX_CHECK table (optional; ORG_CNV_V1)")
    parser.add_argument("--styled-scatter-dir", default=None, help="unused since MARKER VIZ_V1b; accepted for compatibility")
    parser.add_argument("--reconcnv-dir", default=None, help="RECONCNV directory (optional; VIZ_V1)")
    parser.add_argument("--spikein-snps", default=None, help="SPIKEIN_SITES genotype table (optional; SPIKEIN_V1)")
    # Optional inputs (may be sentinels)
    parser.add_argument("--u2af1-report", required=True,
                        help="Optional; sentinel allowed")
    parser.add_argument("--u2af1-rescue", required=True,
                        help="Optional; also gated on >100 bytes")
    args = parser.parse_args()

    s = args.sample
    out = Path(args.outdir) / "clinical"
    out.mkdir(parents=True, exist_ok=True)
    logger.info("Building clinical deliverable tree (Option 2 slim): %s", out)

    # --- Alignment ---
    logger.info("--- Alignment ---")
    hardlink(args.bam, out / (s + ".final.bam"), "ABRA2 realigned BAM")
    hardlink(args.bai, out / (s + ".final.bam.bai"), "BAM index")

    # --- Variant calls ---
    logger.info("--- Variant calls (annotated) ---")
    hardlink(args.clinical_tsv,
             out / (s + ".somaticseq.clinical.final.tsv"),
             "Final clinical variants (VEP + VV + OncoVI + FLT3 ensemble)")
    hardlink(args.filtered_tsv,
             out / (s + ".somaticseq.filtered.tsv"),
             "SomaticSeq pre-filter variants (all)")

    # U2AF1 rescue: report unconditional; rescue TSV gated on >100 bytes.
    hardlink(args.u2af1_report,
             out / (s + "_u2af1_pileup_report.txt"),
             "U2AF1 pileup rescue report")
    if not is_sentinel(args.u2af1_rescue):
        rescue = Path(args.u2af1_rescue)
        if rescue.exists() and rescue.stat().st_size > MIN_U2AF1_RESCUE_SIZE:
            hardlink(rescue, out / (s + "_u2af1_rescue.tsv"),
                     "U2AF1 rescued variants")
        else:
            logger.info("  skip:    u2af1_rescue.tsv "
                        "(<=%d bytes; no real rescues)",
                        MIN_U2AF1_RESCUE_SIZE)

    # --- FLT3-ITD: headline only ---
    # Per-tool VCFs/JSON/getitd are NOT published here. Audit trail lives in work/.
    logger.info("--- FLT3-ITD (headline only) ---")
    hardlink(args.flt3_consensus, out / (s + "_flt3_consensus.tsv"),
             "FLT3-ITD multi-caller consensus")

    # --- Coverage & QC ---
    logger.info("--- Coverage & QC ---")
    hardlink(args.hsmetrics,     out / (s + "_hsmetrics.txt"),
             "Picard HsMetrics")
    hardlink(args.exon_coverage, out / (s + "_exon_coverage.tsv"),
             "Per-exon coverage analysis")
    hardlink(args.fastp_html,    out / (s + "_fastp.html"),
             "Fastp trimming QC report")
    if args.fastp_json:   # DASH_QC_V2
        hardlink(args.fastp_json, out / (s + "_fastp.json"),
                 "Fastp trimming QC metrics (JSON)")
    hardlink(args.igv_report,    out / (s + "_igv_report.html"),
             "IGV review report")
    hardlink(args.dashboard,     out / (s + "_dashboard.html"),
             "Per-sample QC dashboard")

    # --- CNV legacy deliverables (cnv_consensus/, cnvkit_plots/) retired: CNV_RETIRE_7B ---

    # --- CNV v2 (MARKER ORG_CNV_V1): consensus, exon plots, chromosome pages, DECoN, PURPLE, sex check ---
    logger.info("--- CNV v2 ---")
    cnv2 = out / "cnv"

    def present(p):
        return bool(p) and Path(p).exists() and not is_sentinel(Path(p))

    for src, sub, desc in (
            (args.cnv_consensus_genes,    "consensus", "CMX consensus per-gene table"),
            (args.cnv_consensus_segments, "consensus", "CMX consensus segments"),
            (args.cnv_consensus_json,     "consensus", "CMX consensus JSON"),
            (args.decon_filtered,         "decon",     "DECoN filtered calls"),
            (args.decon_genes,            "decon",     "DECoN per-gene table"),
            (args.purple_summary,         "purple",    "PURPLE arm H summary"),
            (args.purple_genes,           "purple",    "PURPLE arm H gene table"),
            (args.sex_check,              "sex_check", "SEX_CHECK table")):
        if present(src):
            hardlink(src, cnv2 / sub / Path(src).name, desc)
        else:
            logger.info("skip (absent): %s", desc)
    for src, sub, desc in (
            (args.exon_plots_dir,  "exon_plots",  "exon figures"),
            (args.chrom_pages_dir, "chrom_pages", "chromosome pages"),
            (args.purple_dir,      "purple",      "PURPLE outputs"),
            (args.reconcnv_dir,    "reconcnv",    "reconCNV")):   # MARKER VIZ_V1
        if src and Path(src).is_dir():
            hardlink_dir(Path(src), cnv2 / sub, "CNV v2 " + desc)
        else:
            logger.info("skip (absent): %s", desc)

    # --- Spike-in SNP genotypes (MARKER SPIKEIN_V1): top-level clinical/<sample>.spikein_snps.tsv ---
    if present(args.spikein_snps):
        hardlink(args.spikein_snps, out / Path(args.spikein_snps).name, "spike-in SNP genotypes")
    else:
        logger.info("skip (absent): spike-in SNP genotypes")

    # --- Summary ---
    total_bytes, unique_files = disk_usage_dedup(out)
    logger.info("=" * 60)
    logger.info("clinical/ tree at: %s", out)
    logger.info("Unique inodes (physical files): %d", unique_files)
    logger.info("Physical disk (inode-deduplicated): %.1f MB",
                total_bytes / (1024 * 1024))
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
