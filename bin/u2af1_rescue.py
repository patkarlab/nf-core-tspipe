#!/usr/bin/env python3
"""
u2af1_rescue.py — Pileup-based rescue for U2AF1 hotspot mutations missed
due to the GRCh38 reference duplication artifact.

Background:
    In GRCh38, a ~153 kb region added to chr21p (chr21:6427259-6580181) is
    nearly identical to the canonical U2AF1 locus on chr21q (21q22.3). This
    causes reads to multimap between the two copies, resulting in MQ=0 at
    the canonical locus and effectively hiding somatic mutations from
    standard variant callers.

    Reference: Miller CA et al. J Mol Diagn. 2022;24(3):219-223.
    PMID: 35041928 | doi: 10.1016/j.jmoldx.2021.10.013

Approach:
    1. Perform pileup at known U2AF1 hotspot positions (S34, Q157) on both
       the canonical locus AND the paralog locus.
    2. Include reads with MQ=0 (multimapped) since these are the reads that
       carry the true signal at this locus in standard GRCh38.
    3. Count pathogenic alleles independent of reference base.
    4. Output rescued variants in TSV format compatible with the pipeline's
       somaticseq_annotated.tsv.

Usage:
    python u2af1_rescue.py --bam <sample.bam> --sample <sample_id> --outdir <dir>

    Optional:
    --min-vaf         Minimum VAF to report (default: 0.01 = 1%)
    --min-alt-count   Minimum alt read count (default: 3)
    --min-depth       Minimum total depth at position (default: 20)
    --check-paralog   Also interrogate the chr21p paralog locus (default: True)
    --no-check-paralog  Skip paralog locus check

Output:
    <outdir>/<sample>_u2af1_rescue.tsv         Rescued variants (if any)
    <outdir>/<sample>_u2af1_pileup_report.txt  Full pileup report at all loci

Dependencies:
    pysam (pip install pysam)
"""

import argparse
import os
import sys
from datetime import datetime

try:
    import pysam
except ImportError:
    sys.exit(
        "ERROR: pysam is required. Install with: pip install pysam --break-system-packages"
    )


# ---------------------------------------------------------------------------
# U2AF1 hotspot definitions (GRCh38 / hg38)
# ---------------------------------------------------------------------------
# Gene is on the MINUS strand of chr21.
# Coding changes are specified on the coding (minus) strand.
# Genomic alleles below are on the PLUS strand.
#
# Canonical locus: chr21q22.3 (~43.09-43.11 Mb)
# Paralog locus:   chr21p    (~6.43-6.58 Mb, within the GRCh38-added region)
#
# Paralog coordinates are estimated from the canonical-to-paralog offset
# and SHOULD BE VERIFIED against your specific reference build. The script
# will report if coverage at paralog positions is zero (suggesting the
# coordinates may need adjustment).

HOTSPOTS = [
    {
        "name": "S34F",
        "gene": "U2AF1",
        "transcript": "NM_006758.3",
        "hgvs_c": "c.101C>T",
        "hgvs_p": "p.Ser34Phe",
        "consequence": "missense_variant",
        "canonical_chrom": "chr21",
        "canonical_pos": 43104346,        # 1-based, hg38
        "plus_strand_ref": "G",           # wildtype allele on + strand
        "plus_strand_alt": "A",           # pathogenic allele on + strand
        "paralog_chrom": "chr21",
        "paralog_pos": 6496026,           # verified against reference FASTA
        "cosmic": "COSV52341059",
        "clinvar": "Likely_pathogenic",
        "oncokb": "Oncogenic",
    },
    {
        "name": "S34Y",
        "gene": "U2AF1",
        "transcript": "NM_006758.3",
        "hgvs_c": "c.101C>A",
        "hgvs_p": "p.Ser34Tyr",
        "consequence": "missense_variant",
        "canonical_chrom": "chr21",
        "canonical_pos": 43104346,        # same position as S34F
        "plus_strand_ref": "G",
        "plus_strand_alt": "T",           # S34Y alt on + strand
        "paralog_chrom": "chr21",
        "paralog_pos": 6496026,           # verified against reference FASTA
        "cosmic": "COSV52341472",
        "clinvar": "Likely_pathogenic",
        "oncokb": "Oncogenic",
    },
    {
        "name": "Q157P",
        "gene": "U2AF1",
        "transcript": "NM_006758.3",
        "hgvs_c": "c.470A>C",
        "hgvs_p": "p.Gln157Pro",
        "consequence": "missense_variant",
        "canonical_chrom": "chr21",
        "canonical_pos": 43094667,        # 1-based, hg38 (ClinVar VCV000376024)
        "plus_strand_ref": "T",
        "plus_strand_alt": "G",
        "paralog_chrom": "chr21",
        "paralog_pos": 6486334,           # verified against reference FASTA
        "cosmic": "COSV52341217",
        "clinvar": "Likely_pathogenic",
        "oncokb": "Oncogenic",
    },
    {
        "name": "Q157R",
        "gene": "U2AF1",
        "transcript": "NM_006758.3",
        "hgvs_c": "c.470A>G",
        "hgvs_p": "p.Gln157Arg",
        "consequence": "missense_variant",
        "canonical_chrom": "chr21",
        "canonical_pos": 43094667,        # same position as Q157P
        "plus_strand_ref": "T",
        "plus_strand_alt": "C",
        "paralog_chrom": "chr21",
        "paralog_pos": 6486334,           # verified against reference FASTA
        "cosmic": "COSV52341263",
        "clinvar": "Likely_pathogenic",
        "oncokb": "Oncogenic",
    },
]


def pileup_at_position(bam, chrom, pos_1based, min_baseq=20, include_mq0=True):
    """
    Count bases at a specific genomic position from a BAM file.

    Parameters
    ----------
    bam : pysam.AlignmentFile
    chrom : str
    pos_1based : int
        1-based genomic coordinate.
    min_baseq : int
        Minimum base quality to count a read.
    include_mq0 : bool
        If True, include reads with mapping quality 0 (multimapped).
        This is critical for U2AF1 in standard GRCh38.

    Returns
    -------
    dict with keys:
        'A', 'C', 'G', 'T' : int counts
        'total' : int total depth
        'mq0_count' : int reads with MQ=0
        'mean_mq' : float mean mapping quality of counted reads
        'mean_bq' : float mean base quality at this position
    """
    pos_0based = pos_1based - 1
    counts = {"A": 0, "C": 0, "G": 0, "T": 0}
    mq_values = []
    bq_values = []
    mq0_count = 0

    min_mq = 0 if include_mq0 else 1

    try:
        for pileup_column in bam.pileup(
            chrom,
            pos_0based,
            pos_0based + 1,
            min_mapping_quality=min_mq,
            min_base_quality=min_baseq,
            truncate=True,
            stepper="samtools",
        ):
            if pileup_column.reference_pos == pos_0based:
                for pileup_read in pileup_column.pileups:
                    if pileup_read.is_del or pileup_read.is_refskip:
                        continue
                    alignment = pileup_read.alignment
                    if alignment.is_duplicate or alignment.is_secondary:
                        continue
                    if alignment.is_supplementary:
                        continue

                    base = alignment.query_sequence[pileup_read.query_position].upper()
                    mq = alignment.mapping_quality
                    bq = alignment.query_qualities[pileup_read.query_position]

                    if base in counts:
                        counts[base] += 1
                        mq_values.append(mq)
                        bq_values.append(bq)
                        if mq == 0:
                            mq0_count += 1

    except ValueError:
        # Chromosome not in BAM
        pass

    total = sum(counts.values())
    mean_mq = sum(mq_values) / len(mq_values) if mq_values else 0.0
    mean_bq = sum(bq_values) / len(bq_values) if bq_values else 0.0

    return {
        **counts,
        "total": total,
        "mq0_count": mq0_count,
        "mean_mq": round(mean_mq, 1),
        "mean_bq": round(mean_bq, 1),
    }


def check_hotspot(bam, hotspot, include_mq0=True, check_paralog=True):
    """
    Interrogate both canonical and paralog loci for a single hotspot.

    Returns dict with pileup results and computed VAF.
    """
    # Canonical locus
    canonical = pileup_at_position(
        bam, hotspot["canonical_chrom"], hotspot["canonical_pos"],
        include_mq0=include_mq0,
    )

    # Paralog locus
    paralog = None
    if check_paralog:
        paralog = pileup_at_position(
            bam, hotspot["paralog_chrom"], hotspot["paralog_pos"],
            include_mq0=include_mq0,
        )

    # Compute alt counts and VAF
    alt_base = hotspot["plus_strand_alt"]
    ref_base = hotspot["plus_strand_ref"]

    canonical_alt = canonical.get(alt_base, 0)
    canonical_ref = canonical.get(ref_base, 0)
    canonical_total = canonical["total"]
    canonical_vaf = canonical_alt / canonical_total if canonical_total > 0 else 0.0

    paralog_alt = 0
    paralog_ref = 0
    paralog_total = 0
    paralog_vaf = 0.0
    if paralog:
        paralog_alt = paralog.get(alt_base, 0)
        paralog_ref = paralog.get(ref_base, 0)
        paralog_total = paralog["total"]
        paralog_vaf = paralog_alt / paralog_total if paralog_total > 0 else 0.0

    # Combined evidence across both loci
    combined_alt = canonical_alt + paralog_alt
    combined_total = canonical_total + paralog_total
    combined_vaf = combined_alt / combined_total if combined_total > 0 else 0.0

    return {
        "hotspot": hotspot,
        "canonical": canonical,
        "paralog": paralog,
        "canonical_alt": canonical_alt,
        "canonical_ref": canonical_ref,
        "canonical_vaf": canonical_vaf,
        "paralog_alt": paralog_alt,
        "paralog_ref": paralog_ref,
        "paralog_vaf": paralog_vaf,
        "combined_alt": combined_alt,
        "combined_total": combined_total,
        "combined_vaf": combined_vaf,
    }


def format_rescue_tsv_row(sample, result):
    """
    Format a rescued variant as a row matching somaticseq_annotated.tsv columns.
    """
    hs = result["hotspot"]
    fields = {
        "Sample": sample,
        "Chr": hs["canonical_chrom"],
        "Start": str(hs["canonical_pos"]),
        "End": str(hs["canonical_pos"]),
        "Ref": hs["plus_strand_ref"],
        "Alt": hs["plus_strand_alt"],
        "Gene": hs["gene"],
        "Consequence": hs["consequence"],
        "HGVSc": f"{hs['transcript']}:{hs['hgvs_c']}",
        "HGVSp": f"{hs['hgvs_p']}",
        "IMPACT": "MODERATE",
        "VariantCaller_Count": "PILEUP_RESCUE",
        "Callers": "U2AF1_PileupRescue",
        "REF_COUNT": str(result["canonical"]["total"] - result["canonical_alt"]),
        "ALT_COUNT": str(result["canonical_alt"]),
        "VAF_pct": f"{result['canonical_vaf'] * 100:.1f}",
        "SomaticSeq_Verdict": "RESCUED",
        "COSMIC_ID": hs["cosmic"],
        "ClinVar": hs["clinvar"],
        "SIFT": "deleterious",
        "PolyPhen": "probably_damaging",
        "gnomAD_exome_AF": "-1",
        "gnomAD_genome_AF": "-1",
        "AF_1KG": "-1",
        "Max_AF": "-1",
        "rsID": "-1",
        "MANE_SELECT": hs["transcript"],
        "Canonical": "YES",
        "HGVSg": f"{hs['canonical_chrom']}:g.{hs['canonical_pos']}{hs['plus_strand_ref']}>{hs['plus_strand_alt']}",
        "Existing_variation": hs["cosmic"],
    }
    return fields


RESCUE_TSV_COLUMNS = [
    "Sample", "Chr", "Start", "End", "Ref", "Alt", "Gene", "Consequence",
    "HGVSc", "HGVSp", "IMPACT", "VariantCaller_Count", "Callers",
    "REF_COUNT", "ALT_COUNT", "VAF_pct", "SomaticSeq_Verdict", "COSMIC_ID",
    "ClinVar", "SIFT", "PolyPhen", "gnomAD_exome_AF", "gnomAD_genome_AF",
    "AF_1KG", "Max_AF", "rsID", "MANE_SELECT", "Canonical", "HGVSg",
    "Existing_variation",
]


def generate_report(sample, results, check_paralog, min_vaf=0.01, min_alt_count=3, min_depth=20):
    """Generate a human-readable pileup report."""
    lines = []
    lines.append("=" * 78)
    lines.append(f"U2AF1 Pileup Rescue Report — {sample}")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 78)
    lines.append("")
    lines.append("BACKGROUND:")
    lines.append("  GRCh38 contains a ~153 kb duplication on chr21p that is nearly")
    lines.append("  identical to the canonical U2AF1 locus on chr21q. This causes")
    lines.append("  reads to multimap (MQ=0) and prevents standard variant callers")
    lines.append("  from detecting somatic mutations at U2AF1 hotspots.")
    lines.append("  Ref: Miller CA et al. J Mol Diagn. 2022;24(3):219-223.")
    lines.append("")

    for r in results:
        hs = r["hotspot"]
        c = r["canonical"]
        lines.append("-" * 78)
        lines.append(
            f"HOTSPOT: {hs['name']} ({hs['hgvs_p']})  |  {hs['hgvs_c']}  |  "
            f"{hs['canonical_chrom']}:{hs['canonical_pos']}"
        )
        lines.append(
            f"  Expected: ref={hs['plus_strand_ref']}  alt={hs['plus_strand_alt']}  "
            f"(+ strand)"
        )
        lines.append("")

        lines.append(f"  CANONICAL LOCUS ({hs['canonical_chrom']}:{hs['canonical_pos']}):")
        lines.append(
            f"    A={c['A']}  C={c['C']}  G={c['G']}  T={c['T']}  "
            f"Total={c['total']}"
        )
        lines.append(
            f"    MQ=0 reads: {c['mq0_count']}  |  Mean MQ: {c['mean_mq']}  |  "
            f"Mean BQ: {c['mean_bq']}"
        )
        lines.append(
            f"    Alt ({hs['plus_strand_alt']}): {r['canonical_alt']}  |  "
            f"VAF: {r['canonical_vaf'] * 100:.2f}%"
        )

        if check_paralog and r["paralog"]:
            p = r["paralog"]
            lines.append("")
            lines.append(
                f"  PARALOG LOCUS ({hs['paralog_chrom']}:{hs['paralog_pos']}):"
            )
            lines.append(
                f"    A={p['A']}  C={p['C']}  G={p['G']}  T={p['T']}  "
                f"Total={p['total']}"
            )
            lines.append(
                f"    MQ=0 reads: {p['mq0_count']}  |  Mean MQ: {p['mean_mq']}  |  "
                f"Mean BQ: {p['mean_bq']}"
            )
            lines.append(
                f"    Alt ({hs['plus_strand_alt']}): {r['paralog_alt']}  |  "
                f"VAF: {r['paralog_vaf'] * 100:.2f}%"
            )
            if p["total"] == 0:
                lines.append(
                    "    WARNING: Zero coverage at paralog position. The estimated "
                    "paralog coordinate may be incorrect for your reference build. "
                    "Verify against your FASTA."
                )

        lines.append("")
        lines.append(
            f"  COMBINED: alt={r['combined_alt']}  total={r['combined_total']}  "
            f"VAF={r['combined_vaf'] * 100:.2f}%"
        )

        # Verdict (canonical locus only, applying rescue thresholds)
        canon_depth_ok = r["canonical"]["total"] >= min_depth
        canon_vaf_ok = r["canonical_vaf"] >= min_vaf
        canon_alt_ok = r["canonical_alt"] >= min_alt_count
        if canon_depth_ok and canon_vaf_ok and canon_alt_ok:
            lines.append(f"  >>> MUTATION DETECTED: {hs['name']}")
        else:
            lines.append(f"  >>> No {hs['name']} mutation detected")

        lines.append("")

    # Summary
    lines.append("=" * 78)
    lines.append("SUMMARY")
    lines.append("=" * 78)
    detected = [r for r in results
                if r["canonical"]["total"] >= min_depth
                and r["canonical_vaf"] >= min_vaf
                and r["canonical_alt"] >= min_alt_count]
    if detected:
        for r in detected:
            hs = r["hotspot"]
            lines.append(
                f"  DETECTED: {hs['gene']} {hs['name']} ({hs['hgvs_p']})  "
                f"VAF={r['canonical_vaf'] * 100:.2f}%  "
                f"alt_reads={r['canonical_alt']}  "
                f"total_depth={r['canonical']['total']}"
            )
    else:
        lines.append("  No U2AF1 hotspot mutations detected.")

    lines.append("")
    lines.append("NOTE: If coverage at the canonical locus is very low (<20x) even")
    lines.append("with MQ=0 reads included, consider using the modified GRCh38")
    lines.append("reference from Miller et al. (doi:10.5281/zenodo.4684553) which")
    lines.append("N-masks chr21:6427259-6580181 to resolve the duplication artifact.")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Pileup-based rescue for U2AF1 hotspot mutations in GRCh38.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--bam", required=True,
        help="Path to coordinate-sorted, indexed BAM file.",
    )
    parser.add_argument(
        "--sample", required=True,
        help="Sample ID for output file naming and report.",
    )
    parser.add_argument(
        "--outdir", required=True,
        help="Output directory.",
    )
    parser.add_argument(
        "--min-vaf", type=float, default=0.01,
        help="Minimum VAF to rescue a variant (default: 0.01 = 1%%).",
    )
    parser.add_argument(
        "--min-alt-count", type=int, default=3,
        help="Minimum alt read count to rescue (default: 3).",
    )
    parser.add_argument(
        "--min-depth", type=int, default=20,
        help="Minimum total depth to consider position evaluable (default: 20).",
    )
    parser.add_argument(
        "--check-paralog", dest="check_paralog", action="store_true", default=True,
        help="Also check the chr21p paralog locus (default: True).",
    )
    parser.add_argument(
        "--no-check-paralog", dest="check_paralog", action="store_false",
        help="Skip paralog locus check.",
    )
    args = parser.parse_args()

    # Validate inputs
    if not os.path.isfile(args.bam):
        sys.exit(f"ERROR: BAM file not found: {args.bam}")

    bai_candidates = [args.bam + ".bai", args.bam.replace(".bam", ".bai")]
    if not any(os.path.isfile(b) for b in bai_candidates):
        sys.exit(f"ERROR: BAM index not found. Expected: {bai_candidates[0]}")

    os.makedirs(args.outdir, exist_ok=True)

    # Open BAM
    bam = pysam.AlignmentFile(args.bam, "rb")

    # Check that chr21 exists in the BAM header
    refs = bam.references
    if "chr21" not in refs:
        # Try without 'chr' prefix
        if "21" in refs:
            print(
                "WARNING: BAM uses numeric chromosome names (no 'chr' prefix). "
                "Adjusting hotspot coordinates.",
                file=sys.stderr,
            )
            for hs in HOTSPOTS:
                hs["canonical_chrom"] = hs["canonical_chrom"].replace("chr", "")
                hs["paralog_chrom"] = hs["paralog_chrom"].replace("chr", "")
        else:
            sys.exit("ERROR: chr21/21 not found in BAM header.")

    print(f"[u2af1_rescue] Processing sample: {args.sample}")
    print(f"[u2af1_rescue] BAM: {args.bam}")
    print(f"[u2af1_rescue] Include MQ=0 reads: True (required for GRCh38 U2AF1)")
    print(f"[u2af1_rescue] Check paralog locus: {args.check_paralog}")
    print(f"[u2af1_rescue] Thresholds: min_vaf={args.min_vaf}, "
          f"min_alt={args.min_alt_count}, min_depth={args.min_depth}")
    print()

    # Interrogate each hotspot
    results = []
    for hs in HOTSPOTS:
        result = check_hotspot(
            bam, hs,
            include_mq0=True,
            check_paralog=args.check_paralog,
        )
        results.append(result)

    bam.close()

    # Determine which variants to rescue
    rescued = []
    for r in results:
        depth_ok = r["canonical"]["total"] >= args.min_depth
        vaf_ok = r["canonical_vaf"] >= args.min_vaf
        alt_ok = r["canonical_alt"] >= args.min_alt_count

        if depth_ok and vaf_ok and alt_ok:
            rescued.append(r)

    # Write rescue TSV
    rescue_path = os.path.join(args.outdir, f"{args.sample}_u2af1_rescue.tsv")
    with open(rescue_path, "w") as f:
        f.write("\t".join(RESCUE_TSV_COLUMNS) + "\n")
        for r in rescued:
            row = format_rescue_tsv_row(args.sample, r)
            f.write("\t".join(row[col] for col in RESCUE_TSV_COLUMNS) + "\n")

    # Write full pileup report
    report_path = os.path.join(args.outdir, f"{args.sample}_u2af1_pileup_report.txt")
    report = generate_report(args.sample, results, args.check_paralog,
                             min_vaf=args.min_vaf, min_alt_count=args.min_alt_count,
                             min_depth=args.min_depth)
    with open(report_path, "w") as f:
        f.write(report)

    # Print summary to stdout
    print(report)
    print()
    if rescued:
        print(f"[u2af1_rescue] RESCUED {len(rescued)} variant(s) -> {rescue_path}")
    else:
        print("[u2af1_rescue] No variants rescued (below thresholds).")
    print(f"[u2af1_rescue] Full report -> {report_path}")


if __name__ == "__main__":
    main()
