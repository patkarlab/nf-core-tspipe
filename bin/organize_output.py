#!/usr/bin/env python3
"""
20_organize_output.py - Create clean analysis deliverable directory.

Copies only essential pipeline deliverables into a structured
{Sample}_analysis/ directory. This is the FINAL step after all
pipeline phases complete.

Input:  Full sample results directory (results/{sample}/)
Output: results/{sample}_analysis/ with curated deliverables only

Run AFTER: All pipeline phases (SNV, CNV, SV, FLT3-ITD) and cleanup.
"""

import argparse
import logging
import os
import shutil
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def safe_copy(src, dst, description=""):
    """Copy a file, creating parent directories as needed."""
    src = Path(src)
    dst = Path(dst)
    if not src.exists():
        logger.warning("  MISSING: %s (%s)", src.name, description)
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    size_mb = src.stat().st_size / (1024 * 1024)
    logger.info("  Copied: %s (%.1f MB) - %s", src.name, size_mb, description)
    return True


def safe_copy_dir(src_dir, dst_dir, description="", exclude_patterns=None):
    """Copy a directory, optionally excluding files matching patterns."""
    src_dir = Path(src_dir)
    dst_dir = Path(dst_dir)
    if not src_dir.exists():
        logger.warning("  MISSING DIR: %s (%s)", src_dir.name, description)
        return 0

    exclude_patterns = exclude_patterns or []
    count = 0
    for item in sorted(src_dir.iterdir()):
        if item.is_file():
            skip = False
            for pattern in exclude_patterns:
                if pattern in item.name:
                    skip = True
                    break
            if skip:
                logger.info("  Skipped: %s (excluded)", item.name)
                continue
            safe_copy(item, dst_dir / item.name, description)
            count += 1
        elif item.is_dir():
            # Recurse into subdirectories
            sub_count = safe_copy_dir(
                item, dst_dir / item.name, description, exclude_patterns
            )
            count += sub_count

    return count


def organize_sample(results_dir, sample_name, output_base=None):
    """
    Create the {Sample}_analysis directory with curated deliverables.

    Directory structure:
        {Sample}_analysis/
        +-- {Sample}.final.bam
        +-- {Sample}.final.bam.bai
        +-- {Sample}.somaticseq.clinical.final.tsv   (now contains FLT3 ITD rows)
        +-- {Sample}.somaticseq.filtered.tsv
        +-- {Sample}_flt3_consensus.tsv              (FLT3-ITD multi-caller summary)
        +-- {Sample}_exon_coverage.tsv
        +-- {Sample}_hsmetrics.txt
        +-- {Sample}_fastp.html
        +-- {Sample}_igv_report.html
        +-- {Sample}_u2af1_pileup_report.txt
        +-- cnv_consensus/
        +-- cnvkit_plots/
        +-- sv_calls/
        +-- sv_annotation/
        +-- flt3_itd/                                 (per-tool FLT3 outputs)
            +-- {Sample}.final_FLT3_ITD.vcf
            +-- {Sample}.final_FLT3_ITD_summary.txt
            +-- {Sample}_filt3r.results.vcf
            +-- {Sample}_filt3r.results.json
            +-- getitd/                               (full getITD output tree)
    """
    results_dir = Path(results_dir)
    sample_dir = results_dir / sample_name

    if not sample_dir.exists():
        logger.error("Sample directory not found: %s", sample_dir)
        sys.exit(1)

    # Output directory: alongside the sample dir, not inside it
    if output_base:
        analysis_dir = Path(output_base) / f"{sample_name}_analysis"
    else:
        analysis_dir = results_dir / f"{sample_name}_analysis"

    if analysis_dir.exists():
        logger.warning("Analysis directory exists, removing: %s", analysis_dir)
        shutil.rmtree(analysis_dir)

    analysis_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Creating analysis directory: %s", analysis_dir)

    s = sample_name  # shorthand
    copied = 0
    missing = 0

    # -------------------------------------------------------------------------
    # 1. ABRA2 BAM + BAI
    # -------------------------------------------------------------------------
    logger.info("--- Alignment ---")
    for fname, desc in [
        (f"{s}.final.bam", "ABRA2 realigned BAM"),
        (f"{s}.final.bam.bai", "BAM index"),
    ]:
        if safe_copy(sample_dir / "abra2" / fname, analysis_dir / fname, desc):
            copied += 1
        else:
            missing += 1

    # -------------------------------------------------------------------------
    # 2. Variant Annotation (single final file + pre-filter)
    # -------------------------------------------------------------------------
    logger.info("--- Variant Annotation ---")

    # Primary: clinical.final.tsv (VV + OncoVI merged). Fall back through
    # other naming conventions the pipeline has used over time.
    # Note: the order matters -- newer / more-annotated outputs win.
    annot_dir = sample_dir / "annotation"
    final_tsv_candidates = [
        annot_dir / f"{s}.somaticseq.clinical.final.tsv",  # OncoVI-merged
        annot_dir / f"{s}.somaticseq.clinical.tsv",        # post-VariantValidator + 17b
        annot_dir / f"{s}.somaticseq.oncovi.tsv",          # legacy naming
    ]
    final_tsv = next((c for c in final_tsv_candidates if c.exists()), None)

    if final_tsv is None:
        logger.warning(
            "  MISSING: final clinical variant TSV "
            "(looked for: clinical.final.tsv, clinical.tsv, oncovi.tsv)"
        )
        missing += 1
    else:
        if final_tsv.name != f"{s}.somaticseq.clinical.final.tsv":
            logger.info(
                "  Using %s (clinical.final.tsv not present)", final_tsv.name
            )
        if safe_copy(
            final_tsv,
            analysis_dir / f"{s}.somaticseq.clinical.final.tsv",
            "Final variant annotation (VV + OncoVI + FLT3-ITD ensemble)",
        ):
            copied += 1
        else:
            missing += 1

    # Pre-filtering SomaticSeq output (all variants before filtering)
    if safe_copy(
        annot_dir / f"{s}.somaticseq.filtered.tsv",
        analysis_dir / f"{s}.somaticseq.filtered.tsv",
        "SomaticSeq pre-filtering (all variants)",
    ):
        copied += 1
    else:
        missing += 1

    # U2AF1 rescue report
    safe_copy(
        annot_dir / f"{s}_u2af1_pileup_report.txt",
        analysis_dir / f"{s}_u2af1_pileup_report.txt",
        "U2AF1 pileup rescue report",
    )

    # U2AF1 rescue variants (if any were rescued)
    u2af1_rescue = annot_dir / f"{s}_u2af1_rescue.tsv"
    if u2af1_rescue.exists() and u2af1_rescue.stat().st_size > 100:
        safe_copy(
            u2af1_rescue,
            analysis_dir / f"{s}_u2af1_rescue.tsv",
            "U2AF1 rescued variants",
        )

    # IGV report
    safe_copy(
        annot_dir / f"{s}_igv_report.html",
        analysis_dir / f"{s}_igv_report.html",
        "IGV variant review report",
    )

    # -------------------------------------------------------------------------
    # 3. FLT3-ITD Ensemble (multi-caller consensus + per-tool outputs)
    # -------------------------------------------------------------------------
    logger.info("--- FLT3-ITD Ensemble ---")
    flt3_src = sample_dir / "flt3"

    # Headline result: consensus TSV at the top level (pathologist-facing)
    flt3_consensus = flt3_src / f"{s}_flt3_consensus.tsv"
    if flt3_consensus.exists():
        if safe_copy(
            flt3_consensus,
            analysis_dir / f"{s}_flt3_consensus.tsv",
            "FLT3-ITD multi-caller consensus (PASS_HIGH / PASS_LOW / REVIEW_REQUIRED)",
        ):
            copied += 1
    else:
        logger.warning(
            "  MISSING: FLT3 consensus TSV (run step 09b_flt3_consensus.py)"
        )

    # Per-tool outputs: keep them in a dedicated subdirectory for audit
    flt3_dst = analysis_dir / "flt3_itd"

    # FLT3_ITD_EXT VCF + summary
    flt3_ext_src = flt3_src / "flt3_itd_ext"
    if flt3_ext_src.exists():
        for fname, desc in [
            (f"{s}.final_FLT3_ITD.vcf",         "FLT3_ITD_EXT VCF"),
            (f"{s}.final_FLT3_ITD_summary.txt", "FLT3_ITD_EXT text summary"),
        ]:
            safe_copy(flt3_ext_src / fname, flt3_dst / fname, desc)

    # filt3r VCF + JSON
    filt3r_src = flt3_src / "filt3r"
    if filt3r_src.exists():
        for fname, desc in [
            (f"{s}_filt3r.results.vcf",  "filt3r VCF (alignment-free, k-mer)"),
            (f"{s}_filt3r.results.json", "filt3r JSON (detailed per-breakpoint metrics)"),
        ]:
            safe_copy(filt3r_src / fname, flt3_dst / fname, desc)

    # getITD: copy the entire output tree (it has many TSVs at different
    # merge / filter stages, plus alignment files for review)
    getitd_src = flt3_src / "getitd" / f"{s}_getitd"
    if getitd_src.exists():
        safe_copy_dir(
            getitd_src,
            flt3_dst / "getitd",
            "getITD output tree",
            exclude_patterns=["out_needle"],  # alignment text files; verbose
        )

    # Pindel-FLT3 VCF (when present)
    pindel_flt3 = flt3_src / "pindel_flt3.vcf"
    if pindel_flt3.exists():
        safe_copy(
            pindel_flt3,
            flt3_dst / pindel_flt3.name,
            "Pindel calls filtered to FLT3 region",
        )

    # -------------------------------------------------------------------------
    # 4. Coverage Analysis
    # -------------------------------------------------------------------------
    logger.info("--- Coverage & QC ---")
    safe_copy(
        sample_dir / "hsmetrics" / f"{s}_hsmetrics.txt",
        analysis_dir / f"{s}_hsmetrics.txt",
        "Picard HS metrics",
    )

    # Exon coverage (from 10b_exon_coverage.py -- may be in different locations)
    exon_cov_candidates = [
        sample_dir / f"{s}_exon_coverage.tsv",
        sample_dir / "hsmetrics" / f"{s}_exon_coverage.tsv",
        analysis_dir / f"{s}_exon_coverage.tsv",  # May already be there
    ]
    for candidate in exon_cov_candidates:
        if candidate.exists():
            if candidate != analysis_dir / f"{s}_exon_coverage.tsv":
                safe_copy(
                    candidate,
                    analysis_dir / f"{s}_exon_coverage.tsv",
                    "Per-exon coverage analysis",
                )
            break
    else:
        logger.warning("  MISSING: exon coverage file (run 10b_exon_coverage.py)")

    # Fastp HTML
    safe_copy(
        sample_dir / "trimmed" / f"{s}_fastp.html",
        analysis_dir / f"{s}_fastp.html",
        "Fastp trimming QC report",
    )

    # -------------------------------------------------------------------------
    # 5. CNV Consensus (exclude verbose text report)
    # -------------------------------------------------------------------------
    logger.info("--- CNV Results ---")
    cnv_consensus_src = sample_dir / "cnv_consensus"
    cnv_consensus_dst = analysis_dir / "cnv_consensus"

    safe_copy_dir(
        cnv_consensus_src,
        cnv_consensus_dst,
        "CNV consensus",
        exclude_patterns=["clinical_report.txt"],  # Exclude verbose text, keep TSV
    )

    # -------------------------------------------------------------------------
    # 6. CNVKit Plots (organized subset)
    # -------------------------------------------------------------------------
    logger.info("--- CNVKit Plots ---")
    cnvkit_src = sample_dir / "cnvkit"
    cnvkit_dst = analysis_dir / "cnvkit_plots"
    cnvkit_dst.mkdir(parents=True, exist_ok=True)

    # Top-level CNVKit plots
    for fname in [
        f"{s}.final-diagram.pdf",
        f"{s}.final-scatter.png",
    ]:
        safe_copy(cnvkit_src / fname, cnvkit_dst / fname, "CNVKit overview plot")

    # Copy plot subdirectories
    plots_src = cnvkit_src / "plots"
    if plots_src.exists():
        for subdir_name in ["combined", "overview", "per_chromosome", "per_gene"]:
            subdir_src = plots_src / subdir_name
            if subdir_src.exists():
                safe_copy_dir(
                    subdir_src,
                    cnvkit_dst / subdir_name,
                    f"CNVKit {subdir_name} plots",
                )

    # -------------------------------------------------------------------------
    # 7. SV Calls (custom merge only, no VCFs)
    # -------------------------------------------------------------------------
    logger.info("--- SV Results ---")
    sv_src = sample_dir / "sv_callers" / "custom_merge"
    sv_dst = analysis_dir / "sv_calls"
    sv_dst.mkdir(parents=True, exist_ok=True)

    for fname, desc in [
        (f"{s}-comparison.txt", "SV caller comparison"),
        (f"{s}-sv-merge_all.txt", "All merged SVs"),
        (f"{s}-sv-merge_filtered.txt", "Filtered merged SVs"),
    ]:
        safe_copy(sv_src / fname, sv_dst / fname, desc)

    # -------------------------------------------------------------------------
    # 8. SV Annotation
    # -------------------------------------------------------------------------
    sv_annot_src = sample_dir / "sv_annotation"
    sv_annot_dst = analysis_dir / "sv_annotation"

    safe_copy_dir(
        sv_annot_src,
        sv_annot_dst,
        "SV annotation",
        exclude_patterns=["unannotated"],  # Skip unannotated file
    )

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    total_files = sum(1 for _ in analysis_dir.rglob("*") if _.is_file())
    total_size_mb = sum(
        f.stat().st_size for f in analysis_dir.rglob("*") if f.is_file()
    ) / (1024 * 1024)

    logger.info("=" * 60)
    logger.info("Analysis directory: %s", analysis_dir)
    logger.info("Total files: %d", total_files)
    logger.info("Total size: %.1f MB", total_size_mb)
    if missing > 0:
        logger.warning("Missing expected files: %d", missing)
    logger.info("=" * 60)

    return analysis_dir


def main():
    parser = argparse.ArgumentParser(
        description="Create clean analysis deliverable directory from pipeline output"
    )
    parser.add_argument(
        "--sample", required=True, help="Sample name"
    )
    parser.add_argument(
        "--results-dir",
        required=True,
        help="Base results directory (parent of sample directories)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output base directory (default: same as results-dir)",
    )

    args = parser.parse_args()
    organize_sample(args.results_dir, args.sample, args.output_dir)


if __name__ == "__main__":
    main()
