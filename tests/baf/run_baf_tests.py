#!/usr/bin/env python3
"""tests/baf/run_baf_tests.py -- regression tests for the per-arm BAF detector and what reads its output.

Covers bin/baf_cnloh_detect.py (BAF_V2 + BAF_HETLOSS_V1), the B arm of bin/cnv_consensus_multi.py,
bin/plot_genome_overview.py, bin/plot_arm_17p.py, the dashboard's BAF-by-arm parser,
tools/compare_baf_arms.py and tools/rescan_baf_arms.py, on synthetic samples made by
tests/baf/simulate_baf_sample.py from the panel's own background table. No patient data, no network, nothing outside the repository; about
one minute, half of it the two figures.

    python3 tests/baf/run_baf_tests.py                 all tests
    python3 tests/baf/run_baf_tests.py --skip-plots    without the two figures (no matplotlib needed)
    python3 tests/baf/run_baf_tests.py --keep DIR      leave the synthetic samples and outputs in DIR

Exit status 0 when every check passes, 1 otherwise. Python 3.6 compatible, standard library only.

What the checks pin down:
  1. A sample without events: no call; --no-het-loss changes nothing.
  2. The defect found on 25 Nov 2026 (an 11q copy-neutral LOH in 90 % of the cells): BAF_V2 has no
     call, the heterozygosity-loss test calls 11q CNLOH HIGH at f 0.90, and no other arm row changes.
  3. A fraction inside the het band (13q, 60 %): the verdict and every BAF_V2 column are untouched.
  4. Heterozygosity absent (11q, 100 %): ROH with a lower bound, not CNLOH; with a copy-number loss: DEL.
  5. Loss of a whole chromosome in 95 % of the cells: DEL on both arms, scope chromosome.
  6. An event over part of an arm: scope segment with the right start, rated like an arm call
     (LOW with --loh-segment-advisory); over most of the arm: arm-level.
  7. chrX is never tested (a male has no heterozygous site there by constitution).
  8. A contaminated sample (5 % of a second genotype): no heterozygosity-loss call, and the
     second-genome warning with a high residual_rate_ctrl; a clean sample has neither.
  9. A background table without the cohort frequencies: the test is skipped with a warning.
 10. Consensus: genes inside the stretch get the B call, genes outside do not; a segment votes for
     the genes inside it and a ROH counts as copy-neutral loss (BAF_HETLOSS_V1B); neither votes when
     the detector is run with its advisory switch, and LOW never does.
 11. The genome-wide figure and the 17p page are written from the new JSON; the dashboard parser
     returns the new columns and still reads a summary written before BAF_HETLOSS_V1.
 12. tools/compare_baf_arms.py lists a heterozygosity-loss call as an explained difference between
     two runs and fails on any other difference.
 13. tools/rescan_baf_arms.py finds the affected arm from the stored files of an earlier run and
     writes nothing into that run.
"""
import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
ASSETS = os.path.join(REPO, "assets", "twist_myeloid")
BIN = os.path.join(REPO, "bin")
SIMULATE = os.path.join(HERE, "simulate_baf_sample.py")
BACKGROUND = os.path.join(ASSETS, "baf_background.tsv")
SNP_BED = os.path.join(ASSETS, "snp_sites.baf.bed")
NO_CALL = ("NEUTRAL", "INDETERMINATE")
V2_COLUMNS = 18      # columns of the BAF_V2 summary; BAF_HETLOSS_V1 appends, never reorders
SEED = 20261125

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print("%-4s %s%s" % ("ok" if ok else "FAIL", name, ("  -- " + detail) if (detail and not ok) else ""))


def run(cmd, expect_ok=True):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if expect_ok and p.returncode != 0:
        sys.stderr.write("[error] command failed (%d): %s\n%s\n" % (p.returncode, " ".join(cmd), p.stderr))
        sys.exit(2)
    return p


def simulate(work, name, sex="female", events=(), seed=SEED, extra=()):
    prefix = os.path.join(work, name)
    cmd = [sys.executable, SIMULATE, "--sample", name, "--out-prefix", prefix, "--sex", sex, "--seed", str(seed)]
    for e in events:
        cmd += ["--event", e]
    run(cmd + list(extra))
    return prefix


def detect(prefix, name, tag, extra=(), background=BACKGROUND):
    out = "%s.%s" % (prefix, tag)
    p = run([sys.executable, os.path.join(BIN, "baf_cnloh_detect.py"), "--allelic", prefix + ".allelicCounts.tsv",
             "--denoised", prefix + ".denoisedCR.tsv", "--background", background, "--snp-bed", SNP_BED,
             "--sample", name, "--min-depth", "20", "--min-het-sites", "10", "--f-min", "0.10",
             "--cr-del", "-0.15", "--cr-gain", "0.15", "--no-plot", "--out-prefix", out] + list(extra))
    with open(out + ".summary.tsv") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    with open(out + ".summary.tsv") as fh:
        raw = [line.rstrip("\n").split("\t") for line in fh]
    return dict((r["arm"], r) for r in rows), raw, out, p


def v2_part(raw, skip_arm=None):
    return [r[:V2_COLUMNS] for r in raw if skip_arm is None or r[1] != skip_arm]


def calls(arms):
    return dict((a, r) for a, r in arms.items() if r["verdict"] not in NO_CALL)


# ---------------------------------------------------------------- inputs for the consensus, made up around a BAF result
def gene_spans():
    spans = {}
    with open(os.path.join(ASSETS, "targets.exonwise.bed")) as fh:
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if len(p) < 4 or "_exon" not in p[3]:
                continue
            g = p[3].split("_exon")[0]
            c, s, e = p[0], int(p[1]), int(p[2])
            cur = spans.get(g)
            spans[g] = (c, s, e) if cur is None else (c, min(cur[1], s), max(cur[2], e))
    return spans


def consensus(work, name, baf_out, denoised, sex="female"):
    """Copy-neutral depth arms around a BAF result; returns ({gene: row}, json payload)."""
    spans = gene_spans()
    base = os.path.join(work, name + ".cmx")
    chroms = ["chr%d" % i for i in range(1, 23)] + ["chrX"]
    with open(base + ".call.cns", "w") as fh:
        fh.write("chromosome\tstart\tend\tgene\tlog2\tcn\n")
        for c in chroms:
            fh.write("%s\t1\t250000000\t-\t0.0\t%d\n" % (c, 1 if (c == "chrX" and sex == "male") else 2))
    with open(base + ".cnr", "w") as fh:
        fh.write("chromosome\tstart\tend\tgene\tlog2\tdepth\tweight\n")
        for g, (c, s, e) in sorted(spans.items(), key=lambda kv: kv[1]):
            fh.write("%s\t%d\t%d\t%s\t0.0\t1000\t1.0\n" % (c, s, e, g))
    with open(base + ".gatk_genes.tsv", "w") as fh:
        fh.write("gene\tchrom\tstart\tend\tn_bins\tmedian_denoised_log2\tseg_call\tseg_mean_log2\tn_segments\n")
        for g, (c, s, e) in sorted(spans.items(), key=lambda kv: kv[1]):
            fh.write("%s\t%s\t%d\t%d\t5\t0.0\t0\t0.0000\t1\n" % (g, c, s, e))
    with open(base + ".called.seg", "w") as fh:
        fh.write("@HD\tVN:1.6\nCONTIG\tSTART\tEND\tNUM_POINTS_COPY_RATIO\tMEAN_LOG2_COPY_RATIO\tCALL\n")
        for c in chroms:
            fh.write("%s\t1\t250000000\t100\t0.0\t0\n" % c)
    run([sys.executable, os.path.join(BIN, "cnv_consensus_multi.py"), "--sample", name, "--sex", sex,
         "--cnr", base + ".cnr", "--call-cns", base + ".call.cns", "--gatk-genes", base + ".gatk_genes.tsv",
         "--gatk-called", base + ".called.seg", "--denoised", denoised,
         "--baf-summary", baf_out + ".summary.tsv", "--baf-sites", baf_out + ".sites.tsv",
         "--loo-summary", os.path.join(ASSETS, "cnvkit_loo_summary.tsv"), "--out-prefix", base])
    with open(base + ".genes.tsv") as fh:
        genes = dict((r["gene"], r) for r in csv.DictReader(fh, delimiter="\t"))
    with open(base + ".json") as fh:
        payload = json.load(fh)
    return genes, payload, base


def main():
    ap = argparse.ArgumentParser(description="Regression tests for the per-arm BAF detector and its consumers")
    ap.add_argument("--skip-plots", action="store_true")
    ap.add_argument("--keep", default=None, help="directory to leave the synthetic samples and outputs in")
    args = ap.parse_args()
    work = args.keep or tempfile.mkdtemp(prefix="baf_tests_")
    if args.keep and not os.path.isdir(work):
        os.makedirs(work)

    # ---- 1. no event
    px = simulate(work, "normal_f")
    new, new_raw, _, proc_clean = detect(px, "normal_f", "new")
    old, old_raw, _, _ = detect(px, "normal_f", "v2", ["--no-het-loss"])
    check("1a sample without events: no call", not calls(new), str(sorted(calls(new))))
    check("1b sample without events: BAF_V2 columns identical with and without the new test",
          v2_part(new_raw) == v2_part(old_raw))
    check("1c summary keeps the 18 BAF_V2 columns in place and appends the new ones",
          new_raw[0][:V2_COLUMNS] == old_raw[0][:V2_COLUMNS] and new_raw[0][V2_COLUMNS] == "n_residual"
          and len(new_raw[0]) == 32 and new_raw[0][-1] == "residual_rate_ctrl", "header: %s" % ",".join(new_raw[0]))
    clean_rates = [float(r["residual_rate_ctrl"]) for r in new.values() if r["residual_rate_ctrl"] != "NA"]
    check("1d ... and its residual rate on the control arms is low on every autosomal arm, no second-genome warning",
          clean_rates and max(clean_rates) < 0.05 and "second genome" not in proc_clean.stderr,
          "max %s | %s" % (max(clean_rates) if clean_rates else "NA", proc_clean.stderr.strip()[:120]))

    # ---- 2. the defect: 11q copy-neutral LOH in 90 % of the cells
    px = simulate(work, "cnloh11q_090", events=["11q:cnloh:0.90"])
    new, new_raw, out_11q, _ = detect(px, "cnloh11q_090", "new")
    old, old_raw, _, _ = detect(px, "cnloh11q_090", "v2", ["--no-het-loss"])
    r = new["11q"]
    check("2a BAF_V2 misses an 11q cnLOH at 90 % (arm INDETERMINATE, no call anywhere)",
          old["11q"]["verdict"] == "INDETERMINATE" and not calls(old), old["11q"]["verdict"])
    check("2b the new test calls it: 11q CNLOH, HIGH, arm, residual mode",
          (r["verdict"], r["confidence"], r["scope"], r["evidence"]) == ("CNLOH", "HIGH", "arm", "het_loss_residual"),
          str((r["verdict"], r["confidence"], r["scope"], r["evidence"])))
    check("2c clonal fraction read back as 0.90 (0.88-0.92)", 0.88 <= float(r["f_estimate"]) <= 0.92, r["f_estimate"])
    check("2d 11q is the only arm with a call", sorted(calls(new)) == ["11q"], str(sorted(calls(new))))
    check("2e every other arm row is unchanged in its BAF_V2 columns",
          v2_part(new_raw, "11q") == v2_part(old_raw, "11q"))
    check("2f stretch runs over the arm (ev_ends both) and starts beyond the centromere",
          r["ev_ends"] == "both" and 55800000 < int(r["ev_lo"]) < 65000000 < 130000000 < int(r["ev_hi"]),
          "%s %s %s" % (r["ev_lo"], r["ev_hi"], r["ev_ends"]))
    px_11q, name_11q = px, "cnloh11q_090"

    # ---- 3. a fraction inside the het band is left to BAF_V2
    px = simulate(work, "cnloh13q_060", events=["13q:cnloh:0.60"])
    new, new_raw, _, _ = detect(px, "cnloh13q_060", "new")
    old, old_raw, _, _ = detect(px, "cnloh13q_060", "v2", ["--no-het-loss"])
    check("3a 13q cnLOH at 60 %: called by the BAF_V2 statistic (evidence shift)",
          new["13q"]["verdict"] == "CNLOH" and new["13q"]["evidence"] == "shift", new["13q"]["evidence"])
    check("3b ... with every BAF_V2 column of every arm identical", v2_part(new_raw) == v2_part(old_raw))

    # ---- 4. heterozygosity absent
    px = simulate(work, "cnloh11q_100", events=["11q:cnloh:1.0"])
    new, _, out_roh, _ = detect(px, "cnloh11q_100", "new")
    r = new["11q"]
    check("4a 11q at 100 %: ROH (not CNLOH), complete mode, f written as 1.000 with a lower bound",
          (r["verdict"], r["evidence"], r["f_estimate"]) == ("ROH", "het_loss_complete", "1.000")
          and 0.90 <= float(r["f_lower"]) <= 0.96, str((r["verdict"], r["evidence"], r["f_estimate"], r["f_lower"])))
    px_roh, name_roh = px, "cnloh11q_100"
    px = simulate(work, "del11q_100", events=["11q:del:1.0"])
    new, _, _, _ = detect(px, "del11q_100", "new")
    check("4b 11q lost in every cell: DEL, HIGH", (new["11q"]["verdict"], new["11q"]["confidence"]) == ("DEL", "HIGH"),
          str((new["11q"]["verdict"], new["11q"]["confidence"])))

    # ---- 5. whole chromosome
    px = simulate(work, "mono7_095", sex="male", events=["7p:del:0.95", "7q:del:0.95"])
    new, _, _, _ = detect(px, "mono7_095", "new")
    old, _, _, _ = detect(px, "mono7_095", "v2", ["--no-het-loss"])
    check("5a loss of chromosome 7 in 95 % of the cells: BAF_V2 has no call",
          not calls(old), str(sorted(calls(old))))
    check("5b ... the new test: DEL HIGH on 7p and 7q, scope chromosome",
          all((new[a]["verdict"], new[a]["confidence"], new[a]["scope"]) == ("DEL", "HIGH", "chromosome") for a in ("7p", "7q")),
          str([(new[a]["verdict"], new[a]["confidence"], new[a]["scope"]) for a in ("7p", "7q")]))
    # ---- 7. chrX (same male sample)
    check("7  chrX is not tested: Xp and Xq keep the BAF_V2 verdict and carry no het-loss columns",
          all(new[a]["verdict"] == old[a]["verdict"] and new[a]["het_loci"] == "NA" and new[a]["evidence"] == "NA"
              for a in ("Xp", "Xq")), str([(new[a]["verdict"], new[a]["het_loci"]) for a in ("Xp", "Xq")]))

    # ---- 6. part of an arm
    px = simulate(work, "cnloh11q_distal", events=["chr11:90000000-135086622:cnloh:0.90"])
    new, _, out_seg, _ = detect(px, "cnloh11q_distal", "new")
    r = new["11q"]
    check("6a distal 11q from 90 Mb at 90 %: CNLOH, HIGH, scope segment, running to the end of the arm",
          (r["verdict"], r["confidence"], r["scope"], r["ev_ends"]) == ("CNLOH", "HIGH", "segment", "end"),
          str((r["verdict"], r["confidence"], r["scope"], r["ev_ends"])))
    adv, _, out_seg_adv, _ = detect(px, "cnloh11q_distal", "advisory", ["--loh-segment-advisory"])
    check("6a2 ... with --loh-segment-advisory the same call is LOW, and nothing else in the row differs",
          adv["11q"]["confidence"] == "LOW"
          and all(adv["11q"][k] == r[k] for k in r if k != "confidence"), adv["11q"]["confidence"])
    check("6b ... stretch starts within 3 Mb of 90 Mb and the fraction is that of the stretch (0.88-0.92)",
          87000000 <= int(r["ev_lo"]) <= 93000000 and 0.88 <= float(r["f_estimate"]) <= 0.92,
          "%s f=%s" % (r["ev_lo"], r["f_estimate"]))
    px_seg, name_seg = px, "cnloh11q_distal"
    px = simulate(work, "cnloh11q_most", events=["chr11:70000000-135086622:cnloh:0.90"])
    new, _, out_most, _ = detect(px, "cnloh11q_most", "new")
    r = new["11q"]
    check("6c 11q from 70 Mb (most of the arm): arm-level CNLOH, HIGH, stretch not reaching the centromere side",
          (r["verdict"], r["confidence"], r["scope"], r["ev_ends"]) == ("CNLOH", "HIGH", "arm", "end"),
          str((r["verdict"], r["confidence"], r["scope"], r["ev_ends"])))
    px_most, name_most = px, "cnloh11q_most"
    px = simulate(work, "cnloh11q_tip", events=["chr11:125000000-135086622:cnloh:0.90"])
    new, _, _, _ = detect(px, "cnloh11q_tip", "new")
    check("6d the last 10 Mb of 11q only: too few loci, no call", not calls(new), str(sorted(calls(new))))

    # ---- 8. contamination
    px = simulate(work, "contaminated", extra=["--contamination", "0.05"])
    new, _, out_contaminated, proc = detect(px, "contaminated", "new")
    check("8a 5 % of a second genotype: no heterozygosity-loss call on any arm",
          not [a for a, r in new.items() if r["evidence"].startswith("het_loss")],
          str([a for a, r in new.items() if r["evidence"].startswith("het_loss")]))
    rates = [float(r["residual_rate_ctrl"]) for r in new.values() if r["residual_rate_ctrl"] != "NA"]
    check("8b ... the residual rate on the control arms is high on every arm and the second-genome warning is printed",
          rates and min(rates) > 0.10 and "second genome" in proc.stderr,
          "min %s | %s" % (min(rates) if rates else "NA", proc.stderr.strip()[:120]))

    px = simulate(work, "contaminated_roh", events=["11q:cnloh:1.0"], extra=["--contamination", "0.05"])
    new, _, out_croh, _ = detect(px, "contaminated_roh", "new")
    r = new["11q"]
    check("8c 11q at 100 % in the contaminated sample: ROH, and no lower bound of the fraction is claimed",
          (r["verdict"], r["evidence"], r["f_lower"]) == ("ROH", "het_loss_complete", "NA"),
          str((r["verdict"], r["evidence"], r["f_lower"])))
    px_croh, name_croh = px, "contaminated_roh"

    # ---- 9. background without cohort frequencies
    slim = os.path.join(work, "background_without_frequencies.tsv")
    with open(BACKGROUND) as src, open(slim, "w") as dst:
        keep = None
        for line in src:
            if line.startswith("#"):
                dst.write(line)
                continue
            p = line.rstrip("\n").split("\t")
            if keep is None:
                keep = [i for i, c in enumerate(p) if c not in ("n_het_like", "n_pass_depth")]
            dst.write("\t".join(p[i] for i in keep) + "\n")
    new, new_raw, _, proc = detect(px_11q, name_11q, "slim", background=slim)
    old, old_raw, _, _ = detect(px_11q, name_11q, "v2")  # default background, for the BAF_V2 columns
    v2, v2_raw, _, _ = detect(px_11q, name_11q, "v2off", ["--no-het-loss"])
    check("9  background without n_het_like / n_pass_depth: warning, test skipped, BAF_V2 result",
          "heterozygosity-loss test skipped" in proc.stderr and v2_part(new_raw) == v2_part(v2_raw), proc.stderr.strip()[:120])

    # ---- 10. consensus
    genes, payload, cmx_11q = consensus(work, name_11q, out_11q, px_11q + ".denoisedCR.tsv")
    on_11q = [g for g in genes.values() if g["chrom"] == "chr11" and int(g["start"]) > 55800000]
    check("10a 11q cnLOH: every 11q gene gets b_call CNLOH, consensus CNLOH at TIER_2 (B alone)",
          on_11q and all((g["b_call"], g["consensus_call"], g["tier"]) == ("CNLOH", "CNLOH", "TIER_2") for g in on_11q),
          str(sorted(set((g["b_call"], g["consensus_call"], g["tier"]) for g in on_11q))))
    off_11q = [g for g in genes.values() if not (g["chrom"] == "chr11" and int(g["start"]) > 55800000)]
    check("10b ... and no gene elsewhere is touched",
          all(g["b_call"] in ("NEUTRAL", "NA") and g["consensus_call"] in ("NEUTRAL", "BLACKLISTED") for g in off_11q),
          str(sorted(set((g["b_call"], g["consensus_call"]) for g in off_11q))))
    state = genes["CBL"]["allelic_state"]
    check("10c allelic_state of CBL names arm, verdict and fraction",
          state.startswith("11q:CNLOH f=") and 0.88 <= float(state.split("f=")[1]) <= 0.92, state)
    check("10d JSON site rows carry the site class as a seventh element",
          all(len(x) == 7 and x[6] in ("het", "res", "hom") for x in payload["tracks"]["baf_sites"]))
    genes, _, _ = consensus(work, name_seg, out_seg, px_seg + ".denoisedCR.tsv")
    check("10e segment: ATM inside the stretch gets the CNLOH vote (TIER_2), with the coordinates in allelic_state",
          (genes["ATM"]["b_call"], genes["ATM"]["consensus_call"], genes["ATM"]["tier"]) == ("CNLOH", "CNLOH", "TIER_2")
          and genes["ATM"]["allelic_state"].startswith("11q:CNLOH f=") and "Mb" in genes["ATM"]["allelic_state"],
          "%s | %s | %s %s" % (genes["ATM"]["b_call"], genes["ATM"]["allelic_state"], genes["ATM"]["consensus_call"], genes["ATM"]["tier"]))
    check("10f ... SF1 (64.8 Mb) is reported as outside the stretch and gets no vote",
          genes["SF1"]["allelic_state"].startswith("11q:outside the CNLOH") and genes["SF1"]["b_call"] == "NA"
          and genes["SF1"]["consensus_call"] == "NEUTRAL", "%s | %s" % (genes["SF1"]["allelic_state"], genes["SF1"]["consensus_call"]))
    genes, _, _ = consensus(work, name_seg + "_advisory", out_seg_adv, px_seg + ".denoisedCR.tsv")
    check("10f2 advisory segment (--loh-segment-advisory): ATM is named with coordinates but gets no vote",
          genes["ATM"]["b_call"] == "NA" and "CNLOH?" in genes["ATM"]["allelic_state"]
          and "Mb" in genes["ATM"]["allelic_state"] and genes["ATM"]["consensus_call"] == "NEUTRAL",
          "%s | %s | %s" % (genes["ATM"]["b_call"], genes["ATM"]["allelic_state"], genes["ATM"]["consensus_call"]))
    genes, _, _ = consensus(work, name_most, out_most, px_most + ".denoisedCR.tsv")
    check("10g arm-level call from 70 Mb: CBL gets the CNLOH vote, SF1 (64.8 Mb, outside the stretch) does not",
          genes["CBL"]["b_call"] == "CNLOH" and genes["CBL"]["tier"] == "TIER_2"
          and genes["SF1"]["b_call"] == "NA" and genes["SF1"]["consensus_call"] == "NEUTRAL",
          "CBL %s %s | SF1 %s %s" % (genes["CBL"]["b_call"], genes["CBL"]["tier"], genes["SF1"]["b_call"], genes["SF1"]["consensus_call"]))
    genes, payload_roh, cmx_roh = consensus(work, name_roh, out_roh, px_roh + ".denoisedCR.tsv")
    check("10h ROH: b_call ROH with the lower bound, counted as copy-neutral loss (consensus CNLOH, TIER_2)",
          (genes["CBL"]["b_call"], genes["CBL"]["consensus_call"], genes["CBL"]["tier"]) == ("ROH", "CNLOH", "TIER_2")
          and genes["CBL"]["allelic_state"].startswith("11q:ROH f>=0.9")
          and "constitutional homozygous arm is not excluded" in genes["CBL"]["allelic_state"],
          "%s | %s %s | %s" % (genes["CBL"]["b_call"], genes["CBL"]["consensus_call"], genes["CBL"]["tier"], genes["CBL"]["allelic_state"]))
    adv, _, out_roh_adv, _ = detect(px_roh, name_roh, "advisory", ["--roh-advisory"])
    genes, _, _ = consensus(work, name_roh + "_advisory", out_roh_adv, px_roh + ".denoisedCR.tsv")
    check("10h2 advisory ROH (--roh-advisory): LOW, shown as ROH? and without a vote (consensus NEUTRAL)",
          (adv["11q"]["verdict"], adv["11q"]["confidence"]) == ("ROH", "LOW") and genes["CBL"]["b_call"] == "NA"
          and genes["CBL"]["consensus_call"] == "NEUTRAL" and genes["CBL"]["allelic_state"].startswith("11q:ROH? f>=0.9"),
          "%s %s | %s | %s | %s" % (adv["11q"]["verdict"], adv["11q"]["confidence"], genes["CBL"]["b_call"],
                                    genes["CBL"]["consensus_call"], genes["CBL"]["allelic_state"]))

    genes, _, _ = consensus(work, name_croh, out_croh, px_croh + ".denoisedCR.tsv")
    check("10i ROH without a bound: allelic_state says the fraction is not measurable",
          genes["CBL"]["allelic_state"].startswith("11q:ROH f not measurable"), genes["CBL"]["allelic_state"])

    # ---- 11. dashboard parser, figures
    sys.path.insert(0, os.path.join(BIN, "dashboard_builder"))
    try:
        from parsers import cnv_v2
        sample_dir = os.path.join(work, "dash_" + name_11q)
        os.makedirs(os.path.join(sample_dir, "cnv", "baf"), exist_ok=True)
        shutil.copy(out_11q + ".summary.tsv", os.path.join(sample_dir, "cnv", "baf", name_11q + ".baf.summary.tsv"))
        ctx = cnv_v2.parse(sample_dir, name_11q)
        row = [a for a in ctx.get("baf_arms", []) if a["arm"] == "11q"]
        check("11a dashboard parser: 11q row with basis, observed / expected het loci and extent; one HIGH call",
              row and row[0]["basis"] == "heterozygosity lost, residual signal"
              and int(row[0]["het_loci"].split(" / ")[0]) <= 2 and float(row[0]["het_loci"].split(" / ")[1]) > 20
              and "the arm" in row[0]["extent"] and len(ctx.get("baf_calls", [])) == 1, str(row[:1]))
        # a summary written before BAF_HETLOSS_V1 (18 columns) must still parse
        old_dir = os.path.join(work, "dash_old")
        os.makedirs(os.path.join(old_dir, "cnv", "baf"), exist_ok=True)
        with open(os.path.join(old_dir, "cnv", "baf", "old.baf.summary.tsv"), "w") as fh:
            for rr in v2_raw:
                fh.write("\t".join(rr[:V2_COLUMNS]) + "\n")
        ctx_old = cnv_v2.parse(old_dir, "old")
        check("11b dashboard parser: an 18-column summary from before the change still parses (new fields blank)",
              len(ctx_old.get("baf_arms", [])) == len(v2_raw) - 1 and all(a["basis"] == "" for a in ctx_old["baf_arms"]))
        flags = {}
        for tag, summary in (("contaminated", out_contaminated + ".summary.tsv"), (name_11q, out_11q + ".summary.tsv")):
            d = os.path.join(work, "dash2_" + tag)
            os.makedirs(os.path.join(d, "cnv", "baf"), exist_ok=True)
            shutil.copy(summary, os.path.join(d, "cnv", "baf", tag + ".baf.summary.tsv"))
            flags[tag] = cnv_v2.parse(d, tag).get("baf_second_genome")
        check("11g dashboard parser: second-genome flag set for the contaminated sample only, absent on an old summary",
              flags["contaminated"] is True and flags[name_11q] is False and ctx_old.get("baf_second_genome") is False
              and ctx_old.get("baf_residual_pct") is None, str(flags))
        d = os.path.join(work, "dash3_" + name_croh)
        os.makedirs(os.path.join(d, "cnv", "baf"), exist_ok=True)
        shutil.copy(out_croh + ".summary.tsv", os.path.join(d, "cnv", "baf", name_croh + ".baf.summary.tsv"))
        row = [a for a in cnv_v2.parse(d, name_croh).get("baf_arms", []) if a["arm"] == "11q"]
        check("11h dashboard parser: ROH without a bound is shown as 'not measurable', not as 1.000",
              row and row[0]["f"] == "not measurable", str(row[:1]))
        from parsers import tp53
        covers = {}
        for tag, region in (("p17_proximal", "chr17:10000000-22700000"), ("p17_distal", "chr17:0-12000000")):
            px = simulate(work, tag, events=["%s:cnloh:0.90" % region])
            arms_17, _, out_17, _ = detect(px, tag, "new")
            _, _, cmx = consensus(work, tag, out_17, px + ".denoisedCR.tsv")
            d = os.path.join(work, "tp53_" + tag)
            os.makedirs(os.path.join(d, "cnv", "baf"), exist_ok=True)
            os.makedirs(os.path.join(d, "cnv", "consensus"), exist_ok=True)
            shutil.copy(out_17 + ".summary.tsv", os.path.join(d, "cnv", "baf", tag + ".baf.summary.tsv"))
            shutil.copy(cmx + ".genes.tsv", os.path.join(d, "cnv", "consensus", tag + ".cnv_consensus4.genes.tsv"))
            block = tp53.parse(d, tag, clinical={"rows": []})
            covers[tag] = (arms_17["17p"]["verdict"], arms_17["17p"]["scope"], block["facts"]["baf_covers_gene"],
                           block["facts"]["b_call"], "does not include TP53" in (block["baf"] or {}).get("basis", ""))
        # the panel has no copy-ratio bins on proximal 17p, so the copy state of that stretch is open: IMBALANCE
        check("11i TP53 block: a 17p call that stops short of TP53 says so (baf_covers_gene no, no B call at the gene)",
              covers["p17_proximal"] == ("IMBALANCE", "segment", "no", "", True), str(covers["p17_proximal"]))
        check("11j ... and a 17p call that includes TP53 gives baf_covers_gene yes with the B call at the gene",
              covers["p17_distal"][0] == "CNLOH" and covers["p17_distal"][2:] == ("yes", "CNLOH", False), str(covers["p17_distal"]))
        check("11c TP53 block helper: basis text for a heterozygosity-loss row, empty for a BAF_V2 row",
              tp53._baf_basis({"evidence": "het_loss_complete", "het_loci": "0", "het_loci_expected": "89.8",
                               "f_lower": "0.960", "ev_lo": "354968", "ev_hi": "22693405", "ev_ends": "both",
                               "verdict": "ROH"}).startswith("heterozygosity absent; 0 heterozygous loci where 89.8 expected; fraction at least 0.96")
              and tp53._baf_basis({"evidence": "shift"}) == "" and "baf_evidence" in tp53.FACT_FIELDS
              and "fraction not measurable" in tp53._baf_basis({"evidence": "het_loss_complete", "f_lower": "NA", "verdict": "ROH"}))
    except ImportError as exc:
        check("11a-c dashboard parsers importable", False, str(exc))

    # ---- 12. tools/compare_baf_arms.py: the comparison the golden regression needs for these files
    genes_v2, _, cmx_v2 = consensus(work, name_11q + "_v2", px_11q + ".v2off", px_11q + ".denoisedCR.tsv")
    layout = {"ref": (px_11q + ".v2off", cmx_v2), "new": (out_11q, cmx_11q)}
    for tag, (baf_out, cmx) in layout.items():
        d = os.path.join(work, "cmp_" + tag, "S1", "clinical", "cnv")
        os.makedirs(os.path.join(d, "baf"), exist_ok=True)
        os.makedirs(os.path.join(d, "consensus"), exist_ok=True)
        shutil.copy(baf_out + ".summary.tsv", os.path.join(d, "baf", "S1.baf.summary.tsv"))
        shutil.copy(baf_out + ".sites.tsv", os.path.join(d, "baf", "S1.baf.sites.tsv"))
        shutil.copy(cmx + ".genes.tsv", os.path.join(d, "consensus", "S1.cnv_consensus4.genes.tsv"))
    compare = [sys.executable, os.path.join(REPO, "tools", "compare_baf_arms.py"),
               "--a", os.path.join(work, "cmp_ref"), "--b", os.path.join(work, "cmp_new")]
    p = run(compare, expect_ok=False)
    check("12a run comparison: the 11q call and its genes are listed as explained, nothing else differs, exit 0",
          p.returncode == 0 and "explained   11q: INDETERMINATE" in p.stdout and "explained   CBL (11q)" in p.stdout
          and "UNEXPLAINED" not in p.stdout and "0 unexplained differences" in p.stdout, p.stdout[-400:] + p.stderr[-200:])
    tampered = os.path.join(work, "cmp_new", "S1", "clinical", "cnv", "baf", "S1.baf.summary.tsv")
    with open(tampered) as fh:
        lines = [line.rstrip("\n").split("\t") for line in fh]
    for row in lines[1:]:
        if row[1] == "5q":
            row[14], row[15] = "DEL", "HIGH"
    with open(tampered, "w") as fh:
        fh.write("\n".join("\t".join(row) for row in lines) + "\n")
    p = run(compare, expect_ok=False)
    check("12b ... a changed verdict on an arm the test did not call is reported as unexplained, exit 1",
          p.returncode == 1 and "UNEXPLAINED 5q" in p.stdout and "RESULT: FAIL" in p.stdout, p.stdout[-300:])

    # ---- 13. tools/rescan_baf_arms.py: the detector over the stored files of an earlier run
    old_run = os.path.join(work, "earlier_run")
    for name in (name_11q, "normal_f"):
        d = os.path.join(old_run, name, "cnv_gatk")
        os.makedirs(d, exist_ok=True)
        for ext in (".allelicCounts.tsv", ".denoisedCR.tsv"):
            shutil.copy(os.path.join(work, name + ext), os.path.join(d, name + ext))
    before = sorted(os.listdir(os.path.join(old_run, name_11q, "cnv_gatk")))
    rescan_out = os.path.join(work, "rescan_out")
    p = run([sys.executable, os.path.join(REPO, "tools", "rescan_baf_arms.py"), "--out", rescan_out, old_run], expect_ok=False)
    listed = []
    if os.path.isfile(os.path.join(rescan_out, "rescan_calls.tsv")):
        with open(os.path.join(rescan_out, "rescan_calls.tsv")) as fh:
            listed = [(r["sample"], r["arm"], r["verdict"]) for r in csv.DictReader(fh, delimiter="\t")]
    check("13 rescan of an earlier run: lists the 11q arm of the one affected sample and writes nothing into the run",
          p.returncode == 0 and listed == [(name_11q, "11q", "CNLOH")] and "2 samples rescanned" in p.stdout
          and sorted(os.listdir(os.path.join(old_run, name_11q, "cnv_gatk"))) == before, "%s | %s" % (listed, p.stdout[-200:] + p.stderr[-200:]))

    if args.skip_plots:
        print("skip 11d-f figures (--skip-plots)")
    else:
        png = os.path.join(work, name_11q + ".genome.png")
        p = run([sys.executable, os.path.join(BIN, "plot_genome_overview.py"), "--sample", name_11q,
                 "--consensus-json", cmx_11q + ".json", "--out", png], expect_ok=False)
        check("11d genome-wide figure written from the new JSON",
              p.returncode == 0 and os.path.isfile(png) and os.path.getsize(png) > 20000, (p.stderr or p.stdout)[-300:])
        # the 17p page on a 17p event
        px = simulate(work, "cnloh17p_090", events=["17p:cnloh:0.90"])
        new, _, out_17p, _ = detect(px, "cnloh17p_090", "new")
        check("11e 17p cnLOH at 90 %: CNLOH HIGH (the TP53 arm)",
              (new["17p"]["verdict"], new["17p"]["confidence"]) == ("CNLOH", "HIGH"), new["17p"]["verdict"])
        _, _, cmx_17p = consensus(work, "cnloh17p_090", out_17p, px + ".denoisedCR.tsv")
        png17 = os.path.join(work, "cnloh17p_090.17p.png")
        p = run([sys.executable, os.path.join(BIN, "plot_arm_17p.py"), "--sample", "cnloh17p_090",
                 "--consensus-json", cmx_17p + ".json", "--out", png17], expect_ok=False)
        check("11f 17p page written from the new JSON",
              p.returncode == 0 and os.path.isfile(png17) and os.path.getsize(png17) > 20000, (p.stderr or p.stdout)[-300:])

    failed = [r for r in RESULTS if not r[1]]
    print("\n%d checks, %d failed%s" % (len(RESULTS), len(failed), "" if not args.keep else "; files in %s" % work))
    if not args.keep:
        shutil.rmtree(work, ignore_errors=True)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
