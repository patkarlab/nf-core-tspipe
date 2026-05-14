#!/usr/bin/env python3
"""
12c_build_sex_pon.py
Classify normal samples by sex using chrX log2 from LOO CNR files,
then build sex-specific PON references with cnvkit.py.
"""

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def parse_args():
    p = argparse.ArgumentParser(
        description="Classify normals by sex and build sex-specific CNVkit PON references."
    )
    p.add_argument(
        "--cov-dir",
        default="results/cnvkit_pon_build",
        help="Directory with .final.targetcoverage.cnn / .antitargetcoverage.cnn files "
             "(default: results/cnvkit_pon_build)",
    )
    p.add_argument(
        "--loo-dir",
        default="results/cnvkit_loo_qc/loo_iterations",
        help="Directory with LOO iteration subdirectories containing {sample}.cnr "
             "(default: results/cnvkit_loo_qc/loo_iterations)",
    )
    p.add_argument(
        "-o",
        "--out-dir",
        default="references/",
        help="Output directory for PON files and sex assignment TSV (default: references/)",
    )
    p.add_argument(
        "--chrx-threshold",
        type=float,
        default=-0.4,
        help="chrX mean target log2 threshold: < threshold => male, >= threshold => female "
             "(default: -0.4)",
    )
    p.add_argument(
        "--exclude",
        nargs="*",
        default=["OCIAML3"],
        help="Samples to exclude from PON (default: OCIAML3)",
    )
    return p.parse_args()


def chrx_mean_target_log2(cnr_path: Path) -> float:
    """Read a CNR file and return the mean log2 of chrX target bins."""
    df = pd.read_csv(cnr_path, sep="\t")
    chrx = df[(df["chromosome"] == "chrX") & (df["gene"] != "Antitarget")]
    if chrx.empty:
        raise ValueError(f"No chrX target bins found in {cnr_path}")
    return chrx["log2"].mean()


def classify_samples(loo_dir: Path, threshold: float) -> pd.DataFrame:
    """Walk LOO directories, compute chrX mean log2, classify sex."""
    records = []
    for sample_dir in sorted(loo_dir.iterdir()):
        if not sample_dir.is_dir():
            continue
        sample = sample_dir.name
        cnr_path = sample_dir / f"{sample}.cnr"
        if not cnr_path.exists():
            log.warning("CNR not found for %s, skipping", sample)
            continue
        mean_log2 = chrx_mean_target_log2(cnr_path)
        sex = "male" if mean_log2 < threshold else "female"
        records.append({"sample": sample, "chrX_mean_log2": round(mean_log2, 4), "sex": sex})
        log.info("  %-30s  chrX_log2=%.4f  => %s", sample, mean_log2, sex)
    return pd.DataFrame(records)


def collect_coverage_files(cov_dir: Path, samples: list[str]) -> list[str]:
    """Return sorted list of .targetcoverage.cnn and .antitargetcoverage.cnn paths for given samples."""
    files = []
    for sample in sorted(samples):
        tcov = cov_dir / f"{sample}.final.targetcoverage.cnn"
        acov = cov_dir / f"{sample}.final.antitargetcoverage.cnn"
        if not tcov.exists() or not acov.exists():
            log.warning("Coverage files missing for %s, skipping from PON", sample)
            continue
        files.extend([str(tcov), str(acov)])
    return files


def build_reference(cov_files: list[str], output: Path, label: str,
                     male_reference: bool = False):
    """Run cnvkit.py reference to build a PON.

    When male_reference is True, -y is passed to cnvkit reference so the
    haploid X expectation is baked into the PoN's stored log2 values.
    Without it, cnvkit median-centers each input as if chrX were diploid,
    washing out the haploid signal and producing a PoN that yields
    systematic chrX 'loss' for any male sample run against it.
    """
    cmd = ["cnvkit.py", "reference", "-o", str(output)] + cov_files
    if male_reference:
        cmd.append("-y")
    log.info("Building %s PON with %d coverage files -> %s%s",
             label, len(cov_files), output,
             " (-y, haploid X)" if male_reference else "")
    log.info("  cmd: cnvkit.py reference -o %s <+%d files>%s",
             output, len(cov_files), " -y" if male_reference else "")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log.error("cnvkit.py reference (%s) failed:\n%s", label, result.stderr)
        sys.exit(1)
    if result.stdout.strip():
        log.info("  stdout: %s", result.stdout.strip()[:500])
    log.info("  %s PON written: %s", label, output)


def main():
    args = parse_args()
    loo_dir = Path(args.loo_dir)
    cov_dir = Path(args.cov_dir)
    out_dir = Path(args.out_dir)
    threshold = args.chrx_threshold

    if not loo_dir.is_dir():
        log.error("LOO directory not found: %s", loo_dir)
        sys.exit(1)
    if not cov_dir.is_dir():
        log.error("Coverage directory not found: %s", cov_dir)
        sys.exit(1)
    out_dir.mkdir(parents=True, exist_ok=True)

    exclude = set(args.exclude or [])

    # --- 1. Classify samples by sex ---
    log.info("=== Classifying samples by sex (chrX threshold=%.2f) ===", threshold)
    if exclude:
        log.info("Excluding from PON: %s", ", ".join(sorted(exclude)))
    sex_df = classify_samples(loo_dir, threshold)
    if sex_df.empty:
        log.error("No samples classified. Check LOO directory.")
        sys.exit(1)

    # Also exclude any samples that don't have coverage files (e.g. tumor samples)
    for sample in list(sex_df["sample"]):
        tcov = cov_dir / f"{sample}.final.targetcoverage.cnn"
        if not tcov.exists():
            log.info("  No coverage files for %s (not in PON build dir), excluding", sample)
            exclude.add(sample)

    # Filter out excluded samples for PON building (keep them in sex_df for reference)
    pon_df = sex_df[~sex_df["sample"].isin(exclude)]
    males = pon_df.loc[pon_df["sex"] == "male", "sample"].tolist()
    females = pon_df.loc[pon_df["sex"] == "female", "sample"].tolist()
    log.info("=== Classification summary: %d male, %d female (total %d, %d excluded) ===",
             len(males), len(females), len(pon_df), len(exclude))

    # --- 2. Save sex assignment ---
    tsv_path = out_dir / "cnvkit_pon_sex_assignment.tsv"
    sex_df.to_csv(tsv_path, sep="\t", index=False)
    log.info("Sex assignment saved to %s", tsv_path)

    # --- 3. Build male PON ---
    if males:
        male_cov = collect_coverage_files(cov_dir, males)
        if male_cov:
            male_out = out_dir / "cnvkit_hg38_pon_male.cnn"
            build_reference(male_cov, male_out, "male", male_reference=True)
        else:
            log.warning("No male coverage files found; skipping male PON.")
    else:
        log.warning("No males classified; skipping male PON.")

    # --- 4. Build female PON ---
    if females:
        female_cov = collect_coverage_files(cov_dir, females)
        if female_cov:
            female_out = out_dir / "cnvkit_hg38_pon_female.cnn"
            build_reference(female_cov, female_out, "female")
        else:
            log.warning("No female coverage files found; skipping female PON.")
    else:
        log.warning("No females classified; skipping female PON.")

    log.info("=== Done ===")


if __name__ == "__main__":
    main()
