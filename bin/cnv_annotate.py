#!/usr/bin/env python3
"""
18_cnv_annotate.py – Annotate CNV concordance output for clinical reporting.

Adds cytoband, ClinGen HI/TS scores, gene role, and heme significance
to the 4-caller concordance table.

Usage:
    python scripts/18_cnv_annotate.py --sample 26CGH40
"""

import argparse
import os
import re
import sys
import pandas as pd

# ── Gene role dictionaries (will be intersected with panel genes) ────────
_TSG_GENES = {
    "TP53", "CDKN2A", "CDKN2B", "TET2", "DNMT3A", "WT1", "EZH2", "ASXL1",
    "STAG2", "PHF6", "IKZF1", "NF1", "CUX1", "ETV6", "RB1", "ATM", "BRCA1",
    "BRCA2", "FAT1", "LZTR1", "SUZ12", "CREBBP", "EP300", "FOXO1", "PRDM1",
    "TNFAIP3", "B2M", "HNRNPK",
}

_ONCOGENES = {
    "FLT3", "KIT", "KRAS", "NRAS", "MYC", "RUNX1T1", "MECOM", "NUP98",
    "ABL1", "JAK2", "MPL", "CALR", "CSF3R", "FGFR1", "PDGFRA", "PDGFRB",
    "BCL2", "BCL6", "MYD88", "NOTCH1", "NOTCH2", "BRAF", "STAT3", "STAT5B",
}

_BOTH_GENES = {
    "RUNX1", "CEBPA", "KMT2A", "NPM1", "GATA2", "PAX5", "IKZF3", "TCF3",
    "SPI1",
}

# All cancer genes (union of all three sets)
_ALL_CANCER_GENES = _TSG_GENES | _ONCOGENES | _BOTH_GENES

# Clinical flag promotion: 12g_exon_cnv.py emits these labels for known
# clinically actionable patterns. Without this map, every flag defaults to
# VUS in assign_heme_significance because that function does not see the
# exon_clinical_flag column.
#
# Edit these mappings if your clinical interpretation differs.
CLINICAL_FLAG_SIGNIFICANCE = {
    "KMT2A-PTD":                  "Pathogenic",
    "IKZF1-Ik6":                  "Pathogenic",
    "IKZF1-del":                  "Pathogenic",
    "CDKN2A-del":                 "Likely Pathogenic",
    "CDKN2B-del":                 "Likely Pathogenic",
    "CDKN2A/CDKN2B_co-deletion":  "Pathogenic",
}


def parse_bed_genes(bed_path: str) -> set:
    """Extract unique gene names from panel BED file."""
    genes = set()
    with open(bed_path) as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.strip().split("\t")
            if len(parts) < 4:
                continue
            name = parts[3].strip('"').strip("'")
            # Parse gene from name field: handle Target=N;ProbeIdx=N;GENE_Ex_N
            # or just GENE_Ex_N or GENE_EX_N
            tokens = name.split(";")
            last = tokens[-1].strip()
            # Compound sub-isoform names: take the first comma alternative.
            if "," in last:
                last = last.split(",", 1)[0]
            # Strip leading "<num>_<num>_" probe-coordinate prefix.
            last = re.sub(r"^(?:\d+_)+", "", last)
            # Intron-feature suffix (e.g. CSF1R_Intron_17-18): fold into parent gene.
            last = re.sub(r"_Intron_\d+(?:-\d+)?(?:_part)?$", "", last)
            # Remove exon suffix: GENE_Ex_N or GENE_EX_N or GENE_ExN
            # Match _Ex_/_EX_ followed by ANY word chars (digits or text),
            # e.g. NPM1_Ex_intr_10_part folds to NPM1.
            m = re.match(r'^(.+?)_[Ee][Xx]_?\w+', last)
            if m:
                genes.add(m.group(1))
            else:
                genes.add(last)
    return genes


def build_role_lookup(panel_genes: set) -> dict:
    """Build gene->role dict restricted to panel genes."""
    lookup = {}
    for g in panel_genes:
        if g in _BOTH_GENES:
            lookup[g] = "Both"
        elif g in _TSG_GENES:
            lookup[g] = "TSG"
        elif g in _ONCOGENES:
            lookup[g] = "Oncogene"
    return lookup


# ── CDKN2A/2B rescue logic ─────────────────────────────────────────────────
_PASSING_TIERS = {"CONCORDANT", "TIER_1", "TIER_2"}
_RESCUABLE_TIERS = {"FILTERED", "CNVKIT_ONLY"}


def rescue_cdkn2_pair(out_df: pd.DataFrame, conc_df: pd.DataFrame) -> None:
    """
    Rescue CDKN2A (or CDKN2B) to TIER_3 if its partner passes as a loss
    and the rescued gene shows loss by CNVKit.

    Modifies out_df in-place (Tier and Comment columns).
    conc_df is the raw concordance table (has cnvkit_call column).
    """
    # Build lookup from raw concordance for cnvkit_call
    cnvkit_call = dict(zip(conc_df["gene"], conc_df["cnvkit_call"].str.lower()))

    for rescued_gene, partner_gene in [("CDKN2A", "CDKN2B"), ("CDKN2B", "CDKN2A")]:
        rescued_idx = out_df.index[out_df["Gene"] == rescued_gene]
        partner_idx = out_df.index[out_df["Gene"] == partner_gene]
        if rescued_idx.empty or partner_idx.empty:
            continue

        ri = rescued_idx[0]
        pi = partner_idx[0]

        partner_tier = str(out_df.at[pi, "Tier"])
        partner_dir = str(out_df.at[pi, "CNV_Direction"])
        rescued_tier = str(out_df.at[ri, "Tier"])

        # Partner must be a passing loss
        if not (partner_tier in _PASSING_TIERS and partner_dir == "loss"):
            continue
        # Rescued gene must be filtered and show loss by CNVKit
        if rescued_tier not in _RESCUABLE_TIERS:
            continue
        if cnvkit_call.get(rescued_gene) != "loss":
            continue

        out_df.at[ri, "Tier"] = "TIER_3"
        out_df.at[ri, "Comment"] = (
            f"Rescued: adjacent {partner_gene} loss confirms 9p co-deletion"
        )


# ── 9p/9q co-deletion comment (HNRNPK) ───────────────────────────────────
def annotate_9p_9q_codeletion(out_df: pd.DataFrame) -> None:
    """
    When HNRNPK (9q21.32) shows loss alongside CDKN2A or CDKN2B (9p21.3),
    add a comment noting 9p and 9q loss detected.
    Modifies out_df in-place.
    """
    tiered = out_df["Tier"].isin(["CONCORDANT", "TIER_1", "TIER_2", "TIER_3"])
    loss = out_df["CNV_Direction"] == "loss"

    cdkn_loss = ((out_df["Gene"].isin(["CDKN2A", "CDKN2B"])) & loss & tiered).any()
    hnrnpk_loss = ((out_df["Gene"] == "HNRNPK") & loss & tiered).any()

    if cdkn_loss and hnrnpk_loss:
        for gene in ["CDKN2A", "CDKN2B", "HNRNPK"]:
            mask = (out_df["Gene"] == gene) & loss & tiered
            for idx in out_df.index[mask]:
                existing = str(out_df.at[idx, "Comment"]) if out_df.at[idx, "Comment"] else ""
                note = "9p and 9q loss detected"
                if note not in existing:
                    out_df.at[idx, "Comment"] = (
                        f"{existing}; {note}" if existing else note
                    )


# ── Heme significance ───────────────────────────────────────────────────────
def assign_heme_significance(out_df: pd.DataFrame, cancer_genes_on_panel: set) -> pd.Series:
    """
    Assign Heme_Significance:
    - "Pathogenic": only if BOTH CDKN2A and CDKN2B show loss (9p21.3 co-deletion)
    - "Likely benign": gene not in cancer gene list AND LOO FP >20%
    - "VUS": everything else with a CNV call
    - "": neutral genes
    """
    sig = pd.Series("", index=out_df.index)

    has_call = out_df["CNV_Direction"].isin(["gain", "loss"])

    # Check for CDKN2A + CDKN2B co-deletion (both must be non-FILTERED loss, including rescued TIER_3)
    tiered = out_df["Tier"].isin(["CONCORDANT", "TIER_1", "TIER_2", "TIER_3"])
    cdkn2a_loss = ((out_df["Gene"] == "CDKN2A") & (out_df["CNV_Direction"] == "loss") & tiered).any()
    cdkn2b_loss = ((out_df["Gene"] == "CDKN2B") & (out_df["CNV_Direction"] == "loss") & tiered).any()
    co_deletion = cdkn2a_loss and cdkn2b_loss

    # Default all calls to VUS
    sig[has_call] = "VUS"

    # Likely benign: not a cancer gene AND LOO FP >20%
    for idx in out_df.index[has_call]:
        gene = out_df.at[idx, "Gene"]
        fp = out_df.at[idx, "LOO_FP_Rate"]
        if gene not in cancer_genes_on_panel:
            try:
                if float(fp) > 0.20:
                    sig[idx] = "Likely benign"
            except (ValueError, TypeError):
                pass

    # Pathogenic: CDKN2A/2B co-deletion (only non-FILTERED rows)
    if co_deletion:
        mask = (has_call & tiered
                & out_df["Gene"].isin(["CDKN2A", "CDKN2B"])
                & (out_df["CNV_Direction"] == "loss"))
        sig[mask] = "Pathogenic"

    return sig


# ── Cytoband lookup ─────────────────────────────────────────────────────────
def load_cytoband(cytoband_file: str) -> pd.DataFrame:
    """Load UCSC cytoBand.txt into a DataFrame."""
    return pd.read_csv(
        cytoband_file,
        sep="\t",
        header=None,
        names=["chrom", "start", "end", "band", "stain"],
    )


def map_cytoband(chrom: str, start, end, cytoband_df: pd.DataFrame) -> str:
    """Map a genomic region to its cytoband(s)."""
    if pd.isna(chrom) or not chrom:
        return ""
    try:
        s = int(float(start))
        e = int(float(end))
    except (ValueError, TypeError):
        return ""

    c = str(chrom)
    sub = cytoband_df[cytoband_df["chrom"] == c]
    hits = sub[(sub["start"] < e) & (sub["end"] > s)]
    if hits.empty:
        return ""

    arm_num = c.replace("chr", "")
    bands = hits["band"].tolist()
    if len(bands) == 1:
        return f"{arm_num}{bands[0]}"
    return f"{arm_num}{bands[0]}-{bands[-1]}"


# ── ClinGen lookup ──────────────────────────────────────────────────────────
def load_clingen(clingen_file: str) -> dict:
    """Load ClinGen gene curation list. Returns {gene: (HI_score, TS_score)}."""
    lookup = {}
    with open(clingen_file) as f:
        for line in f:
            if line.startswith("#"):
                continue
            parts = line.strip().split("\t")
            if len(parts) < 14:
                continue
            gene = parts[0]
            hi = parts[4] if len(parts) > 4 else ""
            ts = parts[12] if len(parts) > 12 else ""
            if gene not in lookup:
                lookup[gene] = (hi, ts)
    return lookup


# ── Main ────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Annotate CNV concordance for clinical reporting"
    )
    parser.add_argument("--sample", required=True, help="Sample name")
    parser.add_argument(
        "--concordance",
        help="Path to 4-caller concordance TSV (default: results/{sample}/cnv_consensus/{sample}_4caller_concordance.tsv)",
    )
    parser.add_argument(
        "--loo-summary",
        default="references/myeloid/cnvkit_loo_summary.tsv",
        help="Path to LOO false-positive summary (panel-namespaced; "
             "override --loo-summary for non-myeloid panels)",
    )
    parser.add_argument(
        "--cytoband",
        default="references/cytoBand_hg38.txt",
        help="Path to UCSC cytoBand file",
    )
    parser.add_argument(
        "--clingen",
        default="references/ClinGen_gene_curation_list_GRCh38.tsv",
        help="Path to ClinGen gene curation list",
    )
    parser.add_argument(
        "--bed",
        default="bedfiles/MYOPOOL_240125_UBTF_hg38.bed",
        help="Panel BED file for gene list",
    )
    parser.add_argument(
        "--outdir",
        help="Output directory (default: results/{sample}/cnv_consensus/)",
    )
    args = parser.parse_args()

    sample = args.sample
    conc_path = args.concordance or f"results/{sample}/cnv_consensus/{sample}_4caller_concordance.tsv"
    outdir = args.outdir or f"results/{sample}/cnv_consensus"
    os.makedirs(outdir, exist_ok=True)

    # Load panel genes from BED file
    panel_genes = parse_bed_genes(args.bed)
    print(f"Panel genes from BED: {len(panel_genes)}")

    # Build role lookup restricted to panel genes
    role_lookup = build_role_lookup(panel_genes)
    cancer_genes_on_panel = _ALL_CANCER_GENES & panel_genes
    print(f"Cancer genes on panel: {len(cancer_genes_on_panel)} "
          f"(TSG={len(_TSG_GENES & panel_genes)}, "
          f"Onc={len(_ONCOGENES & panel_genes)}, "
          f"Both={len(_BOTH_GENES & panel_genes)})")

    # Load inputs
    df = pd.read_csv(conc_path, sep="\t")
    cytoband_df = load_cytoband(args.cytoband)
    clingen = load_clingen(args.clingen)

    # Load LOO summary for FP rates (keyed by gene). Missing or unreadable
    # file is non-fatal: LOO_FP_Rate will be empty for every gene, and
    # downstream FP-based filtering simply does not fire. This is safer
    # than the previous behavior (crash) when the myeloid LOO has not yet
    # been rebuilt at the new namespaced path.
    loo_fp = {}
    if os.path.isfile(args.loo_summary):
        try:
            loo_df = pd.read_csv(args.loo_summary, sep="\t")
            if "gene" in loo_df.columns and "fp_any_rate" in loo_df.columns:
                loo_fp = dict(zip(loo_df["gene"], loo_df["fp_any_rate"]))
                print(f"LOO summary: {len(loo_fp)} genes loaded from {args.loo_summary}")
            else:
                print(f"WARNING: LOO summary {args.loo_summary} missing 'gene' "
                      f"or 'fp_any_rate' column; LOO_FP_Rate will be blank.",
                      file=sys.stderr)
        except Exception as e:
            print(f"WARNING: could not read LOO summary {args.loo_summary} "
                  f"({type(e).__name__}: {e}); LOO_FP_Rate will be blank.",
                  file=sys.stderr)
    else:
        print(f"WARNING: LOO summary not found at {args.loo_summary}; "
              f"LOO_FP_Rate will be blank for every gene.", file=sys.stderr)

    # Determine CNV direction from consensus_type column
    def get_direction(row):
        ct = str(row.get("consensus_type", "")).lower()
        if ct in ("gain", "loss"):
            return ct
        for col in ("cnvkit_call", "zscore_call", "cnmops_call"):
            v = str(row.get(col, "")).lower()
            if v in ("gain", "loss"):
                return v
        return "neutral"

    # Build annotation rows
    rows = []
    for _, row in df.iterrows():
        gene = row["gene"]
        chrom = row.get("chromosome", "")
        start = row.get("start", "")
        end = row.get("end", "")

        direction = get_direction(row)
        cytoband = map_cytoband(chrom, start, end, cytoband_df)
        hi_score, ts_score = clingen.get(gene, ("", ""))
        gene_role = role_lookup.get(gene, "")
        fp_rate = loo_fp.get(gene, "")

        rows.append({
            "Gene": gene,
            "Cytoband": cytoband,
            "CNV_Direction": direction,
            "Tier": row.get("tier", ""),
            "Callers_Concordant": row.get("agreeing_callers", ""),
            "LOO_FP_Rate": fp_rate,
            "ClinGen_HI": hi_score,
            "ClinGen_TS": ts_score,
            "Gene_Role": gene_role,
            "Heme_Significance": "",  # filled below
            "CNVKit_log2": row.get("cnvkit_log2", ""),
            "Zscore_Z": row.get("zscore_mean_z", ""),
            "cn_mops_call": row.get("cnmops_call", ""),
            "ifCNV_call": row.get("ifcnv_call", ""),
            "Comment": "",
        })

    out_df = pd.DataFrame(rows)

    # Rescue CDKN2A/2B pair (must run before heme significance assignment)
    rescue_cdkn2_pair(out_df, df)

    # Annotate 9p/9q co-deletion (HNRNPK + CDKN2A/2B)
    annotate_9p_9q_codeletion(out_df)

    # Assign heme significance (needs whole-sample view for co-deletion check)
    out_df["Heme_Significance"] = assign_heme_significance(out_df, cancer_genes_on_panel)

    # Promote Heme_Significance for 12g clinical flags (KMT2A-PTD, IKZF1-Ik6,
    # etc.). assign_heme_significance does not look at exon_clinical_flag,
    # so without this step those patterns get labelled VUS.
    if "exon_clinical_flag" in df.columns:
        gene_flag = dict(zip(df["gene"], df["exon_clinical_flag"].fillna("")))
        for idx in out_df.index:
            gene = out_df.at[idx, "Gene"]
            tier = str(out_df.at[idx, "Tier"])
            # Do not promote FILTERED rows (likely artefact).
            if tier == "FILTERED":
                continue
            flag = str(gene_flag.get(gene, "")).strip()
            if flag and flag in CLINICAL_FLAG_SIGNIFICANCE:
                out_df.at[idx, "Heme_Significance"] = CLINICAL_FLAG_SIGNIFICANCE[flag]
                existing = str(out_df.at[idx, "Comment"]) if out_df.at[idx, "Comment"] else ""
                if existing == "nan":
                    existing = ""
                note = f"12g clinical pattern: {flag}"
                if note not in existing:
                    out_df.at[idx, "Comment"] = (
                        f"{existing}; {note}" if existing else note
                    )

    # Sort: non-neutral first (by tier), then neutral
    tier_order = {"TIER_1": 0, "TIER_2": 1, "TIER_3": 2, "FILTERED": 3, "NEUTRAL": 4}
    out_df["_sort"] = out_df["Tier"].map(tier_order).fillna(5)
    out_df = out_df.sort_values("_sort").drop(columns=["_sort"])

    out_path = os.path.join(outdir, f"{sample}_cnv_annotated.tsv")
    out_df.to_csv(out_path, sep="\t", index=False)
    print(f"\nWrote {len(out_df)} annotated genes to {out_path}")

    # Summary
    non_neutral = out_df[out_df["CNV_Direction"] != "neutral"]
    print(f"\nCNV calls: {len(non_neutral)}")
    if not non_neutral.empty:
        print(non_neutral[["Gene", "Cytoband", "CNV_Direction", "Tier",
                           "Gene_Role", "Heme_Significance", "Comment"]].to_string(index=False))


if __name__ == "__main__":
    main()
