#!/usr/bin/env python3
"""
17b_flt3_to_variants.py
-----------------------
Append FLT3-ITD consensus events to the per-sample clinical variant TSV so
the pathologist sees all clinically reportable findings in a single table.

Two things are added:

1.  A new column 'Confirmed_by_FLT3_ITD_ensemble' is populated on any
    EXISTING variant row that describes the same biological event as a
    FLT3 consensus ITD. The cell contains the comma-separated list of
    tools that confirmed it (e.g. "FLT3_ITD_EXT,filt3r,getITD").

    Match criteria, in order of preference:
      - HGVSp dup-range match (e.g. existing row p.Val581_Arg595dup matches
        consensus p.581_595dup because the (581, 595) range agrees).
      - Position + length fallback (chr13, Start within +/-5bp, length match).

2.  A new row for each PASS_HIGH / PASS_LOW FLT3 consensus ITD, populated
    with the proper duplication HGVS notation, the consensus VAF, and the
    list of supporting tools. REVIEW_REQUIRED events stay in the consensus
    TSV but are NOT promoted (report builder handles those separately).

The script also ensures a 'HGVS_ITD' column exists (proper dup notation,
empty for non-ITD rows).

Usage:
    python 17b_flt3_to_variants.py \\
        --sample-dir results/<sample> \\
        --sample <sample> \\
        --variant-tsv results/<sample>/annotation/<sample>.somaticseq.clinical.tsv \\
        [--inplace]
"""

import argparse
import csv
import re
import sys
from pathlib import Path

# Statuses from the consensus TSV that get promoted to the variant table.
PROMOTABLE_STATUSES = {"PASS_HIGH", "PASS_LOW"}

# ----------------------------------------------------------------------------
# Column names in the clinical TSV (post-step-17 VariantValidator).
# If your schema diverges, edit these constants.
# ----------------------------------------------------------------------------
COL_SAMPLE       = "Sample"
COL_CHR          = "Chr"
COL_START        = "Start"
COL_END          = "End"
COL_REF          = "Ref"
COL_ALT          = "Alt"
COL_GENE         = "Gene"
COL_CONSEQUENCE  = "Consequence"
COL_HGVSC        = "HGVSc"
COL_HGVSP        = "HGVSp"
COL_IMPACT       = "IMPACT"
COL_NUM_CALLERS  = "VariantCaller_Count"
COL_CALLERS      = "Callers"
COL_REF_COUNT    = "REF_COUNT"
COL_ALT_COUNT    = "ALT_COUNT"
COL_VAF          = "VAF_pct"
COL_VERDICT      = "SomaticSeq_Verdict"
COL_FILTER       = "Filter"

# Columns this script ensures exist; created with empty values if absent.
NEW_COL_HGVS_ITD  = "HGVS_ITD"
NEW_COL_CONFIRMED = "Confirmed_by_FLT3_ITD_ensemble"


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def read_consensus(consensus_tsv):
    """Yield FLT3 consensus rows worth promoting (PASS_HIGH or PASS_LOW)."""
    if not consensus_tsv.exists():
        sys.stderr.write(f"[17b] consensus TSV not found: {consensus_tsv}\n")
        return []
    keepers = []
    with open(consensus_tsv) as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for r in reader:
            if r.get("status", "").strip() in PROMOTABLE_STATUSES:
                keepers.append(r)
    return keepers


_DUP_RE = re.compile(r"(\d+)_[A-Za-z]*?(\d+)dup")


def extract_dup_range(hgvsp):
    """
    Pull (start_aa, end_aa) out of a HGVSp 'dup' string.
    Examples:
        'ENSP00000241453.7:p.Val581_Arg595dup' -> (581, 595)
        'p.581_595dup'                          -> (581, 595)
        'p.R595_E596insVTGSSDNEYFYVDFR'         -> None (not a dup)
    """
    if not hgvsp:
        return None
    m = _DUP_RE.search(hgvsp)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    return None


def col_idx(header, name):
    """Return index of a column in the header, or -1 if absent."""
    try:
        return header.index(name)
    except ValueError:
        return -1


def matches_existing_row(itd, row, header):
    """
    Decide whether a FLT3 consensus ITD describes the same event as an
    existing variant row. Uses HGVSp dup-range match first; falls back to
    position + length.
    """
    gene_idx = col_idx(header, COL_GENE)
    if gene_idx < 0 or gene_idx >= len(row):
        return False
    if row[gene_idx].strip() != "FLT3":
        return False

    # First-choice match: HGVSp dup ranges agree
    hgvsp_idx = col_idx(header, COL_HGVSP)
    if hgvsp_idx >= 0 and hgvsp_idx < len(row):
        itd_range = extract_dup_range(itd.get("hgvsp", ""))
        row_range = extract_dup_range(row[hgvsp_idx])
        if itd_range and row_range and itd_range == row_range:
            return True

    # Fallback: same chromosome, Start within +/- 5bp, length matches
    chr_idx   = col_idx(header, COL_CHR)
    start_idx = col_idx(header, COL_START)
    ref_idx   = col_idx(header, COL_REF)
    alt_idx   = col_idx(header, COL_ALT)
    if min(chr_idx, start_idx, ref_idx, alt_idx) < 0:
        return False
    try:
        row_chr   = row[chr_idx]
        row_start = int(row[start_idx])
        row_ref   = row[ref_idx]
        row_alt   = row[alt_idx]
    except (ValueError, IndexError):
        return False

    if row_chr != "chr13":
        return False
    try:
        itd_pos    = int(itd.get("pos_hg38", 0))
        itd_length = int(itd.get("length_bp", 0))
    except (ValueError, TypeError):
        return False
    if abs(row_start - itd_pos) > 5:
        return False
    # Indel length inferred from REF/ALT strings
    inferred_length = len(row_alt) - len(row_ref)
    return inferred_length == itd_length


def build_flt3_row(itd, sample, header):
    """Construct a new TSV row representing a FLT3 ITD consensus event."""
    try:
        length = int(itd["length_bp"])
    except (KeyError, ValueError):
        length = 0
    try:
        pos = int(itd["pos_hg38"])
    except (KeyError, ValueError):
        pos = 0
    try:
        vaf_mean = float(itd["vaf_mean"])
        vaf_pct = round(vaf_mean * 100, 2)
    except (KeyError, ValueError, TypeError):
        vaf_pct = ""

    consequence = "inframe_duplication" if length and length % 3 == 0 else "inframe_insertion"

    populated = {
        COL_SAMPLE: sample,
        COL_CHR: "chr13",
        COL_START: pos,
        COL_END: pos + length if length else pos,
        COL_REF: ".",
        COL_ALT: "<ITD>",
        COL_GENE: "FLT3",
        COL_CONSEQUENCE: consequence,
        COL_HGVSC: itd.get("hgvsc", ""),
        COL_HGVSP: itd.get("hgvsp", ""),
        COL_IMPACT: "HIGH",
        COL_NUM_CALLERS: itd.get("n_tools", ""),
        COL_CALLERS: itd.get("tools", ""),
        COL_REF_COUNT: "",
        COL_ALT_COUNT: "",
        COL_VAF: vaf_pct,
        COL_VERDICT: itd.get("status", ""),
        COL_FILTER: "PASS_FLT3_ITD",
        NEW_COL_HGVS_ITD:  itd.get("hgvsp", ""),
        NEW_COL_CONFIRMED: itd.get("tools", ""),
    }
    return [str(populated.get(col, "")) for col in header]


def ensure_column(header, body, col_name):
    """Add a column to the header (and pad every body row with '') if missing."""
    if col_name in header:
        return False
    header.append(col_name)
    for row in body:
        while len(row) < len(header) - 1:
            row.append("")
        row.append("")
    return True


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--sample-dir", required=True, help="per-sample results root")
    p.add_argument("--sample", required=True, help="sample ID")
    p.add_argument("--variant-tsv", required=True, help="clinical variant TSV from step 17")
    p.add_argument("--inplace", action="store_true",
                   help="overwrite the variant TSV in place instead of writing a .with_flt3.tsv copy")
    args = p.parse_args()

    sample_dir    = Path(args.sample_dir)
    variant_tsv   = Path(args.variant_tsv)
    consensus_tsv = sample_dir / "flt3" / f"{args.sample}_flt3_consensus.tsv"

    if not variant_tsv.exists():
        sys.exit(f"ERROR: variant TSV not found: {variant_tsv}")

    keepers = read_consensus(consensus_tsv)
    sys.stderr.write(f"[17b] promotable FLT3 consensus events: {len(keepers)}\n")

    with open(variant_tsv) as fh:
        rows = list(csv.reader(fh, delimiter="\t"))
    if not rows:
        sys.exit("ERROR: variant TSV is empty")

    header = rows[0]
    body = rows[1:]

    # Ensure both new columns exist
    if ensure_column(header, body, NEW_COL_HGVS_ITD):
        sys.stderr.write(f"[17b] added new column: {NEW_COL_HGVS_ITD}\n")
    if ensure_column(header, body, NEW_COL_CONFIRMED):
        sys.stderr.write(f"[17b] added new column: {NEW_COL_CONFIRMED}\n")

    # ------------------------------------------------------------------
    # Phase 1: tag existing rows that match a consensus ITD
    # ------------------------------------------------------------------
    confirmed_idx = header.index(NEW_COL_CONFIRMED)
    matched_count = 0
    for itd in keepers:
        for row in body:
            # Pad row up to header width so the index access is safe
            while len(row) < len(header):
                row.append("")
            if matches_existing_row(itd, row, header):
                tools_str = itd.get("tools", "").strip()
                existing = row[confirmed_idx].strip()
                if not existing:
                    row[confirmed_idx] = tools_str
                elif tools_str and tools_str not in existing:
                    row[confirmed_idx] = existing + "; " + tools_str
                matched_count += 1
    sys.stderr.write(f"[17b] tagged {matched_count} existing row(s) as confirmed by ensemble\n")

    # ------------------------------------------------------------------
    # Phase 2: append a new row for each consensus ITD
    # ------------------------------------------------------------------
    flt3_rows = [build_flt3_row(itd, args.sample, header) for itd in keepers]

    # ------------------------------------------------------------------
    # Write output
    # ------------------------------------------------------------------
    out_path = variant_tsv if args.inplace else variant_tsv.with_name(
        variant_tsv.stem + ".with_flt3.tsv"
    )
    with open(out_path, "w", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t")
        writer.writerow(header)
        for row in body:
            writer.writerow(row)
        for row in flt3_rows:
            writer.writerow(row)

    sys.stderr.write(f"[17b] wrote {out_path}\n")
    sys.stderr.write(
        f"[17b]   {len(body)} original rows ({matched_count} ensemble-confirmed) "
        f"+ {len(flt3_rows)} new FLT3 ITD rows\n"
    )


if __name__ == "__main__":
    main()
