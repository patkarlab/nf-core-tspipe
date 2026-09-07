#!/usr/bin/env python3
"""
make_driver_gene_panel.py  (HMF_PANEL_V1)

Driver gene panel TSV for PURPLE from the HMF DriverGenePanel.38.tsv: rows of
HMF genes that are on our panel are copied verbatim; panel genes HMF lacks
get a cloned template row (first HMF TSG row or first HMF ONCO row, gene
name replaced) with the role taken from myeloid_driver_genes.tsv
(Mechanism LoF -> TSG, GoF -> ONCO, anything else -> TSG). Writes the panel
TSV plus a provenance TSV (gene, source, role). Python 3.6, stdlib only.
"""

import argparse
import csv
import sys


def read_panel_genes(chroms_tsv):
    genes = []
    with open(chroms_tsv) as fh:
        for line in fh:
            if not line.strip() or line.startswith("#"):
                continue
            p = line.rstrip("\n").split("\t")
            if len(p) < 2:
                continue
            for g in p[1].split(","):
                g = g.strip()
                if g and g not in genes:
                    genes.append(g)
    return genes


def read_roles(path):
    roles = {}
    if not path:
        return roles
    with open(path) as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            mech = (row.get("Mechanism") or "").strip().lower()
            roles[row["Gene"].strip()] = "ONCO" if mech == "gof" else "TSG"
    return roles


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hmf-panel", required=True)
    ap.add_argument("--panel-genes", required=True, help="panel_gene_chroms.tsv (chrom<TAB>gene,gene,...)")
    ap.add_argument("--roles", default=None, help="myeloid_driver_genes.tsv (Gene, Mechanism)")
    ap.add_argument("--extra-genes", default="", help="comma-separated genes to add beyond the chroms table")
    ap.add_argument("--out", required=True)
    ap.add_argument("--provenance", required=True)
    args = ap.parse_args()

    genes = read_panel_genes(args.panel_genes)
    for g in args.extra_genes.split(","):
        if g.strip() and g.strip() not in genes:
            genes.append(g.strip())
    roles = read_roles(args.roles)

    with open(args.hmf_panel) as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        header = reader.fieldnames
        hmf = {r["gene"]: r for r in reader}
    if "gene" not in header or "likelihoodType" not in header:
        sys.exit("[error] unexpected HMF panel header")
    templates = {}
    for r in hmf.values():
        templates.setdefault(r["likelihoodType"], r)
    for need in ("TSG", "ONCO"):
        if need not in templates:
            sys.exit("[error] no %s template row in the HMF panel" % need)

    out_rows, prov = [], []
    for g in genes:
        if g in hmf:
            out_rows.append(hmf[g]); prov.append((g, "hmf", hmf[g]["likelihoodType"]))
        else:
            role = roles.get(g, "TSG")
            row = dict(templates[role]); row["gene"] = g
            for col in header:
                if col.startswith("reportGermline") or col in ("additionalReportedTranscripts",):
                    row[col] = "NONE" if col in ("reportGermlineVariant", "reportGermlineHotspot") else ("FALSE" if row[col] in ("TRUE", "FALSE") else "")
            out_rows.append(row); prov.append((g, "template_" + role, role))

    with open(args.out, "w") as out:
        w = csv.DictWriter(out, fieldnames=header, delimiter="\t", lineterminator="\n")
        w.writeheader()
        for r in out_rows:
            w.writerow(r)
    with open(args.provenance, "w") as out:
        out.write("gene\tsource\trole\n")
        for g, s, r in prov:
            out.write("%s\t%s\t%s\n" % (g, s, r))
    n_hmf = sum(1 for _, s, _ in prov if s == "hmf")
    print("[ok] %d genes: %d from HMF, %d templated (TSG %d, ONCO %d)" % (
        len(genes), n_hmf, len(genes) - n_hmf,
        sum(1 for _, s, _ in prov if s == "template_TSG"), sum(1 for _, s, _ in prov if s == "template_ONCO")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
