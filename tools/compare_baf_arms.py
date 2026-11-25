#!/usr/bin/env python3
"""tools/compare_baf_arms.py -- what the heterozygosity-loss test (BAF_HETLOSS_V1) changed between two runs.

The golden regression (tools/compare_runs.py, SOP-TSPIPE-001 section 7.10) compares files line
by line and expects the B-allele summaries to be identical. From BAF_HETLOSS_V1 on they cannot
be: the summary carries 14 more columns and the sites table one more, in every sample, whether
or not any verdict changed. This script makes the comparison that the regression needs for
those files. It pairs, by relative path, the files of a reference run (the detector before the
change) and of a new run:

    *.baf.summary.tsv              compared on the 18 BAF_V2 columns, arm by arm
    *.baf.sites.tsv                compared on the nine BAF_V2 columns, line by line
    *.cnv_consensus4.genes.tsv     compared gene by gene, every column

and sorts each difference into one of two kinds:

    explained    the arm is called by the heterozygosity-loss test in the new run (its row says
                 so in the evidence column), or the only change is the scope of an arm whose
                 partner arm is; for a gene, it lies on such an arm
    unexplained  anything else

The explained differences are the effect of the change and are listed in full for review:
each is an arm the old detector could not assess, or assessed from the few sites it still saw.
An unexplained difference means the two runs differ for another reason, and the regression
fails on it exactly as it would have before.

    python3 tools/compare_baf_arms.py --a <reference outdir> --b <new outdir> [--out report.txt]

Exit status 0 when there is no unexplained difference, 1 otherwise, 2 when nothing could be
compared. Python 3.6 compatible, standard library only.
"""
import argparse
import csv
import os
import sys

V2_COLUMNS = ["sample", "arm", "region", "site_lo", "site_hi", "n_informative", "n_covered", "n_het",
              "median_mirrored_dev", "bg_mad_scale", "noise_floor", "f_estimate", "cr_median_log2", "n_cr_bins",
              "verdict", "confidence", "scope", "ctrl_median_dev"]
SITE_COLUMNS = 9
SUFFIXES = (".baf.summary.tsv", ".baf.sites.tsv", ".cnv_consensus4.genes.tsv")
SKIP_DIRS = ("work", ".nextflow", "pipeline_info")


def find(root):
    """{relative path: absolute path} of the three kinds of file under an outdir."""
    found = {}
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith("work_")]
        for name in files:
            if name.endswith(SUFFIXES):
                path = os.path.join(base, name)
                found[os.path.relpath(path, root)] = path
    return found


def read_rows(path):
    with open(path) as fh:
        return list(csv.DictReader((line for line in fh if not line.startswith("#")), delimiter="\t"))


def partner(arm):
    return arm[:-1] + ("q" if arm.endswith("p") else "p")


def describe(row):
    txt = "%s %s f %s scope %s" % (row.get("verdict", "?"), row.get("confidence", "?"), row.get("f_estimate", "?"),
                                   row.get("scope", "?"))
    return txt + " (%s het sites)" % row.get("n_het", "?")


def compare_summary(pa, pb, out):
    """-> (set of arms called by the heterozygosity-loss test in b, number of unexplained differences)"""
    a = dict((r.get("arm"), r) for r in read_rows(pa))
    b = dict((r.get("arm"), r) for r in read_rows(pb))
    het_loss = set(arm for arm, r in b.items() if str(r.get("evidence", "")).startswith("het_loss"))
    unexplained = same = 0
    for arm in sorted(set(a) | set(b)):
        if arm not in a or arm not in b:
            out.append("    UNEXPLAINED %s: present in the %s run only" % (arm, "reference" if arm in a else "new"))
            unexplained += 1
            continue
        changed = [c for c in V2_COLUMNS if a[arm].get(c) != b[arm].get(c)]
        if not changed:
            same += 1
            continue
        if arm in het_loss:
            r = b[arm]
            extent = ""
            if r.get("ev_lo", "NA") != "NA":
                extent = ", %s:%.1f-%.1f Mb" % (r.get("region", "").split(":")[0], int(r["ev_lo"]) / 1e6, int(r["ev_hi"]) / 1e6)
            bound = "" if r.get("f_lower", "NA") == "NA" else ", f at least %s" % r["f_lower"]
            out.append("    explained   %s: %s  ->  %s  [%s, %s of %s expected heterozygous loci%s%s]" % (
                arm, describe(a[arm]), describe(r), r.get("evidence"), r.get("het_loci"), r.get("het_loci_expected"),
                bound, extent))
        elif changed == ["scope"] and partner(arm) in het_loss:
            out.append("    explained   %s: scope %s -> %s (the other arm of the chromosome is called)" % (
                arm, a[arm].get("scope"), b[arm].get("scope")))
        else:
            out.append("    UNEXPLAINED %s: %s  ->  %s  [columns: %s]" % (arm, describe(a[arm]), describe(b[arm]), ", ".join(changed)))
            unexplained += 1
    out.insert(0, "  arms: %d compared, %d identical in the 18 BAF_V2 columns, %d called by the heterozygosity-loss test" % (
        len(set(a) | set(b)), same, len(het_loss)))
    return het_loss, unexplained


def compare_sites(pa, pb, out):
    def nine(path):
        with open(path) as fh:
            return ["\t".join(line.rstrip("\n").split("\t")[:SITE_COLUMNS]) for line in fh]
    a, b = nine(pa), nine(pb)
    if a == b:
        out.append("  sites: %d lines, identical in the nine BAF_V2 columns" % len(a))
        return 0
    n = sum(1 for x, y in zip(a, b) if x != y) + abs(len(a) - len(b))
    out.append("  sites: UNEXPLAINED, %d of %d lines differ in the nine BAF_V2 columns" % (n, max(len(a), len(b))))
    return 1


def compare_genes(pa, pb, het_loss, out):
    a = dict((r.get("gene"), r) for r in read_rows(pa))
    b = dict((r.get("gene"), r) for r in read_rows(pb))
    unexplained, explained = 0, []
    for gene in sorted(set(a) | set(b)):
        if gene not in a or gene not in b:
            out.append("    UNEXPLAINED %s: present in the %s run only" % (gene, "reference" if gene in a else "new"))
            unexplained += 1
            continue
        changed = [c for c in sorted(set(a[gene]) | set(b[gene])) if a[gene].get(c) != b[gene].get(c)]
        if not changed:
            continue
        arm = str(b[gene].get("allelic_state", "")).split(":")[0]
        if arm in het_loss:
            explained.append((gene, arm, changed))
        else:
            out.append("    UNEXPLAINED %s: columns %s" % (gene, ", ".join(changed)))
            unexplained += 1
    if explained:
        out.append("  consensus genes: %d of %d rows differ, all on arms called by the heterozygosity-loss test" % (
            len(explained), len(b)) if not unexplained else "  consensus genes: %d rows differ on arms called by the test" % len(explained))
        for gene, arm, changed in explained:
            r0, r1 = a[gene], b[gene]
            out.append("    explained   %s (%s): consensus %s %s -> %s %s; B %s -> %s; %s" % (
                gene, arm, r0.get("consensus_call"), r0.get("tier"), r1.get("consensus_call"), r1.get("tier"),
                r0.get("b_call"), r1.get("b_call"), r1.get("allelic_state")))
    elif not unexplained:
        out.append("  consensus genes: %d rows, identical" % len(b))
    return unexplained


def main():
    ap = argparse.ArgumentParser(description="What the heterozygosity-loss test changed between a reference run and a new run")
    ap.add_argument("--a", required=True, help="reference outdir (detector before BAF_HETLOSS_V1)")
    ap.add_argument("--b", required=True, help="new outdir")
    ap.add_argument("--out", default=None, help="also write the report to this file")
    args = ap.parse_args()
    for d in (args.a, args.b):
        if not os.path.isdir(d):
            sys.stderr.write("[error] not a directory: %s\n" % d)
            sys.exit(2)
    fa, fb = find(args.a), find(args.b)
    common = sorted(set(fa) & set(fb))
    summaries = [r for r in common if r.endswith(".baf.summary.tsv")]
    if not summaries:
        sys.stderr.write("[error] no *.baf.summary.tsv found under the same relative path in both runs\n")
        sys.exit(2)

    report = ["reference run: %s" % os.path.abspath(args.a), "new run:       %s" % os.path.abspath(args.b), ""]
    total_unexplained = total_calls = 0
    one_side = sorted(set(fa) ^ set(fb))
    for rel in summaries:
        stem = rel[:-len(".baf.summary.tsv")]
        sample = os.path.basename(stem)
        lines = []
        het_loss, n = compare_summary(fa[rel], fb[rel], lines)
        total_calls += len(het_loss)
        sites_rel = stem + ".baf.sites.tsv"
        if sites_rel in fa and sites_rel in fb:
            n += compare_sites(fa[sites_rel], fb[sites_rel], lines)
        for g in [r for r in common if r.endswith("%s.cnv_consensus4.genes.tsv" % sample)]:
            n += compare_genes(fa[g], fb[g], het_loss, lines)
        total_unexplained += n
        report.append("%s  (%s)" % (sample, rel))
        report.extend(lines)
        report.append("")
    if one_side:
        report.append("files on one side only (not compared): %d" % len(one_side))
        report.extend("  %s  [%s]" % (r, "reference" if r in fa else "new") for r in one_side[:20])
        report.append("")
    report.append("%d samples compared, %d arms called by the heterozygosity-loss test, %d unexplained differences" % (
        len(summaries), total_calls, total_unexplained))
    report.append("RESULT: %s" % ("PASS - every difference is the effect of the heterozygosity-loss test; review the arms listed as explained"
                                  if total_unexplained == 0 else "FAIL - differences that the heterozygosity-loss test does not account for"))
    text = "\n".join(report) + "\n"
    sys.stdout.write(text)
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(text)
    sys.exit(0 if total_unexplained == 0 else 1)


if __name__ == "__main__":
    main()
