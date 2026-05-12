#!/usr/bin/env python3
"""
19_sv_annotate.py – Annotate structural variants for clinical reporting.

Reads the custom-merge SV output (.txt and .vcf) from 11_sv_callers.py,
runs AnnotSV on the VCF, and produces clinical SV tables filtered to
panel genes.

Usage:
    python scripts/19_sv_annotate.py --sample 26CGH40
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

import pandas as pd


# ── BED gene parsing ────────────────────────────────────────────────────────
def _extract_gene(name_field: str) -> str:
    """Extract clean gene name from BED name field."""
    name = name_field.strip('"').strip("'")
    # Handle Target=N;ProbeIdx=N;GENE_Ex_N
    tokens = name.split(";")
    last = tokens[-1].strip()
    # Strip numeric probe prefix: 926535_53648134_GENE_Ex_N -> GENE_Ex_N
    m_prefix = re.match(r'^\d+_\d+_(.+)$', last)
    if m_prefix:
        last = m_prefix.group(1)
    # Remove exon suffix: GENE_Ex_N or GENE_EX_N or GENE_ExN
    m = re.match(r'^(.+?)_[Ee][Xx]_?\d+', last)
    if m:
        return m.group(1)
    return last


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
            genes.add(_extract_gene(parts[3]))
    return genes


def load_bed_regions(bed_path: str) -> pd.DataFrame:
    """Load BED file as DataFrame with gene names for overlap checking."""
    rows = []
    with open(bed_path) as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.strip().split("\t")
            if len(parts) < 4:
                continue
            rows.append({
                "chrom": parts[0],
                "start": int(parts[1]),
                "end": int(parts[2]),
                "gene": _extract_gene(parts[3]),
            })
    return pd.DataFrame(rows)


# ── Parse custom-merge SV output ────────────────────────────────────────────
def parse_merged_txt(txt_path: str) -> pd.DataFrame:
    """Parse custom-merge .txt into a standardised DataFrame for annotation.

    The .txt has columns: sample, event_id, is_matching, variant_id, chrom,
    pos, ref, alt, mate_id, callers, num_callers, call_source,
    tumor_discordant_rs, tumor_spanning_rs, tumor_dp,
    intra_chrom_event_length, other_variant_ids.

    Breakpoint pairs share the same event_id. We collapse each event into a
    single row with Chr1/Pos1 and Chr2/Pos2.
    """
    df = pd.read_csv(txt_path, sep="\t", dtype=str)

    rows = []
    for event_id, grp in df.groupby("event_id"):
        grp = grp.sort_values("pos")
        chrom1 = grp.iloc[0]["chrom"]
        pos1 = int(grp.iloc[0]["pos"])

        # Determine second breakpoint from mate / bracket notation
        if len(grp) >= 2:
            chrom2 = grp.iloc[-1]["chrom"]
            pos2 = int(grp.iloc[-1]["pos"])
        else:
            # Single-breakpoint event — try to parse mate from ALT
            alt = grp.iloc[0]["alt"]
            m = re.search(r'(chr[0-9XYM]+):(\d+)', alt)
            if m:
                chrom2 = m.group(1)
                pos2 = int(m.group(2))
            else:
                chrom2 = chrom1
                svlen = grp.iloc[0]["intra_chrom_event_length"]
                pos2 = pos1 + (int(svlen) if svlen not in ("NA", "", "-1") else 0)

        # Infer SV type: prefer event_id prefix (DEL, DUP, INV, BND),
        # fall back to bracket notation parsing
        svtype = _infer_svtype_from_event(event_id)
        if svtype == "UNK":
            alt = grp.iloc[0]["alt"]
            svtype = _infer_svtype_from_alt(alt, chrom1, chrom2)

        svlen_raw = grp.iloc[0]["intra_chrom_event_length"]
        try:
            svlen = abs(int(svlen_raw))
        except (ValueError, TypeError):
            svlen = abs(pos2 - pos1) if chrom1 == chrom2 else 0

        num_callers = int(grp.iloc[0]["num_callers"])
        callers = grp.iloc[0]["callers"].replace(";", ",")

        rows.append({
            "SV_ID": grp.iloc[0]["variant_id"],
            "Chr1": chrom1,
            "Pos1": pos1,
            "Chr2": chrom2,
            "Pos2": pos2,
            "SV_Type": svtype,
            "SV_Length": svlen,
            "Num_Callers": num_callers,
            "Callers": callers,
        })

    return pd.DataFrame(rows)


def _infer_svtype_from_event(event_id: str) -> str:
    """Extract SV type from event_id prefix (e.g. DEL00002543 → DEL)."""
    m = re.match(r'^(DEL|DUP|INV|INS|BND|TRA)', event_id, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    return "UNK"


def _infer_svtype_from_alt(alt: str, chrom1: str, chrom2: str) -> str:
    """Fallback: infer SV type from BND bracket notation ALT string."""
    if chrom1 != chrom2:
        return "BND"
    if re.match(r'^[ACGTNacgtn]+\[', alt):
        return "DEL"
    elif re.match(r'^[ACGTNacgtn]+\]', alt):
        return "INV"
    return "BND"


# ── Run AnnotSV ─────────────────────────────────────────────────────────────
def run_annotsv(merged_vcf: str, outdir: str, sample: str,
                annotsv_path: str = "AnnotSV") -> str | None:
    """Run AnnotSV on the merged VCF. Returns output TSV path or None."""
    out_prefix = os.path.join(outdir, f"{sample}_sv_annotsv")

    # Check for local annotations directory (bioconda install)
    annotsv_bin = shutil.which(annotsv_path) or annotsv_path
    annotsv_prefix = os.path.dirname(os.path.dirname(os.path.abspath(annotsv_bin)))
    annotations_dir = os.path.join(annotsv_prefix, "share", "AnnotSV_annotations",
                                   "AnnotSV", "share", "AnnotSV")

    cmd = [
        annotsv_path,
        "-SVinputFile", merged_vcf,
        "-genomeBuild", "GRCh38",
        "-outputFile", out_prefix,
        "-SVminSize", "50",
        "-annotationMode", "both",
    ]

    # Add annotationsDir if local annotations exist
    if os.path.isdir(os.path.join(annotations_dir, "Annotations_Human")):
        cmd.extend(["-annotationsDir", annotations_dir])
        print(f"Using annotations: {annotations_dir}")

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"AnnotSV stderr:\n{result.stderr}")
        print(f"AnnotSV stdout:\n{result.stdout}")
        return None

    # AnnotSV output is {prefix}.tsv
    out_tsv = out_prefix + ".tsv"
    if os.path.isfile(out_tsv):
        return out_tsv
    # Some versions use .annotated.tsv
    alt_tsv = out_prefix + ".annotated.tsv"
    if os.path.isfile(alt_tsv):
        return alt_tsv
    print(f"Warning: AnnotSV output not found at {out_tsv}")
    return None


# ── Overlap with panel BED ──────────────────────────────────────────────────
def find_overlapping_genes(chrom: str, start: int, end: int,
                           bed_df: pd.DataFrame) -> list:
    """Find panel genes overlapping a genomic interval."""
    sub = bed_df[bed_df["chrom"] == chrom]
    hits = sub[(sub["start"] < end) & (sub["end"] > start)]
    return sorted(hits["gene"].unique().tolist())


# ── Main ────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Annotate structural variants for clinical reporting"
    )
    parser.add_argument("--sample", required=True, help="Sample name")
    parser.add_argument(
        "--sv-vcf",
        help="Merged SV VCF for AnnotSV (default: results/{sample}/sv_callers/{sample}_sv_merged.vcf)",
    )
    parser.add_argument(
        "--sv-txt",
        help="Merged SV TXT from custom merge (default: results/{sample}/sv_callers/{sample}_sv_merged.txt)",
    )
    parser.add_argument(
        "--bed",
        default="bedfiles/MYOPOOL_240125_UBTF_hg38.bed",
        help="Panel BED file",
    )
    parser.add_argument(
        "--outdir",
        help="Output directory (default: results/{sample}/sv_annotation/)",
    )
    parser.add_argument(
        "--annotsv-path",
        default=None,
        help="Path to AnnotSV executable (default: auto-detect)",
    )
    args = parser.parse_args()

    sample = args.sample
    sv_vcf = args.sv_vcf or f"results/{sample}/sv_callers/{sample}_sv_merged.vcf"
    sv_txt = args.sv_txt or f"results/{sample}/sv_callers/{sample}_sv_merged.txt"
    outdir = args.outdir or f"results/{sample}/sv_annotation"
    os.makedirs(outdir, exist_ok=True)

    # Auto-detect AnnotSV path
    annotsv_path = args.annotsv_path
    if annotsv_path is None:
        # Check common locations
        candidates = [
            "AnnotSV",  # in PATH

        ]
        for c in candidates:
            if os.path.isfile(c) and os.access(c, os.X_OK):
                annotsv_path = c
                break
            # Check via which
            import shutil
            if shutil.which(c):
                annotsv_path = c
                break
        if annotsv_path is None:
            annotsv_path = candidates[-1]  # default to source install

    # Load panel BED
    panel_genes = parse_bed_genes(args.bed)
    bed_df = load_bed_regions(args.bed)
    print(f"Panel: {len(panel_genes)} genes, {len(bed_df)} target regions")

    # Parse merged SV calls from custom merge TXT
    sv_df = parse_merged_txt(sv_txt)
    print(f"Parsed {len(sv_df)} SVs from merged TXT: {sv_txt}")
    print(f"  By type: {sv_df['SV_Type'].value_counts().to_dict()}")
    print(f"  By callers: {sv_df['Num_Callers'].value_counts().sort_index().to_dict()}")

    # Run AnnotSV
    annotsv_tsv = run_annotsv(sv_vcf, outdir, sample, annotsv_path)

    # Parse AnnotSV output if available
    # AnnotSV_ID format: CHROM_START_END_TYPE_N (no chr prefix)
    # Merged VCF POS may differ slightly from AnnotSV SV_start, so we index
    # by (chrom, start, end) and also build a spatial index for proximity lookup.
    annotsv_by_coord = {}  # (chrom_with_chr, start, end) -> annotation dict
    if annotsv_tsv and os.path.isfile(annotsv_tsv):
        print(f"Parsing AnnotSV output: {annotsv_tsv}")
        ann_df = pd.read_csv(annotsv_tsv, sep="\t", low_memory=False)
        print(f"  AnnotSV rows: {len(ann_df)}")

        for _, row in ann_df.iterrows():
            mode = row.get("Annotation_mode", "")
            sv_chrom = str(row.get("SV_chrom", ""))
            if not sv_chrom.startswith("chr"):
                sv_chrom = "chr" + sv_chrom
            sv_start = int(row.get("SV_start", 0))
            sv_end = int(row.get("SV_end", 0))
            key = (sv_chrom, sv_start, sv_end)

            gene = str(row.get("Gene_name", ""))
            ranking = row.get("ACMG_class", row.get("AnnotSV_ranking_score", ""))

            if key not in annotsv_by_coord:
                annotsv_by_coord[key] = {
                    "genes": set(),
                    "ranking": "",
                    "gene_disrupted": False,
                }

            if gene and gene != "nan":
                annotsv_by_coord[key]["genes"].add(gene)

            if mode == "full":
                annotsv_by_coord[key]["ranking"] = str(ranking) if pd.notna(ranking) else ""

            if mode == "split":
                loc = str(row.get("Location", row.get("Location2", "")))
                if "exon" in loc.lower() or "cds" in loc.lower():
                    annotsv_by_coord[key]["gene_disrupted"] = True
    else:
        print("AnnotSV not available — using BED overlap for gene annotation")

    def lookup_annotsv(chrom, pos1, pos2, svtype):
        """Find best AnnotSV match by proximity (within 500bp of start)."""
        best = {}
        best_dist = float("inf")
        for (ac, astart, aend), ann in annotsv_by_coord.items():
            if ac != chrom:
                continue
            dist = abs(astart - pos1)
            if dist < 500 and dist < best_dist:
                best = ann
                best_dist = dist
        return best

    # Annotate SVs
    results = []
    for _, sv in sv_df.iterrows():
        chr1 = sv["Chr1"]
        pos1 = sv["Pos1"]
        chr2 = sv["Chr2"]
        pos2 = sv["Pos2"]
        svtype = sv["SV_Type"]
        svlen = sv["SV_Length"]

        # Find overlapping panel genes via BED
        if svtype == "TRA" or (chr1 != chr2):
            # Translocation: check both breakpoints
            genes1 = find_overlapping_genes(chr1, max(0, pos1 - 500), pos1 + 500, bed_df)
            genes2 = find_overlapping_genes(chr2, max(0, pos2 - 500), pos2 + 500, bed_df)
            panel_overlap = sorted(set(genes1 + genes2))
            fusion = f"{','.join(genes1) if genes1 else chr1}--{','.join(genes2) if genes2 else chr2}"
        else:
            # Intrachromosomal: use span
            start = min(pos1, pos2)
            end = max(pos1, pos2)
            panel_overlap = find_overlapping_genes(chr1, start, end, bed_df)
            genes1 = find_overlapping_genes(chr1, max(0, pos1 - 500), pos1 + 500, bed_df)
            genes2 = find_overlapping_genes(chr1, max(0, pos2 - 500), pos2 + 500, bed_df)
            if svtype == "BND" and genes1 and genes2 and genes1 != genes2:
                fusion = f"{','.join(genes1)}--{','.join(genes2)}"
            else:
                fusion = ""

        # AnnotSV data for this SV (proximity match)
        ann = lookup_annotsv(chr1, pos1, pos2, svtype)
        annotsv_genes = ann.get("genes", set())
        gene_disrupted = "yes" if ann.get("gene_disrupted", False) else "no"
        ranking = ann.get("ranking", "")

        # Combine gene lists: panel overlap + AnnotSV genes that are on panel
        all_genes = sorted(set(panel_overlap) | (annotsv_genes & panel_genes))
        genes_str = ",".join(all_genes) if all_genes else ""

        results.append({
            "Sample": sample,
            "SV_ID": sv["SV_ID"],
            "Chr1": chr1,
            "Pos1": pos1,
            "Chr2": chr2,
            "Pos2": pos2,
            "SV_Type": svtype,
            "SV_Length": svlen,
            "Num_Callers": sv["Num_Callers"],
            "Callers": sv["Callers"],
            "Genes": genes_str,
            "Gene_Disrupted": gene_disrupted,
            "Fusion_Genes": fusion if svtype in ("TRA", "BND") else "",
            "AnnotSV_Ranking": ranking,
        })

    full_df = pd.DataFrame(results)

    # Write full annotated output
    full_path = os.path.join(outdir, f"{sample}_sv_annotated.tsv")
    full_df.to_csv(full_path, sep="\t", index=False)
    print(f"\nFull annotated: {full_path} ({len(full_df)} SVs)")

    # Clinical filtering
    clinical = full_df.copy()

    # Remove SVs < 50bp (keep BND/TRA regardless of size)
    size_mask = (clinical["SV_Length"] >= 50) | clinical["SV_Type"].isin(["BND", "TRA"])
    clinical = clinical[size_mask]

    # Must overlap at least one panel gene
    clinical = clinical[clinical["Genes"] != ""]

    # Flag inversions as likely artifacts unless gene is disrupted
    clinical["Artifact_Flag"] = ""
    inv_mask = (clinical["SV_Type"] == "INV") & (clinical["Gene_Disrupted"] != "yes")
    clinical.loc[inv_mask, "Artifact_Flag"] = "likely_artifact"

    # Sort by Num_Callers descending, then SV type
    type_order = {"DEL": 0, "DUP": 1, "BND": 2, "TRA": 3, "INS": 4, "INV": 5, "NA": 6}
    clinical["_sort_type"] = clinical["SV_Type"].map(type_order).fillna(7)
    clinical = clinical.sort_values(
        ["Num_Callers", "_sort_type"], ascending=[False, True]
    ).drop(columns=["_sort_type"])

    clinical_path = os.path.join(outdir, f"{sample}_sv_clinical.tsv")
    clinical.to_csv(clinical_path, sep="\t", index=False)
    print(f"Clinical filtered: {clinical_path} ({len(clinical)} SVs)")

    # Summary
    print(f"\n=== SV Summary for {sample} ===")
    print(f"Total SVs (merged): {len(full_df)}")
    print(f"Clinical SVs (panel genes): {len(clinical)}")
    if not clinical.empty:
        print(f"\nBy SV type:")
        print(clinical["SV_Type"].value_counts().to_string())
        print(f"\nBy caller support:")
        print(clinical["Num_Callers"].value_counts().sort_index().to_string())

        non_artifact = clinical[clinical["Artifact_Flag"] != "likely_artifact"]
        if not non_artifact.empty:
            print(f"\nHigh-confidence clinical SVs (non-artifact):")
            display_cols = ["SV_ID", "Chr1", "Pos1", "SV_Type", "SV_Length",
                            "Num_Callers", "Callers", "Genes"]
            print(non_artifact[display_cols].to_string(index=False))

        artifacts = clinical[clinical["Artifact_Flag"] == "likely_artifact"]
        if not artifacts.empty:
            print(f"\nInversions flagged as likely artifacts: {len(artifacts)}")


if __name__ == "__main__":
    main()
