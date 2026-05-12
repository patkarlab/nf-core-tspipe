#!/usr/bin/env python3
"""
14_variant_filter.py - Clean, deduplicate, and filter annotated somatic variants
for clinical reporting.

Input:  results/{sample}/annotation/{sample}.somaticseq.annotated.tsv
Output: results/{sample}/annotation/{sample}.somaticseq.filtered.tsv   (all + Filter col)
        results/{sample}/annotation/{sample}.somaticseq.clinical.tsv   (PASS only)

Workflow:
  1. Investigate & report VariantCaller_Count = -1 rows (ANNOVAR orphans)
  2. Deduplicate: same position + same gene keeps best-annotated row
  3. Apply SNV blacklist (if --blacklist supplied): tag known recurrent
     artifacts in a Blacklist_Reason column.
  4. Flag overlapping variants for manual review (Dedup_Note)
  5. Apply clinical filters -> Filter column (BLACKLIST is priority 0)
  6. Sanity checks on known variants
"""

import argparse
import logging
import os
import sys

import pandas as pd
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PIPELINE_DIR = os.path.dirname(SCRIPT_DIR)

# Allow importing sibling scripts (apply_blacklist) regardless of CWD
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

MISSING = "-1"


def parse_args():
    ap = argparse.ArgumentParser(description="Filter annotated variants for clinical reporting.")
    ap.add_argument("-s", "--sample", required=True)
    ap.add_argument("-o", "--outdir", default=None,
                    help="Output directory (default: results/{sample}/annotation)")
    ap.add_argument("--blacklist", default=None,
                    help="Path to SNV blacklist TSV (e.g. references/blacklist_snvs_hg38.tsv). "
                         "If omitted or missing, the blacklist step is skipped.")
    return ap.parse_args()


def safe_float(val, default=np.nan):
    """Convert a value to float, treating -1 and empty strings as NaN."""
    if val is None or str(val).strip() in ("", "-1", ".", "nan", "NA"):
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def safe_int(val, default=-1):
    """Convert a value to int, treating -1 and empty strings as -1."""
    if val is None or str(val).strip() in ("", "-1", ".", "nan", "NA"):
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def is_missing(val):
    """Check if a value is missing/placeholder."""
    return val is None or str(val).strip() in ("", "-1", ".", "nan", "NA")


def count_non_missing(row):
    """Count non-missing fields in a row."""
    return sum(1 for v in row if not is_missing(v))


# ---------------------------------------------------------------------------
# Step 1: Investigate -1 rows
# ---------------------------------------------------------------------------

def investigate_minus1(df):
    """Report on rows where VariantCaller_Count = -1."""
    mask = df["VariantCaller_Count"].astype(str).str.strip() == "-1"
    n_minus1 = mask.sum()
    total = len(df)

    log.info("=" * 70)
    log.info("INVESTIGATION: VariantCaller_Count = -1 rows")
    log.info("=" * 70)
    log.info("Total rows: %d", total)
    log.info("Rows with VariantCaller_Count = -1: %d (%.1f%%)", n_minus1, 100 * n_minus1 / total)

    if n_minus1 == 0:
        log.info("No -1 rows found.")
        return

    minus1_df = df[mask].copy()

    # Check what these rows look like
    has_consequence = minus1_df["Consequence"].astype(str).str.strip() != "-1"
    has_hgvsc = minus1_df["HGVSc"].astype(str).str.strip() != "-1"
    has_gene = minus1_df["Gene"].astype(str).str.strip() != "-1"
    has_rsid = minus1_df["rsID"].astype(str).str.strip() != "-1"
    has_clinvar = minus1_df["ClinVar"].astype(str).str.strip() != "-1"

    log.info("")
    log.info("Annotation completeness of -1 rows:")
    log.info("  Has Gene:        %d / %d", has_gene.sum(), n_minus1)
    log.info("  Has Consequence:  %d / %d", has_consequence.sum(), n_minus1)
    log.info("  Has HGVSc:        %d / %d", has_hgvsc.sum(), n_minus1)
    log.info("  Has rsID:         %d / %d", has_rsid.sum(), n_minus1)
    log.info("  Has ClinVar:      %d / %d", has_clinvar.sum(), n_minus1)

    # Check for indel representation differences
    log.info("")
    log.info("Ref/Alt patterns in -1 rows:")
    ref_is_dash = minus1_df["Ref"].astype(str).str.strip() == "-"
    alt_is_dash = minus1_df["Alt"].astype(str).str.strip() == "-"
    log.info("  Ref = '-' (insertion):  %d", ref_is_dash.sum())
    log.info("  Alt = '-' (deletion):   %d", alt_is_dash.sum())
    log.info("  Both SNV-like:          %d", (~ref_is_dash & ~alt_is_dash).sum())

    # Check how many have a properly-annotated duplicate at same position
    n_has_dup = 0
    for _, row in minus1_df.iterrows():
        key = f"{row['Chr']}:{row['Start']}:{row['Gene']}"
        same_pos = df[(df["Chr"] == row["Chr"]) &
                      (df["Start"].astype(str) == str(row["Start"])) &
                      (df["Gene"] == row["Gene"]) &
                      (df["VariantCaller_Count"].astype(str).str.strip() != "-1")]
        if len(same_pos) > 0:
            n_has_dup += 1
    log.info("")
    log.info("Have annotated duplicate at same Chr:Start:Gene: %d / %d", n_has_dup, n_minus1)

    # Show a few examples
    log.info("")
    log.info("Example -1 rows (first 5):")
    for i, (_, row) in enumerate(minus1_df.head(5).iterrows()):
        log.info("  %s:%s %s>%s %s  Csq=%s  rsID=%s  ClinVar=%s",
                 row["Chr"], row["Start"], row["Ref"], row["Alt"],
                 row["Gene"], row["Consequence"], row["rsID"], row["ClinVar"])

    log.info("")
    log.info("CONCLUSION: These %d rows are ANNOVAR-only orphan alleles - indel", n_minus1)
    log.info("representations (Ref='-' or Alt='-') that failed VEP coordinate matching.")
    log.info("Most have a properly-annotated VEP duplicate at the same position.")
    log.info("They will be removed during deduplication.")


# ---------------------------------------------------------------------------
# Step 2: Deduplication
# ---------------------------------------------------------------------------

def _is_orphan_indel(row):
    """Check if a row is an ANNOVAR-style orphan indel (Ref='-' or Alt='-')."""
    ref = str(row["Ref"]).strip()
    alt = str(row["Alt"]).strip()
    return ref == "-" or alt == "-"


def deduplicate(df):
    """Remove duplicate variants at same genomic position + gene.

    Strategy:
      - ANNOVAR orphan indels (Ref='-' or Alt='-') with no VEP annotation are
        matched to VEP-annotated rows at the same Chr:Start:Gene and dropped.
      - For remaining rows, group by Chr:Start:Ref:Alt:Gene (exact allele match)
        and keep the best-annotated row per group.
      - Multi-allelic sites (different Alt at same position) are kept as separate rows.
    """
    log.info("")
    log.info("=" * 70)
    log.info("DEDUPLICATION")
    log.info("=" * 70)

    n_before = len(df)
    df = df.copy()

    # Score each row by annotation completeness
    df["_has_vep"] = df["HGVSc"].apply(lambda v: 0 if is_missing(v) else 1)
    df["_has_callers"] = df["VariantCaller_Count"].apply(lambda v: 0 if str(v).strip() == "-1" else 1)
    df["_n_filled"] = df.apply(lambda row: count_non_missing(row), axis=1)
    df["_score"] = df["_has_vep"] * 1000 + df["_has_callers"] * 100 + df["_n_filled"]
    df["_is_orphan"] = df.apply(_is_orphan_indel, axis=1)

    # Phase 1: Remove ANNOVAR orphan indels that have a VEP-annotated partner
    # at the same Chr:Start:Gene
    pos_key = df["Chr"].astype(str) + ":" + df["Start"].astype(str) + ":" + df["Gene"].astype(str)
    df["_pos_key"] = pos_key

    # Find position keys that have at least one VEP-annotated row
    vep_pos_keys = set(df.loc[df["_has_vep"] == 1, "_pos_key"].unique())

    # Drop orphans that have a VEP partner
    orphan_mask = df["_is_orphan"] & df["_pos_key"].isin(vep_pos_keys) & (df["_has_vep"] == 0)
    n_orphans_with_partner = orphan_mask.sum()
    df = df[~orphan_mask].copy()
    log.info("Orphan indels with VEP partner removed: %d", n_orphans_with_partner)

    # Phase 2: For remaining rows, dedup by exact allele (Chr:Start:Ref:Alt:Gene)
    df["_dedup_key"] = (df["Chr"].astype(str) + ":" + df["Start"].astype(str) + ":" +
                        df["Ref"].astype(str) + ":" + df["Alt"].astype(str) + ":" +
                        df["Gene"].astype(str))

    keep_idx = []
    n_groups_deduped = 0
    for key, group in df.groupby("_dedup_key"):
        if len(group) == 1:
            keep_idx.append(group.index[0])
        else:
            n_groups_deduped += 1
            best = group.sort_values("_score", ascending=False).iloc[0]
            keep_idx.append(best.name)

    df_deduped = df.loc[keep_idx].copy()
    df_deduped.drop(columns=["_has_vep", "_has_callers", "_n_filled", "_score",
                              "_is_orphan", "_pos_key", "_dedup_key"],
                    inplace=True)
    df_deduped.reset_index(drop=True, inplace=True)

    n_after = len(df_deduped)
    n_removed = n_before - n_after
    log.info("Exact-allele duplicate groups: %d", n_groups_deduped)
    log.info("Input rows:       %d", n_before)
    log.info("Rows removed:     %d (orphan: %d, exact-dup: %d)",
             n_removed, n_orphans_with_partner, n_removed - n_orphans_with_partner)
    log.info("Output rows:      %d", n_after)

    return df_deduped


# ---------------------------------------------------------------------------
# Step 2a: SNV blacklist (NEW)
# ---------------------------------------------------------------------------

def apply_snv_blacklist(df, blacklist_path):
    """
    Tag variants matching the SNV blacklist with a non-empty Blacklist_Reason.
    The Filter column gets set to 'BLACKLIST' later in apply_filters().

    Adds two columns to df:
      - Blacklist_Reason : 'gene|reason|<evidence-first-80-chars>' or '' if no match
      - Blacklist_Date   : date_added from the matching entry, or '' if no match
    """
    log.info("")
    log.info("=" * 70)
    log.info("SNV BLACKLIST")
    log.info("=" * 70)

    df = df.copy()
    # Default to empty so downstream apply_filters() always sees the columns
    df["Blacklist_Reason"] = ""
    df["Blacklist_Date"] = ""

    if not blacklist_path:
        log.info("No --blacklist supplied; skipping.")
        return df
    if not os.path.isfile(blacklist_path):
        log.warning("Blacklist file not found: %s -- skipping.", blacklist_path)
        return df

    # Import lazily so the module is optional
    try:
        from apply_blacklist import load_blacklist, variant_matches_blacklist
    except ImportError as e:
        log.warning("Could not import apply_blacklist (%s) -- skipping.", e)
        return df

    blacklist = load_blacklist(blacklist_path)
    log.info("Loaded %d active blacklist entries from %s",
             len(blacklist), blacklist_path)
    if not blacklist:
        return df

    n_matched = 0
    matches_per_entry = {}
    for idx, row in df.iterrows():
        hit = variant_matches_blacklist(
            row["Chr"], row["Start"], row["Ref"], row["Alt"], blacklist
        )
        if hit is None:
            continue
        n_matched += 1
        df.at[idx, "Blacklist_Reason"] = (
            f"{hit['gene']}|{hit['reason']}|{hit['evidence'][:80]}"
        )
        df.at[idx, "Blacklist_Date"] = hit["date_added"]
        key = f"{hit['gene']}|{hit['reason']}"
        matches_per_entry[key] = matches_per_entry.get(key, 0) + 1

    log.info("Tagged %d variant(s) as blacklisted", n_matched)
    for key, n in sorted(matches_per_entry.items(), key=lambda kv: -kv[1]):
        log.info("  %4d  %s", n, key)

    return df


# ---------------------------------------------------------------------------
# Step 2b: Flag likely-duplicate variants for manual review
# ---------------------------------------------------------------------------

def flag_overlapping_variants(df):
    """Flag pairs of variants in the same gene within 10bp that are likely
    the same genomic event with ambiguous breakpoints.

    Strict criteria to avoid flagging unrelated nearby SNVs:
      - Same gene, within 10bp
      - At least one must be an indel (not two independent SNVs)
      - Identical caller set (not just overlapping)
      - Same VAF (+/- 2 percentage points)
      - Same ALT_COUNT (+/- 20% relative) - the strongest signal of a shared event

    Adds a Dedup_Note column.
    """
    log.info("")
    log.info("=" * 70)
    log.info("OVERLAPPING VARIANT DETECTION")
    log.info("=" * 70)

    df = df.copy()
    df["Dedup_Note"] = ""

    # Parse fields for comparison
    starts = df["Start"].apply(lambda v: safe_int(v, default=-1))
    vafs = df["VAF_pct"].apply(safe_float)
    alt_counts = df["ALT_COUNT"].apply(lambda v: safe_int(v, default=-1))
    genes = df["Gene"].astype(str)
    callers_col = df["Callers"].astype(str)
    refs = df["Ref"].astype(str)
    alts = df["Alt"].astype(str)

    def _is_indel(ref, alt):
        return len(ref) != len(alt) or ref == "-" or alt == "-"

    n_flagged = 0
    flagged_pairs = []

    for i in range(len(df)):
        if starts.iloc[i] < 0:
            continue
        for j in range(i + 1, len(df)):
            if starts.iloc[j] < 0:
                continue
            # Same gene?
            if genes.iloc[i] != genes.iloc[j]:
                continue
            # Within 10bp?
            if abs(starts.iloc[i] - starts.iloc[j]) > 10:
                continue
            # At least one must be an indel
            is_indel_i = _is_indel(refs.iloc[i], alts.iloc[i])
            is_indel_j = _is_indel(refs.iloc[j], alts.iloc[j])
            if not is_indel_i and not is_indel_j:
                continue
            # Identical caller set (not just overlapping)
            callers_i = set(callers_col.iloc[i].split(",")) - {"-1", ""}
            callers_j = set(callers_col.iloc[j].split(",")) - {"-1", ""}
            if not callers_i or not callers_j:
                continue
            if callers_i != callers_j:
                continue
            # Same VAF (+/- 2 percentage points)
            vaf_i, vaf_j = vafs.iloc[i], vafs.iloc[j]
            if np.isnan(vaf_i) or np.isnan(vaf_j):
                continue
            if abs(vaf_i - vaf_j) > 2.0:
                continue
            # Same ALT_COUNT (+/- 20% relative)
            ac_i, ac_j = alt_counts.iloc[i], alt_counts.iloc[j]
            if ac_i > 0 and ac_j > 0:
                ac_mean = (ac_i + ac_j) / 2
                if abs(ac_i - ac_j) / ac_mean > 0.20:
                    continue

            # Flag both rows
            gene = genes.iloc[i]
            csq_i = str(df.iloc[i]["Consequence"])
            note = (f"MANUAL_REVIEW: overlapping {csq_i.split('&')[0].replace('_', ' ')}s "
                    f"in {gene}, same VAF/callers, likely single event - "
                    f"verify exact breakpoints in IGV")

            idx_i = df.index[i]
            idx_j = df.index[j]
            df.at[idx_i, "Dedup_Note"] = note
            df.at[idx_j, "Dedup_Note"] = note
            n_flagged += 1
            flagged_pairs.append((gene, str(df.iloc[i]["HGVSc"]), str(df.iloc[j]["HGVSc"]),
                                  vaf_i, vaf_j, ac_i, ac_j))

    if flagged_pairs:
        log.info("Flagged %d variant pair(s) for manual review:", n_flagged)
        for gene, hgvsc_a, hgvsc_b, vaf_a, vaf_b, ac_a, ac_b in flagged_pairs:
            log.info("  %s: %s (VAF=%.1f%%, ALT=%d) <-> %s (VAF=%.1f%%, ALT=%d)",
                     gene, hgvsc_a[:40], vaf_a, ac_a, hgvsc_b[:40], vaf_b, ac_b)
    else:
        log.info("No overlapping variant pairs found.")

    return df


# ---------------------------------------------------------------------------
# Step 3: Filtering
# ---------------------------------------------------------------------------

def apply_filters(df):
    """Add Filter column based on clinical filtering criteria.

    Filter values (applied in priority order):
      BLACKLIST:           Blacklist_Reason is non-empty (known recurrent artifact)
      COMMON_POLYMORPHISM: Max_AF > 0.01
      LOW_IMPACT:          IMPACT == "MODIFIER" and not in splice region
      LOW_CALLERS:         VariantCaller_Count < 2
      LOW_DEPTH:           ALT_COUNT < 10
      PASS:                everything else
    """
    log.info("")
    log.info("=" * 70)
    log.info("FILTERING")
    log.info("=" * 70)

    df = df.copy()

    # Parse numeric fields
    df["_max_af"] = df["Max_AF"].apply(safe_float)
    df["_caller_count"] = df["VariantCaller_Count"].apply(safe_int)
    df["_vaf"] = df["VAF_pct"].apply(safe_float)
    df["_alt_count"] = df["ALT_COUNT"].apply(safe_int)
    df["_impact"] = df["IMPACT"].astype(str).str.strip()
    df["_consequence"] = df["Consequence"].astype(str).str.strip()

    # Ensure Blacklist_Reason exists (zero-impact if apply_snv_blacklist already ran)
    if "Blacklist_Reason" not in df.columns:
        df["Blacklist_Reason"] = ""

    filters = []
    for _, row in df.iterrows():
        # Priority 0: BLACKLIST (known recurrent artifact). Highest precedence;
        # overrides all other filter logic.
        if str(row.get("Blacklist_Reason", "")).strip():
            filters.append("BLACKLIST")
            continue

        # Check if this is a U2AF1 hotspot (exempt from LOW_CALLERS/LOW_DEPTH)
        _is_u2af1_hotspot = False
        if str(row.get("Gene", "")).strip() == "U2AF1":
            hgvsp = str(row.get("HGVSp", "")).strip()
            if "Ser34" in hgvsp or "S34" in hgvsp or "Gln157" in hgvsp or "Q157" in hgvsp:
                _is_u2af1_hotspot = True

        # Priority 1: Common polymorphism
        if not np.isnan(row["_max_af"]) and row["_max_af"] > 0.01:
            filters.append("COMMON_POLYMORPHISM")
            continue

        # Priority 2: Low impact (MODIFIER, not splice)
        if row["_impact"] == "MODIFIER":
            csq = row["_consequence"].lower()
            if "splice" not in csq:
                filters.append("LOW_IMPACT")
                continue

        # Priority 3: Low callers (single-caller variants unreliable)
        # U2AF1 hotspots exempt - pileup rescue uses non-standard caller
        caller_count = row["_caller_count"]
        if caller_count >= 0 and caller_count < 2 and not _is_u2af1_hotspot:
            filters.append("LOW_CALLERS")
            continue

        # Priority 4: Low depth (insufficient alt reads)
        # U2AF1 hotspots exempt - depth may be split across paralog loci
        alt_count = row["_alt_count"]
        if alt_count >= 0 and alt_count < 10 and not _is_u2af1_hotspot:
            filters.append("LOW_DEPTH")
            continue

        # Priority 5: Rows with no caller info at all (-1) that survived dedup
        if caller_count < 0 and not _is_u2af1_hotspot:
            filters.append("NO_CALLER_INFO")
            continue

        filters.append("PASS")

    df["Filter"] = filters

    # Drop helper columns
    df.drop(columns=["_max_af", "_caller_count", "_vaf", "_alt_count",
                      "_impact", "_consequence"], inplace=True)

    # Report filter counts
    counts = df["Filter"].value_counts()
    log.info("Filter results:")
    for filt in ["PASS", "BLACKLIST", "COMMON_POLYMORPHISM", "LOW_IMPACT",
                 "LOW_CALLERS", "LOW_DEPTH", "NO_CALLER_INFO"]:
        n = counts.get(filt, 0)
        log.info("  %-25s %d", filt, n)
    log.info("  %-25s %d", "TOTAL", len(df))

    return df


# ---------------------------------------------------------------------------
# Step 4: Sanity checks
# ---------------------------------------------------------------------------

def sanity_checks(df):
    """Verify expected variants and report HIGH impact variants."""
    log.info("")
    log.info("=" * 70)
    log.info("SANITY CHECKS")
    log.info("=" * 70)

    # Check WT1 frameshift
    wt1 = df[(df["Gene"] == "WT1") & (df["HGVSp"].astype(str).str.contains("Phe408", na=False))]
    if not wt1.empty:
        filt = wt1.iloc[0]["Filter"]
        vaf = wt1.iloc[0]["VAF_pct"]
        callers = wt1.iloc[0]["Callers"]
        log.info("WT1 p.Phe408IlefsTer3: Filter=%s  VAF=%s  Callers=%s", filt, vaf, callers)
        if filt == "PASS":
            log.info("  -> OK: WT1 frameshift is PASS")
        else:
            log.warning("  -> UNEXPECTED: WT1 frameshift is %s (expected PASS)", filt)
    else:
        log.warning("WT1 frameshift p.Phe408IlefsTer3 NOT FOUND in data")

    # Check DDX3X stop_gained
    ddx3x = df[(df["Gene"] == "DDX3X") & (df["HGVSp"].astype(str).str.contains("Cys175Ter", na=False))]
    if not ddx3x.empty:
        filt = ddx3x.iloc[0]["Filter"]
        vaf = ddx3x.iloc[0]["VAF_pct"]
        alt_count = ddx3x.iloc[0]["ALT_COUNT"]
        callers = ddx3x.iloc[0]["Callers"]
        log.info("DDX3X p.Cys175Ter: Filter=%s  VAF=%s  ALT_COUNT=%s  Callers=%s",
                 filt, vaf, alt_count, callers)
        if filt == "PASS":
            log.info("  -> OK: DDX3X stop_gained is PASS")
        else:
            log.warning("  -> NOTE: DDX3X stop_gained is %s (ALT_COUNT=%s)", filt, alt_count)
    else:
        log.warning("DDX3X stop_gained p.Cys175Ter NOT FOUND in data")

    # Check common polymorphisms filtered
    common = df[(df["Filter"] == "COMMON_POLYMORPHISM")]
    if not common.empty:
        max_afs = common["Max_AF"].apply(safe_float)
        very_common = (max_afs > 0.5).sum()
        log.info("Common polymorphisms filtered: %d total, %d with Max_AF > 0.5",
                 len(common), very_common)
    else:
        log.info("No common polymorphisms filtered (unexpected)")

    # Report blacklisted variants
    blacklisted = df[df["Filter"] == "BLACKLIST"]
    if not blacklisted.empty:
        log.info("")
        log.info("BLACKLISTED variants (%d):", len(blacklisted))
        for _, row in blacklisted.iterrows():
            log.info("  %s:%s %s>%s %s  %s  Reason: %s",
                     row["Chr"], row["Start"],
                     str(row["Ref"])[:10], str(row["Alt"])[:10],
                     row["Gene"], str(row["HGVSp"])[:30],
                     str(row.get("Blacklist_Reason", ""))[:80])

    # Print all HIGH impact variants
    log.info("")
    log.info("ALL HIGH IMPACT VARIANTS:")
    log.info("-" * 120)
    high = df[df["IMPACT"].astype(str).str.strip() == "HIGH"].copy()
    if high.empty:
        log.info("  (none)")
    else:
        for _, row in high.iterrows():
            log.info("  %-8s %-12s %-6s>%-6s  %-8s %-30s %-35s  VAF=%-6s  Callers=%-30s  Filter=%s",
                     row["Chr"], row["Start"], str(row["Ref"])[:6], str(row["Alt"])[:6],
                     row["Gene"],
                     str(row["Consequence"])[:30],
                     str(row["HGVSp"])[:35],
                     row["VAF_pct"],
                     str(row["Callers"])[:30],
                     row["Filter"])
    log.info("-" * 120)

    return high


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()
    sample = args.sample

    # Resolve paths - derive input from -o so the batch runner's outdir is respected
    outdir = args.outdir or os.path.join(PIPELINE_DIR, "results", sample, "annotation")
    input_path = os.path.join(outdir, f"{sample}.somaticseq.annotated.tsv")

    if not os.path.isfile(input_path):
        log.error("Input file not found: %s", input_path)
        sys.exit(1)

    os.makedirs(outdir, exist_ok=True)

    log.info("=" * 70)
    log.info("14_variant_filter.py - Clinical Variant Filtering")
    log.info("=" * 70)
    log.info("Sample:    %s", sample)
    log.info("Input:     %s", input_path)
    log.info("Output:    %s", outdir)
    log.info("Blacklist: %s", args.blacklist or "(none)")

    # Load data
    df = pd.read_csv(input_path, sep="\t", dtype=str)
    log.info("Loaded %d variants", len(df))

    # Step 1: Investigate -1 rows
    investigate_minus1(df)

    # Step 2: Deduplicate
    df = deduplicate(df)

    # Step 2a: SNV blacklist (NEW)
    df = apply_snv_blacklist(df, args.blacklist)

    # Step 2b: Flag overlapping variants for manual review
    df = flag_overlapping_variants(df)

    # Step 3: Apply filters
    df = apply_filters(df)

    # Step 4: Sanity checks
    sanity_checks(df)

    # Write filtered output (all variants with Filter column)
    filtered_path = os.path.join(outdir, f"{sample}.somaticseq.filtered.tsv")
    df.to_csv(filtered_path, sep="\t", index=False)
    log.info("")
    log.info("Written: %s (%d variants)", filtered_path, len(df))

    # Write clinical output (PASS only, sorted by Gene)
    clinical = df[df["Filter"] == "PASS"].copy()
    clinical.sort_values(["Gene", "Chr", "Start"], inplace=True)
    clinical.reset_index(drop=True, inplace=True)
    clinical_path = os.path.join(outdir, f"{sample}.somaticseq.clinical.tsv")
    clinical.to_csv(clinical_path, sep="\t", index=False)
    log.info("Written: %s (%d PASS variants)", clinical_path, len(clinical))

    # Merge rescued U2AF1 variants if rescue TSV exists
    rescue_path = os.path.join(outdir, f"{sample}_u2af1_rescue.tsv")
    if os.path.isfile(rescue_path):
        log.info("")
        log.info("=" * 70)
        log.info("U2AF1 RESCUE MERGE")
        log.info("=" * 70)
        rescue_df = pd.read_csv(rescue_path, sep="\t", dtype=str)
        # Keep only rows with ALT_COUNT > 0
        rescue_df["_alt_count_num"] = rescue_df["ALT_COUNT"].apply(lambda v: safe_int(v, default=0))
        rescue_df = rescue_df[rescue_df["_alt_count_num"] > 0].copy()
        rescue_df.drop(columns=["_alt_count_num"], inplace=True)

        if not rescue_df.empty:
            # Check for duplicates already in clinical output (match on Gene + HGVSp)
            def _normalize_hgvsp(val):
                s = str(val).strip()
                if ":p." in s:
                    return "p." + s.split(":p.")[-1]
                return s

            # Build lookup of existing variants by (Gene, normalized HGVSp)
            existing_keys = {}
            if "Gene" in clinical.columns and "HGVSp" in clinical.columns:
                for idx, row in clinical.iterrows():
                    key = (str(row["Gene"]).strip(), _normalize_hgvsp(row["HGVSp"]))
                    existing_keys[key] = idx

            new_rows = []
            replaced = 0
            for _, row in rescue_df.iterrows():
                key = (str(row.get("Gene", "")).strip(), _normalize_hgvsp(row.get("HGVSp", "")))
                if key in existing_keys:
                    old_idx = existing_keys[key]
                    old_alt = safe_int(clinical.at[old_idx, "ALT_COUNT"], default=0)
                    rescue_alt = safe_int(row.get("ALT_COUNT", 0), default=0)
                    if rescue_alt > old_alt:
                        log.info("  U2AF1 %s: replacing existing (ALT_COUNT=%d) with rescue (ALT_COUNT=%d)",
                                 key[1], old_alt, rescue_alt)
                        clinical.drop(old_idx, inplace=True)
                        new_rows.append(row)
                        replaced += 1
                    else:
                        log.info("  U2AF1 %s already in clinical output with sufficient counts - skipping", key[1])
                    continue
                new_rows.append(row)

            if new_rows:
                rescue_to_add = pd.DataFrame(new_rows)
                rescue_to_add["Filter"] = "PASS"
                rescue_to_add["Rescue_Note"] = "U2AF1_GRCh38_rescue: pileup-based detection bypassing MQ0 artifact"

                # Align columns - add missing columns as -1
                for col in clinical.columns:
                    if col not in rescue_to_add.columns:
                        rescue_to_add[col] = MISSING
                for col in rescue_to_add.columns:
                    if col not in clinical.columns:
                        clinical[col] = ""

                clinical = pd.concat([clinical, rescue_to_add[clinical.columns]], ignore_index=True)
                clinical.sort_values(["Gene", "Chr", "Start"], inplace=True)
                clinical.reset_index(drop=True, inplace=True)
                clinical.to_csv(clinical_path, sep="\t", index=False)
                log.info("  Merged %d rescued U2AF1 variant(s) into clinical TSV (%d replaced, %d new)",
                         len(new_rows), replaced, len(new_rows) - replaced)
                log.info("  Updated: %s (%d variants)", clinical_path, len(clinical))
            else:
                log.info("  All rescued U2AF1 variants already present - no merge needed")
        else:
            log.info("  No rescued U2AF1 variants with ALT_COUNT > 0")
    else:
        log.info("No U2AF1 rescue file found at %s - skipping merge", rescue_path)

    # Final summary
    log.info("")
    log.info("=" * 70)
    log.info("SUMMARY")
    log.info("=" * 70)
    log.info("Total input:         %d", pd.read_csv(input_path, sep="\t").shape[0])
    log.info("After dedup:         %d", len(df))
    for filt in ["PASS", "BLACKLIST", "COMMON_POLYMORPHISM", "LOW_IMPACT",
                 "LOW_CALLERS", "LOW_DEPTH", "NO_CALLER_INFO"]:
        n = (df["Filter"] == filt).sum()
        if n > 0:
            log.info("  %-25s %d", filt, n)
    log.info("Clinical (PASS):     %d", len(clinical))


if __name__ == "__main__":
    main()
