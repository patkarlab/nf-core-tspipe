#!/usr/bin/env python3
"""
apply_blacklist.py
------------------
Tag variants in an annotated TSV against the leukemia panel SNV blacklist.

Variants matching a blacklist entry get FILTER=BLACKLIST.
Nothing is deleted -- the row stays in the output so downstream auditing works.

USAGE A: As a library (preferred, used by 14_variant_filter.py)
-----------------------------------------------------------------
    from apply_blacklist import load_blacklist, variant_matches_blacklist

    entries = load_blacklist("references/blacklist_file.tsv")
    hit = variant_matches_blacklist("chr17", 7846896, "C", "CACC", entries)
    if hit is not None:
        print("Blacklisted:", hit["gene"], hit["reason"])

USAGE B: As a standalone CLI (for ad-hoc filtering of an existing TSV)
----------------------------------------------------------------------
    python apply_blacklist.py \\
        --input  results/<sample>/annotation/<sample>.somaticseq.filtered.tsv \\
        --blacklist references/blacklist_file.tsv \\
        --output results/<sample>/annotation/<sample>.somaticseq.blacklisted.tsv

INPUT TSV ASSUMPTIONS:
    - Tab-separated, header row on top.
    - Default required columns: Chr, Start, Ref, Alt, Filter
      (this is the pipeline schema produced by 13_annotate.py).
    - If your TSV uses different names, edit COLMAP below.

The matcher handles the multi-representation problem for indels via
'region_indel' blacklist mode: any insertion/duplication/deletion whose
genomic span overlaps the blacklisted region matches, regardless of how
the caller left-anchored or right-anchored it.
"""

import argparse
import csv
import sys
from pathlib import Path

# ----------------------------------------------------------------------------
# Column-name mapping
# ----------------------------------------------------------------------------
# Keys are what the matcher expects; values are the actual column names in
# the input TSV. These defaults match the pipeline schema produced by
# scripts/13_annotate.py and consumed by scripts/14_variant_filter.py.
COLMAP = {
    "CHROM":  "Chr",
    "POS":    "Start",
    "REF":    "Ref",
    "ALT":    "Alt",
    "FILTER": "Filter",
}

# Tag written into the Filter column for matched variants.
BLACKLIST_TAG = "BLACKLIST"


# ----------------------------------------------------------------------------
# Blacklist loading
# ----------------------------------------------------------------------------
def load_blacklist(path):
    """
    Read the blacklist TSV and return a list of dicts, one per active entry.
    Lines starting with '#' or '##' are comments and are skipped.
    """
    entries = []
    n_candidates = 0   # non-blank, non-comment lines actually attempted (zero-entry guard)
    with open(path) as fh:
        for line_num, raw in enumerate(fh, start=1):
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            n_candidates += 1
            fields = line.split("\t")
            if len(fields) < 11:
                sys.stderr.write(
                    f"[blacklist] line {line_num}: expected 11 columns, got {len(fields)} -- skipping\n"
                )
                continue
            entry = {
                "chrom":      _normalize_chrom(fields[0]),
                "start":      int(fields[1]) if fields[1] != "." else None,
                "end":        int(fields[2]) if fields[2] != "." else None,
                "match_mode": fields[3].strip(),
                "pos_exact":  int(fields[4]) if fields[4] != "." else None,
                "ref_exact":  fields[5].strip() if fields[5] != "." else None,
                "alt_exact":  fields[6].strip() if fields[6] != "." else None,
                "gene":       fields[7].strip(),
                "reason":     fields[8].strip(),
                "evidence":   fields[9].strip(),
                "date_added": fields[10].strip(),
            }
            if entry["match_mode"] not in ("region_indel", "exact"):
                sys.stderr.write(
                    f"[blacklist] line {line_num}: unknown match_mode "
                    f"'{entry['match_mode']}' -- skipping\n"
                )
                continue
            entries.append(entry)
    # [blacklist zero-entry guard]
    # A blacklist supplied with data lines but zero parsed entries almost always
    # means a schema mismatch (e.g. the legacy 4-column Chr/Start/Ref/Alt file
    # fed to this 11-column parser), which would silently disable artefact
    # filtering. Fail loudly. An all-comment / header-only file (no data lines)
    # is still allowed through as a legitimately empty blacklist.
    if n_candidates > 0 and not entries:
        raise ValueError(
            "blacklist %s: %d data line(s) present but none parsed as valid "
            "11-column entries (expected: chrom start end match_mode pos_exact "
            "ref_exact alt_exact gene reason evidence date_added). Refusing to "
            "run with a silently-empty blacklist." % (path, n_candidates)
        )
    return entries


def _normalize_chrom(c):
    """Strip whitespace and ensure 'chr' prefix for consistent matching."""
    c = str(c).strip()
    if not c.startswith("chr"):
        c = "chr" + c
    return c


# ----------------------------------------------------------------------------
# Variant matching
# ----------------------------------------------------------------------------
def _variant_span(pos, ref, alt):
    """
    Return the (start, end) genomic span occupied by a variant, 0-based half-open.
    Lenient for indels so different left-anchored representations of the same
    event still overlap a blacklisted region.

    pos: 1-based POS from VCF/TSV
    ref, alt: REF and ALT alleles as strings

    SNV  : single position
    Insertion / duplication : span the anchor base plus one base on either side
    Deletion : span the deleted bases
    """
    pos = int(pos)
    ref_len = len(ref)
    alt_len = len(alt)
    start_0 = pos - 1  # convert to 0-based
    if ref_len == 1 and alt_len == 1:
        return start_0, start_0 + 1  # SNV
    if alt_len > ref_len:
        # insertion / duplication: pad +/- 1 for left/right-anchor tolerance
        return max(0, start_0 - 1), start_0 + ref_len + 1
    if ref_len > alt_len:
        # deletion
        return start_0, start_0 + ref_len
    # MNV / complex
    return start_0, start_0 + max(ref_len, alt_len)


def variant_matches_blacklist(chrom, pos, ref, alt, blacklist):
    """
    Return the first matching blacklist entry, or None.

    chrom: string (with or without 'chr' prefix; normalized internally)
    pos: 1-based POS (int or string convertible to int)
    ref, alt: REF and ALT alleles as strings
    blacklist: list returned by load_blacklist()
    """
    chrom = _normalize_chrom(chrom)
    try:
        pos = int(pos)
    except (ValueError, TypeError):
        return None

    ref = str(ref).strip()
    alt = str(alt).strip()

    # ANNOVAR-style orphan indels (Ref='-' or Alt='-') cannot be matched by
    # region_indel mode reliably -- skip them. Step 14's dedup already drops
    # most of these against their VEP partners.
    if ref in (".", "-") or alt in (".", "-"):
        return None

    for entry in blacklist:
        if entry["chrom"] != chrom:
            continue
        if entry["match_mode"] == "exact":
            if (
                entry["pos_exact"] == pos
                and entry["ref_exact"] == ref
                and entry["alt_exact"] == alt
            ):
                return entry
        elif entry["match_mode"] == "region_indel":
            # Only indels match region entries; SNVs in the region are NOT blacklisted.
            if len(ref) == len(alt) == 1:
                continue
            v_start, v_end = _variant_span(pos, ref, alt)
            if v_start < entry["end"] and v_end > entry["start"]:
                return entry
    return None


# ----------------------------------------------------------------------------
# Standalone CLI mode (USAGE B above)
# ----------------------------------------------------------------------------
def _append_filter(existing, tag):
    """
    Add tag to a Filter column that may already contain other tags.
    Semicolon-separated, matching VCF FILTER style.
    'PASS' is replaced (not appended) since a blacklisted variant is no longer PASS.
    """
    existing = (existing or "").strip()
    if existing in ("", ".", "PASS"):
        return tag
    if tag in existing.split(";"):
        return existing
    return existing + ";" + tag


def apply_blacklist_cli(input_path, blacklist_path, output_path):
    blacklist = load_blacklist(blacklist_path)
    sys.stderr.write(f"[blacklist] loaded {len(blacklist)} active entries\n")

    required_cols = set(COLMAP.values())
    n_total = 0
    n_matched = 0
    matches_per_entry = {}

    with open(input_path, newline="") as fin, open(output_path, "w", newline="") as fout:
        reader = csv.DictReader(fin, delimiter="\t")
        if reader.fieldnames is None:
            sys.exit(f"ERROR: {input_path} appears empty or has no header")
        missing = required_cols - set(reader.fieldnames)
        if missing:
            sys.exit(
                f"ERROR: input TSV is missing required columns: {sorted(missing)}\n"
                f"Got columns: {reader.fieldnames}\n"
                f"If column names differ, edit COLMAP at the top of apply_blacklist.py."
            )

        writer = csv.DictWriter(fout, fieldnames=reader.fieldnames, delimiter="\t")
        writer.writeheader()

        for row in reader:
            n_total += 1
            chrom = row[COLMAP["CHROM"]]
            pos = row[COLMAP["POS"]]
            ref = row[COLMAP["REF"]]
            alt = row[COLMAP["ALT"]]
            hit = variant_matches_blacklist(chrom, pos, ref, alt, blacklist)
            if hit is not None:
                n_matched += 1
                key = f"{hit['gene']}|{hit['reason']}"
                matches_per_entry[key] = matches_per_entry.get(key, 0) + 1
                row[COLMAP["FILTER"]] = _append_filter(
                    row.get(COLMAP["FILTER"], ""), BLACKLIST_TAG
                )
            writer.writerow(row)

    sys.stderr.write(f"[blacklist] processed {n_total} variants\n")
    sys.stderr.write(f"[blacklist] tagged    {n_matched} as {BLACKLIST_TAG}\n")
    for key, n in sorted(matches_per_entry.items(), key=lambda kv: -kv[1]):
        sys.stderr.write(f"[blacklist]   {n:4d}  {key}\n")


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--input", required=True, help="annotated variant TSV")
    p.add_argument("--blacklist", required=True,
                   help="blacklist TSV (e.g. references/blacklist_file.tsv)")
    p.add_argument("--output", required=True,
                   help="output TSV with Filter column updated")
    args = p.parse_args()

    if not Path(args.input).exists():
        sys.exit(f"ERROR: input file not found: {args.input}")
    if not Path(args.blacklist).exists():
        sys.exit(f"ERROR: blacklist file not found: {args.blacklist}")
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    apply_blacklist_cli(args.input, args.blacklist, args.output)


if __name__ == "__main__":
    main()
