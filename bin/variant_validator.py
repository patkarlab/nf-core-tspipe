#!/usr/bin/env python3
"""
17_variant_validator.py — Validate HGVS nomenclature via local VariantValidator.

Input:  results/{sample}/annotation/{sample}.somaticseq.oncovi.tsv (default)
Output: results/{sample}/annotation/{sample}.somaticseq.validated.tsv

For each variant with an HGVSc value, queries the local VariantValidator REST API
to validate and correct HGVS nomenclature. Replaces original HGVSc/HGVSp/HGVSg
with validated versions (VV_HGVSc, VV_HGVSp, VV_HGVSg) and adds:
  VV_Transcript     Reference transcript used
  VV_Valid          True/False — whether validation succeeded
  VV_Warnings       Validation warnings or correction notes
"""

import argparse
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import re

import pandas as pd
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

PIPELINE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_VV_URL = "http://localhost:5001"
GENOME_BUILD = "GRCh38"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Validate HGVS nomenclature via VariantValidator"
    )
    parser.add_argument("-s", "--sample", required=True, help="Sample name")
    parser.add_argument("-i", "--input", default=None,
                        help="Input TSV (default: oncovi TSV; use --all for filtered TSV)")
    parser.add_argument("-o", "--outdir", default=None,
                        help="Output directory (default: same as input)")
    parser.add_argument("--all", action="store_true", dest="all_variants",
                        help="Run on all filtered variants instead of oncovi only")
    parser.add_argument("--vv-url", default=DEFAULT_VV_URL,
                        help=f"VariantValidator base URL (default: {DEFAULT_VV_URL})")
    parser.add_argument("--threads", type=int, default=1,
                        help="Number of parallel query threads (default: 1)")
    parser.add_argument("--timeout", type=int, default=120,
                        help="Per-query timeout in seconds (default: 120)")
    return parser.parse_args()


def check_vv_connection(base_url):
    """Verify VariantValidator is reachable with a test query."""
    try:
        test_url = (f"{base_url}/VariantValidator/variantvalidator/"
                    f"GRCh38/NM_000088.4:c.589G>T/all?content-type=application/json")
        resp = requests.get(test_url, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("flag") in ("gene_variant", "warning"):
                log.info(f"VariantValidator reachable at {base_url}")
                return True
    except requests.ConnectionError:
        pass
    except requests.Timeout:
        pass
    except Exception:
        pass

    log.error(
        f"Cannot connect to VariantValidator at {base_url}\n"
        f"  Is the Docker container running?\n"
        f"  Start it with:\n"
        f"    cd ~/targeted-seq-pipeline/software/rest_variantValidator\n"
        f"    docker compose up -d\n"
        f"    docker exec -d rest_variantvalidator-rest-variantvalidator-1 "
        f"bash -c 'cd /app/rest_VariantValidator && "
        f"gunicorn -b 0.0.0.0:5000 --timeout 600 app --threads=5'"
    )
    return False


def build_query_hgvs(hgvsc, mane_select="", hgvsg=""):
    """Build the HGVS query string for VariantValidator.

    VV's local instance uses RefSeq, not Ensembl transcripts. Strategy:
    1. If MANE_SELECT is available, combine RefSeq transcript with c. notation
    2. If no MANE_SELECT but HGVSg exists, use genomic notation
    3. Otherwise try the original HGVSc as-is (will likely fail for ENST)
    """
    hgvsc = str(hgvsc).strip()
    mane = str(mane_select).strip()
    hgvsg = str(hgvsg).strip()

    if hgvsc in ("-1", "", "nan"):
        return None

    # Extract the c. change from HGVSc (e.g., "ENST00000361804.5:c.2116+23G>A" -> "c.2116+23G>A")
    match = re.search(r':(c\..+)$', hgvsc)
    if match:
        c_change = match.group(1)
        # Prefer MANE_SELECT RefSeq transcript
        if mane not in ("-1", "", "nan"):
            return f"{mane}:{c_change}"

    # Fallback to HGVSg (genomic notation)
    if hgvsg not in ("-1", "", "nan"):
        return hgvsg

    # Last resort: original HGVSc (will fail for Ensembl transcripts)
    return hgvsc


def query_variant(hgvsc, base_url, timeout):
    """Query VariantValidator for a single variant.

    Returns dict with VV_HGVSc, VV_HGVSp, VV_HGVSg, VV_Transcript, VV_Valid, VV_Warnings.
    """
    result = {
        "VV_HGVSc": "",
        "VV_HGVSp": "",
        "VV_HGVSg": "",
        "VV_Exon": "",
        "VV_Transcript": "",
        "VV_Valid": False,
        "VV_Warnings": "",
    }

    # URL-encode the variant description
    url = (
        f"{base_url}/VariantValidator/variantvalidator/"
        f"{GENOME_BUILD}/{requests.utils.quote(hgvsc, safe='')}/all"
        f"?content-type=application/json"
    )

    max_retries = 5
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, timeout=timeout)
            if resp.status_code == 429:
                # Rate limited — back off and retry
                wait = 2 ** attempt
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            break
        except requests.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            result["VV_Warnings"] = f"API_ERROR: {e}"
            return result
        except ValueError:
            result["VV_Warnings"] = "API_ERROR: invalid JSON response"
            return result
    else:
        result["VV_Warnings"] = "API_ERROR: max retries exceeded (rate limited)"
        return result

    # Check flag
    flag = data.get("flag", "")

    # Find the variant result key (not 'flag' or 'metadata')
    variant_keys = [k for k in data.keys() if k not in ("flag", "metadata")]

    if not variant_keys:
        result["VV_Warnings"] = f"NO_RESULT: flag={flag}"
        return result

    # Handle intergenic / warning flags
    if flag == "intergenic":
        result["VV_Warnings"] = "INTERGENIC: variant maps to intergenic region"
        return result

    warnings = []

    # Process each variant result — take the one matching our input transcript
    input_transcript = hgvsc.split(":")[0] if ":" in hgvsc else ""
    best_match = None

    for vkey in variant_keys:
        vdata = data[vkey]
        if not isinstance(vdata, dict):
            continue

        # Check if this result matches our input transcript
        vv_hgvsc = vdata.get("hgvs_transcript_variant", "")
        vv_transcript = vv_hgvsc.split(":")[0] if ":" in vv_hgvsc else ""

        # Prefer matching transcript (without version)
        input_tx_base = input_transcript.split(".")[0]
        vv_tx_base = vv_transcript.split(".")[0]

        if input_tx_base and vv_tx_base and input_tx_base == vv_tx_base:
            best_match = vdata
            break

    # If no transcript match, use the first valid result
    if best_match is None:
        for vkey in variant_keys:
            vdata = data[vkey]
            if isinstance(vdata, dict) and vdata.get("hgvs_transcript_variant"):
                best_match = vdata
                break

    if best_match is None:
        # Check if there's a validation_warning in any key
        for vkey in variant_keys:
            vdata = data[vkey]
            if isinstance(vdata, dict):
                vw = vdata.get("validation_warnings", [])
                if vw:
                    warnings.extend(vw)
        result["VV_Warnings"] = "; ".join(warnings) if warnings else f"NO_MATCH: flag={flag}"
        return result

    vdata = best_match

    # Extract validated HGVS
    vv_hgvsc = vdata.get("hgvs_transcript_variant", "")
    result["VV_HGVSc"] = vv_hgvsc
    result["VV_Transcript"] = vv_hgvsc.split(":")[0] if ":" in vv_hgvsc else ""

    # Protein consequence
    protein = vdata.get("hgvs_predicted_protein_consequence", {})
    if isinstance(protein, dict):
        # Prefer three-letter (tlr) notation
        result["VV_HGVSp"] = protein.get("tlr", "") or protein.get("slr", "")

    # Genomic HGVS from primary assembly loci
    pal = vdata.get("primary_assembly_loci", {})
    grch38 = pal.get("grch38", {})
    result["VV_HGVSg"] = grch38.get("hgvs_genomic_description", "")

    # Exon number from VariantValidator's variant_exonic_positions. Keyed by
    # RefSeq chromosome accession; start_exon == end_exon for a typical SNV.
    # Exon numbering is transcript-based and identical across genome builds, so
    # if the GRCh38 accession is not present we fall back to any available key.
    # Intronic variants have no exonic position -> VV_Exon stays "".
    exon = ""
    vep = vdata.get("variant_exonic_positions", {})
    if isinstance(vep, dict) and vep:
        acc = result["VV_HGVSg"].split(":")[0] if result["VV_HGVSg"] else ""
        ep = vep.get(acc)
        if ep is None:
            ep = next(iter(vep.values()))
        if isinstance(ep, dict):
            se = str(ep.get("start_exon", "")).strip()
            ee = str(ep.get("end_exon", "")).strip()
            if se and ee:
                exon = se if se == ee else (se + "-" + ee)
            elif se:
                exon = se
    result["VV_Exon"] = exon

    # Validation warnings
    vw = vdata.get("validation_warnings", [])
    if vw:
        warnings.extend(vw)

    # Check if VV corrected the HGVS
    if vv_hgvsc and vv_hgvsc != hgvsc:
        # Check if it's just a version difference
        input_no_ver = ":".join(p.split(".")[0] if i == 0 else p
                                for i, p in enumerate(hgvsc.split(":")))
        vv_no_ver = ":".join(p.split(".")[0] if i == 0 else p
                             for i, p in enumerate(vv_hgvsc.split(":")))
        if input_no_ver != vv_no_ver:
            warnings.insert(0, f"CORRECTED: {hgvsc} → {vv_hgvsc}")
        elif hgvsc.split(":")[0] != vv_hgvsc.split(":")[0]:
            warnings.insert(0, f"TRANSCRIPT_VERSION: {hgvsc.split(':')[0]} → {vv_hgvsc.split(':')[0]}")

    result["VV_Valid"] = True
    result["VV_Warnings"] = "; ".join(warnings)

    return result


def validate_variants(df, base_url, threads, timeout):
    """Validate all variants with HGVSc values using parallel threads."""
    # Identify rows to query
    mask = ~df["HGVSc"].isin(["-1", "", "nan"]) & df["HGVSc"].notna()
    query_indices = df.index[mask].tolist()
    skip_count = len(df) - len(query_indices)
    log.info(f"Querying {len(query_indices)} variants ({skip_count} skipped — no HGVSc)")

    # Build query HGVS using MANE_SELECT RefSeq transcripts where possible
    query_to_indices = {}
    idx_to_query = {}
    no_query_count = 0
    for idx in query_indices:
        hgvsc = str(df.at[idx, "HGVSc"])
        mane = str(df.at[idx, "MANE_SELECT"]) if "MANE_SELECT" in df.columns else ""
        hgvsg = str(df.at[idx, "HGVSg"]) if "HGVSg" in df.columns else ""
        query_hgvs = build_query_hgvs(hgvsc, mane, hgvsg)
        if query_hgvs:
            query_to_indices.setdefault(query_hgvs, []).append(idx)
            idx_to_query[idx] = query_hgvs
        else:
            no_query_count += 1

    unique_hgvsc = list(query_to_indices.keys())
    log.info(f"Unique query HGVS values: {len(unique_hgvsc)} ({no_query_count} could not be converted)")

    # Initialize result columns
    for col in ["VV_HGVSc", "VV_HGVSp", "VV_HGVSg", "VV_Exon", "VV_Transcript", "VV_Warnings"]:
        df[col] = ""
    df["VV_Valid"] = ""

    # Query in parallel
    results = {}
    completed = 0
    failed = 0
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=threads) as executor:
        future_to_hgvsc = {
            executor.submit(query_variant, hgvsc, base_url, timeout): hgvsc
            for hgvsc in unique_hgvsc
        }

        for future in as_completed(future_to_hgvsc):
            hgvsc = future_to_hgvsc[future]
            completed += 1

            try:
                result = future.result()
            except Exception as e:
                result = {
                    "VV_HGVSc": "", "VV_HGVSp": "", "VV_HGVSg": "",
                    "VV_Exon": "", "VV_Transcript": "", "VV_Valid": False,
                    "VV_Warnings": f"EXCEPTION: {e}",
                }

            if not result["VV_Valid"]:
                failed += 1

            results[hgvsc] = result

            if completed % 50 == 0 or completed == len(unique_hgvsc):
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                log.info(f"  Progress: {completed}/{len(unique_hgvsc)} "
                         f"({rate:.1f} variants/sec, {failed} failed)")

    # Apply results back to dataframe
    for query_hgvs, indices in query_to_indices.items():
        result = results.get(query_hgvs, {})
        for idx in indices:
            for col in ["VV_HGVSc", "VV_HGVSp", "VV_HGVSg", "VV_Exon", "VV_Transcript", "VV_Warnings"]:
                df.at[idx, col] = result.get(col, "")
            df.at[idx, "VV_Valid"] = result.get("VV_Valid", False)

    return df, len(query_indices), len(unique_hgvsc), failed


def main():
    args = parse_args()
    sample = args.sample

    # Input file — derive defaults from -o so batch runner's outdir is respected
    default_annot_dir = os.path.join(PIPELINE_DIR, "results", sample, "annotation")

    if args.input:
        input_tsv = args.input
    else:
        annot_dir = args.outdir or default_annot_dir
        if args.all_variants:
            input_tsv = os.path.join(annot_dir, f"{sample}.somaticseq.filtered.tsv")
        else:
            input_tsv = os.path.join(annot_dir, f"{sample}.somaticseq.oncovi.tsv")

    if not os.path.exists(input_tsv):
        log.error(f"Input file not found: {input_tsv}")
        sys.exit(1)

    outdir = args.outdir or os.path.dirname(input_tsv)
    os.makedirs(outdir, exist_ok=True)

    # Check VV connection
    if not check_vv_connection(args.vv_url):
        sys.exit(1)

    # Read input
    df = pd.read_csv(input_tsv, sep="\t", dtype=str)
    log.info(f"Read {len(df)} variants from {input_tsv}")

    # Validate
    df, total_queried, unique_queried, total_failed = validate_variants(
        df, args.vv_url, args.threads, args.timeout
    )

    # Reorder columns — keep original HGVSc/HGVSp/HGVSg alongside VV_ versions
    desired_order = [
        "Sample", "Chr", "Start", "End", "Ref", "Alt", "Gene", "Consequence",
        "HGVSc", "HGVSp", "HGVSg",
        "VV_HGVSc", "VV_HGVSp", "VV_HGVSg", "VV_Transcript", "VV_Valid", "VV_Warnings",
        "OncoVI_Score", "OncoVI_Classification", "OncoVI_Criteria",
        "IMPACT", "VariantCaller_Count", "Callers", "REF_COUNT", "ALT_COUNT",
        "VAF_pct", "SomaticSeq_Verdict", "COSMIC_ID", "ClinVar", "SIFT", "PolyPhen",
        "gnomAD_exome_AF", "gnomAD_genome_AF", "AF_1KG", "Max_AF", "rsID",
        "MANE_SELECT", "Canonical", "Existing_variation", "Dedup_Note", "Filter",
    ]
    # Keep only columns that exist in the dataframe, in the desired order
    final_cols = [c for c in desired_order if c in df.columns]
    # Append any remaining columns not in the desired order
    extra_cols = [c for c in df.columns if c not in desired_order]
    if extra_cols:
        log.info(f"Extra columns appended at end: {extra_cols}")
    df = df[final_cols + extra_cols]

    # Write output
    out_path = os.path.join(outdir, f"{sample}.somaticseq.clinical.validated.tsv")
    df.to_csv(out_path, sep="\t", index=False)
    log.info(f"Wrote validated output: {out_path}")

    # Summary
    total_valid = (df["VV_Valid"] == True).sum() + (df["VV_Valid"] == "True").sum()  # noqa
    total_warnings = df["VV_Warnings"].apply(lambda x: bool(str(x).strip())).sum()
    total_corrected = df["VV_Warnings"].str.contains("CORRECTED", na=False).sum()

    log.info("=== VariantValidator Summary ===")
    log.info(f"  Total variants in file:   {len(df)}")
    log.info(f"  Queried (with HGVSc):     {total_queried} ({unique_queried} unique)")
    log.info(f"  Successfully validated:   {total_valid}")
    log.info(f"  With warnings:            {total_warnings}")
    log.info(f"  HGVS corrected by VV:     {total_corrected}")
    log.info(f"  Failed:                   {total_failed}")


if __name__ == "__main__":
    main()
