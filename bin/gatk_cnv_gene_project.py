#!/usr/bin/env python3
"""Project GATK called copy-ratio segments onto panel gene intervals and
plot the denoised genome profile (TGC_V1).

Inputs:
  --called    CallCopyRatioSegments output (.called.seg): SAM-style '@'
              header, then CONTIG START END NUM_POINTS_COPY_RATIO
              MEAN_LOG2_COPY_RATIO CALL (+ / - / 0).
  --denoised  DenoiseReadCounts denoised copy ratios: '@' header, then
              CONTIG START END LOG2_COPY_RATIO.
  --exonwise  Panel exonwise BED (chrom start end label). Gene unit =
              label with a trailing _exon_N / _intron<N> suffix stripped
              (GENE_5UTR style labels remain distinct units, matching the
              panel census convention).

Outputs:
  --out-tsv   Per-gene table: gene chrom start end n_bins
              median_denoised_log2 seg_call seg_mean_log2 n_segments.
              seg_call is the CALL of the largest-overlap segment;
              seg_mean_log2 is the overlap-length-weighted mean of
              segment means.
  --out-plot  Genome-wide matplotlib PNG (denoised bins + segment means
              colored by call). Plot failure is non-fatal (module output
              is optional); the GATK R plotters are deliberately unused
              (R deps absent on the host env).
"""

import argparse
import os
import re
import statistics
import sys

EXON_SUFFIX = re.compile(r"_(exon_\d+[A-Za-z]?|intron\d*)$")


def fail(msg):
    sys.stderr.write("[error] {0}\n".format(msg))
    sys.exit(1)


def read_table(path, expect_cols):
    """Read a GATK TSV ('@' header lines, then a column-header row)."""
    rows = []
    header = None
    with open(path) as fh:
        for line in fh:
            if line.startswith("@"):
                continue
            parts = line.rstrip("\n").split("\t")
            if header is None:
                header = parts
                missing = [c for c in expect_cols if c not in header]
                if missing:
                    fail("{0}: missing columns {1} (header: {2})".format(
                        path, ",".join(missing), ",".join(header)))
                idx = dict((c, header.index(c)) for c in expect_cols)
                continue
            if len(parts) < len(header):
                continue
            rows.append(tuple(parts[idx[c]] for c in expect_cols))
    if header is None or not rows:
        fail("{0}: no data rows".format(path))
    return rows


def read_genes(exonwise):
    genes = {}
    with open(exonwise) as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.rstrip("\n")
            if not line or line.startswith(("#", "track", "browser")):
                continue
            parts = line.split("\t")
            if len(parts) < 4:
                fail("{0} line {1}: expected 4 columns".format(exonwise, lineno))
            chrom, start, end, label = parts[0], int(parts[1]), int(parts[2]), parts[3]
            gene = EXON_SUFFIX.sub("", label)
            key = (chrom, gene)
            if key in genes:
                g = genes[key]
                genes[key] = (min(g[0], start), max(g[1], end))
            else:
                genes[key] = (start, end)
    if not genes:
        fail("no gene intervals derived from {0}".format(exonwise))
    return genes


def overlap(a1, a2, b1, b2):
    return max(0, min(a2, b2) - max(a1, b1))


def main():
    ap = argparse.ArgumentParser(description="GATK CNV gene projection (TGC_V1)")
    ap.add_argument("--called", required=True)
    ap.add_argument("--denoised", required=True)
    ap.add_argument("--exonwise", required=True)
    ap.add_argument("--sample", required=True)
    ap.add_argument("--out-tsv", required=True)
    ap.add_argument("--out-plot", required=True)
    args = ap.parse_args()

    for p in (args.called, args.denoised, args.exonwise):
        if not os.path.isfile(p):
            fail("input not found: {0}".format(p))

    segs = [(c, int(s), int(e), float(m), call)
            for c, s, e, m, call in read_table(
                args.called,
                ["CONTIG", "START", "END", "MEAN_LOG2_COPY_RATIO", "CALL"])]
    bins = [(c, int(s), int(e), float(l))
            for c, s, e, l in read_table(
                args.denoised,
                ["CONTIG", "START", "END", "LOG2_COPY_RATIO"])]
    genes = read_genes(args.exonwise)

    seg_by_chrom = {}
    for c, s, e, m, call in segs:
        seg_by_chrom.setdefault(c, []).append((s, e, m, call))
    bin_by_chrom = {}
    for c, s, e, l in bins:
        bin_by_chrom.setdefault(c, []).append((s, e, l))

    contig_order = []
    for c, _, _, _ in bins:
        if c not in contig_order:
            contig_order.append(c)
    contig_rank = dict((c, i) for i, c in enumerate(contig_order))

    n_called = 0
    with open(args.out_tsv, "w") as out:
        out.write("gene\tchrom\tstart\tend\tn_bins\tmedian_denoised_log2\t"
                  "seg_call\tseg_mean_log2\tn_segments\n")
        ordered = sorted(genes.items(),
                         key=lambda kv: (contig_rank.get(kv[0][0], 999),
                                         kv[1][0]))
        for (chrom, gene), (gs, ge) in ordered:
            gbins = [l for s, e, l in bin_by_chrom.get(chrom, [])
                     if overlap(gs, ge, s, e) > 0]
            gsegs = [(overlap(gs, ge, s, e), m, call)
                     for s, e, m, call in seg_by_chrom.get(chrom, [])
                     if overlap(gs, ge, s, e) > 0]
            if gsegs:
                wsum = sum(o for o, _, _ in gsegs)
                seg_mean = sum(o * m for o, m, _ in gsegs) / wsum
                seg_call = max(gsegs)[2]
                if seg_call in ("+", "-"):
                    n_called += 1
                med = "{0:.4f}".format(statistics.median(gbins)) if gbins else "NA"
                out.write("{0}\t{1}\t{2}\t{3}\t{4}\t{5}\t{6}\t{7:.4f}\t{8}\n".format(
                    gene, chrom, gs, ge, len(gbins), med,
                    seg_call, seg_mean, len(gsegs)))
            else:
                med = "{0:.4f}".format(statistics.median(gbins)) if gbins else "NA"
                out.write("{0}\t{1}\t{2}\t{3}\t{4}\t{5}\tNA\tNA\t0\n".format(
                    gene, chrom, gs, ge, len(gbins), med))

    print("[ok] {0}: {1} genes projected, {2} with non-neutral segment call -> {3}".format(
        args.sample, len(genes), n_called, args.out_tsv))

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        offsets = {}
        pos = 0
        bounds = []
        for c in contig_order:
            offsets[c] = pos
            cmax = max(e for _, e, _ in bin_by_chrom[c])
            pos += cmax
            bounds.append((c, offsets[c], pos))

        fig, ax = plt.subplots(figsize=(16, 4.5))
        xs = [offsets[c] + (s + e) // 2 for c, s, e, _ in bins]
        ys = [l for _, _, _, l in bins]
        ax.scatter(xs, ys, s=2, c="#aaaaaa", linewidths=0, rasterized=True)
        colors = {"+": "#c0392b", "-": "#2471a3", "0": "#2c2c2c"}
        for c, s, e, m, call in segs:
            if c not in offsets:
                continue
            ax.plot([offsets[c] + s, offsets[c] + e], [m, m],
                    color=colors.get(call, "#2c2c2c"), lw=2.2)
        for c, b0, b1 in bounds:
            ax.axvline(b1, color="#dddddd", lw=0.6, zorder=0)
            ax.text((b0 + b1) / 2, ax.get_ylim()[0], c.replace("chr", ""),
                    ha="center", va="bottom", fontsize=7, color="#555555")
        ax.set_ylim(-3, 3)
        ax.axhline(0, color="#888888", lw=0.6)
        ax.set_ylabel("denoised log2 copy ratio")
        ax.set_title("{0} -- GATK denoised copy ratios (TGC_V1)".format(args.sample))
        ax.set_xticks([])
        fig.tight_layout()
        fig.savefig(args.out_plot, dpi=150)
        print("[ok] {0}: plot -> {1}".format(args.sample, args.out_plot))
    except Exception as exc:
        sys.stderr.write("[warn] plot generation failed (non-fatal): {0}\n".format(exc))


if __name__ == "__main__":
    main()
