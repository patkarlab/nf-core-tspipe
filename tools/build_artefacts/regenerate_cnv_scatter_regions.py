#!/usr/bin/env python3
"""regenerate_cnv_scatter_regions.py — build cnv_scatter_regions.txt from the
panel BED.

The legacy MyOPool chrwise_list.txt was hand-curated against hg19 coordinates.
Running CNVKit on hg38 then plotting against those hg19 regions produces empty
scatter pages because nothing overlaps. This script regenerates the regions
file directly from the panel BED so coordinates always match the run.

Output format (one line per page, whitespace-separated, two columns):
  COL1   comma-separated 'chrN:start-stop' regions
  COL2   comma-separated 'GENE_Ex_N' band labels (one per region)

One line per chromosome present in the BED. Regions within a chromosome are
ordered by genomic start position. Multiple BED rows that map to the same
GENE_Ex_N (e.g. tiled probes 12 and 23 both labeled GNB1_Ex_11) are merged
into a single region spanning min-start to max-end.

Usage:
  python3 regenerate_cnv_scatter_regions.py \\
      --bed    bedfiles/MYOPOOL_240125_UBTF_hg38.bed \\
      --output references/myeloid/cnv_scatter_regions.txt

Compare against an existing file (sanity-check before overwrite):
  python3 regenerate_cnv_scatter_regions.py \\
      --bed bedfiles/MYOPOOL_240125_UBTF_hg38.bed \\
      --output /tmp/regions_new.txt
  diff <(cut -f2 /tmp/regions_new.txt)  <(cut -f2 references/myeloid/cnv_scatter_regions.txt)
"""

import argparse
import logging
import os
import re
import sys
from collections import defaultdict, OrderedDict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def parse_bed_gene_exon(name_field):
    """Extract (gene, exon) from a BED name. Mirrors the post-2026-05-14 parser
    in 12c_cnv_loo_qc.py / 18_cnv_annotate.py."""
    last = name_field.split(";")[-1].strip().strip('"').strip("'")

    # Strip leading numeric-id prefixes like '926535_53648197_'
    while True:
        m = re.match(r"^\d+_", last)
        if not m:
            break
        last = last[m.end():]

    # GENE_Ex_<exon>
    m = re.match(r"^([A-Za-z][A-Za-z0-9-]*)_[Ee][Xx]_?(\w+)$", last)
    if m:
        return m.group(1), m.group(2)

    # Tiling probe fallback: clean up trailing junk
    last = re.sub(r"\.\.\d+$", "", last)
    last = re.sub(r"_[Ee][Xx]_?\w+$", "", last)
    last = re.sub(r"(_\d+)+$", "", last)
    return (last, None) if last else (None, None)


def parse_band_label(name_field):
    """Return the cleaned band label for the scatter regions file.

    For probes with an exon: 'GENE_Ex_N'.
    For tiling probes without an exon: 'GENE' (no suffix).
    """
    gene, exon = parse_bed_gene_exon(name_field)
    if not gene:
        return None
    if exon is not None:
        return f"{gene}_Ex_{exon}"
    return gene


def chrom_sort_key(chrom):
    """Sort chromosomes numerically (1..22), then X, Y, MT, then other."""
    c = re.sub(r"^chr", "", chrom, flags=re.IGNORECASE)
    if c.isdigit():
        return (0, int(c))
    if c.upper() == "X":
        return (1, 0)
    if c.upper() == "Y":
        return (2, 0)
    if c.upper() in ("M", "MT"):
        return (3, 0)
    return (4, c)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bed", required=True,
                    help="Panel BED (4 columns: chrom, start, end, name)")
    ap.add_argument("--output", required=True,
                    help="Output regions file path")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print summary, do not write the file")
    ap.add_argument("--include-antitarget", action="store_true",
                    help="Include rows whose name contains 'Antitarget' "
                         "(default: drop them, matching the scatter behavior)")
    args = ap.parse_args()

    if not os.path.isfile(args.bed):
        log.error("BED not found: %s", args.bed)
        return 1

    # Read BED, group by (chrom, band_label) so duplicate probes for the same
    # exon merge into one region.
    # Structure: per_chr[chrom] = OrderedDict of band_label -> [min_start, max_end]
    per_chr = defaultdict(OrderedDict)
    skipped_antitarget = 0
    skipped_unparsed = 0
    total = 0

    with open(args.bed) as f:
        for line in f:
            if line.startswith(("#", "track")):
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 4:
                continue
            total += 1
            chrom, start, end, name = parts[0], int(parts[1]), int(parts[2]), parts[3]

            if (not args.include_antitarget) and "Antitarget" in name:
                skipped_antitarget += 1
                continue

            band = parse_band_label(name)
            if not band:
                skipped_unparsed += 1
                continue

            bands = per_chr[chrom]
            if band in bands:
                cur_start, cur_end = bands[band]
                bands[band] = [min(cur_start, start), max(cur_end, end)]
            else:
                bands[band] = [start, end]

    log.info("BED rows read: %d", total)
    log.info("  skipped (Antitarget): %d", skipped_antitarget)
    log.info("  skipped (unparsed):   %d", skipped_unparsed)
    log.info("Chromosomes with bands: %d", len(per_chr))
    log.info("Total distinct bands:   %d",
             sum(len(b) for b in per_chr.values()))

    # Sort within each chromosome by min start position, then emit
    sorted_chroms = sorted(per_chr.keys(), key=chrom_sort_key)
    output_lines = []
    summary_rows = []

    for chrom in sorted_chroms:
        bands = per_chr[chrom]
        items = sorted(bands.items(), key=lambda kv: kv[1][0])
        regions_col = ",".join(f"{chrom}:{s}-{e}" for _, (s, e) in items)
        bands_col = ",".join(b for b, _ in items)
        output_lines.append(f"{regions_col}\t{bands_col}")
        summary_rows.append((chrom, len(items),
                             items[0][1][0], items[-1][1][1]))

    log.info("")
    log.info("Per-chromosome summary:")
    log.info("  %-8s  %6s  %12s  %12s", "chrom", "bands", "min_start", "max_end")
    for chrom, n, mn, mx in summary_rows:
        log.info("  %-8s  %6d  %12d  %12d", chrom, n, mn, mx)

    if args.dry_run:
        log.info("")
        log.info("Dry run -- not writing %s", args.output)
        log.info("First emitted line (first 200 chars):")
        log.info("  %s", output_lines[0][:200])
        return 0

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as out:
        out.write("\n".join(output_lines) + "\n")

    log.info("")
    log.info("Wrote %d lines to %s", len(output_lines), args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
