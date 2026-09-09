#!/usr/bin/env python3
"""
igv_reports.py - Generate self-contained IGV HTML reports for clinical variants.

Reads the clinical TSV, converts variants to a VCF, and generates an interactive
HTML report with embedded IGV views of each variant.

Ported from production scripts/16_igv_reports.py (2026-05-12) with two
behavior-preserving changes for the nf-core container environment:

  1. pandas.read_csv -> csv.DictReader  (pandas is not in the igv-reports
     biocontainer; csv is stdlib).
  2. subprocess bgzip/tabix -> pysam.tabix_compress/tabix_index  (bgzip and
     tabix binaries are not in the igv-reports biocontainer; pysam is, and
     its APIs produce byte-equivalent output).

Other than dependency surface, the VCF generated and the create_report
invocation are identical to production. Output HTML is byte-equivalent
modulo timestamps embedded by create_report.

Usage:
    python igv_reports.py \\
        --sample 25NGS1307 \\
        --input 25NGS1307.somaticseq.clinical.final.tsv \\
        --bam 25NGS1307.final.bam \\
        --fasta hg38.fa \\
        --output 25NGS1307_igv_report.html
"""

import argparse
import csv
import logging
import os
import sys

import pysam

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate IGV HTML reports for clinical variants"
    )
    parser.add_argument("-s", "--sample", required=True, help="Sample name")
    parser.add_argument("--extra-input", default=None,
                        help="Filtered TSV (same columns); rows inside --spikein-regions are added (SPIKEIN_V1d)")
    parser.add_argument("--spikein-regions", default=None,
                        help="assets/<panel>/spikein_regions.tsv; regulatory rows define the regions (SPIKEIN_V1d)")
    parser.add_argument("-i", "--input", required=True,
                        help="Input clinical TSV")
    parser.add_argument("--bam", required=True, help="BAM file (post-ABRA2)")
    parser.add_argument("--fasta", required=True,
                        help="Reference FASTA (must be indexed; .fai sibling required)")
    parser.add_argument("-o", "--output", required=True,
                        help="Output HTML")
    parser.add_argument("--flanking", type=int, default=500,
                        help="Flanking region in bp (default: 500, matches production)")
    # IGV_V2B
    parser.add_argument("--flt3-consensus", default=None,
                        help="<sample>_flt3_consensus.tsv; one report row per FLT3-ITD consensus event (IGV_V2B)")
    parser.add_argument("--gene-track", default=None,
                        help="annotation file (BED/GTF) drawn under the reads (IGV_V2B)")
    parser.add_argument("--gene-track-name", default="Exons (panel)",
                        help="display name of --gene-track (default: 'Exons (panel)')")
    parser.add_argument("--color-by", default="strand",
                        help="igv.js colorBy for the alignment track: strand (default), none, ...")
    return parser.parse_args()


def read_clinical_tsv(path):
    """Read clinical TSV as a list of dicts with all values as strings.

    Equivalent to pandas.read_csv(path, sep='\\t', dtype=str) for our use case.
    """
    with open(path) as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        return list(reader)


# Chromosome sort order: chr1..22, chrX, chrY, chrM, everything else last.
CHROM_ORDER = {chrom: i for i, chrom in enumerate(
    [f"chr{i}" for i in range(1, 23)] + ["chrX", "chrY", "chrM"]
)}


def _chrom_sort_key(row):
    return (CHROM_ORDER.get(row["Chr"], 99), int(row["Start"]))


def _clean(value):
    """Production's missing-value sentinel handling: blanks, -1, nan, '.' all
    collapse to '.' for VCF info fields."""
    v = str(value) if value is not None else "."
    return "." if v in ("-1", "", "nan") else v


# IGV_V2B: FLT3-ITD consensus events as report rows. The ITD pathway (FLT3_ITD_EXT, filt3r,
# getITD, Pindel ensemble) is separate from SomaticSeq; a low-VAF ITD is often REJECT/LOW_CALLERS
# in the variant tables and would otherwise never get an IGV view.
FLT3_CHROM = "chr13"
FLT3_NEGATIVE = {"", "negative", "no_itd", "no-itd"}


def flt3_consensus_rows(path, fasta_path, sample):
    """Rows shaped like read_clinical_tsv() output, one per positive consensus event."""
    rows = []
    with open(path) as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        events = list(reader)
    if not events:
        return rows
    fasta = pysam.FastaFile(fasta_path)
    try:
        for ev in events:
            status = (ev.get("status") or "").strip().lower()
            if status in FLT3_NEGATIVE:
                continue
            try:
                pos = int(round(float(ev.get("pos_hg38") or "")))
            except ValueError:
                log.warning("IGV_V2B: FLT3 consensus event without a usable pos_hg38, skipped: %s", ev)
                continue
            ref = fasta.fetch(FLT3_CHROM, pos - 1, pos).upper()
            ins = (ev.get("inserted_seq") or "").strip().upper()
            try:
                length = int(round(float(ev.get("length_bp") or "0")))
            except ValueError:
                length = len(ins)
            row = {
                "Chr": FLT3_CHROM, "Start": str(pos), "Ref": ref,
                "Alt": (ref + ins) if ins else "<DUP>",
                "Gene": "FLT3",
                "Consequence": "FLT3-ITD_%dbp" % (length or len(ins)),
                "HGVSp": ev.get("hgvsp") or "",
                "VAF_pct": ev.get("vaf_pct_mean") or "",
                "Callers": ev.get("tools") or "",
                "rsID": "", "Filter": "PASS",
                "_flt3_end": str(pos + (length or len(ins))) if not ins else "",
            }
            rows.append(row)
    finally:
        fasta.close()
    log.info("IGV_V2B: %d FLT3-ITD consensus event(s) from %s", len(rows), path)
    return rows


def write_track_config(path, sample, vcf_path, bam_path, gene_track, gene_track_name, color_by):
    """igv-reports --track-config: every key other than url/format/type is passed to igv.js."""
    import json
    tracks_cfg = [
        {"url": os.path.abspath(vcf_path), "format": "vcf", "type": "variant",
         "name": os.path.basename(vcf_path).replace(".gz", "")},
        {"url": os.path.abspath(bam_path), "format": "bam", "type": "alignment",
         "name": os.path.basename(bam_path).replace(".bam", "")},
    ]
    if color_by and color_by.lower() != "none":
        tracks_cfg[1]["colorBy"] = color_by
    if gene_track:
        tracks_cfg.append({"url": os.path.abspath(gene_track), "type": "annotation",
                           "name": gene_track_name, "displayMode": "EXPANDED", "height": 70})
    with open(path, "w") as fh:
        json.dump(tracks_cfg, fh, indent=2)
    return path


def tsv_to_vcf(rows, vcf_gz_path):
    """Write the clinical rows as a bgzipped + tabix-indexed VCF at vcf_gz_path.

    rows: list of dicts from read_clinical_tsv().
    vcf_gz_path: output path ending in .vcf.gz. The .tbi sibling will be
        created next to it.

    Behavior mirrors production scripts/16_igv_reports.py:tsv_to_vcf except
    that compression and indexing are done via pysam instead of shelling out
    to bgzip and tabix.
    """
    rows_sorted = sorted(rows, key=_chrom_sort_key)

    raw_vcf = vcf_gz_path[:-3] if vcf_gz_path.endswith(".gz") else vcf_gz_path + ".raw"

    header_lines = [
        "##fileformat=VCFv4.2",
        '##INFO=<ID=Gene,Number=1,Type=String,Description="Gene symbol">',
        '##INFO=<ID=Consequence,Number=1,Type=String,Description="Variant consequence">',
        '##INFO=<ID=HGVSp,Number=1,Type=String,Description="Protein HGVS">',
        '##INFO=<ID=VAF_pct,Number=1,Type=Float,Description="Variant allele frequency (%)">',
        '##INFO=<ID=Callers,Number=1,Type=String,Description="Variant callers">',
        '##INFO=<ID=END,Number=1,Type=Integer,Description="End position (IGV_V2B: FLT3-ITD without inserted sequence)">',
        '##INFO=<ID=SVTYPE,Number=1,Type=String,Description="Structural variant type">',
        '##ALT=<ID=DUP,Description="Duplication">',
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO",
    ]

    with open(raw_vcf, "w") as fh:
        fh.write("\n".join(header_lines) + "\n")
        for row in rows_sorted:
            chrom = row["Chr"]
            pos = str(int(row["Start"]))
            ref = row["Ref"]
            alt = row["Alt"]
            rsid = _clean(row.get("rsID"))
            filt = _clean(row.get("Filter")) or "PASS"
            if filt == ".":
                filt = "PASS"

            info_parts = []
            for key, raw_val in [
                ("Gene", row.get("Gene")),
                ("Consequence", row.get("Consequence")),
                ("HGVSp", row.get("HGVSp")),
                ("VAF_pct", row.get("VAF_pct")),
                ("Callers", row.get("Callers")),
            ]:
                val = _clean(raw_val)
                if val != ".":
                    # Mirror production: replace ';' with ',' since ';' is the
                    # INFO field separator.
                    info_parts.append(f"{key}={val.replace(';', ',')}")
            if row.get("_flt3_end"):   # IGV_V2B: symbolic <DUP> needs END
                info_parts.append(f"END={row['_flt3_end']};SVTYPE=DUP")
            info = ";".join(info_parts) if info_parts else "."

            fh.write(f"{chrom}\t{pos}\t{rsid}\t{ref}\t{alt}\t.\t{filt}\t{info}\n")

    # Compress with pysam (bgzip-compatible) and tabix-index.
    pysam.tabix_compress(raw_vcf, vcf_gz_path, force=True)
    os.remove(raw_vcf)
    pysam.tabix_index(vcf_gz_path, preset="vcf", force=True)
    log.info("Created VCF: %s (.tbi sibling indexed)", vcf_gz_path)


def main():
    args = parse_args()

    for path, label in [
        (args.input, "Clinical TSV"),
        (args.bam, "BAM"),
        (args.bam + ".bai", "BAM index"),
        (args.fasta, "Reference FASTA"),
        (args.fasta + ".fai", "Reference FASTA index"),
    ]:
        if not os.path.isfile(path):
            log.error("%s not found: %s", label, path)
            sys.exit(1)

    rows = read_clinical_tsv(args.input)
    log.info("Read %d clinical variants from %s", len(rows), args.input)

    # SPIKEIN_V1d (D13b-2): filtered-table calls inside the spike-in regions join the site list so
    # the dashboard's Spike-in tab IGV chips resolve; de-duplicated against the clinical rows.
    if args.extra_input and args.spikein_regions:
        regions = []
        with open(args.spikein_regions) as fh:
            header = None
            for line in fh:
                line = line.rstrip("\n")
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if header is None:
                    header = parts
                    continue
                rec = dict(zip(header, parts))
                if rec.get("class") == "regulatory":
                    regions.append((rec["chrom"], int(rec["start"]), int(rec["end"])))
        have = {(r["Chr"], r["Start"], r["Ref"], r["Alt"]) for r in rows}
        extra = []
        for r in read_clinical_tsv(args.extra_input):
            try:
                pos = int(r["Start"])
            except (KeyError, ValueError):
                continue
            if any(r["Chr"] == c and s < pos <= e for c, s, e in regions):
                key = (r["Chr"], r["Start"], r["Ref"], r["Alt"])
                if key not in have:
                    have.add(key)
                    extra.append(r)
        rows.extend(extra)
        log.info("SPIKEIN_V1d: added %d spike-in region call(s) from %s (%d regions)",
                 len(extra), args.extra_input, len(regions))

    # IGV_V2B (D11): FLT3-ITD consensus events, de-duplicated against rows already present
    if args.flt3_consensus and os.path.isfile(args.flt3_consensus):
        have = {(r["Chr"], r["Start"], r["Ref"], r["Alt"]) for r in rows}
        added = 0
        for r in flt3_consensus_rows(args.flt3_consensus, args.fasta, args.sample):
            key = (r["Chr"], r["Start"], r["Ref"], r["Alt"])
            if key not in have:
                have.add(key)
                rows.append(r)
                added += 1
        log.info("IGV_V2B: added %d FLT3-ITD row(s)", added)

    if not rows:
        log.warning("No variants found -- skipping report generation")
        # Touch an empty output so downstream channels do not break.
        with open(args.output, "w") as fh:
            fh.write("<html><body><p>No clinical variants for this sample.</p></body></html>\n")
        sys.exit(0)

    outdir = os.path.dirname(os.path.abspath(args.output)) or "."
    os.makedirs(outdir, exist_ok=True)
    vcf_path = os.path.join(outdir, f"{args.sample}.clinical.vcf.gz")
    tsv_to_vcf(rows, vcf_path)

    # Build create_report invocation. Match production's args exactly,
    # except --genome (production cloud-fetched hg38; we provide a local FASTA).
    import subprocess
    # IGV_V2B: tracks via --track-config so igv.js options (colorBy, annotation track) pass through
    track_cfg = write_track_config(os.path.join(outdir, f"{args.sample}.igv_tracks.json"), args.sample,
                                   vcf_path, args.bam, args.gene_track, args.gene_track_name, args.color_by)
    cmd = [
        "create_report",
        vcf_path,
        "--fasta", args.fasta,
        "--track-config", track_cfg,
        "--info-columns", "Gene", "Consequence", "HGVSp", "VAF_pct", "Callers",
        "--flanking", str(args.flanking),
        "--title", f"{args.sample} Clinical Variant Review",
        "--output", args.output,
    ]
    log.info("Running: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log.error("create_report failed:\n%s", result.stderr)
        sys.exit(1)
    if result.stdout.strip():
        log.info(result.stdout.strip())

    size_mb = os.path.getsize(args.output) / (1024 * 1024)
    log.info("IGV report generated: %s (%.1f MB, %d variants)",
             args.output, size_mb, len(rows))


if __name__ == "__main__":
    main()
