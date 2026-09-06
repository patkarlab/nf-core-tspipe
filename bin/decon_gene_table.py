#!/usr/bin/env python3
"""
decon_gene_table.py  (DECON_V1)

Per-gene DECoN table in the CMX_V2 --decon-genes contract:
    gene  e_call  e_bf  e_n_exons  e_calls  e_qc
one row per gene of the DECoN exon BED (column 4). e_call is GAIN for a
reportable duplication, LOSS for a reportable deletion, NEUTRAL when the
gene has no reportable call, and NA for every gene when the sample failed
the DECoN QC gate (arm E then abstains in the consensus). e_bf is the
highest BF among the gene's reportable calls; e_calls lists every call on
the gene (reportable or not) as type:exonsStart-End:BF:decision.

Inputs: the filtered table from filter_decon_calls.py (columns incl.
Gene, CNV.type, BF, Start.b, End.b, decision, reportable) and the QC
table from decon_call_sample.R (qc_pass column). Python 3.6, stdlib only.
"""

import argparse
import csv
import sys

TYPE_TO_CALL = {"duplication": "GAIN", "dup": "GAIN", "gain": "GAIN",
                "deletion": "LOSS", "del": "LOSS", "loss": "LOSS"}


def read_tsv(path):
    with open(path) as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        return reader.fieldnames or [], list(reader)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample", required=True)
    ap.add_argument("--filtered", required=True, help="filter_decon_calls.py output")
    ap.add_argument("--qc", required=True, help="decon_call_sample.R *_qc.tsv")
    ap.add_argument("--bed", required=True, help="DECoN exon BED (gene in column 4)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    genes = []
    seen = set()
    with open(args.bed) as fh:
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if len(p) < 4 or line.startswith("#"):
                continue
            if p[3] not in seen:
                seen.add(p[3])
                genes.append(p[3])

    qc_fields, qc_rows = read_tsv(args.qc)
    qc_pass = False
    qc_note = "no_qc_row"
    if qc_rows:
        r = qc_rows[0]
        qc_pass = str(r.get("qc_pass", "")).strip().upper() == "TRUE"
        qc_note = "corr={0};depth={1};corr_pass={2};depth_pass={3}".format(
            r.get("max_corr", "NA"), r.get("median_depth", "NA"),
            r.get("corr_pass", "NA"), r.get("depth_pass", "NA"))

    f_fields, f_rows = read_tsv(args.filtered)
    for col in ("Gene", "CNV.type", "BF", "reportable", "decision"):
        if f_rows and col not in f_fields:
            sys.exit("[error] filtered table lacks column {0}".format(col))

    per_gene = {}
    for r in f_rows:
        g = r["Gene"].strip()
        try:
            bf = float(r["BF"])
        except ValueError:
            bf = float("nan")
        call = TYPE_TO_CALL.get(r["CNV.type"].strip().lower(), "NA")
        exons = "{0}-{1}".format(r.get("Start.b", "?"), r.get("End.b", "?"))
        rec = per_gene.setdefault(g, {"calls": [], "rep": []})
        rec["calls"].append("{0}:{1}:{2:.1f}:{3}".format(call, exons, bf, r["decision"]))
        if r["reportable"].strip().lower() == "yes" and call in ("GAIN", "LOSS"):
            rec["rep"].append((bf, call))

    n_called = 0
    with open(args.out, "w") as out:
        out.write("gene\te_call\te_bf\te_n_exons\te_calls\te_qc\n")
        for g in genes:
            rec = per_gene.get(g, {"calls": [], "rep": []})
            if not qc_pass:
                e_call, e_bf = "NA", "NA"
            elif rec["rep"]:
                bf, call = max(rec["rep"])
                dirs = set(c for _, c in rec["rep"])
                e_call = call if len(dirs) == 1 else "DISCORDANT"
                e_bf = "{0:.1f}".format(bf)
                n_called += 1
            else:
                e_call, e_bf = "NEUTRAL", "NA"
            out.write("\t".join([g, e_call, e_bf, str(len(rec["calls"])),
                                 ";".join(rec["calls"]) or ".",
                                 ("PASS" if qc_pass else "FAIL") + ":" + qc_note]) + "\n")
    print("[ok] {0}: {1} genes, qc_pass={2}, {3} gene(s) with a reportable DECoN call".format(
        args.sample, len(genes), qc_pass, n_called))
    return 0


if __name__ == "__main__":
    sys.exit(main())
