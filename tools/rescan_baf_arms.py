#!/usr/bin/env python3
"""tools/rescan_baf_arms.py -- run the current per-arm B-allele detector over the stored files of earlier runs.

Until BAF_HETLOSS_V1 the detector wrote INDETERMINATE for an arm whose loss of heterozygosity was
present in more than about 80 % of the cells (docs/memos/memo21_high_fraction_loss_of_heterozygosity.md).
Every run keeps the two files the detector reads, for every sample:

    <run>/<sample>/cnv_gatk/<sample>.allelicCounts.tsv
    <run>/<sample>/cnv_gatk/<sample>.denoisedCR.tsv

so the question "which earlier samples have such an arm" can be answered in a few seconds per
sample, without re-running the pipeline. This script runs bin/baf_cnloh_detect.py of this
checkout on those files, with the thresholds of conf/twist_apply.config, and lists

    - every arm called by the heterozygosity-loss test, and
    - every sample for which the detector warns of a second genome (contamination, chimerism).

Nothing is written into a run directory. The new summaries and sites tables go to
<out>/<run name>/, and the list of calls to <out>/rescan_calls.tsv.

    python3 tools/rescan_baf_arms.py --out /path/to/rescan_output /path/to/run1 [/path/to/run2 ...]

This is a screen, not a result. A listed arm is a reason to look at the case again; what it
means for a report is for the reporting pathologist. The detector here is the one of this
checkout; it has to be validated before its output is used (docs/sops/baf_het_loss.md).

Exit status 0, or 1 when the detector failed on a sample. Python 3.6 compatible, standard library only.
"""
import argparse
import csv
import os
import re
import subprocess
import sys

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DETECTOR = os.path.join(REPO, "bin", "baf_cnloh_detect.py")
ASSETS = os.path.join(REPO, "assets", "twist_myeloid")
OVERLAY = os.path.join(REPO, "conf", "twist_apply.config")
# option of the detector <- parameter of the panel overlay, with the value used when the overlay cannot be read
THRESHOLDS = [("--min-depth", "baf_min_depth", "20"), ("--min-het-sites", "baf_min_het_sites", "10"),
              ("--f-min", "baf_f_min", "0.10"), ("--cr-del", "baf_cr_del", "-0.15"), ("--cr-gain", "baf_cr_gain", "0.15")]
COLUMNS = ["run", "sample", "arm", "verdict", "confidence", "scope", "f_estimate", "f_lower", "evidence",
           "het_loci", "het_loci_expected", "residual_loci", "het_loss_p", "ev_lo", "ev_hi", "cr_median_log2",
           "residual_rate_ctrl"]


def overlay_thresholds():
    """The detector's thresholds as the panel overlay sets them, so that a rescan uses what a run uses."""
    values = {}
    try:
        with open(OVERLAY) as fh:
            text = fh.read()
    except OSError:
        text = ""
    args = []
    for option, param, default in THRESHOLDS:
        m = re.search(r"^\s*%s\s*=\s*(-?[0-9.]+)" % re.escape(param), text, re.M)
        values[param] = m.group(1) if m else default
        args += [option, values[param]]
    return args, values


def samples_of(run_dir):
    """[(sample, allelic counts, denoised copy ratios)] for the samples of a run that have both files."""
    found = []
    for sample in sorted(os.listdir(run_dir)):
        d = os.path.join(run_dir, sample, "cnv_gatk")
        allelic = os.path.join(d, sample + ".allelicCounts.tsv")
        denoised = os.path.join(d, sample + ".denoisedCR.tsv")
        if os.path.isfile(allelic) and os.path.isfile(denoised):
            found.append((sample, allelic, denoised))
    return found


def main():
    ap = argparse.ArgumentParser(description="Run the current per-arm B-allele detector over the stored files of earlier runs")
    ap.add_argument("runs", nargs="+", help="run output directories (each holds one directory per sample)")
    ap.add_argument("--out", required=True, help="directory for the new summaries and the list of calls; must not be inside a run")
    args = ap.parse_args()

    out = os.path.abspath(args.out)
    for run_dir in args.runs:
        if not os.path.isdir(run_dir):
            sys.exit("[error] not a directory: %s" % run_dir)
        if (out + os.sep).startswith(os.path.abspath(run_dir) + os.sep):
            sys.exit("[error] --out lies inside the run %s; choose a directory outside the runs" % run_dir)
    os.makedirs(out, exist_ok=True)
    threshold_args, values = overlay_thresholds()
    print("detector: %s" % DETECTOR)
    print("thresholds: %s" % ", ".join("%s %s" % kv for kv in sorted(values.items())))

    calls, warned, failed, n_samples = [], [], [], 0
    for run_dir in args.runs:
        run = os.path.basename(os.path.abspath(run_dir))
        found = samples_of(run_dir)
        print("%s: %d samples with allelic counts and denoised copy ratios" % (run, len(found)))
        if not found:
            continue
        os.makedirs(os.path.join(out, run), exist_ok=True)
        for sample, allelic, denoised in found:
            n_samples += 1
            prefix = os.path.join(out, run, sample + ".baf")
            p = subprocess.run([sys.executable, DETECTOR, "--allelic", allelic, "--denoised", denoised,
                                "--background", os.path.join(ASSETS, "baf_background.tsv"),
                                "--snp-bed", os.path.join(ASSETS, "snp_sites.baf.bed"),
                                "--sample", sample, "--no-plot", "--out-prefix", prefix] + threshold_args,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            if p.returncode != 0:
                failed.append((run, sample, p.stderr.strip().splitlines()[-1] if p.stderr.strip() else "no message"))
                continue
            if "second genome" in p.stderr:
                warned.append((run, sample))
            with open(prefix + ".summary.tsv") as fh:
                for r in csv.DictReader(fh, delimiter="\t"):
                    if str(r.get("evidence", "")).startswith("het_loss"):
                        r["run"] = run
                        calls.append(r)

    with open(os.path.join(out, "rescan_calls.tsv"), "w") as fh:
        fh.write("\t".join(COLUMNS) + "\n")
        for r in calls:
            fh.write("\t".join(str(r.get(c, "NA")) for c in COLUMNS) + "\n")

    print("")
    print("%d samples rescanned, %d arms called by the heterozygosity-loss test in %d samples" % (
        n_samples, len(calls), len(set((r["run"], r["sample"]) for r in calls))))
    for r in calls:
        bound = "" if r.get("f_lower", "NA") == "NA" else " (at least %s)" % r["f_lower"]
        print("  %s  %s  %s: %s %s, scope %s, f %s%s, %s of %s expected heterozygous loci, %s:%.1f-%.1f Mb" % (
            r["run"], r["sample"], r["arm"], r["verdict"], r["confidence"], r["scope"], r["f_estimate"], bound,
            r["het_loci"], r["het_loci_expected"], r["region"].split(":")[0], int(r["ev_lo"]) / 1e6, int(r["ev_hi"]) / 1e6))
    if warned:
        print("%d samples with the pattern of a second genome (per-arm verdicts unreliable):" % len(warned))
        for run, sample in warned:
            print("  %s  %s" % (run, sample))
    for run, sample, message in failed:
        print("FAILED  %s  %s: %s" % (run, sample, message))
    print("list of calls: %s" % os.path.join(out, "rescan_calls.tsv"))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
