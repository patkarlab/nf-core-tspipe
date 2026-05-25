#!/usr/bin/env python3
"""
make_report_bundle.py

Build self-contained, shareable bundles of per-sample TSPIPE reports.

For each sample under a TSPIPE outdir, this tool produces a single
shareable zip placed alongside the sample's other module outputs:

    <outdir>/<sample>/<sample>_report.zip

The zip contains everything the report needs to render correctly
when copied to another machine. The fellow downloads the zip,
unzips it, and opens <sample>_report.html.

Inside the zip, the top-level directory is named <sample>/, so
unzipping does not dump files into the current directory.

Why this exists
---------------
The original TSPIPE per-sample report references CSS and JavaScript
via relative paths like ../../assets/css/bootstrap.min.css. When only
the clinical/ folder is deposited to a network share, those paths
do not resolve and the report renders unstyled. This tool produces a
self-contained copy where asset paths have been rewritten to live
inside the bundle, so the report works wherever it is opened.

What is NOT in the bundle
-------------------------
- BAM/BAI files (kept in the original clinical/ for archival;
  the IGV report has the BAM data already embedded as base64).
- Raw TSV/VCF outputs (not referenced by the report).
- The cohort index link (stripped, since fellows view one sample
  at a time when sharing a bundle).
- Anything else outside the report's reference graph.

Inputs (per sample <S>)
-----------------------
    <outdir>/<S>/clinical/<S>_report.html         (the entry point)
    <outdir>/<S>/clinical/<S>_dashboard.html
    <outdir>/<S>/clinical/<S>_fastp.html
    <outdir>/<S>/clinical/<S>_igv_report.html
    <outdir>/<S>/clinical/cnvkit_plots/           (full subtree)
    <outdir>/assets/                              (shared, copied per bundle)

Output (per sample)
-------------------
    <outdir>/<S>/<S>_report.zip

Zip contents
------------
    <S>/<S>_report.html         (with paths rewritten)
    <S>/<S>_dashboard.html      (byte-copy)
    <S>/<S>_fastp.html          (byte-copy)
    <S>/<S>_igv_report.html     (byte-copy)
    <S>/assets/...              (full subtree, copied in)
    <S>/cnvkit_plots/...        (full subtree, copied in)

Path rewrites applied to <S>_report.html
----------------------------------------
1. href="../../assets/..."  ->  href="./assets/..."
2. src ="../../assets/..."  ->  src ="./assets/..."
3. <a ... href="../../cohort_index.html" ...>...</a>  ->  removed entirely

No other HTML in the bundle is rewritten (the sibling HTML files have
no ../ references; this was verified before writing this tool).

Usage
-----
Multi-sample (the common case):

    python3 tools/make_report_bundle.py \\
        --outdir /goast/hemat_data/nfcore_runs/tspipe_clinical_myeloid_cnv_20260524_142741

Single sample or a subset:

    python3 tools/make_report_bundle.py \\
        --outdir /goast/hemat_data/nfcore_runs/tspipe_clinical_myeloid_cnv_20260524_142741 \\
        --samples 26ARC1019 26ARC1020

Re-run over existing zips:

    python3 tools/make_report_bundle.py --outdir <outdir> --force
"""

import argparse
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path


# --------------------------------------------------------------------
# Configuration: top-level entries in outdir that are not samples and
# should be skipped during auto-detection.
# --------------------------------------------------------------------

NON_SAMPLE_DIRS = {"assets", "pipeline_info"}


# --------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------

def fmt_bytes(n):
    """Format a byte count as a human-readable string."""
    n = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{int(n)} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def count_files(path: Path) -> int:
    """Count regular files under path (recursive)."""
    return sum(1 for p in path.rglob("*") if p.is_file())


def total_size(path: Path) -> int:
    """Total size in bytes of all regular files under path."""
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


# --------------------------------------------------------------------
# Sample discovery
# --------------------------------------------------------------------

def find_samples(outdir: Path):
    """
    Return a sorted list of sample directories under outdir.

    A directory <outdir>/<name>/ is considered a sample iff:
      - <name> is not in NON_SAMPLE_DIRS, and
      - <outdir>/<name>/clinical/<name>_report.html exists.
    """
    samples = []
    for child in sorted(outdir.iterdir()):
        if not child.is_dir():
            continue
        if child.name in NON_SAMPLE_DIRS:
            continue
        clinical = child / "clinical"
        if not clinical.is_dir():
            continue
        report = clinical / f"{child.name}_report.html"
        if report.is_file():
            samples.append(child)
    return samples


# --------------------------------------------------------------------
# HTML rewriting
# --------------------------------------------------------------------

# Rewrite "../../assets/" in href= and src= attributes.
ASSET_PATH_RE = re.compile(
    r"""((?:href|src))=(["'])\.\./\.\./assets/""",
    re.IGNORECASE,
)

# Sanity check: are there leftover "../../assets/" references after rewrite?
ASSET_PATH_LEFTOVER_RE = re.compile(
    r"""(?:href|src)=["']\.\./\.\./assets/""",
    re.IGNORECASE,
)

# Find a complete <a> element whose href is the cohort index.
# DOTALL so it spans newlines (icons, spans) inside the anchor.
# Non-greedy on </a> so adjacent anchors are not merged.
COHORT_ANCHOR_RE = re.compile(
    r"""<a\b[^>]*href=["']\.\./\.\./cohort_index\.html["'][^>]*>.*?</a>""",
    re.IGNORECASE | re.DOTALL,
)

# Sanity check: any reference to cohort_index.html still present?
COHORT_LEFTOVER_RE = re.compile(
    r"""\.\./\.\./cohort_index\.html""",
    re.IGNORECASE,
)


def rewrite_report_html(report_text: str, stats: dict) -> str:
    """
    Apply the three rewrites and update stats. Returns the new text.

    stats keys updated:
        asset_paths_rewritten   (int)
        cohort_links_removed    (int)
        warnings                (list, appended on suspicious cases)
    """
    # 1. Asset path rewrite
    new_text, asset_subs = ASSET_PATH_RE.subn(
        r"""\1=\2./assets/""",
        report_text,
    )
    stats["asset_paths_rewritten"] = asset_subs

    # 2. Cohort link removal
    new_text, cohort_subs = COHORT_ANCHOR_RE.subn("", new_text)
    stats["cohort_links_removed"] = cohort_subs

    # 3. Post-rewrite sanity checks
    leftover_assets = len(ASSET_PATH_LEFTOVER_RE.findall(new_text))
    if leftover_assets > 0:
        stats["warnings"].append(
            f"report.html: {leftover_assets} reference(s) to "
            "../../assets/ still present after rewrite. The template "
            "may use an attribute name other than href/src; bundle "
            "may not render correctly."
        )

    leftover_cohort = len(COHORT_LEFTOVER_RE.findall(new_text))
    if leftover_cohort > 0:
        stats["warnings"].append(
            f"report.html: {leftover_cohort} reference(s) to "
            "cohort_index.html still present after anchor removal. "
            "The cohort link may be inside an irregular HTML structure."
        )

    if asset_subs == 0:
        stats["warnings"].append(
            "report.html: no ../../assets/ references found to rewrite. "
            "The template may have changed."
        )

    return new_text


# --------------------------------------------------------------------
# Bundle assembly
# --------------------------------------------------------------------

def bundle_one_sample(
    outdir: Path,
    sample_dir: Path,
    force: bool,
) -> dict:
    """
    Build a zip bundle for one sample, placed at
    <sample_dir>/<sample>_report.zip.

    Internally assembles the bundle in a temporary directory, then
    writes the zip. The temp directory is removed automatically when
    the with-block exits (even on error).

    Raises RuntimeError on any precondition failure. Returns stats.
    """
    sample = sample_dir.name
    clinical = sample_dir / "clinical"
    zip_path = sample_dir / f"{sample}_report.zip"

    # Validate inputs
    expected_html = [
        clinical / f"{sample}_report.html",
        clinical / f"{sample}_dashboard.html",
        clinical / f"{sample}_fastp.html",
        clinical / f"{sample}_igv_report.html",
    ]
    missing = [str(f) for f in expected_html if not f.is_file()]
    if missing:
        raise RuntimeError(
            f"sample {sample}: missing expected file(s): "
            f"{', '.join(missing)}"
        )

    cnvkit_plots = clinical / "cnvkit_plots"
    if not cnvkit_plots.is_dir():
        raise RuntimeError(
            f"sample {sample}: cnvkit_plots/ directory missing: "
            f"{cnvkit_plots}"
        )

    assets = outdir / "assets"
    if not assets.is_dir():
        raise RuntimeError(f"outdir assets/ directory missing: {assets}")

    # Handle existing zip
    if zip_path.exists():
        if not force:
            raise RuntimeError(
                f"bundle zip already exists (use --force to overwrite): "
                f"{zip_path}"
            )
        zip_path.unlink()

    stats = {
        "sample": sample,
        "asset_paths_rewritten": 0,
        "cohort_links_removed": 0,
        "warnings": [],
    }

    # Build the bundle in a temporary directory. tempfile cleans it up
    # automatically when the with-block exits.
    with tempfile.TemporaryDirectory(prefix=f"{sample}_report_bundle_") as tmp:
        staging = Path(tmp) / sample
        staging.mkdir()

        # Byte-copy the three sibling HTML files (no rewrites needed)
        for src in (
            clinical / f"{sample}_dashboard.html",
            clinical / f"{sample}_fastp.html",
            clinical / f"{sample}_igv_report.html",
        ):
            shutil.copy2(src, staging / src.name)

        # Copy cnvkit_plots and assets as whole subtrees
        shutil.copytree(cnvkit_plots, staging / "cnvkit_plots")
        shutil.copytree(assets, staging / "assets")

        # Rewrite and write the entry-point HTML
        report_src = clinical / f"{sample}_report.html"
        report_dst = staging / f"{sample}_report.html"
        report_text = report_src.read_text()
        rewritten = rewrite_report_html(report_text, stats)
        report_dst.write_text(rewritten)

        # Capture content stats before the staging directory is removed
        stats["bundle_files"] = count_files(staging)
        stats["bundle_size"] = total_size(staging)

        # Write the zip. The top-level entry inside the zip is
        # <sample>/, so unzipping creates a folder named <sample>/
        # rather than dumping files into the current directory.
        with zipfile.ZipFile(
            zip_path, "w", compression=zipfile.ZIP_DEFLATED,
        ) as zf:
            for file_path in sorted(staging.rglob("*")):
                if file_path.is_file():
                    arcname = Path(sample) / file_path.relative_to(staging)
                    zf.write(file_path, arcname.as_posix())

    # Temp dir is gone. The zip is the only persistent output.
    stats["zip_size"] = zip_path.stat().st_size
    stats["zip_path"] = zip_path
    return stats


# --------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Build self-contained, shareable zip bundles "
            "of per-sample TSPIPE reports."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--outdir",
        type=Path,
        required=True,
        help="TSPIPE outdir (contains per-sample dirs and an assets/ dir)",
    )
    ap.add_argument(
        "--samples",
        nargs="+",
        default=None,
        help="Specific sample names to bundle. Default: all samples "
             "auto-detected under <outdir>.",
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing <sample>/<sample>_report.zip",
    )
    args = ap.parse_args()

    if not args.outdir.is_dir():
        sys.exit(f"ERROR: outdir not a directory: {args.outdir}")

    if args.samples:
        sample_dirs = []
        for name in args.samples:
            d = args.outdir / name
            if not d.is_dir():
                sys.exit(f"ERROR: sample directory not found: {d}")
            sample_dirs.append(d)
    else:
        sample_dirs = find_samples(args.outdir)
        if not sample_dirs:
            sys.exit(
                f"ERROR: no sample reports found under "
                f"{args.outdir}/*/clinical/*_report.html"
            )

    print(f"Bundling {len(sample_dirs)} sample(s)")
    print()

    n_ok = 0
    n_err = 0
    total_zip_bytes = 0

    for sample_dir in sample_dirs:
        sample = sample_dir.name
        print(f"  {sample}")
        try:
            stats = bundle_one_sample(args.outdir, sample_dir, args.force)
        except Exception as e:
            print(f"    ERROR: {e}", file=sys.stderr)
            n_err += 1
            print()
            continue

        print(f"    asset paths rewritten: {stats['asset_paths_rewritten']}")
        print(f"    cohort links removed:  {stats['cohort_links_removed']}")
        print(
            f"    contents: "
            f"{stats['bundle_files']} files, "
            f"{fmt_bytes(stats['bundle_size'])} raw"
        )
        print(f"    zip:      {fmt_bytes(stats['zip_size'])}")
        print(f"              -> {stats['zip_path']}")
        for w in stats["warnings"]:
            print(f"    WARN: {w}", file=sys.stderr)
        print()

        n_ok += 1
        total_zip_bytes += stats["zip_size"]

    print(
        f"Done: {n_ok} bundled "
        f"({fmt_bytes(total_zip_bytes)} of zips), "
        f"{n_err} failed"
    )
    return 1 if n_err else 0


if __name__ == "__main__":
    sys.exit(main())
