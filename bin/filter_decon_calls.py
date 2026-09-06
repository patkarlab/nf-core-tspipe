#!/usr/bin/env python3
"""
tools/decon/filter_decon_calls.py

Post-hoc classification of DECoN calls (makeCNVcalls.R *calls_all.txt).
DECoN runs unchanged (its --exons/--custom path crashes IdentifyFailures);
this script annotates each call by genomic overlap with the panel exon table
and, optionally, the sample's own variant table, then decides reportability.

Artefact classes for single-exon calls (evidence: twist_pilot/decon_v4,
2026-09-04):
  PARALOG_EXON     exon flagged PARALOG_LIMITED in paralog_limited_exons.tsv
                   (STAT5B exons 6-8 / STAT5A, SUZ12 exons 3,6,9 / SUZ12P1).
                   Never reported.
  PROBE_VARIANT    a PASS variant with VAF >= --variant-min-vaf in the same
                   sample lies inside the call interval: capture dropout from
                   probe mismatch (Male23 ANKRD26 exon 27, two homozygous
                   variants, ratio 0.67). Never reported.
  LOW_POWER_EXON   exon median MAPQ>=20 depth < --low-power-depth or flagged
                   LOW_DEPTH (HRAS exon 1 148x, ANKRD26 exons 5/14/28 ...).
                   Reported only if BF >= --low-power-bf.
  PASS             none of the above; reported if BF >= --bf.
Multi-exon calls are PASS if BF >= --bf; flagged exons inside them are
listed in exon_flags for the reader but do not block the call.

Rows are all written with a `decision` and `reportable` column so the audit
trail is complete; --reportable-only restricts the output.

Example:
  python3 tools/decon/filter_decon_calls.py \
      --calls /goast/hemat_data/twist_pilot/decon_v4/pool25_v4calls_all.txt \
      --exons assets/twist_myeloid/paralog_limited_exons.tsv \
      --variants-pattern "/goast/hemat_data/pon_twist/realign_v4/{sample}/clinical/{sample}.somaticseq.filtered.tsv" \
      --out /goast/hemat_data/twist_pilot/decon_v4/pool25_v4calls_filtered.tsv

Python 3.6-safe, stdlib only.
"""
import argparse
import collections
import csv
import os
import sys


def log(tag, msg):
    print("[{}] {}".format(tag, msg))
    sys.stdout.flush()


def norm_chrom(c):
    c = str(c).strip()
    return c[3:] if c.lower().startswith("chr") else c


def decon_sample(name):
    """DECoN Sample column is the BAM basename without .bam: 'Male23-TwistMy.final'."""
    return name[:-6] if name.endswith(".final") else name


# --------------------------------------------------------------------------
# inputs
# --------------------------------------------------------------------------

def load_exons(path):
    """paralog_limited_exons.tsv (annotated or not). BED-style 0-based start."""
    by_chrom = collections.defaultdict(list)
    with open(path) as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        need = ["chrom", "start", "end", "name", "median_depth_mq20", "flag"]
        for col in need:
            if col not in reader.fieldnames:
                raise SystemExit("[error] exon table lacks column '{}'".format(col))
        for row in reader:
            by_chrom[norm_chrom(row["chrom"])].append({
                "start": int(row["start"]),
                "end": int(row["end"]),
                "name": row["name"],
                "depth": float(row["median_depth_mq20"]),
                "flag": row["flag"],
            })
    n = sum(len(v) for v in by_chrom.values())
    return by_chrom, n


def load_variants(path, min_vaf, verdicts):
    """somaticseq.filtered.tsv: Chr, Start, End, Ref, Alt, VAF_pct, SomaticSeq_Verdict."""
    out = collections.defaultdict(list)
    with open(path) as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        need = ["Chr", "Start", "End", "Ref", "Alt", "VAF_pct", "SomaticSeq_Verdict"]
        for col in need:
            if col not in reader.fieldnames:
                raise SystemExit("[error] variant table {} lacks column '{}'".format(path, col))
        for row in reader:
            if row["SomaticSeq_Verdict"] not in verdicts:
                continue
            try:
                vaf = float(row["VAF_pct"])
            except ValueError:
                continue
            if vaf < min_vaf:
                continue
            out[norm_chrom(row["Chr"])].append({
                "start": int(row["Start"]),
                "end": int(row["End"]),
                "label": "{}:{} {}>{} VAF {:.1f}".format(row["Chr"], row["Start"],
                                                        row["Ref"], row["Alt"], vaf),
            })
    return out


# --------------------------------------------------------------------------
# classification
# --------------------------------------------------------------------------

def overlapping_exons(exons_by_chrom, chrom, start, end):
    """DECoN Start/End are 1-based inclusive; exon table is BED (0-based, half-open)."""
    hits = []
    for e in exons_by_chrom.get(norm_chrom(chrom), []):
        if start <= e["end"] and end >= e["start"] + 1:
            hits.append(e)
    return hits


def variants_in_call(variants_by_chrom, chrom, start, end, flank):
    hits = []
    for v in variants_by_chrom.get(norm_chrom(chrom), []):
        if v["start"] <= end + flank and v["end"] >= start - flank:
            hits.append(v["label"])
    return hits


def classify(bf, n_exons, exon_hits, variant_hits, args):
    flags = sorted(set(e["flag"] for e in exon_hits if e["flag"] != "OK"))
    min_depth = min((e["depth"] for e in exon_hits), default=float("nan"))

    if bf < args.bf:
        return "BELOW_BF", False, flags, min_depth
    if n_exons > 1:
        return "PASS", True, flags, min_depth
    if "PARALOG_LIMITED" in flags:
        return "PARALOG_EXON", False, flags, min_depth
    if variant_hits:
        return "PROBE_VARIANT", False, flags, min_depth
    if "LOW_DEPTH" in flags or (min_depth == min_depth and min_depth < args.low_power_depth):
        return "LOW_POWER_EXON", bf >= args.low_power_bf, flags, min_depth
    return "PASS", True, flags, min_depth


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--calls", required=True, help="DECoN *calls_all.txt")
    p.add_argument("--exons", required=True, help="paralog_limited_exons.tsv")
    p.add_argument("--variants-pattern",
                   help="path pattern with {sample}, e.g. "
                        "'/outdir/{sample}/clinical/{sample}.somaticseq.filtered.tsv'")
    p.add_argument("--out", required=True)
    p.add_argument("--bf", type=float, default=12.0, help="reporting threshold (default 12)")
    p.add_argument("--low-power-depth", type=float, default=300.0,
                   help="exon median MAPQ>=20 depth below this = LOW_POWER_EXON (default 300)")
    p.add_argument("--low-power-bf", type=float, default=20.0,
                   help="BF required to report a single-exon call in a low-power exon (default 20)")
    p.add_argument("--variant-min-vaf", type=float, default=30.0,
                   help="VAF_pct at or above which a sample variant counts (default 30)")
    p.add_argument("--variant-verdicts", default="PASS",
                   help="comma-separated SomaticSeq_Verdict values to consider (default PASS)")
    p.add_argument("--variant-flank", type=int, default=0,
                   help="bp beyond the call interval to search for probe variants (default 0)")
    p.add_argument("--reportable-only", action="store_true")
    args = p.parse_args()

    for f in (args.calls, args.exons):
        if not os.path.isfile(f):
            raise SystemExit("[error] missing: {}".format(f))
    exons_by_chrom, n_exons_loaded = load_exons(args.exons)
    log("ok", "{} exons from {}".format(n_exons_loaded, os.path.basename(args.exons)))
    verdicts = set(v.strip() for v in args.variant_verdicts.split(",") if v.strip())

    with open(args.calls) as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        fields = reader.fieldnames
        for col in ["Sample", "N.exons", "Start", "End", "Chromosome", "BF", "Gene"]:
            if col not in fields:
                raise SystemExit("[error] calls file lacks column '{}'".format(col))
        calls = list(reader)
    log("ok", "{} calls from {}".format(len(calls), os.path.basename(args.calls)))

    variant_cache = {}
    missing_variant_tables = set()

    def variants_for(sample):
        if sample in variant_cache:
            return variant_cache[sample]
        if not args.variants_pattern:
            variant_cache[sample] = None
            return None
        path = args.variants_pattern.format(sample=sample)
        if not os.path.isfile(path):
            missing_variant_tables.add(sample)
            variant_cache[sample] = None
            return None
        variant_cache[sample] = load_variants(path, args.variant_min_vaf, verdicts)
        return variant_cache[sample]

    extra = ["exon_names", "exon_min_depth_mq20", "exon_flags", "variants_in_call",
             "decision", "reportable"]
    out_fields = fields + extra
    counts = collections.Counter()
    reportable_rows = []

    with open(args.out, "w") as fh:
        fh.write("\t".join(out_fields) + "\n")
        for row in calls:
            sample = decon_sample(row["Sample"])
            chrom = row["Chromosome"]
            start = int(float(row["Start"]))
            end = int(float(row["End"]))
            n_ex = int(float(row["N.exons"]))
            bf = float(row["BF"])

            exon_hits = overlapping_exons(exons_by_chrom, chrom, start, end)
            vtab = variants_for(sample)
            variant_hits = variants_in_call(vtab, chrom, start, end, args.variant_flank) if vtab else []

            decision, reportable, flags, min_depth = classify(bf, n_ex, exon_hits, variant_hits, args)
            counts[decision] += 1
            if reportable:
                reportable_rows.append((sample, row["Gene"], row["CNV.type"], n_ex, bf, decision))
            if args.reportable_only and not reportable:
                continue
            vals = [row[f] for f in fields] + [
                ";".join(e["name"] for e in exon_hits) or "NA",
                "{:.1f}".format(min_depth) if min_depth == min_depth else "NA",
                ";".join(flags) or "-",
                ";".join(variant_hits) or "-",
                decision,
                "yes" if reportable else "no",
            ]
            fh.write("\t".join(str(v) for v in vals) + "\n")

    log("done", "wrote {}".format(args.out))
    log("summary", "  ".join("{}={}".format(k, counts[k]) for k in
                             ["PASS", "BELOW_BF", "LOW_POWER_EXON", "PARALOG_EXON", "PROBE_VARIANT"]))
    log("summary", "reportable calls: {}".format(len(reportable_rows)))
    for sample, gene, cnvtype, n_ex, bf, decision in sorted(reportable_rows, key=lambda x: -x[4]):
        log("report", "{:<22s} {:<26s} {:<12s} exons={:<3d} BF={:<6.1f} {}".format(
            sample, gene, cnvtype, n_ex, bf, decision))
    if missing_variant_tables:
        log("warn", "no variant table for {} sample(s): {}".format(
            len(missing_variant_tables), ", ".join(sorted(missing_variant_tables))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
