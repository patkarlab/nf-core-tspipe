#!/usr/bin/env python3
"""
exon_depth_survey.py -- per-exon capture depth across the PoN normals,
measured directly from the BAMs over targets.exonwise.bed.

Standalone QC. Reads BAMs, writes TSVs. Touches nothing in the pipeline.

Why this exists
---------------
The BED-level exclusion list for panel.combined.filtered.bed is defined by a
measured depth criterion, not by reconstructing the 8-exon list whose
provenance is gone. This script produces that measurement: per-exon median
depth across all normals, expressed relative to the exon's own gene median,
so the threshold can be set at the cliff the distribution shows.

It also resolves an open interpretation question. Labels absent from the LOO
bin table have at least two possible mechanisms: genuinely capture-dead bins
dropped by CNVkit's reference filters, or bins merged by `cnvkit.py target`
into compound comma-joined names, which an exact-match diff then miscounts
as absent. Depth from the BAMs is independent of CNVkit's binning, so it
separates the two. If --loo-bins is given, each exon is additionally tagged
with its LOO status: present, compound_only (inside a merged name), or
absent.

Coverage convention
-------------------
mosdepth is called with --flag 772, which drops only the DUP bit and
therefore INCLUDES duplicates, per lab convention. The mosdepth default of
1796 excludes duplicates and must not be used.

Outputs
-------
  exon_depth_survey.tsv    one row per (chrom, exon label), sorted ascending
                           by ratio_to_gene_median: gene, locus, median /
                           min / max depth across samples, gene median,
                           ratio, n_exons_in_gene, loo_status
  gene_depth_summary.tsv   one row per gene: n_exons, gene median depth,
                           exon count below informational ratio marks
                           (0.25 / 0.35 / 0.50) -- for reading the
                           distribution, not a decision

The log ends with the ratio distribution, the lowest-ratio exons, and an
anchor report covering the known cases (JAK2_exon_15, PTEN_exon_3 expected
dead; HRAS_exon_1, AKT1_exon_1, ANKRD26_exon_34, PTEN_exon_9 expected alive;
NPM1_exon_11 must-check).

Python 3.6-safe.

Usage
-----
    cd /goast/hemat_data/nf-core-tspipe
    python3 tools/exon_depth_survey.py \
        --bam-dir  /goast/hemat_data/nxf_work_twist \
        --exonwise assets/twist_myeloid/targets.exonwise.bed \
        --loo-bins /goast/hemat_data/pon_twist/pon/loo_qc/loo_bin_fp_rates.tsv \
        --outdir   qc/twist_pon48 \
        --threads  8

Roughly one minute per BAM; ~45 min for 48. Launch detached:
    setsid bash -c 'cd /goast/hemat_data/nf-core-tspipe && python3 \
        tools/exon_depth_survey.py ... ' < /dev/null \
        > /tmp/exon_depth_survey.log 2>&1 &
"""

import argparse
import glob
import gzip
import os
import re
import subprocess
import sys
import tempfile
from collections import OrderedDict, defaultdict

TAG = "exon_depth_survey"

EXPECTED_SAMPLES = 48

# Informational ratio marks for the gene summary. NOT the exclusion
# threshold -- that is set after the distribution is inspected.
RATIO_MARKS = (0.25, 0.35, 0.50)

# Anchor exons with the expected side of the eventual threshold.
# 'dead'  -> expected well below the cliff (capture failure)
# 'alive' -> expected above it (noisy in LOO but capturing)
# 'check' -> no expectation; must be inspected either way
ANCHORS = OrderedDict([
    ("JAK2_exon_15",    "dead"),
    ("PTEN_exon_3",     "dead"),
    ("HRAS_exon_1",     "alive"),
    ("AKT1_exon_1",     "alive"),
    ("ANKRD26_exon_34", "alive"),
    ("PTEN_exon_9",     "alive"),
    ("NPM1_exon_11",    "check"),
])


def msg(kind, text):
    sys.stdout.write("[%s] %s\n" % (kind, text))
    sys.stdout.flush()


def die(text):
    msg("error", text)
    sys.exit(1)


def run(cmd):
    return subprocess.run(cmd, shell=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, universal_newlines=True)


def need(tool):
    if run("command -v %s" % tool).returncode != 0:
        die("%s not found on PATH. Activate the targeted-seq env first." % tool)


def median(vals):
    if not vals:
        return None
    s = sorted(vals)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def gene_of(name):
    return re.split(r"_", name)[0]


# ---------------------------------------------------------------------------
# discovery
# ---------------------------------------------------------------------------

def discover_bams(bam_dir, bam_glob, expected):
    """Real files only. Nextflow work dirs stage the same BAM as symlinks in
    downstream task dirs, so a naive glob returns each sample several times."""
    hits = glob.glob(os.path.join(bam_dir, bam_glob), recursive=True)
    real = [p for p in hits if os.path.isfile(p) and not os.path.islink(p)]
    by_sample = defaultdict(list)
    for p in real:
        by_sample[re.sub(r"\.final\.bam$", "", os.path.basename(p))].append(p)

    chosen = OrderedDict()
    for sample in sorted(by_sample):
        paths = sorted(by_sample[sample])
        if len(paths) > 1:
            msg("warn", "%s: %d real files; using %s"
                % (sample, len(paths), paths[0]))
        chosen[sample] = paths[0]

    msg("ok", "glob matched %d path(s); %d real file(s); %d unique sample(s)"
        % (len(hits), len(real), len(chosen)))
    if expected and len(chosen) != expected:
        die("expected %d samples, found %d. Pass --expect-samples 0 to "
            "override, or fix the glob." % (expected, len(chosen)))
    return chosen


def read_exonwise(path):
    """One row per (chrom, name) by construction of collapse_exonwise."""
    rows = []
    seen = set()
    fh = open(path)
    try:
        for lineno, line in enumerate(fh, 1):
            line = line.rstrip("\n")
            if not line or line.startswith(("#", "track", "browser")):
                continue
            f = line.split("\t")
            if len(f) < 4:
                die("%s line %d: expected 4 BED columns" % (path, lineno))
            key = (f[0], f[3].strip())
            if key in seen:
                die("%s line %d: duplicate (chrom, name) %s -- exonwise BED "
                    "should be collapsed" % (path, lineno, key))
            seen.add(key)
            rows.append((f[0], int(f[1]), int(f[2]), f[3].strip()))
    finally:
        fh.close()
    return rows


def read_loo_labels(path):
    """Exact label set and compound-token set from the LOO bin table."""
    exact = set()
    compound_tokens = set()
    fh = open(path)
    try:
        header = fh.readline().rstrip("\n").split("\t")
        try:
            gi = header.index("gene")
        except ValueError:
            die("%s: no 'gene' column" % path)
        for line in fh:
            f = line.rstrip("\n").split("\t")
            if len(f) <= gi:
                continue
            g = f[gi].strip()
            exact.add(g)
            if "," in g:
                for tok in g.split(","):
                    compound_tokens.add(tok.strip())
    finally:
        fh.close()
    return exact, compound_tokens


# ---------------------------------------------------------------------------
# depth
# ---------------------------------------------------------------------------

def mosdepth_regions(bam, bed, prefix, threads):
    cmd = ("mosdepth --by {bed} --flag 772 --no-per-base -t {th} {pfx} {bam}"
           ).format(bed=bed, th=threads, pfx=prefix, bam=bam)
    r = run(cmd)
    if r.returncode != 0:
        msg("warn", "mosdepth failed for %s: %s"
            % (os.path.basename(bam), r.stderr.strip()[:120]))
        return {}
    path = prefix + ".regions.bed.gz"
    if not os.path.exists(path):
        return {}
    out = {}
    with gzip.open(path, "rt") as fh:
        for line in fh:
            f = line.rstrip("\n").split("\t")
            if len(f) < 5:
                continue
            try:
                out[(f[0], f[3])] = float(f[-1])
            except ValueError:
                continue
    return out


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bam-dir", required=True)
    ap.add_argument("--bam-glob", default="**/*.final.bam")
    ap.add_argument("--exonwise", required=True, help="targets.exonwise.bed")
    ap.add_argument("--loo-bins", default=None,
                    help="loo_bin_fp_rates.tsv (optional; adds loo_status)")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--expect-samples", type=int, default=EXPECTED_SAMPLES)
    ap.add_argument("--keep-temp", action="store_true")
    args = ap.parse_args()

    need("mosdepth")
    if not os.path.isfile(args.exonwise):
        die("no such file: %s" % args.exonwise)

    bams = discover_bams(args.bam_dir, args.bam_glob, args.expect_samples)
    exons = read_exonwise(args.exonwise)
    msg("ok", "exonwise regions: %d" % len(exons))

    loo_exact, loo_compound = (set(), set())
    if args.loo_bins:
        if not os.path.isfile(args.loo_bins):
            die("no such file: %s" % args.loo_bins)
        loo_exact, loo_compound = read_loo_labels(args.loo_bins)
        msg("ok", "LOO bin table: %d distinct labels, %d compound tokens"
            % (len(loo_exact), len(loo_compound)))

    if not os.path.isdir(args.outdir):
        os.makedirs(args.outdir)
    tmp = tempfile.mkdtemp(prefix="exsurvey_", dir=args.outdir)

    # BED with the name column intact for mosdepth (it echoes column 4).
    per_exon = defaultdict(list)
    n_done = 0
    for i, (sample, bam) in enumerate(bams.items(), 1):
        msg("ok", "[%d/%d] %s" % (i, len(bams), sample))
        d = mosdepth_regions(bam, args.exonwise, os.path.join(tmp, sample),
                             args.threads)
        if not d:
            msg("warn", "skipping %s (no mosdepth output)" % sample)
            continue
        n_done += 1
        for key, v in d.items():
            per_exon[key].append(v)

    if n_done == 0:
        die("no samples produced usable depth output")
    if n_done < len(bams):
        msg("warn", "depth available for %d/%d samples" % (n_done, len(bams)))

    # -- per-exon and per-gene statistics ----------------------------------
    exon_stats = OrderedDict()
    for chrom, start, end, name in exons:
        vals = per_exon.get((chrom, name), [])
        exon_stats[(chrom, name)] = {
            "chrom": chrom, "start": start, "end": end, "name": name,
            "gene": gene_of(name),
            "n": len(vals),
            "med": median(vals),
            "min": min(vals) if vals else None,
            "max": max(vals) if vals else None,
        }
        if len(vals) != n_done:
            msg("warn", "%s %s: depth for %d/%d samples"
                % (chrom, name, len(vals), n_done))

    by_gene = defaultdict(list)
    for st in exon_stats.values():
        if st["med"] is not None:
            by_gene[st["gene"]].append(st["med"])
    gene_median = {}
    for g, meds in by_gene.items():
        gene_median[g] = median(meds)

    def loo_status(name):
        if not args.loo_bins:
            return "NA"
        if name in loo_exact:
            return "present"
        if name in loo_compound:
            return "compound_only"
        return "absent"

    rows = []
    for st in exon_stats.values():
        gmed = gene_median.get(st["gene"])
        ratio = (st["med"] / gmed) if (st["med"] is not None and gmed) else None
        rows.append(OrderedDict([
            ("gene", st["gene"]),
            ("name", st["name"]),
            ("chrom", st["chrom"]),
            ("start", st["start"]),
            ("end", st["end"]),
            ("n_samples", st["n"]),
            ("median_depth", "%.1f" % st["med"] if st["med"] is not None else "NA"),
            ("min_depth", "%.1f" % st["min"] if st["min"] is not None else "NA"),
            ("max_depth", "%.1f" % st["max"] if st["max"] is not None else "NA"),
            ("gene_median_depth", "%.1f" % gmed if gmed else "NA"),
            ("n_exons_in_gene", len(by_gene.get(st["gene"], []))),
            ("ratio_to_gene_median", "%.3f" % ratio if ratio is not None else "NA"),
            ("loo_status", loo_status(st["name"])),
        ]))
    rows.sort(key=lambda r: (float(r["ratio_to_gene_median"])
                             if r["ratio_to_gene_median"] != "NA" else 9.9))

    def write_tsv(path, rws):
        fh = open(path, "w")
        try:
            fh.write("\t".join(rws[0].keys()) + "\n")
            for r in rws:
                fh.write("\t".join(str(v) for v in r.values()) + "\n")
        finally:
            fh.close()
        msg("write", "%s (%d rows)" % (path, len(rws)))

    write_tsv(os.path.join(args.outdir, "exon_depth_survey.tsv"), rows)

    grows = []
    for g in sorted(by_gene):
        meds = by_gene[g]
        gmed = gene_median[g]
        rec = OrderedDict([("gene", g), ("n_exons", len(meds)),
                           ("gene_median_depth", "%.1f" % gmed)])
        for m in RATIO_MARKS:
            rec["n_exons_below_%.2f" % m] = sum(
                1 for v in meds if gmed and (v / gmed) < m)
        grows.append(rec)
    write_tsv(os.path.join(args.outdir, "gene_depth_summary.tsv"), grows)

    # -- distribution and anchors ------------------------------------------
    ratios = [float(r["ratio_to_gene_median"]) for r in rows
              if r["ratio_to_gene_median"] != "NA"]
    msg("ok", "")
    msg("ok", "=== RATIO DISTRIBUTION (exon median / gene median) ===")
    edges = [0.0, 0.05, 0.10, 0.25, 0.35, 0.50, 0.75, 0.90, 1.10, 99.0]
    for lo, hi in zip(edges[:-1], edges[1:]):
        n = sum(1 for v in ratios if lo <= v < hi)
        msg("ok", "  [%.2f, %.2f): %5d" % (lo, hi, n))

    msg("ok", "")
    msg("ok", "=== LOWEST 40 EXONS BY RATIO ===")
    for r in rows[:40]:
        msg("ok", "  %-22s ratio=%-6s med=%-8s gene_med=%-8s loo=%s"
            % (r["name"], r["ratio_to_gene_median"], r["median_depth"],
               r["gene_median_depth"], r["loo_status"]))

    msg("ok", "")
    msg("ok", "=== ANCHORS ===")
    by_name = {}
    for r in rows:
        by_name.setdefault(r["name"], r)
    for name, expect in ANCHORS.items():
        r = by_name.get(name)
        if r is None:
            msg("warn", "  %-22s NOT IN EXONWISE BED (expected %s)" % (name, expect))
            continue
        msg("ok", "  %-22s expect=%-6s ratio=%-6s med=%-8s loo=%s"
            % (name, expect, r["ratio_to_gene_median"], r["median_depth"],
               r["loo_status"]))

    if args.loo_bins:
        absent = [r for r in rows if r["loo_status"] == "absent"]
        comp = [r for r in rows if r["loo_status"] == "compound_only"]
        msg("ok", "")
        msg("ok", "=== LOO ABSENCE MECHANISM ===")
        msg("ok", "  compound_only (merged by cnvkit target, NOT dropped): %d"
            % len(comp))
        msg("ok", "  truly absent from LOO bins:                          %d"
            % len(absent))
        healthy_absent = [r for r in absent
                          if r["ratio_to_gene_median"] != "NA"
                          and float(r["ratio_to_gene_median"]) >= 0.5]
        if healthy_absent:
            msg("warn", "  %d exon(s) absent from LOO despite healthy depth "
                        "(ratio >= 0.5) -- investigate individually:"
                % len(healthy_absent))
            for r in healthy_absent[:15]:
                msg("warn", "    %-22s ratio=%s med=%s"
                    % (r["name"], r["ratio_to_gene_median"], r["median_depth"]))

    if not args.keep_temp:
        run("rm -rf %s" % tmp)
    else:
        msg("ok", "temp kept at %s" % tmp)


if __name__ == "__main__":
    main()
