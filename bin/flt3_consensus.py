#!/usr/bin/env python3
"""
flt3_consensus.py
-----------------
Build a 3-caller consensus for FLT3-ITD calls from three independent tools:
    1. getITD          (TSV)
    2. FLT3_ITD_EXT    (VCF)
    3. filt3r          (VCF)

Each caller's output is parsed into a common per-event record schema, then
records are clustered by ITD length (within +/- 2 bp tolerance). Each cluster
becomes one consensus row in the output TSV, with a status tag reflecting
how many tools support the event:
    PASS_HIGH        -- all 3 callers agree
    PASS_LOW         -- 2 of 3 callers agree
    REVIEW_REQUIRED  -- 1 caller only (manual IGV review before reporting)

This script is a port of scripts/09b_flt3_consensus.py from the production
pipeline, with the following revisions:
    - Pindel parser dropped (Pindel stays in the SNV/INDEL ensemble only).
    - CLI takes explicit per-file paths instead of a sample-dir convention,
      matching Nextflow's file-staging idiom.
    - AR (allelic ratio) is now tracked and emitted alongside VAF.

Output units:
    - VAF is emitted in percent (e.g. 14.05 means 14.05%), under columns
      named `vaf_pct_*`. Internal math stays in fractions; the *100 lift
      happens once, at the moment the consensus TSV is written.
    - AR is emitted as a decimal fraction (e.g. 0.1222), under columns
      `ar_*`. AR can exceed 1.0 in heavily clonal samples, so the percent
      convention does not fit it cleanly.

Usage:
    python flt3_consensus.py \\
        --sample 25NGS1307 \\
        --getitd 25NGS1307_getitd_hc.tsv \\
        --flt3-itd-ext 25NGS1307.final_FLT3_ITD.vcf \\
        --filt3r 25NGS1307_filt3r.results.vcf \\
        --out 25NGS1307_flt3_consensus.tsv
"""

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Length tolerance when clustering ITDs across callers.
# ITDs are PCR-slippage resistant, so different callers usually agree on
# exact length. 2 bp of slack absorbs the rare boundary-disagreement case.
LENGTH_TOLERANCE_BP = 2

# getITD's bundled anno/ files are hg19-based, so the tool reports
# `insertion_site_chr13_bp` in hg19 coordinates regardless of the input BAM.
# FLT3_ITD_EXT and filt3r both report hg38. We lift getITD's positions to
# hg38 for cross-caller consistency. The FLT3 locus has no rearrangement
# between builds, so a fixed offset works for this gene.
FLT3_HG19_TO_HG38_OFFSET = 28608269 - 28034132  # = 574137

# Minimum ITD length to call. filt3r occasionally reports SVLEN=1 single-bp
# dups; these are noise. 6 bp is the conventional biological floor for an
# "ITD" vs a small insertion.
MIN_ITD_LENGTH_BP = 6


# ---------------------------------------------------------------------------
# Per-caller parsers
#
# Each parser returns a list of dicts using this common schema:
#     tool, length, pos_hg38, vaf, ar, supporting_reads, total_reads,
#     inserted_seq, hgvsc, hgvsp, domain, raw_id
# Missing values are None (numeric) or "" (text). Parsers return [] for
# missing, empty, or header-only inputs.
# ---------------------------------------------------------------------------

def parse_getitd(getitd_tsv):
    """Parse the getITD high-confidence ITD TSV.

    getITD reports the same biological ITD twice when reads partially span
    it (trailing=True) vs fully span it (trailing=False). We collapse
    trailing + non-trailing entries of the same length+position so that
    getITD counts as ONE caller per biological event.
    """
    if not getitd_tsv.exists():
        sys.stderr.write(f"[consensus] getITD output not found: {getitd_tsv}\n")
        return []

    rows = []
    with open(getitd_tsv) as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for r in reader:
            try:
                length = int(r["length"])
                # getITD's vaf column is in percent (e.g. 3.4221 means 3.42%).
                vaf_pct = float(r["vaf"])
                # getITD's ar column is already a fraction (mutant/WT reads).
                ar = float(r["ar"])
                pos_hg19 = int(r["insertion_site_chr13_bp"])
            except (KeyError, ValueError) as e:
                sys.stderr.write(f"[consensus] getITD row skipped (bad fields): {e}\n")
                continue
            rows.append({
                "_length": length,
                "_pos_hg19": pos_hg19,
                "_vaf_pct": vaf_pct,
                "_ar": ar,
                "_counts": int(r.get("counts", 0)),
                "_trailing": r.get("trailing", "").strip() == "True",
                "_seq": r.get("seq", "").strip(),
                "_domain": r.get("insertion_site_domain", "").strip(),
            })

    if not rows:
        return []

    # Collapse trailing + non-trailing entries of the same length+position.
    by_key = defaultdict(list)
    for r in rows:
        by_key[(r["_length"], r["_pos_hg19"])].append(r)

    out = []
    for (length, pos_hg19), entries in by_key.items():
        # VAFs (in percent) sum across trailing/non-trailing variants of the
        # same event; convert the total to a fraction. AR is averaged
        # because it is a ratio, not a count we can sum.
        vaf_sum_pct = sum(e["_vaf_pct"] for e in entries)
        vaf_fraction = vaf_sum_pct / 100.0
        ar_mean = sum(e["_ar"] for e in entries) / len(entries)
        reads_sum = sum(e["_counts"] for e in entries)
        # Prefer the non-trailing entry's seq (full ITD); fall back to the
        # first entry if all are trailing.
        full = next((e for e in entries if not e["_trailing"]), entries[0])
        out.append({
            "tool": "getITD",
            "length": length,
            "pos_hg38": _liftover_hg19_to_hg38(pos_hg19),
            "vaf": round(vaf_fraction, 4),
            "ar": round(ar_mean, 4),
            "supporting_reads": reads_sum,
            "total_reads": None,
            "inserted_seq": full["_seq"],
            "hgvsc": "",
            "hgvsp": "",
            "domain": full["_domain"],
            "raw_id": f"getITD:{length}bp@hg19:{pos_hg19}",
        })
    return out


def parse_flt3_itd_ext(vcf):
    """Parse the FLT3_ITD_EXT VCF.

    INFO fields consumed:
        SVLEN  -- ITD length in bp
        CDS    -- HGVSc, e.g. c.1741_1785dup
        AA     -- HGVSp, e.g. p.581_595dup
        RAF    -- read allele frequency (without UMI collapse). Used as VAF.
        RAR    -- read allelic ratio (without UMI collapse). Used as AR.
        RVD    -- reads supporting variant
        RDP    -- read depth in region

    The UMI-collapsed fields (AR, AF, AAR, AAF) are zero in non-UMI
    workflows, so we use the R-prefixed (read-based) fields instead. This
    is consistent with how the production pipeline interprets the VCF.
    """
    if not vcf.exists():
        sys.stderr.write(f"[consensus] FLT3_ITD_EXT VCF not found: {vcf}\n")
        return []

    out = []
    with open(vcf) as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 8:
                continue
            pos = int(parts[1])
            ref, alt = parts[3], parts[4]
            info = _parse_vcf_info(parts[7])
            try:
                length = int(info.get("SVLEN", "0"))
            except ValueError:
                continue
            if length < MIN_ITD_LENGTH_BP:
                continue
            # The inserted sequence is everything in ALT after the REF anchor.
            inserted_seq = alt[len(ref):] if alt.startswith(ref) else alt
            out.append({
                "tool": "FLT3_ITD_EXT",
                "length": length,
                "pos_hg38": pos,
                "vaf": _safe_float(info.get("RAF")),
                "ar": _safe_float(info.get("RAR")),
                "supporting_reads": _safe_int(info.get("RVD")),
                "total_reads": _safe_int(info.get("RDP")),
                "inserted_seq": inserted_seq,
                "hgvsc": info.get("CDS", ""),
                "hgvsp": info.get("AA", ""),
                "domain": "",
                "raw_id": f"FLT3_ITD_EXT:{length}bp@hg38:{pos}",
            })
    return out


def parse_filt3r(vcf):
    """Parse the filt3r VCF.

    Keep only <DUP> SV-style records -- those are filt3r's high-confidence
    duplication calls. Lower-VAF lines with explicit ALT sequences are
    alternate representations / noise.

    INFO fields consumed: SVLEN, M (supporting reads), WT (wild-type reads),
    VAF. filt3r does not emit an AR field, so AR is left as None for filt3r
    records.
    """
    if not vcf.exists():
        sys.stderr.write(f"[consensus] filt3r VCF not found: {vcf}\n")
        return []

    out = []
    with open(vcf) as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 8:
                continue
            alt = parts[4]
            if alt != "<DUP>":
                continue
            pos = int(parts[1])
            info = _parse_vcf_info(parts[7])
            try:
                length = int(info.get("SVLEN", "0"))
            except ValueError:
                continue
            if length < MIN_ITD_LENGTH_BP:
                continue
            out.append({
                "tool": "filt3r",
                "length": length,
                "pos_hg38": pos,
                "vaf": _safe_float(info.get("VAF")),
                "ar": None,  # filt3r does not emit AR
                "supporting_reads": _safe_int(info.get("M")),
                "total_reads": _safe_int(info.get("WT")),
                "inserted_seq": "",
                "hgvsc": "",
                "hgvsp": "",
                "domain": "",
                "raw_id": f"filt3r:{length}bp@hg38:{pos}",
            })
    return out


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _liftover_hg19_to_hg38(pos_hg19):
    """Approximate FLT3-locus hg19->hg38 lift. Sufficient for cross-caller
    clustering, where the cluster key is length, not position."""
    return pos_hg19 - FLT3_HG19_TO_HG38_OFFSET


def _parse_vcf_info(info_str):
    """Parse a VCF INFO field like 'KEY1=VAL1;KEY2=VAL2;FLAG' into a dict.
    Flag-style keys (no '=' sign) map to True."""
    out = {}
    for kv in info_str.split(";"):
        if "=" in kv:
            k, v = kv.split("=", 1)
            out[k] = v
        else:
            out[kv] = True
    return out


def _safe_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _safe_int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _median(xs):
    xs = sorted(xs)
    n = len(xs)
    if n == 0:
        return ""
    if n % 2 == 1:
        return xs[n // 2]
    return (xs[n // 2 - 1] + xs[n // 2]) / 2


def _aggregate_optional_numeric(values, ndigits=4, scale=1.0):
    """Aggregate an optional-numeric field (e.g. VAF, AR) across a cluster.

    Each value is multiplied by `scale` before aggregation, so a single
    helper handles both fraction-output (scale=1.0) and percent-output
    (scale=100.0) cases without duplicating min/max/mean logic.

    Returns (min, max, mean), with blank strings where no real values exist
    in the cluster (i.e. every caller in the cluster left the field as None).
    """
    real = [v for v in values if v is not None]
    if not real:
        return "", "", ""
    real = [v * scale for v in real]
    return (
        round(min(real), ndigits),
        round(max(real), ndigits),
        round(sum(real) / len(real), ndigits),
    )


# ---------------------------------------------------------------------------
# Clustering and row building
# ---------------------------------------------------------------------------

def cluster_by_length(records, tol=LENGTH_TOLERANCE_BP):
    """Cluster records whose ITD lengths agree within `tol` bp.

    Length is the primary key because (a) all callers report it
    consistently, (b) it does not depend on genome build, and (c) ITDs of
    different lengths are biologically distinct events even at the same
    position. All records map to FLT3 by construction of the upstream
    orchestrator, so length alone is sufficient.
    """
    if not records:
        return []
    sorted_rec = sorted(records, key=lambda r: r["length"])
    clusters = []
    current = [sorted_rec[0]]
    for r in sorted_rec[1:]:
        if r["length"] - current[-1]["length"] <= tol:
            current.append(r)
        else:
            clusters.append(current)
            current = [r]
    clusters.append(current)
    return clusters


def consensus_row(cluster, sample):
    """Build a single output row from a cluster of per-caller records.

    Status rules for the 3-caller ensemble:
        3 distinct tools -> PASS_HIGH
        2 distinct tools -> PASS_LOW
        1 tool           -> REVIEW_REQUIRED
    """
    tools = sorted({r["tool"] for r in cluster})
    n_tools = len(tools)

    if n_tools >= 3:
        status = "PASS_HIGH"
    elif n_tools == 2:
        status = "PASS_LOW"
    else:
        status = "REVIEW_REQUIRED"

    lengths = [r["length"] for r in cluster]
    positions = [r["pos_hg38"] for r in cluster if r.get("pos_hg38") is not None]
    # VAF -> percent, 2 decimal places (e.g. 14.05 means 14.05%).
    vaf_pct_min, vaf_pct_max, vaf_pct_mean = _aggregate_optional_numeric(
        [r["vaf"] for r in cluster], ndigits=2, scale=100.0
    )
    # AR -> decimal fraction, 4 decimal places. AR can exceed 1.0.
    ar_min, ar_max, ar_mean = _aggregate_optional_numeric(
        [r["ar"] for r in cluster]
    )

    # Prefer FLT3_ITD_EXT's HGVS (it produces canonical "dup" notation per
    # HGVS rules). For non-HGVS fields, take the first non-empty value.
    hgvsc = next((r["hgvsc"] for r in cluster if r.get("hgvsc")), "")
    hgvsp = next((r["hgvsp"] for r in cluster if r.get("hgvsp")), "")
    domain = next((r["domain"] for r in cluster if r.get("domain")), "")
    inserted_seq = next((r["inserted_seq"] for r in cluster if r.get("inserted_seq")), "")

    return {
        "sample": sample,
        "status": status,
        "n_tools": n_tools,
        "tools": ",".join(tools),
        "length_bp": _median(lengths),
        "length_range": f"{min(lengths)}-{max(lengths)}",
        "pos_hg38": _median(positions) if positions else "",
        "vaf_pct_min": vaf_pct_min,
        "vaf_pct_max": vaf_pct_max,
        "vaf_pct_mean": vaf_pct_mean,
        "ar_min": ar_min,
        "ar_max": ar_max,
        "ar_mean": ar_mean,
        "hgvsc": hgvsc,
        "hgvsp": hgvsp,
        "domain": domain,
        "inserted_seq": inserted_seq,
        "raw_calls": " | ".join(r["raw_id"] for r in cluster),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--sample", required=True,
                   help="sample ID (used as the 'sample' column in output)")
    p.add_argument("--getitd", required=True, type=Path,
                   help="getITD high-confidence ITD TSV "
                        "(itds_collapsed-...-hc.tsv, or header-only if "
                        "the sample is FLT3-ITD negative)")
    p.add_argument("--flt3-itd-ext", required=True, type=Path,
                   dest="flt3_itd_ext",
                   help="FLT3_ITD_EXT final VCF "
                        "(<sample>.final_FLT3_ITD.vcf)")
    p.add_argument("--filt3r", required=True, type=Path,
                   help="filt3r results VCF "
                        "(<sample>_filt3r.results.vcf)")
    p.add_argument("--out", required=True, type=Path,
                   help="output consensus TSV path")
    args = p.parse_args()

    records = []
    records += parse_getitd(args.getitd)
    records += parse_flt3_itd_ext(args.flt3_itd_ext)
    records += parse_filt3r(args.filt3r)

    sys.stderr.write(f"[consensus] collected {len(records)} per-caller records\n")
    by_tool = defaultdict(int)
    for r in records:
        by_tool[r["tool"]] += 1
    for tool in ("getITD", "FLT3_ITD_EXT", "filt3r"):
        sys.stderr.write(f"[consensus]   {tool}: {by_tool[tool]}\n")

    clusters = cluster_by_length(records)
    sys.stderr.write(f"[consensus] {len(clusters)} consensus event(s) after clustering\n")

    fieldnames = [
        "sample", "status", "n_tools", "tools",
        "length_bp", "length_range", "pos_hg38",
        "vaf_pct_min", "vaf_pct_max", "vaf_pct_mean",
        "ar_min", "ar_max", "ar_mean",
        "hgvsc", "hgvsp", "domain", "inserted_seq",
        "raw_calls",
    ]

    rows = [consensus_row(c, args.sample) for c in clusters]
    # Sort by VAF descending; rows with no VAF (filt3r-only clusters where
    # filt3r's VAF was unparseable, etc.) sink to the bottom.
    rows.sort(
        key=lambda r: r["vaf_pct_mean"] if isinstance(r["vaf_pct_mean"], (int, float)) else -1,
        reverse=True,
    )

    with open(args.out, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    sys.stderr.write(f"[consensus] wrote {args.out}\n")


if __name__ == "__main__":
    main()
