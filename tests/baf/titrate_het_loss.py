#!/usr/bin/env python3
"""tests/baf/titrate_het_loss.py -- clone-fraction titration of bin/baf_cnloh_detect.py on synthetic samples.

For one arm and one event type, plants the event at each clonal fraction in --levels on
--replicates synthetic samples (tests/baf/simulate_baf_sample.py; seed = --seed + replicate,
so a re-run reproduces the table), and runs the detector twice on every sample:

    BAF_V2          --no-het-loss   (the detector as it was before BAF_HETLOSS_V1)
    BAF_HETLOSS_V1  default

Prints one line per level: how often the planted arm was called by each, with which verdict,
the median f_estimate, and how many OTHER arms were called in total (false positives). The
BAF_HETLOSS_V1 line ends with two counts of what the new test changed in the 18 BAF_V2
columns: on the planted arm where BAF_V2 already had a call, and on any other arm. Both are
expected to be 0 except where the heterozygous loci of a called arm are significantly depleted.
--out writes every run as a TSV row.

    python3 tests/baf/titrate_het_loss.py --arm 11q --type cnloh
    python3 tests/baf/titrate_het_loss.py --arm 7q  --type del   --levels 0.5,0.8,0.9,0.95,1.0
    python3 tests/baf/titrate_het_loss.py --arm none --replicates 200        (false-positive side only)

On a real sample (--base). The synthetic samples carry the noise the simulator was given; what a
real sample shows at its homozygous sites decides how well the residual sites of an event
stand out. --base PREFIX takes PREFIX.allelicCounts.tsv and PREFIX.denoisedCR.tsv of a real
sample (the two files of its cnv_gatk output directory) and plants the event in them instead:
inside the event every site that is heterozygous in the sample (ALT fraction 0.10-0.90) has
its ALT count redrawn binomially at the shifted fraction, with a random side per site; depth
and copy ratio are scaled for a deletion or gain; every other site of the sample, on the arm
and elsewhere, keeps its real counts. The arm should be one without an event of its own.

    python3 tests/baf/titrate_het_loss.py --base /path/to/SAMPLE/cnv_gatk/SAMPLE --arm 11q --type cnloh \
        --levels 0,0.6,0.8,0.85,0.9,0.95,0.98,1.0

Python 3.6 compatible, standard library only.
"""
import argparse
import csv
import math
import os
import random
import shutil
import statistics
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
ASSETS = os.path.join(REPO, "assets", "twist_myeloid")
SIMULATE = os.path.join(HERE, "simulate_baf_sample.py")
DETECT = os.path.join(REPO, "bin", "baf_cnloh_detect.py")
NO_CALL = ("NEUTRAL", "INDETERMINATE")
V2_COLUMNS = 18      # columns of the BAF_V2 summary; BAF_HETLOSS_V1 appends after them
sys.path.insert(0, HERE)
import simulate_baf_sample as SIM   # noqa: E402  (event syntax, shifted fractions, binomial draw)


def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if p.returncode != 0:
        sys.stderr.write("[error] %s\n%s\n" % (" ".join(cmd), p.stderr))
        sys.exit(1)
    return p.stdout


def detect(prefix, sample, out_prefix, extra):
    run([sys.executable, DETECT, "--allelic", prefix + ".allelicCounts.tsv", "--denoised", prefix + ".denoisedCR.tsv",
         "--background", os.path.join(ASSETS, "baf_background.tsv"), "--snp-bed", os.path.join(ASSETS, "snp_sites.baf.bed"),
         "--sample", sample, "--min-depth", "20", "--min-het-sites", "10", "--f-min", "0.10",
         "--cr-del", "-0.15", "--cr-gain", "0.15", "--no-plot", "--out-prefix", out_prefix] + extra)
    with open(out_prefix + ".summary.tsv") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    with open(out_prefix + ".summary.tsv") as fh:
        raw = [line.rstrip("\n").split("\t") for line in fh][1:]
    return rows, dict((r[1], r[:V2_COLUMNS]) for r in raw)


def plant_in_real_sample(base, prefix, event, rng):
    """Copy base.allelicCounts.tsv / base.denoisedCR.tsv to prefix.*, with one event planted.

    event: (chrom, start, end, type, f) as SIM.parse_events returns it, or None for a plain copy.
    Sites heterozygous in the sample (ALT fraction 0.10-0.90) inside the event are redrawn at
    the shifted fraction; homozygous sites keep their observed minor-read share. Returns the
    number of heterozygous sites redrawn."""
    redrawn = 0
    scale, shift = 1.0, 0.0
    if event is not None:
        chrom, start, end, etype, f = event
        scale = SIM.copies(etype, f) / 2.0
        shift = math.log(scale, 2)
    with open(base + ".allelicCounts.tsv") as src, open(prefix + ".allelicCounts.tsv", "w") as dst:
        for line in src:
            p = line.rstrip("\n").split("\t")
            if event is None or line.startswith("@") or p[0] != chrom or len(p) < 4 or not p[1].isdigit() \
                    or not start <= int(p[1]) <= end:
                dst.write(line)
                continue
            ref, alt = int(p[2]), int(p[3])
            depth = ref + alt
            if depth > 0:
                new_depth = int(round(depth * scale))
                if 0.10 <= alt / float(depth) <= 0.90:
                    alt = SIM.draw_binomial(rng, new_depth, SIM.shifted_fraction(etype, f, rng.random() < 0.5))
                    redrawn += 1
                else:
                    alt = min(new_depth, int(round(alt * scale)))
                ref = new_depth - alt
            dst.write("\t".join([p[0], p[1], str(ref), str(alt)] + p[4:]) + "\n")
    with open(base + ".denoisedCR.tsv") as src, open(prefix + ".denoisedCR.tsv", "w") as dst:
        col = None
        for line in src:
            p = line.rstrip("\n").split("\t")
            if line.startswith("@"):
                dst.write(line)
                continue
            if col is None:
                col = dict((name, i) for i, name in enumerate(p))
                dst.write(line)
                continue
            if event is not None and shift != 0.0 and p[col["CONTIG"]] == chrom \
                    and int(p[col["END"]]) >= start and int(p[col["START"]]) <= end:
                p[col["LOG2_COPY_RATIO"]] = "%.6f" % (float(p[col["LOG2_COPY_RATIO"]]) + shift)
                dst.write("\t".join(p) + "\n")
            else:
                dst.write(line)
    return redrawn


def main():
    ap = argparse.ArgumentParser(description="Clone-fraction titration of the BAF detector on synthetic samples")
    ap.add_argument("--arm", default="11q", help="arm to plant the event on (e.g. 11q, 17p), or 'none' for unmodified samples")
    ap.add_argument("--type", default="cnloh", choices=["cnloh", "del", "gain"])
    ap.add_argument("--levels", default="0,0.2,0.4,0.6,0.7,0.75,0.8,0.85,0.9,0.95,0.98,1.0")
    ap.add_argument("--replicates", type=int, default=20)
    ap.add_argument("--sex", default="female", choices=["male", "female"])
    ap.add_argument("--contamination", type=float, default=0.0)
    ap.add_argument("--depth-scale", type=float, default=1.0)
    ap.add_argument("--region", default=None,
                    help="plant the event on CHR:START-END instead of the whole arm (--arm still names the arm that is read)")
    ap.add_argument("--seed", type=int, default=20261125)
    ap.add_argument("--base", default=None,
                    help="plant the events in a real sample instead of simulating one: prefix of its "
                         ".allelicCounts.tsv and .denoisedCR.tsv (the files of its cnv_gatk directory)")
    ap.add_argument("--out", default=None, help="TSV with one row per run")
    args = ap.parse_args()

    if args.base:
        for ext in (".allelicCounts.tsv", ".denoisedCR.tsv"):
            if not os.path.isfile(args.base + ext):
                sys.exit("[error] --base: %s not found" % (args.base + ext))
        if args.arm == "none":
            sys.exit("[error] --base needs an arm to plant the event on; run the detector on the sample itself for the unmodified case")
    levels = [0.0] if args.arm == "none" else [float(x) for x in args.levels.split(",")]
    work = tempfile.mkdtemp(prefix="baf_titration_")
    runs = []
    try:
        for f in levels:
            for rep in range(args.replicates):
                sample = "SIM_%s_%s_f%03d_r%02d" % (args.arm, args.type, int(round(f * 100)), rep)
                prefix = os.path.join(work, sample)
                if args.base:
                    event = SIM.parse_events(["%s:%s:%s" % (args.region or args.arm, args.type, f)])[0] if f > 0 else None
                    plant_in_real_sample(args.base, prefix, event, random.Random(args.seed + 1000 * rep + int(round(f * 100))))
                else:
                    cmd = [sys.executable, SIMULATE, "--sample", sample, "--out-prefix", prefix, "--sex", args.sex,
                           "--seed", str(args.seed + rep), "--contamination", str(args.contamination),
                           "--depth-scale", str(args.depth_scale)]
                    if args.arm != "none" and f > 0:
                        cmd += ["--event", "%s:%s:%s" % (args.region or args.arm, args.type, f)]
                    run(cmd)
                v2_columns = {}
                for label, extra in (("BAF_V2", ["--no-het-loss"]), ("BAF_HETLOSS_V1", [])):
                    rows, v2_columns[label] = detect(prefix, sample, prefix + "." + label, extra)
                    target = next((r for r in rows if r["arm"] == args.arm), None)
                    others = [r for r in rows if r["arm"] != args.arm and r["verdict"] not in NO_CALL]
                    runs.append({"detector": label, "level": f, "replicate": rep,
                                 "verdict": target["verdict"] if target else "NA",
                                 "confidence": target["confidence"] if target else "NA",
                                 "f_estimate": target["f_estimate"] if target else "NA",
                                 "evidence": target.get("evidence", "NA") if target else "NA",
                                 "n_het": target["n_het"] if target else "NA",
                                 "het_loci": target.get("het_loci", "NA") if target else "NA",
                                 "het_loci_expected": target.get("het_loci_expected", "NA") if target else "NA",
                                 "residual_loci": target.get("residual_loci", "NA") if target else "NA",
                                 "other_arm_calls": ";".join("%s:%s(%s)" % (r["arm"], r["verdict"], r["confidence"]) for r in others),
                                 "v2_call_altered": 0, "other_rows_altered": 0})
                # what the new test changed in the BAF_V2 columns of this sample
                before, after = v2_columns["BAF_V2"], v2_columns["BAF_HETLOSS_V1"]
                altered = [arm for arm in before if before[arm] != after.get(arm)]
                old_run, new_run = runs[-2], runs[-1]
                new_run["v2_call_altered"] = int(args.arm in altered and old_run["verdict"] not in NO_CALL + ("NA",))
                new_run["other_rows_altered"] = len([arm for arm in altered if arm != args.arm])
                for ext in (".allelicCounts.tsv", ".denoisedCR.tsv"):
                    os.remove(prefix + ext)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    if args.out:
        cols = ["detector", "level", "replicate", "verdict", "confidence", "f_estimate", "evidence", "n_het",
                "het_loci", "het_loci_expected", "residual_loci", "other_arm_calls", "v2_call_altered", "other_rows_altered"]
        with open(args.out, "w") as fh:
            fh.write("\t".join(cols) + "\n")
            for r in runs:
                fh.write("\t".join(str(r[c]) for c in cols) + "\n")

    what = "unmodified samples" if args.arm == "none" else "%s %s%s" % (
        args.arm, args.type, " on %s" % args.region if args.region else "")
    if args.base:
        print("%s planted in the real sample %s, %d replicates per level, seed %d" % (
            what, os.path.basename(args.base), args.replicates, args.seed))
    else:
        print("%s, %d replicates per level, sex %s, contamination %s, depth scale %s, seed %d" % (
            what, args.replicates, args.sex, args.contamination, args.depth_scale, args.seed))
    print("level  detector         called  HIGH  verdicts                      f_estimate median (min-max)  calls on other arms  BAF_V2 calls altered / other arm rows altered")
    for f in levels:
        for label in ("BAF_V2", "BAF_HETLOSS_V1"):
            rs = [r for r in runs if r["level"] == f and r["detector"] == label]
            called = [r for r in rs if r["verdict"] not in NO_CALL + ("NA",)]
            high = [r for r in called if r["confidence"] == "HIGH"]
            verdicts = {}
            for r in rs:
                verdicts[r["verdict"]] = verdicts.get(r["verdict"], 0) + 1
            fe = []
            for r in called:
                try:
                    fe.append(float(r["f_estimate"]))
                except ValueError:
                    pass
            f_txt = "%.3f (%.3f-%.3f)" % (statistics.median(fe), min(fe), max(fe)) if fe else "-"
            n_other = sum(len(r["other_arm_calls"].split(";")) for r in rs if r["other_arm_calls"])
            tail = ""
            if label == "BAF_HETLOSS_V1":
                tail = "%d / %d" % (sum(r["v2_call_altered"] for r in rs), sum(r["other_rows_altered"] for r in rs))
            print("%-5s  %-15s  %2d/%-3d  %-4d  %-28s  %-27s  %-19d  %s" % (
                ("%.2f" % f), label, len(called), len(rs), len(high),
                " ".join("%s:%d" % kv for kv in sorted(verdicts.items())), f_txt, n_other, tail))


if __name__ == "__main__":
    main()
