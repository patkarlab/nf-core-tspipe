#!/usr/bin/env python3
"""tests/baf/fuzz_baf_detector.py -- random synthetic samples through the BAF detector and its readers.

The regression tests (run_baf_tests.py) pin down chosen cases; this script looks for what nobody
chose. Each round makes a synthetic sample with a random sex, depth, contamination and up to
four random events (whole arms or regions, any type, any clonal fraction), sometimes removes
the coverage of a chromosome or the copy-ratio bins of an arm, and then runs

    bin/baf_cnloh_detect.py            with and without the heterozygosity-loss test
    bin/cnv_consensus_multi.py         on the result (inputs made up as in run_baf_tests.py)
    the dashboard's BAF-by-arm parser  on the summary

and checks the invariants that must hold whatever the sample:

  - no program fails, and no 'nan' or 'inf' is written to a table;
  - the summary has 32 columns, the verdicts are known ones, and every fraction lies
    between 0 and 1; --no-het-loss never produces a heterozygosity-loss call;
  - an arm without a heterozygosity-loss call has exactly the BAF_V2 result (all 18 columns;
    the scope column may differ when the other arm of the chromosome was called);
  - a heterozygosity-loss call has a stretch inside its arm and is never on chrX or chrY; a
    ROH with a vote gives the consensus call CNLOH and nothing else; in the rounds run with
    --loh-segment-advisory and --roh-advisory, every segment and every ROH is LOW;
  - the consensus never gives a B call to a gene outside the stretch (which counts up to the
    arm boundary at an end of the arm it runs to).

    python3 tests/baf/fuzz_baf_detector.py                 200 rounds, seed 1
    python3 tests/baf/fuzz_baf_detector.py --rounds 1000 --seed 7

Exit status 0 when every round holds, 1 otherwise (the failing rounds are listed with their
simulator arguments, so each can be reproduced). Python 3.6 compatible, standard library only.
"""
import argparse
import os
import random
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_baf_tests as T   # noqa: E402  (simulate, detect, consensus and the paths)

VERDICTS = ("NEUTRAL", "INDETERMINATE", "DEL", "CNLOH", "GAIN", "IMBALANCE", "ROH")
ARMS = ["%d%s" % (c, a) for c in range(1, 23) for a in "pq"] + ["Xp", "Xq"]
CHROM_LENGTH = 130000000    # events on regions are drawn inside this; longer than most arms on purpose


def random_events(rng):
    events = []
    for _ in range(rng.choice([0, 1, 1, 1, 2, 2, 3, 4])):
        kind = rng.choice(["cnloh", "cnloh", "del", "gain"])
        f = rng.choice([round(rng.uniform(0.05, 1.0), 2), 1.0, 0.9, 0.95, 0.85, 0.8])
        if rng.random() < 0.3:
            chrom = "chr%s" % rng.choice([str(i) for i in range(1, 23)] + ["X"])
            lo = rng.randrange(0, CHROM_LENGTH - 2000000)
            hi = rng.randrange(lo + 1000000, CHROM_LENGTH)
            events.append("%s:%d-%d:%s:%s" % (chrom, lo, hi, kind, f))
        else:
            events.append("%s:%s:%s" % (rng.choice(ARMS), kind, f))
    return events


def drop_lines(path, keep):
    """Rewrite a GATK table keeping the header lines and the data lines for which keep(fields) is true."""
    with open(path) as fh:
        lines = fh.readlines()
    with open(path, "w") as fh:
        for line in lines:
            p = line.split("\t")
            if line.startswith("@") or p[0] == "CONTIG" or keep(p):
                fh.write(line)


def check_round(work, i, rng):
    problems = []
    name = "fuzz_%04d" % i
    sex = rng.choice(["female", "male"])
    events = random_events(rng)
    extra = ["--contamination", str(rng.choice([0, 0, 0, 0, 0.02, 0.05, 0.1, 0.3])),
             "--depth-scale", str(rng.choice([1, 1, 1, 0.5, 0.25, 0.1, 0.05, 0.02]))]
    seed = rng.randrange(1, 10 ** 8)
    what = "--sex %s --seed %d %s %s" % (sex, seed, " ".join(extra), " ".join("--event " + e for e in events))
    px = T.simulate(work, name, sex=sex, events=events, seed=seed, extra=extra)
    mutilation = rng.random()
    if mutilation < 0.10:      # a chromosome without any coverage at the catalog sites
        gone = "chr%d" % rng.randrange(1, 23)
        drop_lines(px + ".allelicCounts.tsv", lambda p: p[0] != gone)
        what += "  [no allelic counts on %s]" % gone
    elif mutilation < 0.20:    # an arm side without copy-ratio bins
        gone = "chr%d" % rng.randrange(1, 23)
        drop_lines(px + ".denoisedCR.tsv", lambda p: not (p[0] == gone and int(p[1]) > 60000000))
        what += "  [no copy-ratio bins on %s beyond 60 Mb]" % gone

    advisory = rng.random() < 0.25      # a quarter of the rounds with both advisory switches
    if advisory:
        what += "  [--loh-segment-advisory --roh-advisory]"
    try:
        new, new_raw, out_new, _ = T.detect(px, name, "new", ["--loh-segment-advisory", "--roh-advisory"] if advisory else [])
        old, old_raw, _, _ = T.detect(px, name, "v2", ["--no-het-loss"])
    except SystemExit:
        return what, ["detector failed"]

    if len(new_raw[0]) != 32 or len(old_raw[0]) != 32:
        problems.append("column count %d / %d" % (len(new_raw[0]), len(old_raw[0])))
    if any(r["evidence"].startswith("het_loss") for r in old.values()):
        problems.append("heterozygosity-loss call with --no-het-loss")
    for raw in (new_raw, old_raw):
        if any(cell.lower() in ("nan", "inf", "-inf") for row in raw for cell in row):
            problems.append("nan or inf written to the summary")
    old_v2 = dict((r[1], r[:T.V2_COLUMNS]) for r in old_raw[1:])
    for raw_row in new_raw[1:]:
        arm = raw_row[1]
        r = new[arm]
        if r["verdict"] not in VERDICTS:
            problems.append("%s: unknown verdict %s" % (arm, r["verdict"]))
        for col in ("f_estimate", "f_lower"):
            if r[col] != "NA" and not 0.0 <= float(r[col]) <= 1.0:
                problems.append("%s: %s = %s" % (arm, col, r[col]))
        if r["evidence"].startswith("het_loss"):
            lo, hi = int(r["ev_lo"]), int(r["ev_hi"])
            region = r["region"].split(":")[1].split("-")
            if not int(region[0]) <= lo <= hi <= int(region[1]):
                problems.append("%s: stretch %d-%d outside the arm %s" % (arm, lo, hi, r["region"]))
            if arm[:-1] in ("X", "Y"):
                problems.append("%s: heterozygosity-loss call on a sex chromosome" % arm)
            if advisory and r["confidence"] != "LOW" and (r["scope"] == "segment" or r["verdict"] == "ROH"):
                problems.append("%s: %s %s with confidence %s under the advisory switches" % (arm, r["scope"], r["verdict"], r["confidence"]))
            if r["evidence"] == "het_loss_complete" and r["f_estimate"] != "1.000":
                problems.append("%s: complete loss with f_estimate %s" % (arm, r["f_estimate"]))
        else:
            # untouched by the new test: the BAF_V2 result, the scope column apart (index 16)
            a, b = list(raw_row[:T.V2_COLUMNS]), list(old_v2.get(arm, []))
            if b:
                a[16] = b[16] = ""
            if a != b:
                problems.append("%s: BAF_V2 columns changed without a heterozygosity-loss call" % arm)

    # the readers of the summary
    try:
        genes, _, _ = T.consensus(work, name, out_new, px + ".denoisedCR.tsv", sex=sex)
    except SystemExit:
        return what, problems + ["consensus failed"]
    for g in genes.values():
        state = g.get("allelic_state", "")
        arm = state.split(":")[0] if ":" in state else None
        r = new.get(arm) if arm else None
        if r is None:
            continue
        if g["b_call"] not in ("NA", "NEUTRAL") and r["confidence"] != "HIGH":
            problems.append("%s: B call %s from a %s arm result" % (g["gene"], g["b_call"], r["confidence"]))
        if g["b_call"] == "ROH" and g["consensus_call"] not in ("CNLOH", "BLACKLISTED"):   # depth arms are neutral here
            problems.append("%s: ROH vote gave consensus call %s" % (g["gene"], g["consensus_call"]))
        if r["evidence"].startswith("het_loss") and g["b_call"] not in ("NA", "NEUTRAL"):
            # towards an end of the arm that the stretch runs to, it counts up to the arm boundary
            arm_lo, arm_hi = [int(x) for x in r["region"].split(":")[1].split("-")]
            lo = arm_lo if r["ev_ends"] in ("both", "start") else int(r["ev_lo"])
            hi = arm_hi if r["ev_ends"] in ("both", "end") else int(r["ev_hi"])
            if int(g["end"]) < lo or int(g["start"]) > hi:
                problems.append("%s: B call %s outside the stretch %d-%d" % (g["gene"], g["b_call"], lo, hi))
    try:
        sys.path.insert(0, os.path.join(T.BIN, "dashboard_builder"))
        from parsers import cnv_v2
        d = os.path.join(work, "dash_" + name)
        os.makedirs(os.path.join(d, "cnv", "baf"))
        shutil.copy(out_new + ".summary.tsv", os.path.join(d, "cnv", "baf", name + ".baf.summary.tsv"))
        ctx = cnv_v2.parse(d, name)
        if len(ctx.get("baf_arms", [])) != len(new_raw) - 1:
            problems.append("dashboard parser returned %d arm rows for %d" % (len(ctx.get("baf_arms", [])), len(new_raw) - 1))
    except ImportError:
        pass
    except Exception as exc:   # the parser must not fail on any summary the detector writes
        problems.append("dashboard parser failed: %r" % (exc,))
    return what, problems


def main():
    ap = argparse.ArgumentParser(description="Random synthetic samples through the BAF detector and its readers")
    ap.add_argument("--rounds", type=int, default=200)
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()
    rng = random.Random(args.seed)
    failed, n_events = [], 0
    for i in range(args.rounds):
        work = tempfile.mkdtemp(prefix="baf_fuzz_")
        try:
            what, problems = check_round(work, i, rng)
        finally:
            shutil.rmtree(work, ignore_errors=True)
        n_events += what.count("--event")
        if problems:
            failed.append((i, what, problems))
            print("FAIL round %d: %s\n     %s" % (i, "; ".join(problems[:6]), what))
    print("%d rounds (seed %d), %d planted events, %d rounds failed" % (args.rounds, args.seed, n_events, len(failed)))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
