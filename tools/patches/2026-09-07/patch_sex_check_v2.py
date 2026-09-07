#!/usr/bin/env python3
"""
patch_sex_check_v2.py -- SEX_CHECK_V2: chrX heterozygosity as the deciding sex vote.

Why: 26CGH1250 (male, +X hyperdiploid B-ALL at 65 percent purity) reads X/A 0.898
and was called female by the depth-only SEX_CHECK_V1, so every CNV arm used the
female stratum and chrX was wrong across the board. Calibration on tspipe_run8
(2026-09-07, 76 chrX catalog sites at depth >= 30): males 0.000-0.013 chrX het
fraction, females 0.38-0.43, autosomal 0.40-0.44; 1250 = 0.000.

What changes (all-or-nothing):
  modules/local/sex_check.nf          rewritten: BAM + reference + het catalog inputs,
                                      CollectAllelicCounts at the catalog sites in the
                                      GATK container, optional allelic-counts output
  bin/sex_check.py                    rewritten: het vote decides, depth vote confirms,
                                      X_DEPTH_CONFLICT / AUTOSOMAL_HET_LOW flags, seven
                                      new trailing columns (existing 16 unchanged)
  subworkflows/local/preprocessing.nf anchor edits: het catalog resolution, SEX_CHECK
                                      call on regions joined with ABRA2 BAM, log lines
  conf/modules.config                 anchor edit: publish the allelic counts beside
                                      the sex_check TSV
  docs/sops/sex_check.md              rewritten SOP

Dry run by default; --apply writes. Every guard and anchor is validated before any
file is touched. Backups: <file>.bak_sexcheck_v2_<timestamp>. Idempotent: files
already carrying MARKER SEX_CHECK_V2 are skipped.
"""

import argparse
import os
import re
import stat
import sys
import time

MARKER = "SEX_CHECK_V2"
TAG = "sexcheck_v2"

# ---------------------------------------------------------------------------
# Full-file payloads
# ---------------------------------------------------------------------------

NEW_SEX_CHECK_NF = r'''/*
 * modules/local/sex_check.nf  (SEX_CHECK_V2; supersedes SEX_CHECK_V1)
 *
 * Two votes on sample sex, both computed here so meta.sex is resolved before
 * any CNV arm runs.
 *
 *   1. Heterozygosity (decides): GATK CollectAllelicCounts on the final BAM at
 *      the panel het catalog sites (assets/<panel>/het_catalog.tsv, v2). A male
 *      has no heterozygous chrX sites outside the PAR whatever the tumour does
 *      to chrX copy number; a female has about the autosomal het fraction.
 *   2. Depth (confirms): mosdepth per-region chrX/autosome ratio, per region
 *      class, PAR excluded (the SEX_CHECK_V1 method). A somatic chrX gain or
 *      loss moves this ratio; disagreement with vote 1 is X_DEPTH_CONFLICT.
 *
 * Panels without a het catalog stage [] and keep the depth-only inference.
 * Samplesheet male/female always wins; 'unknown' takes the inference; a
 * MISMATCH is flagged, never applied. Output <sample>.sex_check.tsv keeps the
 * sixteen V1 columns and appends seven.
 *
 * Container: GATK image (CollectAllelicCounts + Python 3.6); bin/sex_check.py
 * is stdlib only.
 */

process SEX_CHECK {
    tag        "${meta.id}"
    label      'process_low'
    container  'docker://broadinstitute/gatk:4.5.0.0'

    input:
        tuple val(meta),
              path(regions),
              path(regions_csi),
              path(thresholds),
              path(thresholds_csi),
              path(bam),
              path(bai)
        tuple path(fasta), path(fai), path(dict)
        path het_catalog

    output:
        tuple val(meta), path("${meta.id}.sex_check.tsv"), emit: tsv
        path "${meta.id}.sexcheck.allelicCounts.tsv", optional: true, emit: allelic
        path "versions.yml", emit: versions

    stub:
        def sheet_sex = meta.sex ?: 'unknown'
        """
        printf 'sample\\tsheet_sex\\tinferred_sex\\tresolved_sex\\tstatus\\tx_auto_ratio\\ty_auto_ratio\\ty_status\\tn_auto\\tn_x\\tn_y\\tauto_median_exon\\tauto_median_backbone\\tn_par_excluded\\tn_noncanonical_skipped\\tflags\\tmethod\\thet_inferred_sex\\tdepth_inferred_sex\\tx_het_frac\\tauto_het_frac\\tn_x_het_sites\\tn_auto_het_sites\\n' > ${meta.id}.sex_check.tsv
        printf '${meta.id}\\t${sheet_sex}\\tindeterminate\\t${sheet_sex}\\tSTUB\\tNA\\tNA\\tNA\\t0\\t0\\t0\\tNA\\tNA\\t0\\t0\\tstub\\tnone\\tNA\\tNA\\tNA\\tNA\\t0\\t0\\n' >> ${meta.id}.sex_check.tsv
        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            stub: true
        END_VERSIONS
        """

    script:
        def sheet_sex = meta.sex ?: 'unknown'
        def xmx       = task.memory ? Math.max(2, task.memory.toGiga() - 2) : 4
        def ac        = "${meta.id}.sexcheck.allelicCounts.tsv"
        def het_cmd   = het_catalog ? """awk -F'\\t' 'NR > 1 { printf "%s\\t%d\\t%s\\n", \$1, \$2 - 1, \$2 }' ${het_catalog} > sexcheck_sites.bed
        gatk --java-options "-Xmx${xmx}g" CollectAllelicCounts \\
            -I ${bam} \\
            -L sexcheck_sites.bed \\
            -R ${fasta} \\
            -O ${ac}
        n_sites=\$(grep -vc '^@' ${ac})
        echo "[sex_check] ${meta.id}: \$n_sites allelic-count records at het catalog sites (incl. header)"
        """ : "echo '[sex_check] ${meta.id}: no het catalog staged; depth vote only'"
        def het_args  = het_catalog ? "--allelic-counts ${ac} --het-catalog ${het_catalog}" : ''
        """
        ${het_cmd}

        sex_check.py \\
            --regions ${regions} \\
            --sample ${meta.id} \\
            --sheet-sex ${sheet_sex} \\
            ${het_args} \\
            --out ${meta.id}.sex_check.tsv

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            python: \$(python3 --version 2>&1 | awk '{print \$2}')
            gatk: \$(gatk --version 2>&1 | grep -m1 -oE '[0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+' || echo unknown)
        END_VERSIONS
        """
}
'''

NEW_SEX_CHECK_PY = r'''#!/usr/bin/env python3
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
'''

NEW_SOP = r'''# SOP: SEX_CHECK (V2) -- sample sex inference

Module `modules/local/sex_check.nf`, script `bin/sex_check.py`, wired in
`subworkflows/local/preprocessing.nf` (MARKER SEX_CHECK_V1 / SEX_CHECK_V2).
Runs once per sample after MOSDEPTH and ABRA2, before any CNV arm, and
writes `<outdir>/<sample>/sex_check/<sample>.sex_check.tsv` (one row) plus
`<sample>.sexcheck.allelicCounts.tsv` when a het catalog exists.

## Inputs

- mosdepth `regions.bed.gz` (exon-collapsed BED, `--mapq 20 --flag 772`).
- Final BAM (ABRA2) with index; reference FASTA, .fai, .dict.
- Het catalog `assets/<panel>/het_catalog.tsv` (columns `chrom pos ref alt
  n_het n_het_male n_het_female median_af source`). Override with
  `--sex_check_het_catalog <path>`. A panel without the file stages `[]`
  and gets the depth-only inference with `HET_VOTE_UNAVAILABLE`.

## Two votes

1. Heterozygosity (decides). `gatk CollectAllelicCounts` at every catalog
   position (single-base BED built in the task). At sites with ref+alt
   depth >= 30 a site is heterozygous if 0.15 < AF < 0.85. chrX het
   fraction (PAR excluded) <= 0.10 male, >= 0.25 female, between
   `CHRX_HET_AMBIGUOUS`. Needs >= 20 chrX sites at depth
   (`TOO_FEW_HET_SITES`) and an autosomal het fraction >= 0.25
   (`AUTOSOMAL_HET_LOW`, e.g. contamination or a bad library); either
   failure hands the decision to the depth vote.
2. Depth (confirms). Median chrX depth over median autosomal depth per
   region class, PAR excluded: X/A <= 0.70 male, >= 0.80 female, between
   `CHRX_RATIO_AMBIGUOUS`. chrY is used where the BED has it (the Twist
   myeloid BED has none, so `y_status` is NA).

When both votes are present and disagree the het vote wins and
`X_DEPTH_CONFLICT` is set: the usual cause is a somatic chrX gain or loss
(26CGH1250, male +X hyperdiploid B-ALL, X/A 0.898, chrX het 0.000).

Calibration, tspipe_run8, 2026-09-07 (76 chrX sites, depth >= 30):
males 0.000-0.013, females 0.382-0.434, autosomal 0.400-0.437.

## Resolution into meta.sex

`resolved_sex` = samplesheet value if male/female, else the inference.
Samplesheet always wins; `MISMATCH` is logged (`log.warn`) and flagged,
never applied. `X_DEPTH_CONFLICT` is logged as a warning with both votes.
Every downstream channel from PREPROCESSING carries the resolved meta.sex;
CNVkit, GATK, PureCN, DECoN, PURPLE and the consensus select the stratum
from it (`params.cnv_sex_fallback` for anything else).

## Columns

V1 (unchanged): sample, sheet_sex, inferred_sex, resolved_sex, status,
x_auto_ratio, y_auto_ratio, y_status, n_auto, n_x, n_y, auto_median_exon,
auto_median_backbone, n_par_excluded, n_noncanonical_skipped, flags.
V2 (appended): method (heterozygosity | depth | none), het_inferred_sex,
depth_inferred_sex, x_het_frac, auto_het_frac, n_x_het_sites,
n_auto_het_sites.

## Checks after a run

    awk -F'\t' 'FNR==2' <outdir>/*/sex_check/*.sex_check.tsv | cut -f1-5,16,17,20,21

Any `X_DEPTH_CONFLICT` should correspond to a chrX call in the CNV
consensus; any `AUTOSOMAL_HET_LOW` needs a look at contamination before
the sample's CNV results are read.

## Standalone use

    python3 bin/sex_check.py --regions <sample>.regions.bed.gz \
        --allelic-counts <counts.tsv> --het-catalog assets/twist_myeloid/het_catalog.tsv \
        --sample <id> --sheet-sex unknown --out <id>.sex_check.tsv

Any CollectAllelicCounts file covering the catalog positions works
(the GATK_CNV_COLLECT_ALLELIC output does).

## History

- SEX_CHECK_V1 (2026-09-06): depth-only. Failed on 26CGH1250 (see above).
- SEX_CHECK_V2 (2026-09-07): heterozygosity vote added and made decisive;
  patcher `tools/patches/2026-09-07/patch_sex_check_v2.py`.
'''

# ---------------------------------------------------------------------------
# Anchor edits
# ---------------------------------------------------------------------------

PREPROC_EDITS = [
    (
        "SEX_CHECK call",
        """        // MARKER SEX_CHECK_V1: sex from the mosdepth regions (X/A ratio); one row per sample.
        // resolved_sex = sheet value if male/female, else the inference.
        SEX_CHECK(MOSDEPTH.out.regions_thresholds)
""",
        """        // MARKER SEX_CHECK_V1: sex from the mosdepth regions (X/A ratio); one row per sample.
        // resolved_sex = sheet value if male/female, else the inference.
        // MARKER SEX_CHECK_V2: chrX heterozygosity at the panel het catalog is the deciding
        // vote (CollectAllelicCounts inside SEX_CHECK on the final BAM); X/A confirms or
        // raises X_DEPTH_CONFLICT. Panels without assets/<panel>/het_catalog.tsv stage []
        // and keep the depth-only inference.
        def sex_het_catalog_path = (params.containsKey('sex_check_het_catalog') && params.sex_check_het_catalog)
            ? params.sex_check_het_catalog
            : "${projectDir}/assets/${params.panel}/het_catalog.tsv"
        def sex_het_catalog_file = file(sex_het_catalog_path)
        if( !sex_het_catalog_file.exists() )
            log.warn "[SEX_CHECK] no het catalog at ${sex_het_catalog_path}; sex inference is depth-only"
        ch_sex_het_catalog = Channel.value( sex_het_catalog_file.exists() ? sex_het_catalog_file : [] )
        SEX_CHECK(
            MOSDEPTH.out.regions_thresholds.join(ABRA2.out.bam, by: 0),
            reference_ch,
            ch_sex_het_catalog
        )
""",
    ),
    (
        "SEX_CHECK log lines",
        """                    else if( row.sheet_sex == 'unknown' )
                        log.info "[SEX_CHECK] ${meta.id}: samplesheet sex unknown; using inferred ${row.resolved_sex} (X/A=${row.x_auto_ratio}, status=${row.status})"
                }
""",
        """                    else if( row.sheet_sex == 'unknown' )
                        log.info "[SEX_CHECK] ${meta.id}: samplesheet sex unknown; using inferred ${row.resolved_sex} (method=${row.method}, X het=${row.x_het_frac}, X/A=${row.x_auto_ratio}, status=${row.status})"
                    // MARKER SEX_CHECK_V2: the two votes disagree; heterozygosity decided
                    if( (row.flags ?: '').contains('X_DEPTH_CONFLICT') )
                        log.warn "[SEX_CHECK] ${meta.id}: chrX heterozygosity says ${row.het_inferred_sex}, depth says ${row.depth_inferred_sex} (X het=${row.x_het_frac}, X/A=${row.x_auto_ratio}); using ${row.inferred_sex}; a chrX copy-number change in the tumour is likely"
                }
""",
    ),
]

MODULES_CONFIG_EDITS = [
    (
        "SEX_CHECK publish pattern",
        "pattern: '*.sex_check.tsv'",
        "pattern: '*.{sex_check.tsv,sexcheck.allelicCounts.tsv}'   // MARKER SEX_CHECK_MODULES_V2",
    ),
]

FULL_WRITES = [
    # path, payload, required guard string (must be present in the current file), executable
    ("modules/local/sex_check.nf", NEW_SEX_CHECK_NF, "SEX_CHECK_V1", False),
    ("bin/sex_check.py", NEW_SEX_CHECK_PY, "def run(args):", True),
    ("docs/sops/sex_check.md", NEW_SOP, None, False),
]

ANCHOR_FILES = [
    # path, edits, skip marker (file already patched when present)
    ("subworkflows/local/preprocessing.nf", PREPROC_EDITS, MARKER),
    ("conf/modules.config", MODULES_CONFIG_EDITS, "SEX_CHECK_MODULES_V2"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def flex_pattern(anchor):
    """Regex for an anchor that tolerates tab/space differences per line."""
    lines = anchor.rstrip("\n").split("\n")
    out = []
    for ln in lines:
        stripped = ln.lstrip(" \t")
        body = re.escape(stripped)
        body = re.sub(r"(\\ )+", r"[ \\t]+", body)
        out.append(r"[ \t]*" + body)
    pat = r"\n".join(out)
    if anchor.endswith("\n"):
        pat += r"\n"
    return re.compile(pat)


def brace_balance(text):
    return text.count("{") - text.count("}")


def read(path):
    with open(path) as fh:
        return fh.read()


def backup(path, ts):
    bak = "%s.bak_%s_%s" % (path, TAG, ts)
    with open(path) as src, open(bak, "w") as dst:
        dst.write(src.read())
    os.chmod(bak, os.stat(path).st_mode)
    print("[backup] %s" % bak)


# ---------------------------------------------------------------------------
# Plan and apply
# ---------------------------------------------------------------------------

def plan(repo):
    """Validate everything; return list of (path, new_text, executable) or exit 1."""
    actions = []
    errors = 0

    for rel, payload, guard, executable in FULL_WRITES:
        path = os.path.join(repo, rel)
        if os.path.exists(path):
            cur = read(path)
            if MARKER in cur:
                print("[skip] %s already carries %s" % (rel, MARKER))
                continue
            if guard and guard not in cur:
                print("[error] %s: guard '%s' not found; file is not the expected version" % (rel, guard))
                errors += 1
                continue
        elif guard:
            print("[error] %s: file missing" % rel)
            errors += 1
            continue
        else:
            print("[info] %s: new file" % rel)
        if rel.endswith(".nf") and brace_balance(payload) != 0:
            print("[error] %s: payload brace balance %d" % (rel, brace_balance(payload)))
            errors += 1
            continue
        actions.append((rel, payload, executable))

    for rel, edits, skip_marker in ANCHOR_FILES:
        path = os.path.join(repo, rel)
        if not os.path.exists(path):
            print("[error] %s: file missing" % rel)
            errors += 1
            continue
        cur = read(path)
        if skip_marker in cur:
            print("[skip] %s already carries %s" % (rel, skip_marker))
            continue
        new = cur
        ok = True
        for label, old, rep in edits:
            pat = flex_pattern(old)
            hits = list(pat.finditer(new))
            if len(hits) != 1:
                print("[error] %s: anchor '%s' matched %d times (need exactly 1)" % (rel, label, len(hits)))
                ok = False
                continue
            new = new[:hits[0].start()] + rep + new[hits[0].end():]
        if not ok:
            errors += 1
            continue
        if brace_balance(new) != brace_balance(cur):
            print("[error] %s: brace balance changed (%d -> %d)" % (rel, brace_balance(cur), brace_balance(new)))
            errors += 1
            continue
        actions.append((rel, new, False))

    if errors:
        print("[error] %d problem(s); nothing written" % errors)
        sys.exit(1)
    return actions


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=os.getcwd(), help="repo root (default: cwd)")
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    args = ap.parse_args()
    repo = os.path.abspath(args.repo)

    actions = plan(repo)
    if not actions:
        print("[ok] nothing to do")
        return
    for rel, _, _ in actions:
        print("[plan] %s" % rel)
    if not args.apply:
        print("[dry-run] %d file(s) would change; re-run with --apply" % len(actions))
        return

    ts = time.strftime("%Y%m%d_%H%M%S")
    for rel, new, executable in actions:
        path = os.path.join(repo, rel)
        d = os.path.dirname(path)
        if not os.path.isdir(d):
            os.makedirs(d)
        if os.path.exists(path):
            backup(path, ts)
        with open(path, "w") as fh:
            fh.write(new)
        if executable:
            os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        print("[patch] %s" % rel)

    # Post-check
    for rel, _, _ in actions:
        path = os.path.join(repo, rel)
        txt = read(path)
        print("[check] %s: V2 markers x%d, braces %+d%s" % (
            rel, txt.count(MARKER) + txt.count("SEX_CHECK_MODULES_V2"), brace_balance(txt),
            ", executable" if os.access(path, os.X_OK) else ""))


if __name__ == "__main__":
    main()
