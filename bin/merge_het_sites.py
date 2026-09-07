#!/usr/bin/env python3
"""
merge_het_sites.py  (BAF_CATALOG_V1)

Build the genome-wide BAF site catalog from per-normal het SNP candidates
(discover_hets.sh output, one file per sample named <sample>.hets.tsv).

A site is kept when it is heterozygous (alt fraction within --af-lo..--af-hi
at depth >= --min-depth) in at least --min-samples include_in_pon normals;
on chrX only females count; chrY is skipped; sites inside PARALOG_LIMITED
exons of the paralog table are dropped. Kept sites are written as 1-bp
intervals and appended to the base catalog (the 17p probe windows), which
is preserved unchanged; discovered sites already inside a base window are
not duplicated. The output BED is sorted in reference order.

Outputs: --out-bed (chrom, start, end, name) and --out-catalog
(per kept site: n_het, n_het_male, n_het_female, median_af, source).
Python 3.6, stdlib only.
"""

import argparse
import collections
import csv
import statistics
import sys

CHROM_ORDER = dict((c, i) for i, c in enumerate(
    ["chr%d" % i for i in range(1, 23)] + ["chrX", "chrY", "chrM"]))


def read_sheet(path):
    info = {}
    with open(path) as fh:
        for row in csv.DictReader(fh):
            info[row["sample"]] = (row.get("sex", "unknown"), str(row.get("include_in_pon", "")).lower() == "true")
    return info


def read_bed(path):
    rows = []
    with open(path) as fh:
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if len(p) < 3 or line.startswith("#") or line.startswith("track"):
                continue
            rows.append((p[0], int(p[1]), int(p[2]), p[3] if len(p) > 3 else ""))
    return rows


def read_paralog_exons(path):
    by_chrom = collections.defaultdict(list)
    if not path:
        return by_chrom
    with open(path) as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            if row.get("flag", "") == "PARALOG_LIMITED":
                by_chrom[row["chrom"]].append((int(row["start"]), int(row["end"])))
    return by_chrom


def in_intervals(iv, pos0):
    for s, e in iv:
        if s <= pos0 < e:
            return True
    return False


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sheet", required=True)
    ap.add_argument("--base-bed", required=True, help="existing snp_sites.baf.bed (17p block); preserved")
    ap.add_argument("--paralog-exons", default=None)
    ap.add_argument("--min-samples", type=int, default=3)
    ap.add_argument("--min-depth", type=int, default=50)
    ap.add_argument("--af-lo", type=float, default=0.20)
    ap.add_argument("--af-hi", type=float, default=0.80)
    ap.add_argument("--out-bed", required=True)
    ap.add_argument("--out-catalog", required=True)
    ap.add_argument("files", nargs="+", help="<sample>.hets.tsv files")
    args = ap.parse_args()

    sheet = read_sheet(args.sheet)
    base = read_bed(args.base_bed)
    base_by_chrom = collections.defaultdict(list)
    for c, s, e, _ in base:
        base_by_chrom[c].append((s, e))
    paralog = read_paralog_exons(args.paralog_exons)

    # site -> {sample: af}
    hets = collections.defaultdict(dict)
    alleles = {}
    n_files_used = 0
    for path in args.files:
        sample = path.split("/")[-1]
        sample = sample[:-len(".hets.tsv")] if sample.endswith(".hets.tsv") else sample
        if sample not in sheet:
            sys.stderr.write("[warn] %s not in sheet; skipped\n" % sample)
            continue
        sex, include = sheet[sample]
        if not include:
            continue
        n_files_used += 1
        with open(path) as fh:
            for line in fh:
                p = line.rstrip("\n").split("\t")
                if len(p) < 6:
                    continue
                chrom, pos, ref, alt = p[0], int(p[1]), p[2], p[3]
                if chrom == "chrY" or chrom not in CHROM_ORDER:
                    continue
                if "," in alt:
                    continue
                try:
                    ad = [int(x) for x in p[5].split(",")]
                    dp = ad[0] + ad[1]
                except (ValueError, IndexError):
                    continue
                if dp < args.min_depth:
                    continue
                af = ad[1] / float(dp)
                if af < args.af_lo or af > args.af_hi:
                    continue
                if chrom == "chrX" and sex != "female":
                    continue
                hets[(chrom, pos)][sample] = af
                alleles.setdefault((chrom, pos), (ref, alt))

    kept = []
    n_paralog = n_in_base = 0
    for (chrom, pos), samples in hets.items():
        if len(samples) < args.min_samples:
            continue
        if in_intervals(paralog.get(chrom, []), pos - 1):
            n_paralog += 1
            continue
        if in_intervals(base_by_chrom.get(chrom, []), pos - 1):
            n_in_base += 1
            continue
        males = sum(1 for s in samples if sheet[s][0] == "male")
        females = sum(1 for s in samples if sheet[s][0] == "female")
        kept.append((chrom, pos, alleles[(chrom, pos)], len(samples), males, females,
                     statistics.median(samples.values())))

    kept.sort(key=lambda k: (CHROM_ORDER[k[0]], k[1]))
    out_rows = [(c, s, e, n or "base_%s_%d" % (c, s), "base") for c, s, e, n in base]
    out_rows += [(c, p - 1, p, "het_%s_%d_%s%s" % (c, p, ra[0], ra[1]), "discovered")
                 for c, p, ra, _, _, _, _ in kept]
    out_rows.sort(key=lambda r: (CHROM_ORDER.get(r[0], 99), r[1]))
    with open(args.out_bed, "w") as out:
        for c, s, e, n, _ in out_rows:
            out.write("%s\t%d\t%d\t%s\n" % (c, s, e, n))
    with open(args.out_catalog, "w") as out:
        out.write("chrom\tpos\tref\talt\tn_het\tn_het_male\tn_het_female\tmedian_af\tsource\n")
        for c, p, (ref, alt), n, m, f, med in kept:
            out.write("%s\t%d\t%s\t%s\t%d\t%d\t%d\t%.3f\tdiscovered\n" % (c, p, ref, alt, n, m, f, med))

    per_chrom = collections.Counter(c for c, _, _, _, _, _, _ in kept)
    print("[ok] %d include_in_pon samples; %d candidate sites; kept %d (>= %d het samples), "
          "dropped %d paralog-limited, %d inside base windows; base rows %d; BED rows %d"
          % (n_files_used, len(hets), len(kept), args.min_samples, n_paralog, n_in_base, len(base), len(out_rows)))
    print("[ok] per chromosome: " + " ".join("%s:%d" % (c, per_chrom[c]) for c in sorted(per_chrom, key=lambda x: CHROM_ORDER[x])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
