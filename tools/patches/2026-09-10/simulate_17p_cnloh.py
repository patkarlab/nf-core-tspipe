#!/usr/bin/env python3
"""In-silico dilution of BAF_V2 on 17p (handoff 2026-09-10 v2, section 2).

Takes a diploid-17 sample's allelic counts, imposes copy-neutral LOH of clonal fraction f
on 17p and runs bin/baf_cnloh_detect.py (BAF_V2, unchanged parameters) on every replicate.

Model. At each 17p site that the detector would treat as heterozygous in the unmodified
sample (background-informative, depth >= --min-depth, raw AF in [0.10, 0.90]) the ALT count
is redrawn as Binomial(depth, p) with
    p = centre + s * f / 2,   s = +1 or -1 at random per site (unphased),
    centre = the cohort median ALT fraction when het-like (0.35-0.65), else 0.5,
so that after the detector's own bias correction the expected mirrored deviation is f/2.
Depth is kept; every other site and every other arm is untouched; the denoised copy ratio
is untouched (17p stays copy-neutral, so a detected shift is a CNLOH verdict). Level f = 0
redraws the same sites with no shift and measures what the resampling alone does.

Outputs (in --outdir):
    dilution_runs.tsv      one row per replicate: the detector's 17p row plus any arm outside
                           17p whose verdict differs from the unmodified run
    dilution_summary.tsv   one row per level: calls, confidence, f_estimate spread, noise floor
    baseline.summary.tsv   the detector on the unmodified input (must equal the pipeline's row)
    clean/<sample>.summary.tsv   the detector on each --clean sample as is (false-positive check)
    dilution.png           f_estimate per level against the noise floor (if matplotlib is present)
Standard library only (matplotlib optional); Python 3.6+.
"""

import argparse
import csv
import os
import random
import statistics
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor

HET_LO, HET_HI = 0.10, 0.90
CEN17 = (22700000, 27400000)      # hg38, as in the detector


def read_background(path):
    bg = {}
    with open(path) as fh:
        hdr = None
        for line in fh:
            if line.startswith("#"):
                continue
            p = line.rstrip("\n").split("\t")
            if hdr is None:
                hdr = p
                continue
            r = dict(zip(hdr, p))
            if r.get("informative") == "true":
                bg[(r["contig"], int(r["position"]))] = float(r["median_alt_fraction"])
    return bg


def read_allelic(path, keep=None):
    """GATK CollectAllelicCounts table. With ``keep`` (a set of (contig, position)), only those
    rows are retained: the detector evaluates background-informative positions only, so the
    subset is equivalent and keeps the per-replicate files small. The @ header is dropped
    (the detector skips it); the CONTIG header line is kept."""
    head, rows = [], []
    with open(path) as fh:
        for line in fh:
            if line.startswith("@"):
                continue
            p = line.rstrip("\n").split("\t")
            if p and p[0] == "CONTIG":
                head.append(line)
                continue
            if len(p) < 4:
                continue
            key = (p[0], int(p[1]))
            if keep is not None and key not in keep:
                continue
            rows.append([p[0], int(p[1]), int(p[2]), int(p[3])] + p[4:])
    if not head:
        raise SystemExit("no CONTIG header in %s" % path)
    return head, rows


def het_sites_17p(rows, bg, min_depth, arm):
    lo, hi = (0, CEN17[0]) if arm == "17p" else (CEN17[1], 10 ** 9)
    out = {}
    for i, r in enumerate(rows):
        if r[0] != "chr17" or not (lo <= r[1] < hi):
            continue
        key = (r[0], r[1])
        if key not in bg:
            continue
        depth = r[2] + r[3]
        if depth < min_depth:
            continue
        af = r[3] / float(depth)
        if HET_LO <= af <= HET_HI:
            med = bg[key]
            out[i] = med if 0.35 <= med <= 0.65 else 0.5
    return out


def write_allelic(path, head, rows):
    with open(path, "w") as out:
        for h in head:
            out.write(h)
        for r in rows:
            out.write("\t".join(str(x) for x in r) + "\n")


def simulate(rows, hets, f, rng, mode):
    """mode 'shift': p = observed AF +/- f/2 (keeps the sample's own site-level noise and bias;
    the redraw adds one more round of counting noise, small at these depths);
    mode 'ideal': p = centre +/- f/2 (pure binomial counting noise around the het expectation)."""
    sim = [list(r) for r in rows]
    for i, centre in hets.items():
        depth = sim[i][2] + sim[i][3]
        sign = 1 if rng.random() < 0.5 else -1
        base = centre if mode == "ideal" else sim[i][3] / float(depth)
        p = min(1.0, max(0.0, base + sign * f / 2.0))
        alt = sum(1 for _ in range(depth) if rng.random() < p)
        sim[i][2], sim[i][3] = depth - alt, alt
    return sim


STUB_DIR = None   # set in main(): a stub matplotlib that raises ImportError, so the detector skips its (slow) plot


def make_stub(outdir):
    d = os.path.join(outdir, "_no_matplotlib", "matplotlib")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "__init__.py"), "w") as fh:
        fh.write('raise ImportError("matplotlib disabled for the dilution run (simulate_17p_cnloh.py)")\n')
    return os.path.dirname(d)


def run_detector(args_tuple):
    detector, allelic, denoised, background, snp_bed, sample, prefix, extra = args_tuple
    cmd = [sys.executable, detector, "--allelic", allelic, "--denoised", denoised, "--background", background,
           "--snp-bed", snp_bed, "--sample", sample, "--out-prefix", prefix] + extra
    env = dict(os.environ)
    env.setdefault("MPLCONFIGDIR", "/tmp/mpl_" + str(os.getpid()))
    env.setdefault("MPLBACKEND", "Agg")
    if STUB_DIR:
        env["PYTHONPATH"] = STUB_DIR + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    if res.returncode != 0:
        raise RuntimeError("detector failed for %s: %s" % (prefix, res.stderr.decode(errors="replace")[-500:]))
    for ext in (".png", ".sites.tsv"):
        try:
            os.remove(prefix + ext)
        except OSError:
            pass
    return prefix + ".summary.tsv"


def read_summary(path):
    with open(path) as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def arm_verdicts(rows):
    return dict((r["arm"], (r["verdict"], r["confidence"])) for r in rows)


def fnum(x, nd=3):
    try:
        return "%.*f" % (nd, float(x))
    except (TypeError, ValueError):
        return "NA"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--allelic", required=True, help="diploid-17 sample allelicCounts.tsv (full or informative subset)")
    ap.add_argument("--denoised", required=True)
    ap.add_argument("--background", required=True)
    ap.add_argument("--snp-bed", required=True)
    ap.add_argument("--detector", required=True, help="path to bin/baf_cnloh_detect.py")
    ap.add_argument("--sample", required=True)
    ap.add_argument("--clean", action="append", default=[], metavar="SAMPLE=ALLELIC,DENOISED",
                    help="additional unmodified samples for the false-positive check (repeatable)")
    ap.add_argument("--levels", default="0,0.02,0.05,0.10,0.15,0.20")
    ap.add_argument("--replicates", type=int, default=20)
    ap.add_argument("--seed", type=int, default=20260910)
    ap.add_argument("--arm", default="17p", choices=["17p", "17q"])
    ap.add_argument("--mode", default="shift", choices=["shift", "ideal"],
                    help="shift: observed AF +/- f/2 (realistic, default); ideal: cohort het centre +/- f/2 (counting noise only)")
    ap.add_argument("--min-depth", type=int, default=20)
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--detector-args", default="", help="extra arguments passed verbatim to the detector")
    ap.add_argument("--keep-detector-plots", action="store_true",
                    help="let the detector draw its genome-wide PNG for every replicate (slow; off by default)")
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()

    os.makedirs(os.path.join(args.outdir, "sim"), exist_ok=True)
    os.makedirs(os.path.join(args.outdir, "clean"), exist_ok=True)
    global STUB_DIR
    STUB_DIR = None if args.keep_detector_plots else make_stub(args.outdir)
    extra = args.detector_args.split() if args.detector_args else []
    levels = [float(x) for x in args.levels.split(",")]
    bg = read_background(args.background)
    head, rows = read_allelic(args.allelic, keep=set(bg))
    print("[info] %d background-informative positions; %d of them covered in %s" % (len(bg), len(rows), args.allelic))
    hets = het_sites_17p(rows, bg, args.min_depth, args.arm)
    depths = [rows[i][2] + rows[i][3] for i in hets]
    print("[info] %s: %d %s het sites in the unmodified sample (median depth %d, min %d, max %d); mode %s" % (
        args.sample, len(hets), args.arm, statistics.median(depths), min(depths), max(depths), args.mode))

    # baseline: the unmodified input through the detector
    base_prefix = os.path.join(args.outdir, "baseline")
    run_detector((args.detector, args.allelic, args.denoised, args.background, args.snp_bed, args.sample, base_prefix, extra))
    base_rows = read_summary(base_prefix + ".summary.tsv")
    base_v = arm_verdicts(base_rows)
    base17 = [r for r in base_rows if r["arm"] == args.arm][0]
    print("[info] baseline %s: verdict %s f %s n_het %s noise_floor %s median_dev %s" % (
        args.arm, base17["verdict"], base17["f_estimate"], base17["n_het"], base17["noise_floor"], base17["median_mirrored_dev"]))
    base_called = sorted(a for a, (v, c) in base_v.items() if v not in ("NEUTRAL", "INDETERMINATE"))
    print("[info] baseline arms with a call: %s" % (", ".join("%s:%s(%s)" % (a, base_v[a][0], base_v[a][1]) for a in base_called) or "none"))

    # clean samples as they are
    clean_results = []
    for spec in args.clean:
        name, files = spec.split("=", 1)
        allelic, denoised = files.split(",", 1)
        prefix = os.path.join(args.outdir, "clean", name)
        run_detector((args.detector, allelic, denoised, args.background, args.snp_bed, name, prefix, extra))
        rows_c = read_summary(prefix + ".summary.tsv")
        called = [(r["arm"], r["verdict"], r["confidence"], r["f_estimate"], r["n_het"]) for r in rows_c
                  if r["verdict"] not in ("NEUTRAL", "INDETERMINATE")]
        r17 = [r for r in rows_c if r["arm"] == args.arm][0]
        clean_results.append((name, r17, called))
        print("[info] clean %s: %s %s f %s; calls: %s" % (
            name, args.arm, r17["verdict"], r17["f_estimate"],
            ", ".join("%s:%s(%s,f=%s,n=%s)" % c for c in called) or "none"))

    # simulated replicates
    jobs, meta = [], []
    for li, f in enumerate(levels):
        for rep in range(args.replicates):
            rng = random.Random(args.seed + li * 1000 + rep)
            sim = simulate(rows, hets, f, rng, args.mode)
            tag = "f%03d_r%02d" % (int(round(f * 1000)), rep)
            allelic = os.path.join(args.outdir, "sim", tag + ".allelicCounts.tsv")
            write_allelic(allelic, head, sim)
            prefix = os.path.join(args.outdir, "sim", tag)
            jobs.append((args.detector, allelic, args.denoised, args.background, args.snp_bed,
                         "%s_%s" % (args.sample, tag), prefix, extra))
            meta.append((f, rep, prefix))
    print("[info] running the detector on %d replicates with %d workers" % (len(jobs), args.threads))
    with ProcessPoolExecutor(max_workers=args.threads) as ex:
        list(ex.map(run_detector, jobs))

    runs = []
    for (f, rep, prefix) in meta:
        srows = read_summary(prefix + ".summary.tsv")
        v = arm_verdicts(srows)
        r17 = [r for r in srows if r["arm"] == args.arm][0]
        changed = sorted("%s:%s>%s" % (a, base_v.get(a, ("NA", ""))[0], vv[0]) for a, vv in v.items()
                         if a != args.arm and vv[0] != base_v.get(a, ("NA", ""))[0])
        runs.append({"level": f, "replicate": rep, "verdict": r17["verdict"], "confidence": r17["confidence"],
                     "f_estimate": r17["f_estimate"], "median_dev": r17["median_mirrored_dev"],
                     "noise_floor": r17["noise_floor"], "n_het": r17["n_het"], "scope": r17["scope"],
                     "ctrl_median_dev": r17["ctrl_median_dev"], "other_arms_changed": ";".join(changed) or "-"})
        os.remove(prefix + ".allelicCounts.tsv")

    with open(os.path.join(args.outdir, "dilution_runs.tsv"), "w") as out:
        cols = ["level", "replicate", "verdict", "confidence", "f_estimate", "median_dev", "noise_floor", "n_het",
                "scope", "ctrl_median_dev", "other_arms_changed"]
        out.write("\t".join(cols) + "\n")
        for r in runs:
            out.write("\t".join(str(r[c]) for c in cols) + "\n")

    summary = []
    for f in levels:
        rs = [r for r in runs if r["level"] == f]
        fe = [float(r["f_estimate"]) for r in rs]
        called = [r for r in rs if r["verdict"] not in ("NEUTRAL", "INDETERMINATE")]
        high = [r for r in called if r["confidence"] == "HIGH"]
        verdicts = {}
        for r in rs:
            verdicts[r["verdict"]] = verdicts.get(r["verdict"], 0) + 1
        other = sum(1 for r in rs if r["other_arms_changed"] != "-")
        summary.append({
            "mode": args.mode, "level_f": "%.2f" % f, "n_rep": len(rs),
            "n_called": len(called), "n_high": len(high), "n_low": len(called) - len(high),
            "pct_called": "%.0f" % (100.0 * len(called) / len(rs)), "pct_high": "%.0f" % (100.0 * len(high) / len(rs)),
            "verdicts": ",".join("%s:%d" % kv for kv in sorted(verdicts.items())),
            "f_est_median": fnum(statistics.median(fe)), "f_est_min": fnum(min(fe)), "f_est_max": fnum(max(fe)),
            "median_dev_median": fnum(statistics.median(float(r["median_dev"]) for r in rs)),
            "noise_floor_median": fnum(statistics.median(float(r["noise_floor"]) for r in rs)),
            "n_het_median": fnum(statistics.median(int(r["n_het"]) for r in rs), 0),
            "runs_with_other_arm_change": other,
        })
    cols = list(summary[0].keys())
    with open(os.path.join(args.outdir, "dilution_summary.tsv"), "w") as out:
        out.write("\t".join(cols) + "\n")
        for s in summary:
            out.write("\t".join(str(s[c]) for c in cols) + "\n")

    print("\nmode %s\nlevel_f  called  HIGH  LOW  f_est median (min-max)  median_dev  noise_floor  n_het  other-arm changes" % args.mode)
    for s in summary:
        print("%-7s  %3d/%-3d %4d %4d  %s (%s-%s)        %s       %s      %s      %s" % (
            s["level_f"], s["n_called"], s["n_rep"], s["n_high"], s["n_low"], s["f_est_median"], s["f_est_min"],
            s["f_est_max"], s["median_dev_median"], s["noise_floor_median"], s["n_het_median"], s["runs_with_other_arm_change"]))

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(6.5, 4))
        data = [[float(r["f_estimate"]) for r in runs if r["level"] == f] for f in levels]
        bp_kw = {"widths": 0.5}
        try:
            ax.boxplot(data, tick_labels=["%.2f" % f for f in levels], **bp_kw)
        except TypeError:
            ax.boxplot(data, labels=["%.2f" % f for f in levels], **bp_kw)
        floor = float(summary[0]["noise_floor_median"])
        ax.axhline(2 * floor, color="#c0392b", ls="--", lw=1, label="any call: f_est >= 2 x noise floor")
        ax.axhline(3 * floor, color="#1e8449", ls=":", lw=1, label="HIGH confidence: f_est >= 3 x noise floor")
        ax.plot(range(1, len(levels) + 1), levels, "o", color="#2471a3", ms=4, label="imposed f")
        top = max(max(d) for d in data) * 1.18
        ax.set_ylim(0, top)
        for i, s in enumerate(summary):
            ax.text(i + 1, top * 0.99, "%s/%s\n%s" % (s["n_called"], s["n_rep"], s["n_high"]), ha="center", va="top", fontsize=7)
        ax.text(0.55, top * 0.99, "called\nHIGH", ha="right", va="top", fontsize=7, color="#555555")
        ax.set_xlabel("imposed cnLOH clonal fraction f on %s" % args.arm)
        ax.set_ylabel("BAF_V2 f_estimate")
        ax.legend(fontsize=8, loc="lower right")
        ax.set_title("%s: in-silico cnLOH dilution, mode %s, %d replicates per level%s" % (
            args.sample, args.mode, args.replicates, (" (" + args.detector_args + ")") if args.detector_args else ""), fontsize=9)
        fig.savefig(os.path.join(args.outdir, "dilution.png"), dpi=130, bbox_inches="tight")
        print("[ok] figure -> %s" % os.path.join(args.outdir, "dilution.png"))
    except Exception as exc:   # noqa: BLE001
        print("[warn] no figure: %s" % exc)


if __name__ == "__main__":
    main()
