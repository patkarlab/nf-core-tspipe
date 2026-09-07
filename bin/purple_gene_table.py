#!/usr/bin/env python3
"""
purple_gene_table.py  (HMF_PURPLE_V1)

PURPLE outputs -> CMX arm H contract.
  --purity   <id>.purple.purity.tsv   (purity, ploidy, gender, status, ...)
  --qc       <id>.purple.purity.qc    (QCStatus, Method, ...)      [optional]
  --genes    <id>.purple.cnv.gene.tsv (minCopyNumber, maxCopyNumber, minMinorAlleleCopyNumber, ...)
Writes:
  --out-genes   gene, h_call, h_cn_min, h_cn_max, h_macn_min, h_loh, h_expected_cn
  --out-summary sample, status, method, purity, ploidy, gender, trusted, comment
h_call: LOSS when minCopyNumber < expected - 0.5, GAIN when maxCopyNumber >
expected + 0.5, both -> COMPLEX, else NEUTRAL; expected cn is 2, or 1 on
chrX/chrY for a MALE (PURPLE gender, --sex as fallback). h_loh: minor allele
copy number < 0.5. trusted = status has no FAIL_ (WARN_* keeps trust; the
consensus sees the status). On any failure the sentinel tables carry status
FAILED so the DAG and the consensus join survive. Python 3.6, stdlib only.
"""

import argparse
import csv
import os
import sys


def read_one_row(path):
    with open(path) as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    return rows[0] if rows else {}


def read_key_value(path):
    """MARKER HMF_PURPLE_V1c: <id>.purple.qc is key<TAB>value per line (QCStatus, Method, ...)."""
    out = {}
    with open(path) as fh:
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if len(p) >= 2:
                out[p[0].strip()] = p[1].strip()
    return out


def expected_cn(chrom, sex):
    c = chrom.replace("chr", "")
    if c not in ("X", "Y"):
        return 2.0
    if sex == "MALE":
        return 1.0
    if sex == "FEMALE":
        return 2.0 if c == "X" else None
    return None


def write_sentinel(args, reason):
    with open(args.out_genes, "w") as out:
        out.write("gene\th_call\th_cn_min\th_cn_max\th_macn_min\th_loh\th_expected_cn\n")
    with open(args.out_summary, "w") as out:
        out.write("sample\tstatus\tmethod\tpurity\tploidy\tgender\ttrusted\tcomment\n")
        out.write("%s\tFAILED\tNA\tNA\tNA\tNA\tFALSE\t%s\n" % (args.sample, reason))
    print("[warn] %s: PURPLE sentinel written (%s)" % (args.sample, reason))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample", required=True)
    ap.add_argument("--purity", default=None)
    ap.add_argument("--qc", default=None)
    ap.add_argument("--genes", default=None)
    ap.add_argument("--sex", default="unknown")
    ap.add_argument("--failed", action="store_true")
    ap.add_argument("--out-genes", required=True)
    ap.add_argument("--out-summary", required=True)
    args = ap.parse_args()

    if args.failed or not args.purity or not args.genes:
        write_sentinel(args, "purple_exit_nonzero" if args.failed else "missing_inputs")
        return 0
    try:
        pur = read_one_row(args.purity)
        qc = read_key_value(args.qc) if args.qc and os.path.isfile(args.qc) else {}
    except (OSError, IndexError) as exc:
        write_sentinel(args, "unreadable_purity: %s" % exc)
        return 0
    status = qc.get("QCStatus") or pur.get("status") or "UNKNOWN"
    method = qc.get("Method") or pur.get("fitMethod") or pur.get("status") or "NA"
    gender = (pur.get("gender") or "").strip().upper()
    if gender not in ("MALE", "FEMALE"):
        gender = args.sex.upper() if args.sex.lower() in ("male", "female") else "UNKNOWN"
    trusted = "FAIL_" not in status
    try:
        purity = float(pur.get("purity", "nan")); ploidy = float(pur.get("ploidy", "nan"))
    except ValueError:
        purity, ploidy = float("nan"), float("nan")

    n = {"GAIN": 0, "LOSS": 0, "COMPLEX": 0, "LOH": 0}
    with open(args.genes) as fh, open(args.out_genes, "w") as out:
        reader = csv.DictReader(fh, delimiter="\t")
        out.write("gene\th_call\th_cn_min\th_cn_max\th_macn_min\th_loh\th_expected_cn\n")
        for r in reader:
            try:
                cmin = float(r["minCopyNumber"]); cmax = float(r["maxCopyNumber"])
                macn = float(r.get("minMinorAlleleCopyNumber", "nan"))
            except (KeyError, ValueError):
                continue
            exp = expected_cn(r.get("chromosome", ""), gender)
            if exp is None:
                call = "NA"
            else:
                loss = cmin < exp - 0.5
                gain = cmax > exp + 0.5
                call = "COMPLEX" if (loss and gain) else ("LOSS" if loss else ("GAIN" if gain else "NEUTRAL"))
            loh = "TRUE" if (macn == macn and macn < 0.5 and exp not in (None, 1.0)) else "FALSE"
            if call in n:
                n[call] += 1
            if loh == "TRUE":
                n["LOH"] += 1
            out.write("%s\t%s\t%.2f\t%.2f\t%s\t%s\t%s\n" % (
                r["gene"], call, cmin, cmax, ("%.2f" % macn) if macn == macn else "NA", loh,
                ("%.0f" % exp) if exp is not None else "NA"))
    with open(args.out_summary, "w") as out:
        out.write("sample\tstatus\tmethod\tpurity\tploidy\tgender\ttrusted\tcomment\n")
        out.write("%s\t%s\t%s\t%.3f\t%.3f\t%s\t%s\t%s\n" % (
            args.sample, status, method, purity, ploidy, gender, "TRUE" if trusted else "FALSE",
            "gain=%d;loss=%d;complex=%d;loh=%d" % (n["GAIN"], n["LOSS"], n["COMPLEX"], n["LOH"])))
    print("[ok] %s: status=%s purity=%.2f ploidy=%.2f gender=%s trusted=%s gain=%d loss=%d loh=%d" % (
        args.sample, status, purity, ploidy, gender, trusted, n["GAIN"], n["LOSS"], n["LOH"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
