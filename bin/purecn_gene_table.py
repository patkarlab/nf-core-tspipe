#!/usr/bin/env python3
"""Normalise PureCN outputs into consensus-ready tables (PCN_V1).

Inputs (PureCN.R --out <sample> products):
  --genes    <sample>_genes.csv  (callAlterations all.genes=TRUE):
             Sampleid, gene.symbol, chr, start, end, C, seg.mean, focal,
             ..., type in {AMPLIFICATION, DELETION, NA}
  --loh      <sample>_loh.csv (region-level callLOH): chr, start, end,
             C, M, type in {"", LOH, COPY-NEUTRAL LOH, WHOLE ARM ...}
  --solution <sample>.csv (createCurationFile): Purity, Ploidy, Sex,
             Contamination, Flagged, Failed, Comment

Outputs:
  --out-genes   gene, chrom, start, end, p_C, p_minor, p_seg_mean,
                p_type, p_call (GAIN if C > round(ploidy) else LOSS if
                C < round(ploidy), ploidy-aware), p_loh
                (true/copy_neutral/false)
  --out-summary sample, status(OK/FAILED), purity, ploidy, sex_inferred,
                contamination, flagged, comment

--failed writes header-only genes + a FAILED summary row (used by the
PURECN module when purity fitting fails on copy-flat samples).
"""

import argparse
import csv
import os
import sys


def fail(msg):
    sys.stderr.write("[error] {0}\n".format(msg))
    sys.exit(1)


def warn(msg):
    sys.stderr.write("[warn] {0}\n".format(msg))


GENE_HDR = ("gene\tchrom\tstart\tend\tp_C\tp_minor\tp_seg_mean\t"
            "p_type\tp_call\tp_loh\n")
SUM_HDR = ("sample\tstatus\tpurity\tploidy\tsex_inferred\t"
           "contamination\tflagged\tcomment\n")


def read_csv(path):
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        fail("no rows in {0}".format(path))
    return rows


def pick(row, names, default=""):
    for n in names:
        if n in row and row[n] not in (None, ""):
            return row[n]
    return default


def overlap(a1, a2, b1, b2):
    return max(0, min(a2, b2) - max(a1, b1))


def main():
    ap = argparse.ArgumentParser(description="PureCN gene-table normaliser (PCN_V1)")
    ap.add_argument("--sample", required=True)
    ap.add_argument("--genes")
    ap.add_argument("--loh")
    ap.add_argument("--solution")
    ap.add_argument("--out-genes", required=True)
    ap.add_argument("--out-summary", required=True)
    ap.add_argument("--failed", action="store_true")
    args = ap.parse_args()

    if args.failed:
        with open(args.out_genes, "w") as out:
            out.write(GENE_HDR)
        with open(args.out_summary, "w") as out:
            out.write(SUM_HDR)
            out.write("{0}\tFAILED\tNA\tNA\tNA\tNA\tNA\tpurity_fit_failed\n".format(
                args.sample))
        print("[warn] {0}: FAILED sentinels written".format(args.sample))
        return

    for p in (args.genes, args.loh, args.solution):
        if not p or not os.path.isfile(p):
            fail("missing input (use --failed for sentinel mode): {0}".format(p))

    sol = read_csv(args.solution)[0]
    purity = pick(sol, ["Purity"], "NA")
    ploidy = pick(sol, ["Ploidy"], "NA")
    try:
        ploidy_round = int(round(float(ploidy)))
    except (TypeError, ValueError):
        ploidy_round = 2

    loh_regions = []
    for r in read_csv(args.loh):
        t = pick(r, ["type"], "")
        if not t or t.upper() in ("NA",):
            continue
        try:
            loh_regions.append((pick(r, ["chr", "chrom"]),
                                int(float(pick(r, ["start"]))),
                                int(float(pick(r, ["end"]))),
                                t.upper()))
        except ValueError:
            continue

    def loh_state(chrom, gs, ge):
        for c, s, e, t in loh_regions:
            if c == chrom and overlap(gs, ge, s, e) > 0:
                return "copy_neutral" if "COPY-NEUTRAL" in t else "true"
        return "false"

    n_out, n_called = 0, 0
    with open(args.out_genes, "w") as out:
        out.write(GENE_HDR)
        for r in read_csv(args.genes):
            gene = pick(r, ["gene.symbol", "Gene", "gene"])
            chrom = pick(r, ["chr", "chrom"])
            try:
                gs = int(float(pick(r, ["start"])))
                ge = int(float(pick(r, ["end"])))
            except ValueError:
                continue
            c_raw = pick(r, ["C"], "NA")
            try:
                c_int = int(round(float(c_raw)))
            except ValueError:
                c_int = None
            p_type = pick(r, ["type"], "NA") or "NA"
            if c_int is None:
                p_call = "NA"
            elif c_int > ploidy_round:
                p_call = "GAIN"
            elif c_int < ploidy_round:
                p_call = "LOSS"
            else:
                p_call = "NEUTRAL"
            if p_call in ("GAIN", "LOSS"):
                n_called += 1
            out.write("{0}\t{1}\t{2}\t{3}\t{4}\t{5}\t{6}\t{7}\t{8}\t{9}\n".format(
                gene, chrom, gs, ge,
                c_raw, pick(r, ["M", "M.gene"], "NA"),
                pick(r, ["seg.mean", "gene.mean"], "NA"),
                p_type, p_call, loh_state(chrom, gs, ge)))
            n_out += 1

    with open(args.out_summary, "w") as out:
        out.write(SUM_HDR)
        out.write("{0}\tOK\t{1}\t{2}\t{3}\t{4}\t{5}\t{6}\n".format(
            args.sample, purity, ploidy,
            pick(sol, ["Sex"], "NA"),
            pick(sol, ["Contamination"], "NA"),
            pick(sol, ["Flagged"], "NA"),
            (pick(sol, ["Comment"], "") or "").replace("\t", " ")))

    print("[ok] {0}: {1} genes ({2} non-neutral, ploidy-aware vs {3}), "
          "{4} LOH regions; purity={5} ploidy={6}".format(
              args.sample, n_out, n_called, ploidy_round,
              len(loh_regions), purity, ploidy))


if __name__ == "__main__":
    main()
