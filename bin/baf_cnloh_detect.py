#!/usr/bin/env python3
"""17p BAF-shift / cnLOH detector for the twist myeloid panel (BAF_V1).

Method (v1 heuristic; thresholds are CLI args, validation on known
del(17p)/cnLOH material pending):
  1. Load the male-cohort background (baf_background.tsv): per-position
     median_alt_fraction, mad_alt_fraction, informative flag. Informative
     positions on chr17 define the 17p test set; non-chr17 informative
     positions are the autosomal internal controls.
  2. Load the sample's CollectAllelicCounts; keep positions with depth
     >= --min-depth.
  3. Candidate sample-het sites: informative positions with raw AF in
     [0.10, 0.90] (wide band so shifts up to clonal fraction ~0.8 are
     retained).
  4. Per site: bias-correct AF_adj = AF - (bg_median - 0.5); mirrored
     deviation d = |AF_adj - 0.5|. Under diploid heterozygosity d ~ site
     noise (bg MAD); under an allelic imbalance of clonal fraction f,
     d ~ f/2 (cnLOH) or f/(2*(2-f)) (hemizygous deletion) -- both
     reported via the simple estimate f_est = 2 * median(d).
  5. Verdict: shift called when n_het >= --min-het-sites, f_est >= --f-min
     and median(d) >= 3 * median(bg MAD). Split on the 17p denoised
     copy-ratio median: <= --cr-del -> DEL_17P, else CNLOH_17P. No shift
     -> NEUTRAL. Too few het sites -> INDETERMINATE.

Outputs: <prefix>.summary.tsv (one row), <prefix>.sites.tsv (per-site
detail), <prefix>.png (17p AF panel + autosomal controls; non-fatal).
"""

import argparse
import os
import statistics
import sys

CHR17 = "chr17"
HET_LO, HET_HI = 0.10, 0.90


def fail(msg):
    sys.stderr.write("[error] {0}\n".format(msg))
    sys.exit(1)


def read_background(path):
    sites = {}
    header = None
    with open(path) as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if header is None:
                header = parts
                need = ["contig", "position", "median_alt_fraction",
                        "mad_alt_fraction", "informative"]
                missing = [c for c in need if c not in header]
                if missing:
                    fail("background missing columns: {0}".format(",".join(missing)))
                idx = dict((c, header.index(c)) for c in need)
                continue
            if parts[idx["informative"]] != "true":
                continue
            contig = parts[idx["contig"]]
            pos = int(parts[idx["position"]])
            med = float(parts[idx["median_alt_fraction"]])
            mad = float(parts[idx["mad_alt_fraction"]])
            sites[(contig, pos)] = (med, mad)
    if not sites:
        fail("no informative background sites in {0}".format(path))
    return sites


def read_allelic(path):
    counts = {}
    header_seen = False
    with open(path) as fh:
        for line in fh:
            if line.startswith("@"):
                continue
            parts = line.rstrip("\n").split("\t")
            if not header_seen:
                if parts and parts[0] == "CONTIG":
                    header_seen = True
                continue
            if len(parts) < 4:
                continue
            try:
                counts[(parts[0], int(parts[1]))] = (int(parts[2]), int(parts[3]))
            except ValueError:
                fail("malformed allelic record in {0}: {1}".format(path, line[:100]))
    if not header_seen:
        fail("no CONTIG header in {0}".format(path))
    return counts


def read_denoised(path):
    bins = []
    header = None
    with open(path) as fh:
        for line in fh:
            if line.startswith("@"):
                continue
            parts = line.rstrip("\n").split("\t")
            if header is None:
                header = parts
                idx = dict((c, header.index(c))
                           for c in ["CONTIG", "START", "END", "LOG2_COPY_RATIO"])
                continue
            if len(parts) < len(header):
                continue
            bins.append((parts[idx["CONTIG"]], int(parts[idx["START"]]),
                         int(parts[idx["END"]]), float(parts[idx["LOG2_COPY_RATIO"]])))
    if not bins:
        fail("no denoised bins in {0}".format(path))
    return bins


def main():
    ap = argparse.ArgumentParser(description="17p BAF/cnLOH detector (BAF_V1)")
    ap.add_argument("--allelic", required=True)
    ap.add_argument("--denoised", required=True)
    ap.add_argument("--background", required=True)
    ap.add_argument("--snp-bed", required=True)
    ap.add_argument("--sample", required=True)
    ap.add_argument("--min-depth", type=int, default=20)
    ap.add_argument("--min-het-sites", type=int, default=10)
    ap.add_argument("--f-min", type=float, default=0.10)
    ap.add_argument("--cr-del", type=float, default=-0.15)
    ap.add_argument("--out-prefix", required=True)
    args = ap.parse_args()

    for p in (args.allelic, args.denoised, args.background, args.snp_bed):
        if not os.path.isfile(p):
            fail("input not found: {0}".format(p))

    bg = read_background(args.background)
    counts = read_allelic(args.allelic)
    bins = read_denoised(args.denoised)

    sites17 = sorted(k for k in bg if k[0] == CHR17)
    ctrl = sorted(k for k in bg if k[0] != CHR17)
    if not sites17:
        fail("no informative chr17 sites in background")
    p_lo = min(p for _, p in sites17)
    p_hi = max(p for _, p in sites17)

    def evaluate(keys):
        rows, devs, mads = [], [], []
        for contig, pos in keys:
            med, mad = bg[(contig, pos)]
            rc = counts.get((contig, pos))
            if rc is None:
                continue
            depth = rc[0] + rc[1]
            if depth < args.min_depth:
                continue
            af = rc[1] / float(depth)
            is_het = HET_LO <= af <= HET_HI
            af_adj = af - (med - 0.5)
            d = abs(af_adj - 0.5)
            rows.append((contig, pos, depth, af, af_adj, d, mad, is_het))
            if is_het:
                devs.append(d)
                mads.append(mad)
        return rows, devs, mads

    rows17, devs17, mads17 = evaluate(sites17)
    rows_ctrl, devs_ctrl, _ = evaluate(ctrl)

    cr17 = [l for c, s, e, l in bins if c == CHR17 and s <= p_hi and e >= p_lo]
    cr_med = statistics.median(cr17) if cr17 else float("nan")

    n_het = len(devs17)
    if n_het >= args.min_het_sites:
        med_d = statistics.median(devs17)
        mad_scale = statistics.median(mads17) if mads17 else 0.0
        f_est = 2.0 * med_d
        shifted = f_est >= args.f_min and (mad_scale == 0.0 or med_d >= 3.0 * mad_scale)
        if not shifted:
            verdict = "NEUTRAL"
        elif cr17 and cr_med <= args.cr_del:
            verdict = "DEL_17P"
        elif cr17:
            verdict = "CNLOH_17P"
        else:
            verdict = "INDETERMINATE"
    else:
        med_d, mad_scale, f_est = float("nan"), float("nan"), float("nan")
        verdict = "INDETERMINATE"

    ctrl_med = statistics.median(devs_ctrl) if devs_ctrl else float("nan")

    with open(args.out_prefix + ".sites.tsv", "w") as out:
        out.write("contig\tposition\tdepth\taf_raw\taf_adj\tmirrored_dev\t"
                  "bg_mad\tsample_het\n")
        for contig, pos, depth, af, af_adj, d, mad, is_het in rows17 + rows_ctrl:
            out.write("{0}\t{1}\t{2}\t{3:.4f}\t{4:.4f}\t{5:.4f}\t{6:.4f}\t{7}\n".format(
                contig, pos, depth, af, af_adj, d, mad,
                "true" if is_het else "false"))

    with open(args.out_prefix + ".summary.tsv", "w") as out:
        out.write("sample\tregion\tn_informative\tn_covered\tn_het\t"
                  "median_mirrored_dev\tbg_mad_scale\tf_estimate\t"
                  "cr17p_median_log2\tn_cr_bins\tctrl_median_dev\tverdict\n")
        out.write("{0}\tchr17:{1}-{2}\t{3}\t{4}\t{5}\t{6}\t{7}\t{8}\t{9}\t{10}\t{11}\t{12}\n".format(
            args.sample, p_lo, p_hi, len(sites17), len(rows17), n_het,
            "{0:.4f}".format(med_d) if med_d == med_d else "NA",
            "{0:.4f}".format(mad_scale) if mad_scale == mad_scale else "NA",
            "{0:.3f}".format(f_est) if f_est == f_est else "NA",
            "{0:.4f}".format(cr_med) if cr_med == cr_med else "NA",
            len(cr17), 
            "{0:.4f}".format(ctrl_med) if ctrl_med == ctrl_med else "NA",
            verdict))

    print("[ok] {0}: 17p n_het={1} f_est={2} cr_median={3} -> {4}".format(
        args.sample, n_het,
        "{0:.3f}".format(f_est) if f_est == f_est else "NA",
        "{0:.3f}".format(cr_med) if cr_med == cr_med else "NA",
        verdict))

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, (ax1, ax2) = plt.subplots(
            1, 2, figsize=(13, 4), gridspec_kw={"width_ratios": [5, 1]})
        if rows17:
            xs = [pos / 1e6 for _, pos, _, _, _, _, _, _ in rows17]
            ys = [af for _, _, _, af, _, _, _, _ in rows17]
            hets = [h for _, _, _, _, _, _, _, h in rows17]
            ax1.scatter(xs, ys, s=14, c=["#c0392b" if h else "#bbbbbb" for h in hets],
                        linewidths=0)
        ax1.axhline(0.5, color="#555555", lw=0.8)
        if f_est == f_est and verdict in ("CNLOH_17P", "DEL_17P"):
            ax1.axhline(0.5 + f_est / 2, color="#2471a3", lw=0.8, ls="--")
            ax1.axhline(0.5 - f_est / 2, color="#2471a3", lw=0.8, ls="--")
        ax1.set_ylim(0, 1)
        ax1.set_xlabel("chr17 position (Mb)")
        ax1.set_ylabel("ALT allele fraction")
        ax1.set_title("{0} -- 17p BAF: {1} (f_est {2}, CR {3})".format(
            args.sample, verdict,
            "{0:.2f}".format(f_est) if f_est == f_est else "NA",
            "{0:.2f}".format(cr_med) if cr_med == cr_med else "NA"))
        if rows_ctrl:
            ax2.scatter([0.5] * len(rows_ctrl),
                        [af for _, _, _, af, _, _, _, _ in rows_ctrl],
                        s=18, c="#2c7a2c", linewidths=0)
        ax2.axhline(0.5, color="#555555", lw=0.8)
        ax2.set_ylim(0, 1)
        ax2.set_xticks([])
        ax2.set_title("autosomal ctrl")
        fig.tight_layout()
        fig.savefig(args.out_prefix + ".png", dpi=150)
        print("[ok] {0}: plot -> {1}.png".format(args.sample, args.out_prefix))
    except Exception as exc:
        sys.stderr.write("[warn] plot generation failed (non-fatal): {0}\n".format(exc))


if __name__ == "__main__":
    main()
