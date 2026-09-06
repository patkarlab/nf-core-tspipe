#!/usr/bin/env python3
"""
sex_check.py -- infer sample sex from mosdepth per-region depth.

Input is the mosdepth regions.bed.gz produced by MOSDEPTH (--by panel BED,
--mapq 20, --flag 772). Every region's mean depth is normalised to the
autosomal median of its own region class (exon target or CNV backbone
tile), then the chrX and chrY medians of those normalised depths give the
X/A and Y/A ratios. Expected: X/A ~0.5 male, ~1.0 female; Y/A ~0.5 male,
~0 female. Pseudoautosomal regions are excluded on both chromosomes.

Output is a one-row TSV. resolved_sex is what the workflow may write into
meta.sex: the samplesheet value when it is male/female, otherwise the
inference. A MISMATCH between sheet and inference never overrides the sheet.

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


def run(args):
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

    # Per-class autosomal medians; a class is usable only if it has enough
    # autosomal regions at adequate depth.
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

    if inferred == "male" and y_status == "ABSENT":
        flags.append("Y_DEPLETED")
    if inferred == "female" and y_status == "PRESENT":
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

    def fmt(v):
        return "NA" if v is None else "%.3f" % v

    row = [
        ("sample", args.sample),
        ("sheet_sex", sheet),
        ("inferred_sex", inferred),
        ("resolved_sex", resolved),
        ("status", status),
        ("x_auto_ratio", fmt(x_ratio)),
        ("y_auto_ratio", fmt(y_ratio)),
        ("y_status", y_status),
        ("n_auto", str(n_auto)),
        ("n_x", str(n_x)),
        ("n_y", str(n_y)),
        ("auto_median_exon", fmt(class_auto_median.get("exon"))),
        ("auto_median_backbone", fmt(class_auto_median.get("backbone"))),
        ("n_par_excluded", str(n_par_excluded)),
        ("n_noncanonical_skipped", str(n_noncanonical)),
        ("flags", ";".join(flags) if flags else "."),
    ]
    with open(args.out, "w") as out:
        out.write("\t".join(k for k, _ in row) + "\n")
        out.write("\t".join(v for _, v in row) + "\n")

    if args.json:
        with open(args.json, "w") as jf:
            json.dump(dict(row), jf, indent=2)
            jf.write("\n")

    sys.stderr.write("[sex_check] %s sheet=%s inferred=%s resolved=%s status=%s "
                     "X/A=%s Y/A=%s (%s) nX=%d nY=%d flags=%s\n"
                     % (args.sample, sheet, inferred, resolved, status,
                        fmt(x_ratio), fmt(y_ratio), y_status, n_x, n_y,
                        ";".join(flags) or "."))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--regions", required=True, help="mosdepth <sample>.regions.bed.gz")
    ap.add_argument("--sample", required=True)
    ap.add_argument("--sheet-sex", default="unknown", help="samplesheet value: male|female|unknown")
    ap.add_argument("--out", required=True, help="output TSV (one row)")
    ap.add_argument("--json", default=None, help="optional JSON copy of the row")
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
    except Exception as exc:  # never fail the sample: emit an 'unknown' row
        sheet = (args.sheet_sex or "unknown").strip().lower()
        if sheet not in ("male", "female"):
            sheet = "unknown"
        cols = ["sample", "sheet_sex", "inferred_sex", "resolved_sex", "status",
                "x_auto_ratio", "y_auto_ratio", "y_status", "n_auto", "n_x", "n_y",
                "auto_median_exon", "auto_median_backbone", "n_par_excluded",
                "n_noncanonical_skipped", "flags"]
        vals = [args.sample, sheet, "indeterminate", sheet, "INDETERMINATE",
                "NA", "NA", "NA", "0", "0", "0", "NA", "NA", "0", "0",
                "ERROR:%s" % str(exc).replace("\t", " ").replace("\n", " ")]
        with open(args.out, "w") as out:
            out.write("\t".join(cols) + "\n")
            out.write("\t".join(vals) + "\n")
        sys.stderr.write("[sex_check] ERROR %s: %s (wrote indeterminate row)\n" % (args.sample, exc))
        rc = 0
    sys.exit(rc)


if __name__ == "__main__":
    main()
