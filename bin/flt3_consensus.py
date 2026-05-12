#!/usr/bin/env python3
"""
09b_flt3_consensus.py
---------------------
Merge per-tool FLT3-ITD calls from 09_flt3_itd.py into a single consensus
TSV. Clusters ITDs by length (the most reliable cross-tool key) and emits
one row per biological event with caller-set, VAF range, and a status tag.

Inputs are read from the standard layout produced by 09_flt3_itd.py:
    {sample_dir}/flt3/
        getitd/{sample}_getitd/itds_collapsed-is-same_is-similar_is-close_is-same_trailing_hc.tsv
        flt3_itd_ext/{sample}.final_FLT3_ITD.vcf
        filt3r/{sample}_filt3r.results.vcf
        pindel_flt3.vcf   (optional)

Output:
    {sample_dir}/flt3/{sample}_flt3_consensus.tsv

Status tags:
    PASS_HIGH         -- 3 or more tools agree
    PASS_LOW          -- 2 tools agree
    REVIEW_REQUIRED   -- 1 tool only (flag for manual IGV review)

Usage:
    python 09b_flt3_consensus.py \\
        --sample-dir results/<sample> \\
        --sample <sample>
"""

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

# Length tolerance when clustering ITDs across callers. ITDs are PCR-slippage
# resistant so different callers usually agree on exact length; 2bp slack
# absorbs the rare boundary-disagreement case.
LENGTH_TOLERANCE_BP = 2


# ----------------------------------------------------------------------------
# Per-tool parsers
# Each returns a list of dicts with keys: tool, length, pos_hg38, vaf,
# supporting_reads, total_reads, inserted_seq, hgvsc, hgvsp, domain, raw_id
# Missing fields are empty string or None.
# ----------------------------------------------------------------------------

def parse_getitd(getitd_tsv):
    """
    Parse the getITD high-confidence ITD TSV. Handles the trailing/non-trailing
    split: getITD reports the same ITD twice when reads partially span it
    (trailing=True, partial sequence) vs fully span it (trailing=False). We
    sum their VAFs so getITD counts as ONE caller per biological event.
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
                vaf = float(r["vaf"])  # getITD reports VAF as percent
                pos_hg19 = int(r["insertion_site_chr13_bp"])
            except (KeyError, ValueError) as e:
                sys.stderr.write(f"[consensus] getITD row skipped (bad fields): {e}\n")
                continue
            rows.append({
                "_length": length,
                "_pos_hg19": pos_hg19,
                "_vaf_pct": vaf,
                "_counts": int(r.get("counts", 0)),
                "_trailing": r.get("trailing", "").strip() == "True",
                "_seq": r.get("seq", "").strip(),
                "_domain": r.get("insertion_site_domain", "").strip(),
                "_protein_as": r.get("insertion_site_protein_as", "").strip(),
            })

    # Collapse trailing + non-trailing entries of the same length+position
    by_key = defaultdict(list)
    for r in rows:
        by_key[(r["_length"], r["_pos_hg19"])].append(r)

    out = []
    for (length, pos_hg19), entries in by_key.items():
        vaf_sum = sum(e["_vaf_pct"] for e in entries) / 100.0  # to fraction
        reads_sum = sum(e["_counts"] for e in entries)
        # Pick the non-trailing entry's sequence (full ITD seq) if present
        full = next((e for e in entries if not e["_trailing"]), entries[0])
        out.append({
            "tool": "getITD",
            "length": length,
            "pos_hg38": liftover_hg19_to_hg38_flt3(pos_hg19),
            "vaf": round(vaf_sum, 4),
            "supporting_reads": reads_sum,
            "total_reads": None,
            "inserted_seq": full["_seq"],
            "hgvsc": "",
            "hgvsp": "",  # getITD doesn't emit proper HGVS; protein info goes in `domain`
            "domain": full["_domain"],
            "raw_id": f"getITD:{length}bp@hg19:{pos_hg19}",
        })
    return out


def parse_flt3_itd_ext(vcf):
    """
    Parse the FLT3_ITD_EXT VCF. INFO fields of interest:
      SVLEN  - ITD length (bp)
      CDS    - HGVSc, e.g. c.1741_1785dup
      AA     - HGVSp, e.g. p.581_595dup
      RAF    - read allele frequency (without UMI collapse) -- our VAF metric
      RVD    - reads supporting variant
      RDP    - read depth in region
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
            chrom, pos, _id, ref, alt = parts[0], int(parts[1]), parts[2], parts[3], parts[4]
            info = dict(kv.split("=", 1) for kv in parts[7].split(";") if "=" in kv)
            try:
                length = int(info.get("SVLEN", "0"))
            except ValueError:
                continue
            if length == 0:
                continue
            # The inserted seq is everything in ALT after the REF anchor base.
            inserted_seq = alt[len(ref):] if alt.startswith(ref) else alt
            out.append({
                "tool": "FLT3_ITD_EXT",
                "length": length,
                "pos_hg38": pos,
                "vaf": _safe_float(info.get("RAF")),
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
    """
    Parse the filt3r VCF. We only keep the <DUP> SV-style records -- those
    are filt3r's high-confidence duplication calls. The lower-VAF lines with
    explicit ALT sequences are alternate representations / noise.
    INFO fields: SVLEN, M (supporting reads), WT (wild-type reads), VAF.
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
            alt = parts[4]
            if alt != "<DUP>":
                continue
            chrom, pos = parts[0], int(parts[1])
            info = dict(kv.split("=", 1) for kv in parts[7].split(";") if "=" in kv)
            try:
                length = int(info.get("SVLEN", "0"))
            except ValueError:
                continue
            if length < 6:  # filt3r reports SVLEN=1 single-bp dup noise; suppress
                continue
            out.append({
                "tool": "filt3r",
                "length": length,
                "pos_hg38": pos,
                "vaf": _safe_float(info.get("VAF")),
                "supporting_reads": _safe_int(info.get("M")),
                "total_reads": _safe_int(info.get("WT")),
                "inserted_seq": "",
                "hgvsc": "",
                "hgvsp": "",
                "domain": "",
                "raw_id": f"filt3r:{length}bp@hg38:{pos}",
            })
    return out


def parse_pindel(vcf):
    """
    Parse a Pindel VCF, filtered upstream to the FLT3 region. We keep DUP
    and INS events of length >= 6bp.
    """
    if vcf is None or not vcf.exists():
        return []
    out = []
    with open(vcf) as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.rstrip("\n").split("\t")
            chrom, pos, _id, ref, alt = parts[0], int(parts[1]), parts[2], parts[3], parts[4]
            info = dict(kv.split("=", 1) for kv in parts[7].split(";") if "=" in kv)
            svtype = info.get("SVTYPE", "")
            if svtype not in ("DUP", "INS"):
                continue
            length_str = info.get("SVLEN", "0").lstrip("+-")
            try:
                length = abs(int(length_str))
            except ValueError:
                length = abs(len(alt) - len(ref))
            if length < 6:
                continue
            # Pindel VAF derivation depends on FORMAT/AD; we'll do a best effort.
            vaf = _pindel_vaf_from_format(parts)
            out.append({
                "tool": "Pindel",
                "length": length,
                "pos_hg38": pos,
                "vaf": vaf,
                "supporting_reads": None,
                "total_reads": None,
                "inserted_seq": alt[len(ref):] if alt.startswith(ref) else alt,
                "hgvsc": "",
                "hgvsp": "",
                "domain": "",
                "raw_id": f"Pindel:{length}bp@hg38:{pos}",
            })
    return out


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

# FLT3 hg19 -> hg38 lift. The FLT3 locus has no rearrangement between builds,
# so a fixed offset works for this gene. The offset is hg19_pos - hg38_pos.
FLT3_HG19_TO_HG38_OFFSET = 28608269 - 28034132  # = 574137


def liftover_hg19_to_hg38_flt3(pos_hg19):
    """Approximate FLT3-locus lift. Adequate for cross-caller clustering only."""
    return pos_hg19 - FLT3_HG19_TO_HG38_OFFSET


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


def _pindel_vaf_from_format(parts):
    """Best-effort VAF from a Pindel VCF FORMAT field. Returns None if not computable."""
    if len(parts) < 10:
        return None
    fmt_keys = parts[8].split(":")
    sample_vals = parts[9].split(":")
    fmt = dict(zip(fmt_keys, sample_vals))
    ad = fmt.get("AD")
    if ad and "," in ad:
        try:
            ref_n, alt_n = (int(x) for x in ad.split(",")[:2])
            total = ref_n + alt_n
            return round(alt_n / total, 4) if total else None
        except ValueError:
            return None
    return None


# ----------------------------------------------------------------------------
# Clustering
# ----------------------------------------------------------------------------

def cluster_by_length(records, tol=LENGTH_TOLERANCE_BP):
    """
    Cluster records whose ITD lengths agree within `tol` bp.

    We use length as the primary key because (a) all callers report it
    consistently, (b) it does not depend on genome build, and (c) ITDs of
    different lengths are biologically distinct events even at the same
    position. Within a cluster we also assert all records map to FLT3
    (true by construction of the orchestrator), so length alone is
    sufficient.

    Returns a list of clusters; each cluster is a list of records.
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
    """Build a single output row from a cluster of caller-records."""
    tools = sorted({r["tool"] for r in cluster})
    n_tools = len(tools)
    # Per-tool counts (so we know if getITD contributed once or twice etc.)
    per_tool_calls = defaultdict(list)
    for r in cluster:
        per_tool_calls[r["tool"]].append(r)

    if n_tools >= 3:
        status = "PASS_HIGH"
    elif n_tools == 2:
        status = "PASS_LOW"
    else:
        status = "REVIEW_REQUIRED"

    # Aggregate numerics
    lengths = [r["length"] for r in cluster]
    positions = [r["pos_hg38"] for r in cluster if r.get("pos_hg38") is not None]
    vafs = [r["vaf"] for r in cluster if r.get("vaf") is not None]

    # Prefer FLT3_ITD_EXT's HGVS (it produces proper "dup" notation per HGVS rules)
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
        "vaf_min": round(min(vafs), 4) if vafs else "",
        "vaf_max": round(max(vafs), 4) if vafs else "",
        "vaf_mean": round(sum(vafs) / len(vafs), 4) if vafs else "",
        "hgvsc": hgvsc,
        "hgvsp": hgvsp,
        "domain": domain,
        "inserted_seq": inserted_seq,
        "raw_calls": " | ".join(r["raw_id"] for r in cluster),
    }


def _median(xs):
    xs = sorted(xs)
    n = len(xs)
    if n == 0:
        return ""
    if n % 2 == 1:
        return xs[n // 2]
    return (xs[n // 2 - 1] + xs[n // 2]) / 2


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--sample-dir", required=True, help="per-sample results root (contains flt3/)")
    p.add_argument("--sample", required=True, help="sample ID")
    args = p.parse_args()

    flt3_dir = Path(args.sample_dir) / "flt3"
    if not flt3_dir.exists():
        sys.exit(f"ERROR: flt3/ subdir not found under {args.sample_dir}")

    getitd_tsv = (
        flt3_dir / "getitd" / f"{args.sample}_getitd"
        / "itds_collapsed-is-same_is-similar_is-close_is-same_trailing_hc.tsv"
    )
    flt3_itd_ext_vcf = flt3_dir / "flt3_itd_ext" / f"{args.sample}.final_FLT3_ITD.vcf"
    # filt3r names its VCF based on the --out json path; we pass <sample>_filt3r.results.json
    # which results in <sample>_filt3r.results.vcf.
    filt3r_vcf = flt3_dir / "filt3r" / f"{args.sample}_filt3r.results.vcf"
    pindel_vcf = flt3_dir / "pindel_flt3.vcf"

    records = []
    records += parse_getitd(getitd_tsv)
    records += parse_flt3_itd_ext(flt3_itd_ext_vcf)
    records += parse_filt3r(filt3r_vcf)
    records += parse_pindel(pindel_vcf if pindel_vcf.exists() else None)

    sys.stderr.write(f"[consensus] collected {len(records)} per-caller records\n")
    by_tool = defaultdict(int)
    for r in records:
        by_tool[r["tool"]] += 1
    for tool, n in sorted(by_tool.items()):
        sys.stderr.write(f"[consensus]   {tool}: {n}\n")

    clusters = cluster_by_length(records)
    sys.stderr.write(f"[consensus] {len(clusters)} consensus event(s) after clustering\n")

    out_path = flt3_dir / f"{args.sample}_flt3_consensus.tsv"
    fieldnames = [
        "sample", "status", "n_tools", "tools",
        "length_bp", "length_range", "pos_hg38",
        "vaf_min", "vaf_max", "vaf_mean",
        "hgvsc", "hgvsp", "domain", "inserted_seq",
        "raw_calls",
    ]
    with open(out_path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        # Sort consensus rows by VAF desc, with no-vaf at the bottom
        rows = [consensus_row(c, args.sample) for c in clusters]
        rows.sort(key=lambda r: (r["vaf_mean"] if isinstance(r["vaf_mean"], (int, float)) else -1), reverse=True)
        for row in rows:
            writer.writerow(row)
    sys.stderr.write(f"[consensus] wrote {out_path}\n")


if __name__ == "__main__":
    main()
