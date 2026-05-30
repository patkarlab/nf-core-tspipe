#!/usr/bin/env python3
"""
15_oncovi.py — Run OncoVI oncogenicity classification on clinical variants.

Input:  results/{sample}/annotation/{sample}.somaticseq.clinical.tsv
Output: results/{sample}/annotation/{sample}.somaticseq.oncovi.tsv

OncoVI implements the Horak et al. (2022) oncogenicity guidelines, scoring
each variant on a point scale:
  >=10  Oncogenic
  6-9   Likely Oncogenic
  0-5   VUS
  -1..-6 Likely Benign
  <=-7  Benign

Columns added:
  OncoVI_Score          (integer point total)
  OncoVI_Classification (text classification)
  OncoVI_Criteria       (comma-separated triggered criteria)
"""

import argparse
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

# Paths relative to pipeline root
PIPELINE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ONCOVI_SCRIPT = os.path.join(PIPELINE_DIR, "software", "oncovi", "src", "03_OncoVI_SOP.py")
ONCOVI_RESOURCES = os.path.join(PIPELINE_DIR, "software", "oncovi", "resources")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run OncoVI oncogenicity scoring on clinical variants"
    )
    parser.add_argument("-s", "--sample", required=True, help="Sample name (e.g. 26CGH40)")
    parser.add_argument("-o", "--outdir", default=None,
                        help="Output directory (default: results/{sample}/annotation)")
    parser.add_argument("--oncovi-dir", default=None,
                        help="Path to the OncoVI install (must contain src/ and "
                             "resources/). Default: <repo>/software/oncovi relative "
                             "to this script.")
    return parser.parse_args()


def prepare_oncovi_input(clinical_df):
    """Map our clinical TSV columns to OncoVI's expected Excel format.

    OncoVI expects columns:
      CHROM, POS, REF, ALT, SYMBOL, Consequence, HGVSc, HGVSp,
      gnomADe_AF, gnomADe_{AFR,EAS,NFE,AMR,SAS}_AF,
      gnomADg_AF, gnomADg_{AFR,EAS,NFE,AMR,SAS}_AF,
      ClinVar_germline, ClinVar_germline_ReviewStatus,
      phyloP100way_vertebrate_rankscore, phastCons100way_vertebrate_rankscore,
      SpliceAI_cutoff, HGVSg

    OncoVI reads with na_filter=False, so empty cells become empty strings.
    COSMIC dictionaries use plain chromosome numbers (no 'chr' prefix).
    """
    oncovi = pd.DataFrame()

    # Strip 'chr' prefix for CHROM — COSMIC keys use plain numbers
    oncovi["CHROM"] = clinical_df["Chr"].astype(str).str.replace("^chr", "", regex=True)
    oncovi["POS"] = clinical_df["Start"]
    oncovi["REF"] = clinical_df["Ref"]
    oncovi["ALT"] = clinical_df["Alt"]
    oncovi["SYMBOL"] = clinical_df["Gene"]
    oncovi["Consequence"] = clinical_df["Consequence"]

    # HGVSc/HGVSp: use original Ensembl columns (OncoVI requires ENST transcripts)
    for our_col, oncovi_col in [("HGVSc", "HGVSc"), ("HGVSp", "HGVSp")]:
        oncovi[oncovi_col] = clinical_df[our_col].apply(
            lambda x: "" if str(x).strip() in ("-1", "", "nan") else str(x)
        )

    # gnomAD overall frequencies — convert -1 to empty string
    for our_col, oncovi_col in [
        ("gnomAD_exome_AF", "gnomADe_AF"),
        ("gnomAD_genome_AF", "gnomADg_AF"),
    ]:
        oncovi[oncovi_col] = clinical_df[our_col].apply(
            lambda x: "" if str(x).strip() in ("-1", "", "nan") else str(x)
        )

    # Population-specific gnomAD AFs — not available in our annotation
    for pop in ["AFR", "EAS", "NFE", "AMR", "SAS"]:
        oncovi[f"gnomADe_{pop}_AF"] = ""
        oncovi[f"gnomADg_{pop}_AF"] = ""

    # ClinVar — convert -1 to empty string
    oncovi["ClinVar_germline"] = clinical_df["ClinVar"].apply(
        lambda x: "" if str(x).strip() in ("-1", "", "nan") else str(x)
    )

    # ClinVar review status — not available in our annotation
    oncovi["ClinVar_germline_ReviewStatus"] = ""

    # Conservation / splicing scores — not available
    oncovi["phyloP100way_vertebrate_rankscore"] = ""
    oncovi["phastCons100way_vertebrate_rankscore"] = ""
    oncovi["SpliceAI_cutoff"] = ""

    # HGVSg — strip 'chr' prefix to match COSMIC format
    oncovi["HGVSg"] = clinical_df["HGVSg"].apply(
        lambda x: "" if str(x).strip() in ("-1", "", "nan")
        else str(x).replace("chr", "")
    )

    return oncovi


def run_oncovi(oncovi_df, sample):
    """Write OncoVI input to temp Excel, run the scoring engine, parse output."""
    with tempfile.TemporaryDirectory(prefix="oncovi_") as tmpdir:
        input_xlsx = os.path.join(tmpdir, f"{sample}_oncovi_input.xlsx")
        oncovi_df.to_excel(input_xlsx, index=False)
        log.info(f"Wrote OncoVI input: {input_xlsx} ({len(oncovi_df)} variants)")

        cmd = [
            sys.executable, ONCOVI_SCRIPT,
            "-i", input_xlsx,
            "-r", ONCOVI_RESOURCES,
            "-d", sample,
        ]
        log.info(f"Running: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            log.error(f"OncoVI stderr:\n{result.stderr}")
            log.error(f"OncoVI stdout:\n{result.stdout}")
            raise RuntimeError(f"OncoVI exited with code {result.returncode}")

        log.info("OncoVI completed successfully")
        if result.stdout:
            for line in result.stdout.strip().split("\n")[-5:]:
                log.info(f"  {line}")

        # OncoVI output: {input_dir}/{sample}_OncoVI/{sample}_OncoVI_eval.csv
        output_dir = os.path.join(tmpdir, f"{sample}_OncoVI")
        eval_csv = os.path.join(output_dir, f"{sample}_OncoVI_eval.csv")

        if not os.path.exists(eval_csv):
            # Check for prediction xlsx too
            pred_xlsx = os.path.join(output_dir, f"{sample}_OncoVI_prediction.xlsx")
            if os.path.exists(pred_xlsx):
                log.info("Using OncoVI prediction xlsx instead of eval csv")
                pred_df = pd.read_excel(pred_xlsx)
                return pred_df[["new_identifier", "Points", "Classification", "Criteria"]]
            raise FileNotFoundError(f"OncoVI output not found: {eval_csv}")

        eval_df = pd.read_csv(eval_csv, index_col=0)
        log.info(f"Parsed OncoVI output: {len(eval_df)} variants scored")

        return eval_df[["Points", "Classification", "Criteria"]].reset_index().rename(
            columns={"index": "new_identifier"}
        )


def merge_results(clinical_df, oncovi_results):
    """Merge OncoVI scores back into the clinical dataframe."""
    # Build new_identifier matching OncoVI's format: CHROM_POS_REF_ALT (no 'chr')
    clinical_df = clinical_df.copy()
    clinical_df["_oncovi_id"] = (
        clinical_df["Chr"].astype(str).str.replace("^chr", "", regex=True)
        + "_"
        + clinical_df["Start"].astype(str)
        + "_"
        + clinical_df["Ref"].astype(str)
        + "_"
        + clinical_df["Alt"].astype(str)
    )

    oncovi_results = oncovi_results.rename(columns={
        "new_identifier": "_oncovi_id",
        "Points": "OncoVI_Score",
        "Classification": "OncoVI_Classification",
        "Criteria": "OncoVI_Criteria",
    })

    merged = clinical_df.merge(
        oncovi_results[["_oncovi_id", "OncoVI_Score", "OncoVI_Classification", "OncoVI_Criteria"]],
        on="_oncovi_id",
        how="left",
    )
    merged.drop(columns=["_oncovi_id"], inplace=True)

    # Report any unscored variants
    unscored = merged["OncoVI_Classification"].isna().sum()
    if unscored > 0:
        log.warning(f"{unscored} variant(s) could not be scored by OncoVI")

    return merged


def main():
    args = parse_args()
    sample = args.sample

    # Locate the OncoVI engine + resources. Default (PIPELINE_DIR/software/oncovi)
    # is kept for backward compatibility; --oncovi-dir lets the pipeline point at
    # an install that lives outside this repo (OncoVI is third-party software,
    # not vendored into the pipeline repo).
    if args.oncovi_dir:
        global ONCOVI_SCRIPT, ONCOVI_RESOURCES
        _base = os.path.abspath(args.oncovi_dir)
        ONCOVI_SCRIPT = os.path.join(_base, "src", "03_OncoVI_SOP.py")
        ONCOVI_RESOURCES = os.path.join(_base, "resources")

    # Input: clinical TSV from variant filter — derive from -o so batch runner's outdir is respected
    outdir = args.outdir or os.path.join(PIPELINE_DIR, "results", sample, "annotation")
    # Prefer validated TSV (from step 17) over plain clinical TSV
    validated_tsv = os.path.join(outdir, f"{sample}.somaticseq.clinical.validated.tsv")
    plain_tsv = os.path.join(outdir, f"{sample}.somaticseq.clinical.tsv")
    if os.path.exists(validated_tsv):
        clinical_tsv = validated_tsv
    elif os.path.exists(plain_tsv):
        log.warning(f"Validated TSV not found, falling back to: {plain_tsv}")
        clinical_tsv = plain_tsv
    else:
        log.error(f"No clinical TSV found (tried {validated_tsv} and {plain_tsv})")
        sys.exit(1)
    os.makedirs(outdir, exist_ok=True)

    # Read clinical variants
    clinical_df = pd.read_csv(clinical_tsv, sep="\t", dtype=str)
    log.info(f"Read {len(clinical_df)} clinical PASS variants from {clinical_tsv}")

    if len(clinical_df) == 0:
        log.warning("No clinical variants to score — writing empty output")
        clinical_df["OncoVI_Score"] = []
        clinical_df["OncoVI_Classification"] = []
        clinical_df["OncoVI_Criteria"] = []
        out_path = os.path.join(outdir, f"{sample}.somaticseq.clinical.final.tsv")
        clinical_df.to_csv(out_path, sep="\t", index=False)
        return

    # Prepare OncoVI input
    oncovi_input = prepare_oncovi_input(clinical_df)

    # Run OncoVI
    oncovi_results = run_oncovi(oncovi_input, sample)

    # Merge results
    result_df = merge_results(clinical_df, oncovi_results)

    # Write output
    out_path = os.path.join(outdir, f"{sample}.somaticseq.clinical.final.tsv")
    result_df.to_csv(out_path, sep="\t", index=False)
    log.info(f"Wrote OncoVI-scored output: {out_path}")

    # Summary
    log.info("=== OncoVI Classification Summary ===")
    if "OncoVI_Classification" in result_df.columns:
        counts = result_df["OncoVI_Classification"].value_counts()
        for cls, n in counts.items():
            log.info(f"  {cls}: {n}")
    log.info(f"Total: {len(result_df)} variants")


if __name__ == "__main__":
    main()
