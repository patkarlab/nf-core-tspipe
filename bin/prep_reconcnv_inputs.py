#!/usr/bin/env python3
"""Prepare reconCNV inputs from nf-core-tspipe outputs.

reconCNV (Ghu et al., Bioinformatics 2021; GPLv3) draws the standard
targeted-panel CNV dashboard from CNVkit-shaped files. This adapter
maps the pipeline's artefacts onto its expectations:

  ratio file   <sample>.cnr with backbone tiles relabelled to the
               configured off-target label (reconCNV matches the label
               exactly; our tiles are named bb.<chrom>.<pos>).
  genome file  chromosome, length, cumulative offset from a .fai.
  segments     <sample>.call.cns with mcn/lcn/cf columns; when a
               PureCN _loh.csv is given, C and M are taken from the
               PureCN segment overlapping each CNVkit segment midpoint.
  het VCF      heterozygous SNPs from the raw Mutect2 VCF with INFO
               DP/SAF/SAR, which reconCNV expects (FreeBayes shape);
               strand counts come from Mutect2's FORMAT SB field.
  config       reconCNV's template with build, thresholds, inline JS.

Python 3.6 compatible. Standard library only.

Usage:
    prep_reconcnv_inputs.py --cnr S.cnr --cns S.call.cns --vcf S.mutect2.vcf.gz \
        --fai hg38.fa.fai --template config.json --outdir recon_in \
        [--loh S_loh.csv] [--purity 0.8] [--sex female] \
        [--loss -0.5 --deep-loss -1.0 --gain 0.5 --amp 1.0]
"""

import argparse
import csv
import gzip
import json
import os
import sys

CHROMS = ["chr%d" % i for i in range(1, 23)] + ["chrX", "chrY"]


def write_genome(fai, out):
    lengths = {}
    with open(fai) as fh:
        for line in fh:
            p = line.split("\t")
            if p[0] in CHROMS:
                lengths[p[0]] = int(p[1])
    acc = 0
    with open(out, "w") as fo:
        fo.write("chromosome\tlength\tlength_cumsum\n")
        for c in CHROMS:
            if c in lengths:
                fo.write("%s\t%d\t%d\n" % (c, lengths[c], acc))
                acc += lengths[c]


def write_ratio(cnr, out, off_label, drop_chroms):
    with open(cnr) as fi, open(out, "w") as fo:
        rd = csv.DictReader(fi, delimiter="\t")
        cols = ["chromosome", "start", "end", "gene", "depth", "log2", "weight", "target"]
        fo.write("\t".join(cols) + "\n")
        for r in rd:
            if r["chromosome"] in drop_chroms:
                continue
            name = r["gene"]
            gene = off_label if name.startswith("bb.") else name.split("_")[0]
            fo.write("\t".join([r["chromosome"], r["start"], r["end"], gene, r.get("depth", "0"),
                                r["log2"], r.get("weight", "1"), name]) + "\n")


def load_loh(path):
    segs = []
    if not path:
        return segs
    with open(path) as fh:
        for r in csv.DictReader(fh):
            segs.append((r["chr"], int(r["start"]), int(r["end"]), int(r["C"]), int(r["M"])))
    return segs


def write_segments(cns, out, loh, purity, drop_chroms):
    with open(cns) as fi, open(out, "w") as fo:
        rd = csv.DictReader(fi, delimiter="\t")
        fo.write("chromosome\tstart\tend\tgene\tlog2\tmcn\tlcn\tcf\n")
        for r in rd:
            c = r["chromosome"]
            if c in drop_chroms:
                continue
            s, e = int(r["start"]), int(r["end"])
            cn = int(float(r["cn"])) if r.get("cn") not in (None, "", "NA") else 2
            mid = (s + e) / 2.0
            C, M = cn, (1 if cn >= 2 else 0)
            for lc, ls, le, LC, LM in loh:
                if lc == c and ls <= mid <= le:
                    C, M = LC, LM
                    break
            fo.write("%s\t%d\t%d\tseg\t%s\t%d\t%d\t%.2f\n" % (c, s, e, r["log2"], C - M, M, purity))


def write_het_vcf(vcf, out, min_dp, lo, hi, drop_chroms):
    opener = gzip.open if vcf.endswith(".gz") else open
    n = 0
    with opener(vcf, "rt") as fi, open(out, "w") as fo:
        fo.write("##fileformat=VCFv4.2\n"
                 "##INFO=<ID=DP,Number=1,Type=Integer,Description=\"Read depth\">\n"
                 "##INFO=<ID=SAF,Number=A,Type=Integer,Description=\"Alt reads forward\">\n"
                 "##INFO=<ID=SAR,Number=A,Type=Integer,Description=\"Alt reads reverse\">\n"
                 "##FORMAT=<ID=GT,Number=1,Type=String,Description=\"Genotype\">\n"
                 "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE\n")
        for line in fi:
            if line.startswith("#"):
                continue
            p = line.rstrip("\n").split("\t")
            if p[0] in drop_chroms or "," in p[4]:
                continue
            fmt, smp = p[8].split(":"), p[9].split(":")
            try:
                af = float(smp[fmt.index("AF")])
                dp = int(smp[fmt.index("DP")])
            except (ValueError, IndexError):
                continue
            if dp < min_dp or af < lo or af > hi:
                continue
            saf = sar = None
            if "SB" in fmt:
                sb = smp[fmt.index("SB")].split(",")
                if len(sb) == 4:
                    saf, sar = int(sb[2]), int(sb[3])
            if saf is None:
                alt = int(round(dp * af))
                saf, sar = alt // 2, alt - alt // 2
            fo.write("%s\t%s\t.\t%s\t%s\t100\tPASS\tDP=%d;SAF=%d;SAR=%d\tGT\t0/1\n" % (p[0], p[1], p[3], p[4], dp, saf, sar))
            n += 1
    return n


def write_config(template, out, build, thresholds, off_label):
    with open(template) as fh:
        c = json.load(fh)
    c["files"]["genome_build"] = build
    c["files"]["ratio_file"]["off_target_label"] = off_label
    c["files"]["ratio_file"]["off_target_low_conf_log2"] = -3.0
    c["files"]["gene_file"].update({"loss_threshold": thresholds[0], "deep_loss_threshold": thresholds[1],
                                    "gain_threshold": thresholds[2], "amp_threshold": thresholds[3]})
    c["plots"]["bokeh_js_css_code"] = "INLINE"
    with open(out, "w") as fh:
        json.dump(c, fh, indent=1)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cnr", required=True)
    ap.add_argument("--cns", required=True, help="CNVkit call.cns (needs cn column)")
    ap.add_argument("--vcf", required=True, help="raw Mutect2 VCF (all variants)")
    ap.add_argument("--fai", required=True, help="reference .fai for chromosome lengths")
    ap.add_argument("--template", required=True, help="reconCNV config.json template")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--loh", default=None, help="PureCN <sample>_loh.csv (C, M per segment)")
    ap.add_argument("--purity", type=float, default=1.0)
    ap.add_argument("--sex", default="unknown", help="female drops chrY tiles from the plots")
    ap.add_argument("--build", default="hg38")
    ap.add_argument("--off-label", default="Antitarget")
    ap.add_argument("--min-depth", type=int, default=30)
    ap.add_argument("--loss", type=float, default=-0.5)
    ap.add_argument("--deep-loss", type=float, default=-1.0)
    ap.add_argument("--gain", type=float, default=0.5)
    ap.add_argument("--amp", type=float, default=1.0)
    args = ap.parse_args()

    if not os.path.isdir(args.outdir):
        os.makedirs(args.outdir)
    drop = set(["chrY"]) if args.sex.lower().startswith("f") else set()
    o = lambda name: os.path.join(args.outdir, name)
    write_genome(args.fai, o("genome.tsv"))
    write_ratio(args.cnr, o("ratio.cnr"), args.off_label, drop)
    write_segments(args.cns, o("segments.cns"), load_loh(args.loh), args.purity, drop)
    n = write_het_vcf(args.vcf, o("hets.vcf"), args.min_depth, 0.10, 0.90, drop)
    write_config(args.template, o("config.json"), args.build, (args.loss, args.deep_loss, args.gain, args.amp), args.off_label)
    print("[ok] reconCNV inputs in %s (%d heterozygous sites)" % (args.outdir, n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
