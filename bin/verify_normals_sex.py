#!/usr/bin/env python3
"""
verify_normals_sex.py -- genotype-based sex verification for PoN normals.

Standalone QC. Reads BAMs, writes a TSV. Touches nothing in the pipeline.

Why this exists
---------------
Sex labels on the 48 PoN normals come from the filename, not from the data.
A single mislabelled normal contaminates a 24-sample stratum by 4%, and the
failure is silent: chrX calls degrade with no error anywhere. The existing
BUILD_SEX_PON module infers sex from chrX log2 in the LOO .cnr files, but that
is depth-only and its threshold is derived from params.male_reference (the
'-y' hack). A mislabelled sample and a genuine chrX event look identical to a
log2 threshold.

Two orthogonal signals are used here instead:

  1. chrX heterozygosity rate  -- PRIMARY.
     Males have one X, so heterozygous calls on chrX are near-zero (a small
     residue from PAR regions and mapping artefacts). Females show a normal
     het rate. This is independent of coverage normalisation entirely, which
     is what makes it orthogonal to the depth-based method.

  2. chrX : autosome median depth ratio -- CONFIRMATORY.
     ~0.5 in males, ~1.0 in females.

chrY is deliberately NOT used. The panel has 5 backbone tiles and no
main-panel chrY probes, and loss of Y is common in older male marrows, so low
chrY depth is not evidence of female sex.

Panel support for this is good: 596 chrX probes, 63,162 bp merged, across 14
genes (ALAS2, BCOR, BCORL1, BTK, DDX3X, DKC1, GATA1, KDM6A, PHF6, PIGA,
SMC1A, STAG2, UBA1, ZRSR2).

Output
------
normals_sex_verified.tsv, one row per sample:
    sample, label_sex, chrx_het_rate, chrx_sites_called, chrx_median_depth,
    autosome_median_depth, chrx_ratio, call_het, call_depth, call_final,
    agrees_with_label, flag

Samples where the two signals disagree are flagged 'DISCORDANT' and given
call_final='unknown' rather than being guessed at. Samples whose verified sex
contradicts the filename are flagged 'LABEL_MISMATCH'. Both should be
excluded from the PoN or investigated before use.

Python 3.6-safe.

Usage
-----
    python3 verify_normals_sex.py \
        --bam-dir  /goast/hemat_data/pon_twist \
        --bam-glob '*/preprocessing/*.final.bam' \
        --exonic   assets/twist_myeloid/targets.exonic.bed \
        --reference /goast/hemat_data/targeted-seq-pipeline/references/hg38_broad/Homo_sapiens_assembly38.masked.fasta \
        --outdir   qc/twist_myeloid \
        --threads  8
"""

import argparse
import glob
import os
import re
import subprocess
import sys
import tempfile
from collections import OrderedDict

TAG = "verify_normals_sex"

# Decision thresholds. Deliberately wide gaps: anything landing in between is
# reported as ambiguous rather than forced into a call.
HET_MALE_MAX = 0.05      # het rate below this  -> male
HET_FEMALE_MIN = 0.15    # het rate above this  -> female
RATIO_MALE_MAX = 0.70    # chrX:autosome below  -> male
RATIO_FEMALE_MIN = 0.80  # chrX:autosome above  -> female

MIN_SITES_FOR_HET = 50   # below this, het rate is not interpretable
MIN_DEPTH_FOR_SITE = 20  # per-site depth floor for a genotype call

# PAR1/PAR2 on hg38. Excluded: these regions are diploid in males and would
# produce heterozygous calls that mimic a female signal.
PAR_REGIONS = [
    ("chrX", 10001, 2781479),
    ("chrX", 155701383, 156030895),
]


def msg(kind, text):
    sys.stdout.write("[%s] %s\n" % (kind, text))
    sys.stdout.flush()


def die(text):
    msg("error", text)
    sys.exit(1)


def run(cmd, **kw):
    return subprocess.run(cmd, shell=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, universal_newlines=True, **kw)


def need(tool):
    r = run("command -v %s" % tool)
    if r.returncode != 0:
        die("%s not found on PATH. Activate the targeted-seq env first." % tool)
    return r.stdout.strip()


def split_bed_by_chrom(bed_path, outdir):
    """Write chrX-minus-PAR and autosome BED files. Returns (chrx, auto, counts)."""
    chrx_rows = []
    auto_rows = []
    fh = open(bed_path)
    try:
        for line in fh:
            line = line.rstrip("\n")
            if not line or line.startswith(("#", "track", "browser")):
                continue
            f = line.split("\t")
            if len(f) < 3:
                continue
            chrom, start, end = f[0], int(f[1]), int(f[2])
            name = f[3] if len(f) > 3 else "."
            if chrom == "chrX":
                in_par = False
                for pc, ps, pe in PAR_REGIONS:
                    if pc == chrom and start < pe and end > ps:
                        in_par = True
                        break
                if not in_par:
                    chrx_rows.append((chrom, start, end, name))
            elif re.fullmatch(r"chr([1-9]|1[0-9]|2[0-2])", chrom):
                auto_rows.append((chrom, start, end, name))
    finally:
        fh.close()

    chrx_bed = os.path.join(outdir, "_chrX_nonPAR.bed")
    auto_bed = os.path.join(outdir, "_autosomes.bed")
    for path, rows in ((chrx_bed, chrx_rows), (auto_bed, auto_rows)):
        fh = open(path, "w")
        try:
            for r in rows:
                fh.write("%s\t%d\t%d\t%s\n" % r)
        finally:
            fh.close()
    return chrx_bed, auto_bed, len(chrx_rows), len(auto_rows)


def chrx_het_rate(bam, chrx_bed, reference, threads):
    """Heterozygosity rate over chrX non-PAR targets via bcftools.

    --flag equivalent: bcftools mpileup default excludes duplicates. That is
    the right choice HERE (unlike coverage reporting, where lab convention is
    to include them) because duplicate reads carry no independent allelic
    information and would inflate apparent depth without improving the
    genotype call.
    """
    cmd = (
        "bcftools mpileup -f {ref} -R {bed} -q 20 -Q 20 -d 1000 "
        "-a FORMAT/AD --threads {th} {bam} 2>/dev/null | "
        "bcftools call -m -v --threads {th} 2>/dev/null | "
        "bcftools query -f '[%DP\\t%AD\\t%GT\\n]' 2>/dev/null"
    ).format(ref=reference, bed=chrx_bed, th=threads, bam=bam)
    r = run(cmd)
    het = 0
    total = 0
    for line in r.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        try:
            dp = int(parts[0])
        except ValueError:
            continue
        if dp < MIN_DEPTH_FOR_SITE:
            continue
        gt = parts[2].replace("|", "/")
        if gt in ("./.", "."):
            continue
        alleles = gt.split("/")
        if len(alleles) != 2:
            continue
        total += 1
        if alleles[0] != alleles[1]:
            het += 1
    rate = (float(het) / total) if total else 0.0
    return rate, total


def median_depth(bam, bed, outprefix, threads):
    """Median per-region depth via mosdepth.

    --flag 772 drops only the DUP bit, keeping duplicates in the coverage
    calculation. This follows lab convention for coverage reporting; the
    mosdepth default of 1796 would exclude duplicates.
    """
    cmd = ("mosdepth --by {bed} --flag 772 --no-per-base -t {th} {pfx} {bam}"
           ).format(bed=bed, th=threads, pfx=outprefix, bam=bam)
    r = run(cmd)
    if r.returncode != 0:
        return None
    regions = outprefix + ".regions.bed.gz"
    if not os.path.exists(regions):
        return None
    rr = run("zcat %s | awk '{print $NF}' | sort -n" % regions)
    vals = [float(x) for x in rr.stdout.split() if x]
    if not vals:
        return None
    n = len(vals)
    return vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2.0


def classify(het_rate, n_sites, ratio):
    call_het = "unknown"
    if n_sites >= MIN_SITES_FOR_HET:
        if het_rate <= HET_MALE_MAX:
            call_het = "male"
        elif het_rate >= HET_FEMALE_MIN:
            call_het = "female"

    call_depth = "unknown"
    if ratio is not None:
        if ratio <= RATIO_MALE_MAX:
            call_depth = "male"
        elif ratio >= RATIO_FEMALE_MIN:
            call_depth = "female"

    if call_het == "unknown" and call_depth == "unknown":
        return call_het, call_depth, "unknown", "NO_SIGNAL"
    if call_het == "unknown":
        return call_het, call_depth, call_depth, "HET_UNINFORMATIVE"
    if call_depth == "unknown":
        return call_het, call_depth, call_het, "DEPTH_UNINFORMATIVE"
    if call_het != call_depth:
        return call_het, call_depth, "unknown", "DISCORDANT"
    return call_het, call_depth, call_het, "OK"


def label_from_name(sample):
    low = sample.lower()
    if low.startswith("female"):
        return "female"
    if low.startswith("male"):
        return "male"
    return "unknown"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bam-dir", required=True, help="root directory to search for BAMs")
    ap.add_argument("--bam-glob", default="**/*.final.bam",
                    help="glob relative to --bam-dir (default: **/*.final.bam)")
    ap.add_argument("--exonic", required=True, help="targets.exonic.bed")
    ap.add_argument("--reference", required=True, help="reference FASTA")
    ap.add_argument("--outdir", required=True, help="output directory")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--keep-temp", action="store_true")
    args = ap.parse_args()

    need("bcftools")
    need("mosdepth")

    for p in (args.exonic, args.reference):
        if not os.path.isfile(p):
            die("no such file: %s" % p)

    bams = sorted(glob.glob(os.path.join(args.bam_dir, args.bam_glob), recursive=True))
    if not bams:
        die("no BAMs matched %s under %s" % (args.bam_glob, args.bam_dir))
    msg("ok", "found %d BAM(s)" % len(bams))

    if not os.path.isdir(args.outdir):
        os.makedirs(args.outdir)

    tmp = tempfile.mkdtemp(prefix="sexqc_", dir=args.outdir)
    chrx_bed, auto_bed, n_chrx, n_auto = split_bed_by_chrom(args.exonic, tmp)
    msg("ok", "chrX non-PAR targets: %d   autosomal targets: %d" % (n_chrx, n_auto))
    if n_chrx < 100:
        msg("warn", "only %d chrX targets; het rate may be underpowered" % n_chrx)

    rows = []
    for i, bam in enumerate(bams, 1):
        sample = re.sub(r"\.final\.bam$", "", os.path.basename(bam))
        msg("ok", "[%d/%d] %s" % (i, len(bams), sample))

        het_rate, n_sites = chrx_het_rate(bam, chrx_bed, args.reference, args.threads)
        dx = median_depth(bam, chrx_bed, os.path.join(tmp, sample + ".chrX"), args.threads)
        da = median_depth(bam, auto_bed, os.path.join(tmp, sample + ".auto"), args.threads)
        ratio = (dx / da) if (dx is not None and da not in (None, 0)) else None

        call_het, call_depth, call_final, flag = classify(het_rate, n_sites, ratio)
        label = label_from_name(sample)
        agrees = "yes" if (call_final != "unknown" and call_final == label) else "no"
        if flag == "OK" and agrees == "no":
            flag = "LABEL_MISMATCH"

        rows.append(OrderedDict([
            ("sample", sample),
            ("label_sex", label),
            ("chrx_het_rate", "%.4f" % het_rate),
            ("chrx_sites_called", n_sites),
            ("chrx_median_depth", "%.1f" % dx if dx is not None else "NA"),
            ("autosome_median_depth", "%.1f" % da if da is not None else "NA"),
            ("chrx_ratio", "%.3f" % ratio if ratio is not None else "NA"),
            ("call_het", call_het),
            ("call_depth", call_depth),
            ("call_final", call_final),
            ("agrees_with_label", agrees),
            ("flag", flag),
        ]))

    out = os.path.join(args.outdir, "normals_sex_verified.tsv")
    fh = open(out, "w")
    try:
        fh.write("\t".join(rows[0].keys()) + "\n")
        for r in rows:
            fh.write("\t".join(str(v) for v in r.values()) + "\n")
    finally:
        fh.close()
    msg("write", "%s (%d rows)" % (out, len(rows)))

    n_ok = sum(1 for r in rows if r["flag"] == "OK")
    problems = [r for r in rows if r["flag"] != "OK"]
    msg("ok", "verified clean: %d/%d" % (n_ok, len(rows)))
    for r in problems:
        msg("warn", "%-22s flag=%-20s label=%-7s het=%s (n=%s) ratio=%s -> %s"
            % (r["sample"], r["flag"], r["label_sex"], r["chrx_het_rate"],
               r["chrx_sites_called"], r["chrx_ratio"], r["call_final"]))

    males = [r for r in rows if r["call_final"] == "male"]
    females = [r for r in rows if r["call_final"] == "female"]
    msg("ok", "verified strata: %d male, %d female, %d unresolved"
        % (len(males), len(females), len(rows) - len(males) - len(females)))
    if problems:
        msg("warn", "Resolve flagged samples before building the PoN. Do not "
                    "guess: exclude them, or investigate the discordance.")

    if not args.keep_temp:
        run("rm -rf %s" % tmp)
    else:
        msg("ok", "temp kept at %s" % tmp)


if __name__ == "__main__":
    main()
