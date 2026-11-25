#!/usr/bin/env python3
"""tests/baf/simulate_baf_sample.py -- synthetic inputs for bin/baf_cnloh_detect.py.

Writes the two per-sample files the detector reads, for a made-up sample, from the panel's own
background table and interval list (no patient data, nothing outside the repository):

    <prefix>.allelicCounts.tsv   GATK CollectAllelicCounts layout, one row per catalog position
    <prefix>.denoisedCR.tsv      GATK DenoiseReadCounts layout, one row per preprocessed interval

Model (deliberately simple; it tests the detector's logic, it does not validate the assay):
  genotype   each informative site is heterozygous with the cohort's own frequency at that
             site (n_het_like / n_pass_depth); otherwise homozygous for the reference or the
             alternate allele. Sites within 20 kb of the first site of a group share its
             heterozygous state four times out of five (linkage disequilibrium). chrX is
             hemizygous (no heterozygous site) when --sex male.
  depth      cohort median depth at the position x --depth-scale x lognormal(0, 0.15), scaled
             by the copy number of a planted deletion or gain.
  allele     a heterozygous site sits at the cohort's own median ALT fraction when that is
  fraction   het-like (0.35-0.65), else at 0.473 (the reference bias measured on the
             validation run). An event of clonal fraction f moves it, with a random side per
             site (unphased):
                 cnloh   (1 -/+ f) / 2
                 del     (1 - f) / (2 - f)   or   1 / (2 - f)
                 gain    1 / (2 + f)         or   (1 + f) / (2 + f)
             A per-site scatter of 0.13 on the log-odds scale is added (about 0.03 at 0.5; with
             the counting noise this reproduces the 0.029 median deviation of balanced arms on
             the validation run), then counts are drawn binomially.
  artefacts  what every real sample shows and a detector must tolerate: 3 % of heterozygous
             sites at an odd ratio (0.12-0.35 or mirrored); homozygous sites with a per-site
             error rate of about 0.15 %, one in a hundred with a systematic minor fraction of
             2-8 %; sites heterozygous in more than 75 % of the normals behave as paralogue
             differences (a fixed ratio in every sample, untouched by any event).
             --contamination mixes in a second, unrelated genotype.
  copy       log2 ratio per interval ~ N(0, 0.12), shifted by log2(copies / 2) inside a planted
  ratio      deletion or gain.

Events:  --event ARM:TYPE:F        e.g. 11q:cnloh:0.90   7q:del:0.95   8q:gain:0.6
         --event CHR:START-END:TYPE:F   e.g. chr11:90000000-135086622:cnloh:0.9  (part of an arm)
A whole chromosome is two events (7p and 7q).

Python 3.6 compatible, standard library only. Same seed, same files, byte for byte.
"""
import argparse
import math
import os
import random
import sys

CENTROMERE_HG38 = {
    "chr1": (121700000, 125100000), "chr2": (91800000, 96000000), "chr3": (87800000, 94000000),
    "chr4": (48200000, 51800000), "chr5": (46100000, 51400000), "chr6": (58500000, 62600000),
    "chr7": (58100000, 62100000), "chr8": (43200000, 47200000), "chr9": (42200000, 45500000),
    "chr10": (38000000, 41600000), "chr11": (51000000, 55800000), "chr12": (33200000, 37800000),
    "chr13": (16500000, 18900000), "chr14": (16100000, 18200000), "chr15": (17500000, 20500000),
    "chr16": (35300000, 38400000), "chr17": (22700000, 27400000), "chr18": (15400000, 21500000),
    "chr19": (24200000, 28100000), "chr20": (25700000, 30400000), "chr21": (10900000, 13000000),
    "chr22": (13700000, 17400000), "chrX": (58100000, 61000000), "chrY": (10300000, 10600000),
}
REF_BIAS_CENTRE = 0.473     # median raw ALT fraction of balanced het sites on the validation run
SITE_SCATTER_LOGIT = 0.13   # per-site spread, about 0.03 at 0.5
ARTEFACT_RATE = 0.01        # homozygous informative sites with a systematic 2-8 % minor fraction
ODD_HET_RATE = 0.03         # heterozygous sites sitting at an odd ratio (0.12-0.35 or mirrored)
PARALOGUE_HET_FREQ = 0.75   # sites heterozygous in more of the normals than this: paralogue differences
LD_SPAN = 20000             # sites this close to the first site of a group share its state ...
LD_SHARE = 0.8              # ... this often


def fail(msg):
    sys.stderr.write("[error] %s\n" % msg)
    sys.exit(1)


def expit(x):
    if x > 700:
        return 1.0
    if x < -700:
        return 0.0
    return 1.0 / (1.0 + math.exp(-x))


def logit(p):
    return math.log(p / (1.0 - p))


def draw_binomial(rng, n, p):
    """Binomial(n, p) draw without numpy: exact for small n, Poisson for rare events, normal otherwise."""
    if n <= 0 or p <= 0.0:
        return 0
    if p >= 1.0:
        return n
    if p > 0.5:
        return n - draw_binomial(rng, n, 1.0 - p)
    mean = n * p
    if n < 40:
        return sum(1 for _ in range(n) if rng.random() < p)
    if mean < 30.0:
        # Poisson approximation by inversion (p is small here)
        limit, k, prod = math.exp(-mean), 0, rng.random()
        while prod > limit:
            k += 1
            prod *= rng.random()
        return min(k, n)
    k = int(round(rng.gauss(mean, math.sqrt(mean * (1.0 - p)))))
    return max(0, min(n, k))


def read_background(path):
    rows, header = [], None
    with open(path) as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            p = line.rstrip("\n").split("\t")
            if header is None:
                header = p
                continue
            rows.append(dict(zip(header, p)))
    if not rows:
        fail("no rows in background: %s" % path)
    return rows


def read_intervals(path):
    out = []
    with open(path) as fh:
        for line in fh:
            if line.startswith("@") or not line.strip():
                continue
            p = line.rstrip("\n").split("\t")
            out.append((p[0], int(p[1]), int(p[2])))
    if not out:
        fail("no intervals in %s" % path)
    return out


def parse_events(specs):
    """-> [(chrom, start, end, type, f)]"""
    events = []
    for spec in specs or []:
        parts = spec.split(":")
        try:
            if len(parts) == 3:                      # ARM:TYPE:F
                arm, etype, f = parts[0], parts[1].lower(), float(parts[2])
                chrom = "chr" + arm[:-1].replace("chr", "")
                cen = CENTROMERE_HG38[chrom]
                start, end = (0, cen[0]) if arm[-1] == "p" else (cen[1], 10 ** 9)
                if arm[-1] not in "pq":
                    raise ValueError(spec)
            elif len(parts) == 4:                    # CHR:START-END:TYPE:F
                chrom, etype, f = parts[0], parts[2].lower(), float(parts[3])
                start, end = [int(x) for x in parts[1].split("-")]
            else:
                raise ValueError(spec)
        except (ValueError, KeyError):
            fail("cannot read --event %s (want ARM:TYPE:F or CHR:START-END:TYPE:F)" % spec)
        if etype not in ("cnloh", "del", "gain") or not 0.0 <= f <= 1.0:
            fail("--event %s: type must be cnloh, del or gain and F between 0 and 1" % spec)
        events.append((chrom, start, end, etype, f))
    return events


def event_at(events, chrom, pos):
    for c, s, e, etype, f in events:
        if c == chrom and s <= pos <= e:
            return etype, f
    return None, 0.0


def shifted_fraction(etype, f, up):
    """ALT fraction of a heterozygous site under an event; `up` picks which allele is retained."""
    if etype == "cnloh":
        lo = (1.0 - f) / 2.0
    elif etype == "del":
        lo = (1.0 - f) / (2.0 - f)
    elif etype == "gain":
        lo = 1.0 / (2.0 + f)
    else:
        return 0.5
    return 1.0 - lo if up else lo


def copies(etype, f):
    return 2.0 - f if etype == "del" else (2.0 + f if etype == "gain" else 2.0)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    assets = os.path.normpath(os.path.join(here, "..", "..", "assets", "twist_myeloid"))
    ap = argparse.ArgumentParser(description="Synthetic allelic counts and denoised copy ratios for the BAF detector tests")
    ap.add_argument("--background", default=os.path.join(assets, "baf_background.tsv"))
    ap.add_argument("--intervals", default=os.path.join(assets, "targets.preprocessed.interval_list"))
    ap.add_argument("--sample", required=True)
    ap.add_argument("--out-prefix", required=True)
    ap.add_argument("--sex", default="female", choices=["male", "female"])
    ap.add_argument("--event", action="append", default=[], help="ARM:TYPE:F or CHR:START-END:TYPE:F; repeatable")
    ap.add_argument("--contamination", type=float, default=0.0, help="fraction of reads from a second, unrelated genotype")
    ap.add_argument("--depth-scale", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=20261125)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    events = parse_events(args.event)
    bg = read_background(args.background)

    def het_frequency(row):
        try:
            return int(row["n_het_like"]) / float(row["n_pass_depth"]) if float(row["n_pass_depth"]) > 0 else 0.0
        except ValueError:
            return 0.0

    def genotype(row, chrom, linked_het=None):
        """-> ALT dosage 0, 1 or 2 drawn from the cohort's het frequency at the site.
        linked_het: heterozygous state of the first site of the linkage group, or None."""
        if row["informative"] != "true":
            return 0
        p_het = het_frequency(row)
        if chrom == "chrY" or (chrom == "chrX" and args.sex == "male"):
            is_het = False
        elif linked_het is not None and rng.random() < LD_SHARE:
            is_het = linked_het
        else:
            is_het = rng.random() < p_het
        if is_het:
            return 1
        q = 0.5 if p_het >= 0.5 else (1.0 - math.sqrt(1.0 - 2.0 * p_het)) / 2.0   # minor allele frequency
        try:
            med = float(row["median_alt_fraction"])
        except ValueError:
            med = 0.0
        if med >= 0.65:
            q_alt = 1.0 - q
        elif med <= 0.35:
            q_alt = q
        else:
            q_alt = q if rng.random() < 0.5 else 1.0 - q
        p_alt_hom = q_alt * q_alt / (q_alt * q_alt + (1.0 - q_alt) * (1.0 - q_alt))
        return 2 if rng.random() < p_alt_hom else 0

    n_het = n_inf = 0
    group = None    # (chrom, first position, heterozygous state) of the current linkage group
    with open(args.out_prefix + ".allelicCounts.tsv", "w") as out:
        out.write("@HD\tVN:1.6\n@RG\tID:GATKCopyNumber\tSM:%s\n" % args.sample)
        out.write("CONTIG\tPOSITION\tREF_COUNT\tALT_COUNT\tREF_NUCLEOTIDE\tALT_NUCLEOTIDE\n")
        for row in bg:
            chrom, pos = row["contig"], int(row["position"])
            informative = row["informative"] == "true"
            try:
                med_depth = float(row["median_depth"])
            except ValueError:
                med_depth = 0.0
            try:
                cohort_median = float(row["median_alt_fraction"])
            except ValueError:
                cohort_median = 0.0
            etype, f = event_at(events, chrom, pos)
            depth = med_depth * args.depth_scale * math.exp(rng.gauss(0.0, 0.15)) * copies(etype, f) / 2.0
            if chrom == "chrX" and args.sex == "male":
                depth *= 0.5
            depth = int(round(depth))
            err = min(0.01, max(0.0003, math.exp(rng.gauss(math.log(0.0015), 0.5))))
            paralogue = informative and het_frequency(row) > PARALOGUE_HET_FREQ
            if paralogue:
                # a fixed difference between two copies of a duplicated sequence: same ratio in everyone
                true_af = min(0.6, max(0.15, cohort_median if 0.1 < cohort_median < 0.9 else 0.35))
                dosage = 1
            else:
                linked = None
                if informative:
                    if group and group[0] == chrom and pos - group[1] <= LD_SPAN:
                        linked = group[2]
                dosage = genotype(row, chrom, linked)
                if informative and linked is None:
                    group = (chrom, pos, dosage == 1)
                if dosage == 1:
                    centre = cohort_median if 0.35 <= cohort_median <= 0.65 else REF_BIAS_CENTRE
                    if etype:
                        up = rng.random() < 0.5
                        true_af = shifted_fraction(etype, f, up)
                        # carry the site's own bias onto the shifted fraction (log-odds scale)
                        true_af = expit(logit(min(1.0 - err, max(err, true_af))) + logit(centre))
                    elif rng.random() < ODD_HET_RATE:
                        odd = rng.uniform(0.12, 0.35)
                        true_af = odd if rng.random() < 0.5 else 1.0 - odd
                    else:
                        true_af = centre
                else:
                    true_af = 1.0 if dosage == 2 else 0.0
                    if informative and rng.random() < ARTEFACT_RATE:
                        minor = rng.uniform(0.02, 0.08)
                        true_af = 1.0 - minor if dosage == 2 else minor
            if dosage == 1:
                n_het += 1
            if informative:
                n_inf += 1
            if args.contamination > 0.0 and informative and not paralogue:
                other = genotype(row, "chr1") / 2.0     # an unrelated diploid genotype at the same site
                true_af = (1.0 - args.contamination) * true_af + args.contamination * other
            true_af = min(1.0 - err, max(err, true_af))
            scatter = rng.gauss(0.0, SITE_SCATTER_LOGIT) if dosage == 1 else 0.0
            p_alt = expit(logit(true_af) + scatter)
            alt = draw_binomial(rng, depth, p_alt)
            out.write("%s\t%d\t%d\t%d\tN\tN\n" % (chrom, pos, depth - alt, alt))

    n_bins = 0
    with open(args.out_prefix + ".denoisedCR.tsv", "w") as out:
        out.write("@HD\tVN:1.6\n@RG\tID:GATKCopyNumber\tSM:%s\n" % args.sample)
        out.write("CONTIG\tSTART\tEND\tLOG2_COPY_RATIO\n")
        for chrom, start, end in read_intervals(args.intervals):
            etype, f = event_at(events, chrom, (start + end) // 2)
            l2 = rng.gauss(0.0, 0.12) + math.log(copies(etype, f) / 2.0, 2)
            out.write("%s\t%d\t%d\t%.6f\n" % (chrom, start, end, l2))
            n_bins += 1

    print("[ok] %s: %d positions (%d informative, %d heterozygous), %d copy-ratio bins, sex %s, events %s -> %s.{allelicCounts,denoisedCR}.tsv" % (
        args.sample, len(bg), n_inf, n_het, n_bins, args.sex,
        ", ".join("%s:%d-%d %s f=%.2f" % e for e in events) or "none", args.out_prefix))


if __name__ == "__main__":
    main()
