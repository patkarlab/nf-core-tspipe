#!/usr/bin/env python3
"""
sex_check.py (SEX_CHECK_V2) -- infer sample sex from two votes.

Vote 1, heterozygosity (decides when available): allelic counts at the
panel het catalog sites (het_catalog.tsv). A male has no heterozygous
sites on chrX outside the PAR; a female has about the autosomal het
fraction. Calibrated on tspipe_run8 (2026-09-07, 76 chrX sites, depth
>= 30): males 0.000-0.013, females 0.38-0.43, autosomal 0.40-0.44.
Immune to chrX copy number in the tumour: a male +X keeps zero het sites.
The vote is trusted only when the autosomal het fraction is itself normal
(>= --auto-het-min); otherwise AUTOSOMAL_HET_LOW is flagged and the depth
vote decides.

Vote 2, depth (confirms; decides when vote 1 is unavailable): mosdepth
per-region depth, median chrX over median autosomal, each region
normalised within its own class (exon target vs backbone tile), PAR
excluded. X/A ~0.5 male, ~1.0 female. A somatic chrX gain or loss moves
this ratio: 26CGH1250 (male, +X at 65 percent purity) reads X/A 0.898.

When both votes are present and disagree, the het vote decides and
X_DEPTH_CONFLICT is flagged.

resolved_sex is what the workflow may write into meta.sex: the
samplesheet value when it is male/female, otherwise the inference.
A MISMATCH between sheet and inference never overrides the sheet.

Output is a one-row TSV: the sixteen SEX_CHECK_V1 columns unchanged,
then method, het_inferred_sex, depth_inferred_sex, x_het_frac,
auto_het_frac, n_x_het_sites, n_auto_het_sites.

Python 3.6 compatible (GATK 4.5 container). Standard library only.
"""

import argparse
import gzip
import json
import re
import sys

AUTOSOMES = set("chr%d" % i for i in range(1, 23))
PAR_HG38 = {
    "chrX": [(10001, 2781479), (155701383, 156030895)],
    "chrY": [(10001, 2781479), (56887903, 57217415)],
}
BACKBONE_RE = re.compile(r"^(bb\.|CNVbb|CNV_?backbone)", re.IGNORECASE)

COLUMNS = [
    "sample", "sheet_sex", "inferred_sex", "resolved_sex", "status",
    "x_auto_ratio", "y_auto_ratio", "y_status", "n_auto", "n_x", "n_y",
    "auto_median_exon", "auto_median_backbone", "n_par_excluded",
    "n_noncanonical_skipped", "flags",
    "method", "het_inferred_sex", "depth_inferred_sex",
    "x_het_frac", "auto_het_frac", "n_x_het_sites", "n_auto_het_sites",
]


def median(values):
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2.0


def in_par(chrom, start, end):
    for lo, hi in PAR_HG38.get(chrom, []):
        if start < hi and end > lo:
            return True
    return False


def fmt(v):
    return "NA" if v is None else "%.3f" % v


# ---------------------------------------------------------------------------
# Vote 2: depth (SEX_CHECK_V1 method, unchanged)
# ---------------------------------------------------------------------------

def read_regions(path):
    """Yield (chrom, start, end, name, depth) from mosdepth regions.bed.gz.

    mosdepth writes 4 columns (no BED name) or 5 columns (name in col 4).
    """
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt") as fh:
        for line in fh:
            if not line.strip() or line.startswith("#"):
                continue
            p = line.rstrip("\n").split("\t")
            if len(p) < 4:
                continue
            chrom = p[0]
            try:
                start, end = int(p[1]), int(p[2])
            except ValueError:
                continue
            if len(p) >= 5:
                name, depth_s = p[3], p[4]
            else:
                name, depth_s = "", p[3]
            try:
                depth = float(depth_s)
            except ValueError:
                continue
            yield chrom, start, end, name, depth


def classify_region(name):
    return "backbone" if BACKBONE_RE.match(name or "") else "exon"


def depth_vote(args):
    """Return a dict with the depth-vote fields and its own flags."""
    per_class = {"exon": {"auto": [], "chrX": [], "chrY": []},
                 "backbone": {"auto": [], "chrX": [], "chrY": []}}
    n_par_excluded = 0
    n_noncanonical = 0

    for chrom, start, end, name, depth in read_regions(args.regions):
        if chrom in AUTOSOMES:
            key = "auto"
        elif chrom in ("chrX", "chrY"):
            if in_par(chrom, start, end):
                n_par_excluded += 1
                continue
            key = chrom
        else:
            n_noncanonical += 1
            continue
        per_class[classify_region(name)][key].append(depth)

    class_auto_median = {}
    for cls, d in per_class.items():
        m = median(d["auto"])
        if m is not None and len(d["auto"]) >= args.min_auto_regions and m >= args.min_depth:
            class_auto_median[cls] = m

    norm_x, norm_y = [], []
    n_auto = 0
    for cls, m in class_auto_median.items():
        n_auto += len(per_class[cls]["auto"])
        norm_x.extend(v / m for v in per_class[cls]["chrX"])
        norm_y.extend(v / m for v in per_class[cls]["chrY"])

    x_ratio = median(norm_x)
    y_ratio = median(norm_y)
    n_x, n_y = len(norm_x), len(norm_y)
    flags = []

    if not class_auto_median:
        inferred = "indeterminate"
        flags.append("NO_USABLE_CLASS")
    elif n_x < args.min_x_regions:
        inferred = "indeterminate"
        flags.append("TOO_FEW_CHRX_REGIONS")
    elif x_ratio <= args.x_male_max:
        inferred = "male"
    elif x_ratio >= args.x_female_min:
        inferred = "female"
    else:
        inferred = "indeterminate"
        flags.append("CHRX_RATIO_AMBIGUOUS")

    if n_y < args.min_y_regions:
        y_status = "NA"
    elif y_ratio >= args.y_present_min:
        y_status = "PRESENT"
    elif y_ratio < args.y_absent_max:
        y_status = "ABSENT"
    else:
        y_status = "AMBIGUOUS"

    return {
        "inferred": inferred, "flags": flags,
        "x_ratio": x_ratio, "y_ratio": y_ratio, "y_status": y_status,
        "n_auto": n_auto, "n_x": n_x, "n_y": n_y,
        "auto_median_exon": class_auto_median.get("exon"),
        "auto_median_backbone": class_auto_median.get("backbone"),
        "n_par_excluded": n_par_excluded, "n_noncanonical": n_noncanonical,
    }


# ---------------------------------------------------------------------------
# Vote 1: heterozygosity at the het catalog sites
# ---------------------------------------------------------------------------

def read_het_catalog(path):
    """Set of (chrom, pos) from het_catalog.tsv (header: chrom pos ...)."""
    sites = set()
    with open(path) as fh:
        header = None
        for line in fh:
            if not line.strip() or line.startswith("#"):
                continue
            p = line.rstrip("\n").split("\t")
            if header is None:
                header = p
                if p[0] == "chrom":
                    continue
            try:
                sites.add((p[0], int(p[1])))
            except (ValueError, IndexError):
                continue
    return sites


def read_allelic_counts(path):
    """Yield (chrom, pos, ref_count, alt_count) from GATK CollectAllelicCounts."""
    with open(path) as fh:
        for line in fh:
            if not line.strip() or line.startswith("@") or line.startswith("CONTIG"):
                continue
            p = line.rstrip("\n").split("\t")
            if len(p) < 4:
                continue
            try:
                yield p[0], int(p[1]), int(p[2]), int(p[3])
            except ValueError:
                continue


def het_vote(args):
    """Return a dict with the het-vote fields and its own flags."""
    flags = []
    out = {"inferred": "NA", "x_het": None, "auto_het": None,
           "n_x_sites": 0, "n_auto_sites": 0, "flags": flags}
    if not (args.allelic_counts and args.het_catalog):
        flags.append("HET_VOTE_UNAVAILABLE")
        return out

    catalog = read_het_catalog(args.het_catalog)
    nx = hx = na = ha = 0
    for chrom, pos, ref_c, alt_c in read_allelic_counts(args.allelic_counts):
        if (chrom, pos) not in catalog:
            continue
        if chrom == "chrX":
            if in_par(chrom, pos - 1, pos):
                continue
        elif chrom not in AUTOSOMES:
            continue
        dp = ref_c + alt_c
        if dp < args.het_min_depth:
            continue
        f = alt_c / float(dp)
        het = 1 if (args.het_af_lo < f < args.het_af_hi) else 0
        if chrom == "chrX":
            nx += 1
            hx += het
        else:
            na += 1
            ha += het

    x_het = hx / float(nx) if nx else None
    auto_het = ha / float(na) if na else None
    out.update({"x_het": x_het, "auto_het": auto_het,
                "n_x_sites": nx, "n_auto_sites": na})

    if nx < args.min_het_sites:
        out["inferred"] = "indeterminate"
        flags.append("TOO_FEW_HET_SITES")
    elif auto_het is None or auto_het < args.auto_het_min:
        out["inferred"] = "indeterminate"
        flags.append("AUTOSOMAL_HET_LOW")
    elif x_het <= args.x_het_male_max:
        out["inferred"] = "male"
    elif x_het >= args.x_het_female_min:
        out["inferred"] = "female"
    else:
        out["inferred"] = "indeterminate"
        flags.append("CHRX_HET_AMBIGUOUS")
    return out


# ---------------------------------------------------------------------------
# Combine
# ---------------------------------------------------------------------------

def run(args):
    d = depth_vote(args)
    h = het_vote(args)
    flags = list(h["flags"]) + list(d["flags"])

    if h["inferred"] in ("male", "female"):
        inferred = h["inferred"]
        method = "heterozygosity"
        if d["inferred"] in ("male", "female") and d["inferred"] != inferred:
            flags.append("X_DEPTH_CONFLICT")
    elif d["inferred"] in ("male", "female"):
        inferred = d["inferred"]
        method = "depth"
    else:
        inferred = "indeterminate"
        method = "none"

    if inferred == "male" and d["y_status"] == "ABSENT":
        flags.append("Y_DEPLETED")
    if inferred == "female" and d["y_status"] == "PRESENT":
        flags.append("Y_UNEXPECTED")

    sheet = (args.sheet_sex or "unknown").strip().lower()
    if sheet not in ("male", "female"):
        sheet = "unknown"

    if inferred == "indeterminate":
        status = "INDETERMINATE"
    elif sheet == "unknown":
        status = "SHEET_UNKNOWN"
    elif sheet == inferred:
        status = "CONCORDANT"
    else:
        status = "MISMATCH"

    if sheet in ("male", "female"):
        resolved = sheet
    elif inferred in ("male", "female"):
        resolved = inferred
    else:
        resolved = "unknown"

    row = {
        "sample": args.sample,
        "sheet_sex": sheet,
        "inferred_sex": inferred,
        "resolved_sex": resolved,
        "status": status,
        "x_auto_ratio": fmt(d["x_ratio"]),
        "y_auto_ratio": fmt(d["y_ratio"]),
        "y_status": d["y_status"],
        "n_auto": str(d["n_auto"]),
        "n_x": str(d["n_x"]),
        "n_y": str(d["n_y"]),
        "auto_median_exon": fmt(d["auto_median_exon"]),
        "auto_median_backbone": fmt(d["auto_median_backbone"]),
        "n_par_excluded": str(d["n_par_excluded"]),
        "n_noncanonical_skipped": str(d["n_noncanonical"]),
        "flags": ";".join(flags) if flags else ".",
        "method": method,
        "het_inferred_sex": h["inferred"],
        "depth_inferred_sex": d["inferred"],
        "x_het_frac": fmt(h["x_het"]),
        "auto_het_frac": fmt(h["auto_het"]),
        "n_x_het_sites": str(h["n_x_sites"]),
        "n_auto_het_sites": str(h["n_auto_sites"]),
    }
    write_row(args, row)

    sys.stderr.write("[sex_check] %s sheet=%s inferred=%s (method=%s; het=%s X_het=%s auto_het=%s nX=%d; "
                     "depth=%s X/A=%s Y/A=%s %s) resolved=%s status=%s flags=%s\n"
                     % (args.sample, sheet, inferred, method, h["inferred"], row["x_het_frac"],
                        row["auto_het_frac"], h["n_x_sites"], d["inferred"], row["x_auto_ratio"],
                        row["y_auto_ratio"], d["y_status"], resolved, status, row["flags"]))
    return 0


def write_row(args, row):
    with open(args.out, "w") as out:
        out.write("\t".join(COLUMNS) + "\n")
        out.write("\t".join(row[c] for c in COLUMNS) + "\n")
    if args.json:
        with open(args.json, "w") as jf:
            json.dump(row, jf, indent=2)
            jf.write("\n")


def error_row(args, exc):
    sheet = (args.sheet_sex or "unknown").strip().lower()
    if sheet not in ("male", "female"):
        sheet = "unknown"
    row = dict((c, "NA") for c in COLUMNS)
    row.update({
        "sample": args.sample, "sheet_sex": sheet, "inferred_sex": "indeterminate",
        "resolved_sex": sheet, "status": "INDETERMINATE",
        "n_auto": "0", "n_x": "0", "n_y": "0", "n_par_excluded": "0",
        "n_noncanonical_skipped": "0", "method": "none",
        "n_x_het_sites": "0", "n_auto_het_sites": "0",
        "flags": "ERROR:%s" % str(exc).replace("\t", " ").replace("\n", " "),
    })
    write_row(args, row)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--regions", required=True, help="mosdepth <sample>.regions.bed.gz")
    ap.add_argument("--sample", required=True)
    ap.add_argument("--sheet-sex", default="unknown", help="samplesheet value: male|female|unknown")
    ap.add_argument("--out", required=True, help="output TSV (one row)")
    ap.add_argument("--json", default=None, help="optional JSON copy of the row")
    # vote 1: heterozygosity
    ap.add_argument("--allelic-counts", default=None,
                    help="GATK CollectAllelicCounts TSV at the het catalog sites (enables vote 1)")
    ap.add_argument("--het-catalog", default=None, help="het_catalog.tsv (chrom, pos, ...)")
    ap.add_argument("--het-min-depth", type=int, default=30,
                    help="minimum ref+alt depth for a catalog site to count (default 30)")
    ap.add_argument("--het-af-lo", type=float, default=0.15, help="het if AF > this (default 0.15)")
    ap.add_argument("--het-af-hi", type=float, default=0.85, help="het if AF < this (default 0.85)")
    ap.add_argument("--min-het-sites", type=int, default=20,
                    help="minimum chrX catalog sites at depth for the het vote (default 20)")
    ap.add_argument("--x-het-male-max", type=float, default=0.10,
                    help="chrX het fraction at or below this is male (default 0.10)")
    ap.add_argument("--x-het-female-min", type=float, default=0.25,
                    help="chrX het fraction at or above this is female (default 0.25)")
    ap.add_argument("--auto-het-min", type=float, default=0.25,
                    help="autosomal het fraction below this invalidates the het vote (default 0.25)")
    # vote 2: depth
    ap.add_argument("--min-depth", type=float, default=20.0,
                    help="minimum class autosomal median depth to use that class (default 20)")
    ap.add_argument("--min-auto-regions", type=int, default=50)
    ap.add_argument("--min-x-regions", type=int, default=10)
    ap.add_argument("--min-y-regions", type=int, default=5)
    ap.add_argument("--x-male-max", type=float, default=0.70)
    ap.add_argument("--x-female-min", type=float, default=0.80)
    ap.add_argument("--y-present-min", type=float, default=0.15)
    ap.add_argument("--y-absent-max", type=float, default=0.05)
    args = ap.parse_args()
    try:
        rc = run(args)
    except Exception as exc:  # never fail the sample: emit an indeterminate row
        error_row(args, exc)
        sys.stderr.write("[sex_check] ERROR %s: %s (wrote indeterminate row)\n" % (args.sample, exc))
        rc = 0
    sys.exit(rc)


if __name__ == "__main__":
    main()
