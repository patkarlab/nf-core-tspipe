#!/usr/bin/env python3
"""
bin/plot_exon_ratio_batch.py  (EXON_PLOTS_V1)

Per-sample exon-level copy-ratio figures for the EXON_PLOTS process. One
figure per chromosome that carries
  - a non-neutral consensus gene (consensus_call != NEUTRAL), or
  - a DECoN call at BF >= --min-bf (sub-threshold calls included on purpose), or
  - a gene from the focal-CNV target BED (--focal-bed, optional),
with every panel gene of that chromosome on the axis in genomic order.
Writes <outdir>/<sample>.<chrom>_exons.png and an index
<outdir>/<sample>.exon_plots.tsv (chrom, n_genes, reasons, file) so the
dashboard can list the figures. The index is written even when nothing
qualifies.

Inputs: the CMX_V2 consensus JSON (tracks.cnr_bins), the consensus genes
TSV (gene, chrom, start, ..., consensus_call), the DECoN filtered table
(optional), the focal-CNV BED (optional). Python 3.6, matplotlib >= 3.2.
"""

import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plot_exon_ratio import read_json_bins, read_decon_calls, render, CHROM_ORDER  # noqa: E402


def read_consensus_genes(path):
    by_chrom = {}
    with open(path) as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for r in reader:
            try:
                start = int(r["start"])
            except (KeyError, ValueError):
                continue
            by_chrom.setdefault(r["chrom"], []).append(
                (start, r["gene"], r.get("consensus_call", "NA"), r.get("tier", "NA")))
    for c in by_chrom:
        by_chrom[c].sort()
    return by_chrom


def read_focal_chroms(path):
    chroms = set()
    if not path or not os.path.isfile(path):
        return chroms
    with open(path) as fh:
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if len(p) >= 3 and not line.startswith("#"):
                chroms.add(p[0] if p[0].startswith("chr") else "chr" + p[0])
    return chroms


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample", required=True)
    ap.add_argument("--json", required=True, help="consensus JSON")
    ap.add_argument("--genes-tsv", required=True, help="consensus genes TSV")
    ap.add_argument("--decon", default=None, help="DECoN filtered table (optional)")
    ap.add_argument("--focal-bed", default=None, help="focal-CNV target BED (optional)")
    ap.add_argument("--min-bf", type=float, default=5.0, help="DECoN BF at or above which a chromosome is drawn")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--ymax", type=float, default=3.0)
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    bins = read_json_bins(args.json)
    genes_by_chrom = read_consensus_genes(args.genes_tsv)
    decon = read_decon_calls(args.decon) if args.decon and os.path.isfile(args.decon) else []
    focal = read_focal_chroms(args.focal_bed)

    reasons = {}
    for chrom, rows in genes_by_chrom.items():
        nn = [g for _, g, call, _ in rows if call not in ("NEUTRAL", "NA", "")]
        if nn:
            reasons.setdefault(chrom, []).append("consensus:" + ",".join(nn))
    dec_by_chrom = {}
    for c in decon:
        if c["bf"] >= args.min_bf:
            dec_by_chrom.setdefault(c["chrom"], []).append("%s(%s,BF%.1f)" % (c["gene"], c["type"][:3], c["bf"]))
    for chrom, items in dec_by_chrom.items():
        reasons.setdefault(chrom, []).append("decon:" + ",".join(sorted(set(items))))
    for chrom in focal:
        if chrom in genes_by_chrom:
            reasons.setdefault(chrom, []).append("focal")

    index_path = os.path.join(args.outdir, "%s.exon_plots.tsv" % args.sample)
    n_drawn = 0
    with open(index_path, "w") as idx:
        idx.write("sample\tchrom\tn_genes\treasons\tfile\n")
        for chrom in sorted(reasons, key=lambda c: CHROM_ORDER.get(c, 99)):
            genes = [g for _, g, _, _ in genes_by_chrom.get(chrom, [])]
            if not genes:
                continue
            out = os.path.join(args.outdir, "%s.%s_exons.png" % (args.sample, chrom))
            n, missing = render(bins, genes, out, decon_calls=decon, sample=args.sample, ymax=args.ymax)
            if n == 0:
                sys.stderr.write("[warn] %s: no bins on %s\n" % (args.sample, chrom))
                continue
            n_drawn += 1
            idx.write("\t".join([args.sample, chrom, str(len(genes) - len(missing)),
                                 ";".join(reasons[chrom]), os.path.basename(out)]) + "\n")
    print("[ok] %s: %d figure(s) -> %s (index %s)" % (args.sample, n_drawn, args.outdir, os.path.basename(index_path)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
