#!/usr/bin/env python3
"""
tools/paralog_limited_exons.py

Panel-wide table of exons whose reads are lost to MAPQ filtering because of
primary-assembly paralogs (STAT5B/STAT5A, SUZ12/SUZ12P1, ANKRD26 pseudogenes,
...). Alt-contig awareness does not help these; they are a permanent property
of the panel and must be known to the CNV caveats, DECoN exclusion list and
the SNV rescue logic.

Three subcommands, designed to be run in order:

  run        mosdepth over the exon BED at MAPQ>=0 and MAPQ>=20 for every BAM
             (duplicates included, --flag 772, house convention). Idempotent:
             existing outputs are skipped unless --force.
  summarise  per-exon MAPQ-retained fraction (mean depth at MAPQ>=20 divided
             by mean depth at MAPQ>=0), aggregated across samples; flags
             PARALOG_LIMITED / LOW_DEPTH / OK.
  annotate   for each flagged exon, the modal alternative-hit locus (XA tag)
             of low-MAPQ reads in one BAM, binned to 0.1 Mb. This is the
             evidence that named STAT5A and SUZ12P1 on 2026-09-04.

Example (gandalf):
  python3 tools/paralog_limited_exons.py run \
      --bams pon_samplesheets/twist_males_24_v3.csv --bam-column bam \
      --bed assets/twist_myeloid/targets.exonwise.bed \
      --workdir /goast/hemat_data/pon_twist/paralog_v4 --jobs 8
  python3 tools/paralog_limited_exons.py summarise \
      --workdir /goast/hemat_data/pon_twist/paralog_v4 \
      --out /goast/hemat_data/pon_twist/paralog_v4/paralog_limited_exons.tsv \
      --matrix /goast/hemat_data/pon_twist/paralog_v4/retained_fraction_matrix.tsv
  python3 tools/paralog_limited_exons.py annotate \
      --table /goast/hemat_data/pon_twist/paralog_v4/paralog_limited_exons.tsv \
      --bam /goast/hemat_data/pon_twist/realign_v4/Male3-TwistMy/clinical/Male3-TwistMy.final.bam \
      --out /goast/hemat_data/pon_twist/paralog_v4/paralog_limited_exons.annotated.tsv

Python 3.6-safe. External tools: mosdepth (run), samtools (annotate).
"""
import argparse
import collections
import csv
import gzip
import os
import re
import statistics
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

MAPQ_LOW = 0
MAPQ_HIGH = 20
MOSDEPTH_FLAG = "772"  # exclude unmapped/secondary/QC-fail, keep duplicates


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def log(tag, msg):
    print("[{}] {}".format(tag, msg))
    sys.stdout.flush()


def read_bam_list(path, column):
    """Accept a plain list (one BAM path per line) or a CSV with a header."""
    bams = []
    with open(path) as fh:
        first = fh.readline()
        fh.seek(0)
        if "," in first:
            reader = csv.DictReader(fh)
            if column not in reader.fieldnames:
                raise SystemExit("[error] column '{}' not in {}".format(column, path))
            for row in reader:
                if row.get("include_in_pon", "true").strip().lower() == "false":
                    continue
                if row[column].strip():
                    bams.append(row[column].strip())
        else:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#"):
                    bams.append(line)
    return bams


def sample_name(bam):
    base = os.path.basename(bam)
    for suffix in (".final.bam", ".bam"):
        if base.endswith(suffix):
            return base[: -len(suffix)]
    return base


def gene_from_name(name):
    """GENE from 'GENE_exon_3', 'GENE|Ex__3', 'GENE' ..."""
    m = re.match(r"^([A-Za-z0-9.\-]+?)(?:_exon_|_Ex|\|Ex|\||_[0-9]+$|$)", name)
    return m.group(1) if m else name


def median(values):
    return statistics.median(values) if values else float("nan")


# --------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------

def mosdepth_prefix(workdir, sample, mapq):
    return os.path.join(workdir, "{}.mq{}".format(sample, mapq))


def run_one(mosdepth, bam, bed, workdir, mapq, threads, force):
    sample = sample_name(bam)
    prefix = mosdepth_prefix(workdir, sample, mapq)
    out = prefix + ".regions.bed.gz"
    if os.path.exists(out) and not force:
        return ("skip", sample, mapq)
    cmd = [
        mosdepth,
        "--threads", str(threads),
        "--by", bed,
        "--flag", MOSDEPTH_FLAG,
        "--mapq", str(mapq),
        "--no-per-base",
        prefix,
        bam,
    ]
    logpath = prefix + ".log"
    with open(logpath, "w") as lf:
        rc = subprocess.call(cmd, stdout=lf, stderr=subprocess.STDOUT)
    if rc != 0 or not os.path.exists(out):
        return ("error", sample, mapq)
    return ("ok", sample, mapq)


def cmd_run(args):
    for f in (args.bams, args.bed):
        if not os.path.isfile(f):
            raise SystemExit("[error] missing: {}".format(f))
    bams = read_bam_list(args.bams, args.bam_column)
    missing = [b for b in bams if not os.path.isfile(b)]
    if missing:
        raise SystemExit("[error] {} BAM(s) not found, first: {}".format(len(missing), missing[0]))
    os.makedirs(args.workdir, exist_ok=True)
    log("ok", "{} BAMs, exon BED {}, workdir {}".format(len(bams), args.bed, args.workdir))

    jobs = []
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for bam in bams:
            for mapq in (MAPQ_LOW, MAPQ_HIGH):
                jobs.append(pool.submit(run_one, args.mosdepth, bam, args.bed,
                                        args.workdir, mapq, args.threads, args.force))
        counts = collections.Counter()
        for job in jobs:
            status, sample, mapq = job.result()
            counts[status] += 1
            if status == "error":
                log("error", "{} mq{} failed; see {}.log".format(
                    sample, mapq, mosdepth_prefix(args.workdir, sample, mapq)))
    log("done", "mosdepth ok={} skip={} error={}".format(
        counts["ok"], counts["skip"], counts["error"]))
    return 1 if counts["error"] else 0


# --------------------------------------------------------------------------
# summarise
# --------------------------------------------------------------------------

def read_regions(path):
    """mosdepth regions.bed.gz with a 4-column --by BED: chrom start end name depth."""
    regions = collections.OrderedDict()
    with gzip.open(path, "rt") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) == 5:
                chrom, start, end, name, depth = parts
            elif len(parts) == 4:
                chrom, start, end, depth = parts
                name = "{}:{}-{}".format(chrom, start, end)
            else:
                continue
            key = (chrom, int(start), int(end), name)
            regions[key] = float(depth)
    return regions


def cmd_summarise(args):
    files = sorted(f for f in os.listdir(args.workdir) if f.endswith(".mq{}.regions.bed.gz".format(MAPQ_HIGH)))
    samples = [f[: -len(".mq{}.regions.bed.gz".format(MAPQ_HIGH))] for f in files]
    if not samples:
        raise SystemExit("[error] no mq{} outputs in {}".format(MAPQ_HIGH, args.workdir))

    per_sample = {}
    for s in samples:
        low = read_regions(os.path.join(args.workdir, "{}.mq{}.regions.bed.gz".format(s, MAPQ_LOW)))
        high = read_regions(os.path.join(args.workdir, "{}.mq{}.regions.bed.gz".format(s, MAPQ_HIGH)))
        if list(low.keys()) != list(high.keys()):
            raise SystemExit("[error] region sets differ between mq0 and mq20 for {}".format(s))
        per_sample[s] = (low, high)
    keys = list(per_sample[samples[0]][0].keys())
    log("ok", "{} samples, {} exons".format(len(samples), len(keys)))

    header = ["chrom", "start", "end", "name", "gene",
              "n_samples", "median_depth_mq0", "median_depth_mq20",
              "median_retained", "min_retained", "max_retained", "flag"]
    rows = []
    matrix = []
    counts = collections.Counter()
    for key in keys:
        chrom, start, end, name = key
        d0 = [per_sample[s][0][key] for s in samples]
        d20 = [per_sample[s][1][key] for s in samples]
        retained = []
        for a, b in zip(d0, d20):
            retained.append(b / a if a > 0 else float("nan"))
        valid = [r for r in retained if r == r]  # drop NaN
        med0 = median(d0)
        med20 = median(d20)
        medr = median(valid)
        if med0 < args.min_depth:
            flag = "LOW_DEPTH"
        elif medr < args.min_retained:
            flag = "PARALOG_LIMITED"
        else:
            flag = "OK"
        counts[flag] += 1
        rows.append([chrom, start, end, name, gene_from_name(name), len(valid),
                     "{:.1f}".format(med0), "{:.1f}".format(med20),
                     "{:.3f}".format(medr) if valid else "NA",
                     "{:.3f}".format(min(valid)) if valid else "NA",
                     "{:.3f}".format(max(valid)) if valid else "NA",
                     flag])
        matrix.append([chrom, start, end, name] +
                      ["{:.3f}".format(r) if r == r else "NA" for r in retained])

    with open(args.out, "w") as fh:
        fh.write("\t".join(header) + "\n")
        for r in rows:
            fh.write("\t".join(str(x) for x in r) + "\n")
    log("ok", "wrote {}".format(args.out))
    if args.matrix:
        with open(args.matrix, "w") as fh:
            fh.write("\t".join(["chrom", "start", "end", "name"] + samples) + "\n")
            for r in matrix:
                fh.write("\t".join(str(x) for x in r) + "\n")
        log("ok", "wrote {}".format(args.matrix))

    log("done", "OK={} PARALOG_LIMITED={} LOW_DEPTH={} (min_retained {}, min_depth {})".format(
        counts["OK"], counts["PARALOG_LIMITED"], counts["LOW_DEPTH"],
        args.min_retained, args.min_depth))
    flagged = [r for r in rows if r[-1] == "PARALOG_LIMITED"]
    for r in sorted(flagged, key=lambda x: float(x[8])):
        log("flag", "{:<24s} {}:{}-{}  retained median {} (min {}, max {})  depth mq0 {}".format(
            r[3], r[0], r[1], r[2], r[8], r[9], r[10], r[6]))
    return 0


# --------------------------------------------------------------------------
# annotate
# --------------------------------------------------------------------------

XA_RE = re.compile(r"XA:Z:(\S+)")


def modal_xa_locus(samtools, bam, region, mapq_cut, bin_bp):
    """Return (n_low, n_with_xa, top_locus, top_fraction) for reads with MAPQ < mapq_cut."""
    cmd = [samtools, "view", bam, region]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            universal_newlines=True)
    n_low = 0
    n_xa = 0
    loci = collections.Counter()
    for line in proc.stdout:
        parts = line.split("\t")
        if len(parts) < 12:
            continue
        try:
            mq = int(parts[4])
        except ValueError:
            continue
        if mq >= mapq_cut:
            continue
        n_low += 1
        m = XA_RE.search(line)
        if not m:
            continue
        n_xa += 1
        for hit in m.group(1).strip(";").split(";"):
            fields = hit.split(",")
            if len(fields) < 2:
                continue
            chrom = fields[0]
            try:
                pos = abs(int(fields[1]))
            except ValueError:
                continue
            loci[(chrom, pos // bin_bp)] += 1
    proc.wait()
    if not loci:
        return n_low, n_xa, "NA", 0.0
    (chrom, b), n = loci.most_common(1)[0]
    locus = "{}:{:.1f}Mb".format(chrom, b * bin_bp / 1e6)
    return n_low, n_xa, locus, n / float(n_xa) if n_xa else 0.0


def cmd_annotate(args):
    if not os.path.isfile(args.bam):
        raise SystemExit("[error] missing BAM: {}".format(args.bam))
    with open(args.table) as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        rows = list(reader)
        fields = reader.fieldnames
    targets = [r for r in rows if r["flag"] == "PARALOG_LIMITED" or
               (args.include_low_depth and r["flag"] == "LOW_DEPTH")]
    log("ok", "{} exons to annotate from {}".format(len(targets), os.path.basename(args.bam)))

    out_fields = fields + ["xa_n_lowmapq", "xa_n_with_xa", "xa_modal_locus", "xa_modal_fraction"]
    annotated = {}
    for r in targets:
        region = "{}:{}-{}".format(r["chrom"], int(r["start"]) + 1, r["end"])
        n_low, n_xa, locus, frac = modal_xa_locus(args.samtools, args.bam, region,
                                                  MAPQ_HIGH, args.bin_bp)
        annotated[(r["chrom"], r["start"], r["end"], r["name"])] = (n_low, n_xa, locus, frac)
        log("xa", "{:<24s} {}  low-MAPQ reads {}  with XA {}  modal {} ({:.0%})".format(
            r["name"], region, n_low, n_xa, locus, frac))

    with open(args.out, "w") as fh:
        fh.write("\t".join(out_fields) + "\n")
        for r in rows:
            key = (r["chrom"], r["start"], r["end"], r["name"])
            extra = annotated.get(key)
            if extra:
                vals = [str(extra[0]), str(extra[1]), extra[2], "{:.3f}".format(extra[3])]
            else:
                vals = ["", "", "", ""]
            fh.write("\t".join([r[f] for f in fields] + vals) + "\n")
    log("done", "wrote {}".format(args.out))
    return 0


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd")

    r = sub.add_parser("run", help="mosdepth at MAPQ>=0 and MAPQ>=20 per BAM")
    r.add_argument("--bams", required=True, help="BAM list (one per line) or samplesheet CSV")
    r.add_argument("--bam-column", default="bam", help="column name if --bams is a CSV")
    r.add_argument("--bed", required=True, help="exon BED, 4th column = exon name")
    r.add_argument("--workdir", required=True)
    r.add_argument("--mosdepth", default="mosdepth")
    r.add_argument("--jobs", type=int, default=8, help="parallel mosdepth processes")
    r.add_argument("--threads", type=int, default=2, help="threads per mosdepth")
    r.add_argument("--force", action="store_true", help="recompute existing outputs")
    r.set_defaults(func=cmd_run)

    s = sub.add_parser("summarise", help="per-exon retained fraction across samples")
    s.add_argument("--workdir", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--matrix", help="optional per-sample retained-fraction matrix")
    s.add_argument("--min-retained", type=float, default=0.80,
                   help="median MAPQ>=20 / MAPQ>=0 below this = PARALOG_LIMITED")
    s.add_argument("--min-depth", type=float, default=50.0,
                   help="median MAPQ>=0 depth below this = LOW_DEPTH (not evaluated for paralogs)")
    s.set_defaults(func=cmd_summarise)

    a = sub.add_parser("annotate", help="modal XA locus of low-MAPQ reads for flagged exons")
    a.add_argument("--table", required=True, help="output of summarise")
    a.add_argument("--bam", required=True, help="one representative BAM")
    a.add_argument("--out", required=True)
    a.add_argument("--samtools", default="samtools")
    a.add_argument("--bin-bp", type=int, default=100000, help="locus binning for XA hits")
    a.add_argument("--include-low-depth", action="store_true")
    a.set_defaults(func=cmd_annotate)

    args = p.parse_args()
    if not args.cmd:
        p.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
