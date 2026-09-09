#!/usr/bin/env python3
"""Genome-wide per-arm BAF-shift / cnLOH detector for the Twist myeloid panel (BAF_V2).

BAF_V1 (7 Sep 2026) evaluated chr17 only. BAF_V2 (9 Sep 2026) evaluates every chromosome
arm that carries informative sites in the cohort background (snp_sites.baf.bed v2 catalog,
4,193 intervals; baf_background.tsv built from the 48 normals), with the same statistic.

Method (unchanged from V1 per arm; thresholds are CLI args):
  1. Background: per-position median_alt_fraction, mad_alt_fraction, informative flag.
  2. Sample: CollectAllelicCounts; positions with depth >= --min-depth.
  3. Sample-het sites: informative positions with raw AF in [0.10, 0.90].
  4. Per site: AF_adj = AF - (bg_median - 0.5) when the cohort median is het-like
     (0.35-0.65; at a common SNP the cohort distribution is trimodal 0/0.5/1 and the
     median then carries no bias information), else AF_adj = AF. Mirrored deviation
     d = |AF_adj - 0.5|; under an allelic imbalance of clonal fraction f, d ~ f/2 (cnLOH)
     or f/(2(2-f)) (hemizygous loss); f_est = 2*median(d).
  5. Per arm (p/q split at the hg38 centromere; --cytoband overrides the built-in table):
     shift when n_het >= --min-het-sites, f_est >= --f-min and median(d) >= noise_floor,
     where noise_floor = max(--f-min/2, --noise-mult * median over the OTHER arms of their
     per-arm median d). The sample's own diploid arms calibrate the noise; the cohort MAD
     (trimodal off 17p) is reported but not used for the test.
     Copy state from the arm's denoised log2 copy-ratio median:
        <= --cr-del  -> DEL          (hemizygous loss)
        >= --cr-gain -> GAIN         (gain with allelic imbalance)
        otherwise    -> CNLOH        (copy-neutral LOH / UPD)
        no bins      -> IMBALANCE    (allelic imbalance, copy state unknown)
     No shift -> NEUTRAL. Too few het sites -> INDETERMINATE (n_het reported).
  6. confidence: DEL / GAIN are HIGH (the copy ratio corroborates the shift). CNLOH / IMBALANCE,
     where BAF is the only evidence, are HIGH when n_het >= --conf-min-het and median(d) >=
     --conf-mult * noise_floor, or median(d) >= 3 * noise_floor; else LOW (shown with '?',
     casts no B vote in the consensus).
     scope: 'chromosome' when both arms carry the same verdict with |f_p - f_q| < 0.15,
     else 'arm'. ctrl_median_dev: median over the other arms of their median d.

Outputs (prefix from --out-prefix, e.g. <sample>.baf):
  <prefix>.summary.tsv   one row per arm with informative sites
  <prefix>.sites.tsv     per-site detail (contig, position, arm, depth, af_raw, af_adj,
                         mirrored_dev, bg_mad, sample_het) -- consumed by the consensus
                         and the chromosome pages; column names unchanged from V1 plus 'arm'
  <prefix>.png           genome-wide AF panel coloured by arm verdict (non-fatal)
"""

import argparse
import os
import statistics
import sys

HET_LO, HET_HI = 0.10, 0.90

# hg38 centromeres (UCSC cytoBand acen bands): p arm < start, q arm > end.
CENTROMERE_HG38 = {
    "chr1": (121700000, 125100000), "chr2": (91800000, 96000000), "chr3": (87800000, 94000000),
    "chr4": (48200000, 51800000), "chr5": (46100000, 51400000), "chr6": (58500000, 62600000),
    "chr7": (58100000, 62100000), "chr8": (43200000, 47200000), "chr9": (42200000, 45500000),
    "chr10": (38000000, 41600000), "chr11": (51000000, 55800000), "chr12": (33200000, 37800000),
    "chr13": (16500000, 18900000), "chr14": (16100000, 18200000), "chr15": (17500000, 20500000),
    "chr16": (35300000, 38400000), "chr17": (22700000, 27400000), "chr18": (15400000, 21500000),
    "chr19": (24200000, 28100000), "chr20": (25700000, 30400000), "chr21": (10900000, 13000000),
    "chr22": (13700000, 17400000), "chrX": (58100000, 61000000), "chrY": (10300000, 10600000),
}
CHROM_ORDER = ["chr%d" % i for i in range(1, 23)] + ["chrX", "chrY"]
VERDICT_COLOUR = {"NEUTRAL": "#9e9e9e", "DEL": "#c0392b", "CNLOH": "#2471a3", "GAIN": "#1e8449",
                  "IMBALANCE": "#8e44ad", "INDETERMINATE": "#d5d5d5"}


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
                need = ["contig", "position", "median_alt_fraction", "mad_alt_fraction", "informative"]
                missing = [c for c in need if c not in header]
                if missing:
                    fail("background missing columns: {0}".format(",".join(missing)))
                idx = dict((c, header.index(c)) for c in need)
                continue
            if parts[idx["informative"]] != "true":
                continue
            sites[(parts[idx["contig"]], int(parts[idx["position"]]))] = (
                float(parts[idx["median_alt_fraction"]]), float(parts[idx["mad_alt_fraction"]]))
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
                idx = dict((c, header.index(c)) for c in ["CONTIG", "START", "END", "LOG2_COPY_RATIO"])
                continue
            if len(parts) < len(header):
                continue
            bins.append((parts[idx["CONTIG"]], int(parts[idx["START"]]), int(parts[idx["END"]]),
                         float(parts[idx["LOG2_COPY_RATIO"]])))
    if not bins:
        fail("no denoised bins in {0}".format(path))
    return bins


def read_centromeres(cytoband_path):
    """UCSC cytoBand.txt -> {chrom: (acen_start, acen_end)}; falls back to the built-in table."""
    cen = dict(CENTROMERE_HG38)
    if not cytoband_path:
        return cen
    acen = {}
    with open(cytoband_path) as fh:
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if len(p) >= 5 and p[4] == "acen":
                lo, hi = acen.get(p[0], (None, None))
                s, e = int(p[1]), int(p[2])
                acen[p[0]] = (s if lo is None else min(lo, s), e if hi is None else max(hi, e))
    cen.update(acen)
    return cen


def arm_of(chrom, pos, cen):
    c = cen.get(chrom)
    if c is None:
        return None
    if pos < c[0]:
        return "p"
    if pos > c[1]:
        return "q"
    return None   # inside the centromere


def fmt(x, nd=4):
    return "NA" if x is None or x != x else "{0:.{1}f}".format(x, nd)


def main():
    ap = argparse.ArgumentParser(description="Genome-wide per-arm BAF/cnLOH detector (BAF_V2)")
    ap.add_argument("--allelic", required=True)
    ap.add_argument("--denoised", required=True)
    ap.add_argument("--background", required=True)
    ap.add_argument("--snp-bed", required=True, help="kept for provenance; sites come from the background")
    ap.add_argument("--sample", required=True)
    ap.add_argument("--cytoband", default=None, help="UCSC cytoBand file; overrides the built-in hg38 centromeres")
    ap.add_argument("--min-depth", type=int, default=20)
    ap.add_argument("--min-het-sites", type=int, default=10)
    ap.add_argument("--f-min", type=float, default=0.10)
    ap.add_argument("--cr-del", type=float, default=-0.15)
    ap.add_argument("--cr-gain", type=float, default=0.15)
    ap.add_argument("--noise-mult", type=float, default=2.5,
                    help="noise floor = this x the median of the other arms' median deviations (default 2.5)")
    ap.add_argument("--conf-min-het", type=int, default=20, help="HIGH confidence needs >= this many het sites (default 20)")
    ap.add_argument("--conf-mult", type=float, default=1.5, help="HIGH confidence needs median d >= this x noise floor (default 1.5)")
    ap.add_argument("--out-prefix", required=True)
    args = ap.parse_args()

    for p in (args.allelic, args.denoised, args.background, args.snp_bed):
        if not os.path.isfile(p):
            fail("input not found: {0}".format(p))

    bg = read_background(args.background)
    counts = read_allelic(args.allelic)
    bins = read_denoised(args.denoised)
    cen = read_centromeres(args.cytoband)

    # group informative sites by arm
    arm_sites = {}
    for (contig, pos) in bg:
        a = arm_of(contig, pos, cen)
        if a is None:
            continue
        arm_sites.setdefault((contig, a), []).append(pos)

    def evaluate(contig, positions):
        rows, devs, mads = [], [], []
        for pos in sorted(positions):
            med, mad = bg[(contig, pos)]
            rc = counts.get((contig, pos))
            if rc is None:
                continue
            depth = rc[0] + rc[1]
            if depth < args.min_depth:
                continue
            af = rc[1] / float(depth)
            is_het = HET_LO <= af <= HET_HI
            af_adj = af - (med - 0.5) if 0.35 <= med <= 0.65 else af   # het-like cohort median only
            d = abs(af_adj - 0.5)
            rows.append((contig, pos, depth, af, af_adj, d, mad, is_het))
            if is_het:
                devs.append(d)
                mads.append(mad)
        return rows, devs, mads

    results = {}   # (chrom, arm) -> dict
    all_rows = []
    keys = sorted(arm_sites, key=lambda k: (CHROM_ORDER.index(k[0]) if k[0] in CHROM_ORDER else 99, k[1]))
    evaluated = {}
    for key in keys:
        rows, devs, mads = evaluate(key[0], arm_sites[key])
        evaluated[key] = (rows, devs, mads)
        for r in rows:
            all_rows.append(r + (key[1],))
    arm_med = dict((k, statistics.median(v[1])) for k, v in evaluated.items() if len(v[1]) >= args.min_het_sites)
    for key in keys:
        chrom, arm = key
        rows, devs, mads = evaluated[key]
        c0, c1 = cen[chrom]
        arm_lo, arm_hi = (0, c0) if arm == "p" else (c1, 10 ** 9)
        cr = [l for c, s, e, l in bins if c == chrom and e > arm_lo and s < arm_hi]
        cr_med = statistics.median(cr) if cr else float("nan")
        n_het = len(devs)
        med_d = mad_scale = f_est = floor = float("nan")
        others = [m for k2, m in arm_med.items() if k2 != key]
        ctrl_med = statistics.median(others) if others else float("nan")
        if n_het >= args.min_het_sites:
            med_d = statistics.median(devs)
            mad_scale = statistics.median(mads) if mads else 0.0
            f_est = 2.0 * med_d
            floor = max(args.f_min / 2.0, args.noise_mult * ctrl_med) if ctrl_med == ctrl_med else args.f_min / 2.0
            shifted = f_est >= args.f_min and med_d >= floor
            if not shifted:
                verdict = "NEUTRAL"
            elif not cr:
                verdict = "IMBALANCE"
            elif cr_med <= args.cr_del:
                verdict = "DEL"
            elif cr_med >= args.cr_gain:
                verdict = "GAIN"
            else:
                verdict = "CNLOH"
        else:
            verdict = "INDETERMINATE"
        if verdict in ("NEUTRAL", "INDETERMINATE"):
            confidence = "NA"
        elif verdict in ("DEL", "GAIN"):
            confidence = "HIGH"   # the arm's copy ratio corroborates the shift; site count already >= min
        elif (n_het >= args.conf_min_het and med_d >= args.conf_mult * floor) or med_d >= 3.0 * floor:
            confidence = "HIGH"   # BAF is the only evidence: many sites at a clear shift, or a very strong shift
        else:
            confidence = "LOW"
        results[key] = {"confidence": confidence, "chrom": chrom, "arm": arm, "arm_lo": arm_lo, "arm_hi": arm_hi,
                        "site_lo": min(arm_sites[key]), "site_hi": max(arm_sites[key]),
                        "n_informative": len(arm_sites[key]), "n_covered": len(rows), "n_het": n_het,
                        "med_d": med_d, "mad_scale": mad_scale, "f_est": f_est, "floor": floor,
                        "cr_med": cr_med, "n_cr": len(cr), "verdict": verdict, "devs": devs, "ctrl_med": ctrl_med}

    # scope and leave-one-arm-out control
    for key, r in results.items():
        other = results.get((key[0], "q" if key[1] == "p" else "p"))
        r["scope"] = "arm"
        if other and r["verdict"] == other["verdict"] and r["verdict"] not in ("NEUTRAL", "INDETERMINATE") \
                and r["f_est"] == r["f_est"] and other["f_est"] == other["f_est"] \
                and abs(r["f_est"] - other["f_est"]) < 0.15:
            r["scope"] = "chromosome"

    ordered = sorted(results.values(), key=lambda r: (CHROM_ORDER.index(r["chrom"]) if r["chrom"] in CHROM_ORDER else 99, r["arm"]))

    with open(args.out_prefix + ".sites.tsv", "w") as out:
        out.write("contig\tposition\tarm\tdepth\taf_raw\taf_adj\tmirrored_dev\tbg_mad\tsample_het\n")
        for contig, pos, depth, af, af_adj, d, mad, is_het, arm in all_rows:
            out.write("{0}\t{1}\t{2}\t{3}\t{4:.4f}\t{5:.4f}\t{6:.4f}\t{7:.4f}\t{8}\n".format(
                contig, pos, arm, depth, af, af_adj, d, mad, "true" if is_het else "false"))

    with open(args.out_prefix + ".summary.tsv", "w") as out:
        out.write("sample\tarm\tregion\tsite_lo\tsite_hi\tn_informative\tn_covered\tn_het\t"
                  "median_mirrored_dev\tbg_mad_scale\tnoise_floor\tf_estimate\tcr_median_log2\tn_cr_bins\t"
                  "verdict\tconfidence\tscope\tctrl_median_dev\n")
        for r in ordered:
            out.write("\t".join(str(x) for x in [
                args.sample, r["chrom"].replace("chr", "") + r["arm"],
                "{0}:{1}-{2}".format(r["chrom"], r["arm_lo"], r["arm_hi"]),
                r["site_lo"], r["site_hi"], r["n_informative"], r["n_covered"], r["n_het"],
                fmt(r["med_d"]), fmt(r["mad_scale"]), fmt(r["floor"]), fmt(r["f_est"], 3), fmt(r["cr_med"]), r["n_cr"],
                r["verdict"], r["confidence"], r["scope"], fmt(r["ctrl_med"])]) + "\n")

    called = [r for r in ordered if r["verdict"] not in ("NEUTRAL", "INDETERMINATE")]
    print("[ok] {0}: {1} arms evaluated, {2} with a call: {3}".format(
        args.sample, len(ordered), len(called),
        ", ".join("{0}{1} {2}{3} f={4}".format(r["chrom"].replace("chr", ""), r["arm"], r["verdict"],
                                                "?" if r["confidence"] == "LOW" else "", fmt(r["f_est"], 2))
                  for r in called) or "none"))

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        chroms = [c for c in CHROM_ORDER if any(r["chrom"] == c for r in ordered)]
        offsets, spans, x0 = {}, {}, 0.0
        for c in chroms:
            hi = max([r["site_hi"] for r in ordered if r["chrom"] == c] +
                     [e for cc, s_, e, l in bins if cc == c])
            offsets[c] = x0
            spans[c] = hi / 1e6
            x0 += hi / 1e6 + 5.0
        fig, (ax0, ax1) = plt.subplots(2, 1, figsize=(18, 7), sharex=True,
                                       gridspec_kw={"height_ratios": [1, 1.2], "hspace": 0.08})
        # depth track: denoised log2 copy ratio per bin, arm medians
        for c, s_, e, l in bins:
            if c in offsets:
                ax0.scatter(offsets[c] + (s_ + e) / 2e6, l, s=3, c="#8c8c8c", linewidths=0)
        for r in ordered:
            if r["cr_med"] == r["cr_med"]:
                x_lo = offsets[r["chrom"]] + r["arm_lo"] / 1e6
                x_hi = offsets[r["chrom"]] + min(r["arm_hi"], spans[r["chrom"]] * 1e6) / 1e6
                col = "#c0392b" if r["cr_med"] <= args.cr_del else ("#1e8449" if r["cr_med"] >= args.cr_gain else "#333333")
                ax0.plot([x_lo, x_hi], [r["cr_med"], r["cr_med"]], color=col, lw=1.8)
        ax0.axhline(0.0, color="#555555", lw=0.6)
        ax0.set_ylim(-1.5, 1.5)
        ax0.set_ylabel("denoised log2 copy ratio")
        # BAF track
        for contig, pos, depth, af, af_adj, d, mad, is_het, arm in all_rows:
            if contig not in offsets:
                continue
            v = results[(contig, arm)]["verdict"]
            ax1.scatter(offsets[contig] + pos / 1e6, af, s=6, linewidths=0,
                        c=VERDICT_COLOUR.get(v, "#9e9e9e") if is_het else "#e0e0e0")
        for c in chroms:
            for ax in (ax0, ax1):
                ax.axvline(offsets[c] - 2.5, color="#bbbbbb", lw=0.5)
                cs, ce = cen[c]
                ax.axvspan(offsets[c] + cs / 1e6, offsets[c] + ce / 1e6, color="#f2f2f2", lw=0)
        ax1.axhline(0.5, color="#555555", lw=0.6)
        ax1.set_ylim(0, 1)
        ax1.set_xlim(-3, x0)
        ax1.set_xticks([offsets[c] + spans[c] / 2 for c in chroms])
        ax1.set_xticklabels([c.replace("chr", "") for c in chroms], fontsize=8)
        ax1.tick_params(axis="x", length=0)
        ax1.set_xlabel("chromosome")
        ax1.set_ylabel("ALT allele fraction")
        from matplotlib.lines import Line2D
        handles = [Line2D([0], [0], marker="o", color="w", markerfacecolor=col, markersize=6, label=lab) for lab, col in [
            ("DEL", VERDICT_COLOUR["DEL"]), ("CNLOH", VERDICT_COLOUR["CNLOH"]), ("GAIN", VERDICT_COLOUR["GAIN"]),
            ("imbalance", VERDICT_COLOUR["IMBALANCE"]), ("balanced het", "#9e9e9e"), ("homozygous", "#e0e0e0")]]
        ax1.legend(handles=handles, loc="upper right", ncol=6, fontsize=7, frameon=True, framealpha=0.9,
                   bbox_to_anchor=(1.0, 1.0), borderaxespad=0.3)
        ax0.set_title("{0} -- depth and BAF by arm: {1}".format(
            args.sample,
            ", ".join("{0}{1} {2}{3} f={4}".format(r["chrom"].replace("chr", ""), r["arm"], r["verdict"],
                                                  "?" if r["confidence"] == "LOW" else "", fmt(r["f_est"], 2))
                      for r in called) or "no call"),
            fontsize=10, pad=14)
        fig.savefig(args.out_prefix + ".png", dpi=130, bbox_inches="tight")
        print("[ok] {0}: plot -> {1}.png".format(args.sample, args.out_prefix))
    except Exception as exc:
        sys.stderr.write("[warn] plot generation failed (non-fatal): {0}\n".format(exc))


if __name__ == "__main__":
    main()
