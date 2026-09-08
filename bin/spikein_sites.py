#!/usr/bin/env python3
"""bin/spikein_sites.py -- SPIKEIN_V1 (D13)

Genotype the panel's germline spike-in SNPs from GATK CollectAllelicCounts
output on the final BAM. Stdlib only; runs under Python 3.6 in the GATK
container (no f-strings with '=', no PEP 585 generics, no walrus).

Input
  --asset            assets/<panel>/spikein_regions.tsv (rows with class == germline_snp)
  --allelic-counts   CollectAllelicCounts TSV (may be absent: header-only output)
Output
  --out              <sample>.spikein_snps.tsv, one row per SNP in the asset

Genotype rule (germline, read from a tumour BAM):
  depth < MIN_DEPTH                  -> LOW_DEPTH, genotype "-"
  alt_af < HOM_REF_MAX               -> hom_ref
  HOM_REF_MAX <= alt_af <= HOM_ALT_MIN -> het
  alt_af > HOM_ALT_MIN               -> hom_alt
A somatic copy-number change or cnLOH on the SNP's chromosome can move the
allele fraction; the dashboard text says so, this script does not adjust.

risk_copies: number of risk-allele copies implied by the genotype when the
asset gives a risk_allele; "-" when the allele is not curated; "?" when the
observed alleles do not include the risk allele in a way the rule can score.
"""

import argparse
import sys

MIN_DEPTH = 20
HOM_REF_MAX = 0.15
HOM_ALT_MIN = 0.85
ALT_SHOW_MIN_AF = 0.02   # SPIKEIN_V1b: alt allele shown only at >= 2% of depth

OUT_COLUMNS = [
    "sample", "name", "gene", "rsid", "rsid_alias", "chrom", "pos",
    "ref", "alt", "ref_count", "alt_count", "depth", "alt_af",
    "genotype", "risk_allele", "risk_copies", "status", "description",
]


def read_asset(path):
    """Return the germline_snp rows of the asset as a list of dicts."""
    rows = []
    header = None
    with open(path) as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if header is None:
                header = parts
                continue
            row = dict(zip(header, parts))
            if row.get("class") != "germline_snp":
                continue
            rows.append(row)
    return rows


def read_allelic_counts(path):
    """Map (contig, position) -> dict(ref_count, alt_count, ref, alt)."""
    counts = {}
    if path is None:
        return counts
    with open(path) as fh:
        header = None
        for line in fh:
            if line.startswith("@"):
                continue
            parts = line.rstrip("\n").split("\t")
            if header is None:
                header = parts
                continue
            rec = dict(zip(header, parts))
            key = (rec["CONTIG"], int(rec["POSITION"]))
            counts[key] = {
                "ref_count": int(rec["REF_COUNT"]),
                "alt_count": int(rec["ALT_COUNT"]),
                "ref": rec["REF_NUCLEOTIDE"],
                "alt": rec["ALT_NUCLEOTIDE"],
            }
    return counts


def call_genotype(ref_count, alt_count):
    depth = ref_count + alt_count
    if depth < MIN_DEPTH:
        return "-", depth, None, "LOW_DEPTH"
    af = alt_count / float(depth)
    if af < HOM_REF_MAX:
        gt = "hom_ref"
    elif af > HOM_ALT_MIN:
        gt = "hom_alt"
    else:
        gt = "het"
    return gt, depth, af, "OK"


def risk_copies(genotype, ref, alt, risk_allele):
    if risk_allele in ("", "-", None):
        return "-"
    if genotype == "-":
        return "-"
    if risk_allele == ref:
        return {"hom_ref": "2", "het": "1", "hom_alt": "0"}[genotype]
    if risk_allele == alt:
        return {"hom_ref": "0", "het": "1", "hom_alt": "2"}[genotype]
    if genotype == "hom_ref":
        return "0"
    return "?"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--asset", required=True)
    ap.add_argument("--allelic-counts", default=None)
    ap.add_argument("--sample", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    snps = read_asset(args.asset)
    counts = read_allelic_counts(args.allelic_counts)

    n_ok = 0
    with open(args.out, "w") as out:
        out.write("\t".join(OUT_COLUMNS) + "\n")
        for s in snps:
            pos = int(s["pos"])
            rec = counts.get((s["chrom"], pos))
            if rec is None:
                row = {
                    "ref": "-", "alt": "-", "ref_count": "0", "alt_count": "0",
                    "depth": "0", "alt_af": "-", "genotype": "-",
                    "risk_copies": "-", "status": "NO_DATA",
                }
            else:
                gt, depth, af, status = call_genotype(rec["ref_count"], rec["alt_count"])
                alt = rec["alt"] if (depth > 0 and rec["alt_count"] / float(depth) >= ALT_SHOW_MIN_AF) else "-"   # SPIKEIN_V1b
                row = {
                    "ref": rec["ref"], "alt": alt,
                    "ref_count": str(rec["ref_count"]),
                    "alt_count": str(rec["alt_count"]),
                    "depth": str(depth),
                    "alt_af": "-" if af is None else "%.3f" % af,
                    "genotype": gt,
                    "risk_copies": risk_copies(gt, rec["ref"], alt, s.get("risk_allele", "-")),
                    "status": status,
                }
                if status == "OK":
                    n_ok += 1
            row.update({
                "sample": args.sample, "name": s["name"], "gene": s["gene"],
                "rsid": s["rsid"], "rsid_alias": s.get("rsid_alias", "-"),
                "chrom": s["chrom"], "pos": str(pos),
                "risk_allele": s.get("risk_allele", "-"),
                "description": s.get("description", ""),
            })
            out.write("\t".join(row[c] for c in OUT_COLUMNS) + "\n")

    sys.stderr.write("[spikein_sites] %s: %d SNP sites in asset, %d genotyped at >= %dx\n"
                     % (args.sample, len(snps), n_ok, MIN_DEPTH))
    return 0


if __name__ == "__main__":
    sys.exit(main())
