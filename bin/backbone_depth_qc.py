#!/usr/bin/env python3
"""
backbone_depth_qc.py -- measure CNV backbone tile depth against main-panel
exonic targets, stratified by GC content.

Standalone QC. Reads BAMs, writes TSVs. Touches nothing in the pipeline.

Why this exists
---------------
The whole arm-level CNV design rests on an assumption: that the 3,047 backbone
spike-in tiles achieve depth comparable to the main-panel exonic targets. If
they run at a fraction of exonic depth, arm-level sensitivity is bounded by
that fraction and no amount of downstream modelling recovers it.

Being synthesised in one pool with the main panel fixes probe stoichiometry,
which removes the main reason depth would diverge. It does not fix two things:

  1. Capture efficiency is GC-dependent. This panel has a documented history
     here -- GC decile 1 efficiency ran 0.003 at 1 hr hybridisation and 0.184
     at 16 hr. The bottom deciles are where any surprise will be.

  2. Backbone loci carry ONE probe each. Main-panel exons are tiled with
     several overlapping probes. Per-locus capture opportunity differs even
     when per-probe efficiency does not.

So this is measured, not assumed. It is one mosdepth pass per BAM and the
answer sets the arm-level sensitivity floor directly.

Coverage convention
-------------------
mosdepth is called with --flag 772, which drops only the DUP bit and therefore
INCLUDES duplicates. This follows lab convention for coverage reporting. The
mosdepth default of 1796 excludes duplicates and must not be used here.

Outputs
-------
  backbone_depth_summary.tsv   one row per sample: median/mean depth for
                               backbone and exonic targets, the ratio, and
                               the fraction of tiles below usability floors
  backbone_depth_by_gc.tsv     backbone depth by GC decile, pooled and per
                               sample, against the exonic baseline
  backbone_tile_depth.tsv      per-tile median depth across all samples, with
                               GC -- the table to consult when a specific
                               region calls oddly

Python 3.6-safe.

Usage
-----
    python3 backbone_depth_qc.py \
        --bam-dir   /goast/hemat_data/pon_twist \
        --bam-glob  '*/preprocessing/*.final.bam' \
        --backbone  assets/twist_myeloid/backbone.hg38.bed \
        --exonic    assets/twist_myeloid/targets.exonic.bed \
        --reference /goast/hemat_data/targeted-seq-pipeline/references/hg38_broad/Homo_sapiens_assembly38.masked.fasta \
        --outdir    qc/twist_myeloid \
        --threads   8
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

TAG = "backbone_depth_qc"

# Usability floors. A backbone tile below these contributes little to an
# arm-level call.
DEPTH_FLOORS = [30, 50, 100]


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


def mean(vals):
    return (sum(vals) / float(len(vals))) if vals else None


def gc_of_regions(bed, reference, outdir):
    """Per-region GC fraction via bedtools nuc, falling back to samtools faidx."""
    out = os.path.join(outdir, "_gc.txt")
    if run("command -v bedtools").returncode == 0:
        r = run("bedtools nuc -fi %s -bed %s > %s 2>/dev/null" % (reference, bed, out))
        if r.returncode == 0 and os.path.exists(out):
            gc = {}
            fh = open(out)
            try:
                header = fh.readline().rstrip("\n").split("\t")
                gc_idx = None
                for i, h in enumerate(header):
                    if h.endswith("pct_gc"):
                        gc_idx = i
                        break
                if gc_idx is not None:
                    for line in fh:
                        f = line.rstrip("\n").split("\t")
                        if len(f) > gc_idx:
                            try:
                                gc["%s:%s-%s" % (f[0], f[1], f[2])] = float(f[gc_idx])
                            except ValueError:
                                pass
            finally:
                fh.close()
            if gc:
                return gc
    msg("warn", "bedtools nuc unavailable or failed; GC stratification skipped")
    return {}


def mosdepth_regions(bam, bed, prefix, threads):
    """Return {region_key: depth} from a mosdepth --by run."""
    # MARKER mapq20_qc: --mapq 20 excludes MAPQ<20 reads (alt-contig blind spot, 2026-09-02)
    cmd = ("mosdepth --by {bed} --flag 772 --mapq 20 --no-per-base -t {th} {pfx} {bam}"
           ).format(bed=bed, th=threads, pfx=prefix, bam=bam)
    r = run(cmd)
    if r.returncode != 0:
        msg("warn", "mosdepth failed for %s: %s" % (os.path.basename(bam),
                                                    r.stderr.strip()[:120]))
        return {}
    path = prefix + ".regions.bed.gz"
    if not os.path.exists(path):
        return {}
    out = {}
    with gzip.open(path, "rt") as fh:
        for line in fh:
            f = line.rstrip("\n").split("\t")
            if len(f) < 4:
                continue
            try:
                out["%s:%s-%s" % (f[0], f[1], f[2])] = float(f[-1])
            except ValueError:
                continue
    return out


def decile(gc_pct):
    d = int(gc_pct * 10) + 1
    return 10 if d > 10 else (1 if d < 1 else d)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bam-dir", required=True)
    ap.add_argument("--bam-glob", default="**/*.final.bam")
    ap.add_argument("--backbone", required=True, help="backbone.hg38.bed")
    ap.add_argument("--exonic", required=True, help="targets.exonic.bed")
    ap.add_argument("--reference", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--keep-temp", action="store_true")
    args = ap.parse_args()

    need("mosdepth")
    for p in (args.backbone, args.exonic, args.reference):
        if not os.path.isfile(p):
            die("no such file: %s" % p)

    bams = sorted(glob.glob(os.path.join(args.bam_dir, args.bam_glob), recursive=True))
    if not bams:
        die("no BAMs matched %s under %s" % (args.bam_glob, args.bam_dir))
    msg("ok", "found %d BAM(s)" % len(bams))

    if not os.path.isdir(args.outdir):
        os.makedirs(args.outdir)
    tmp = tempfile.mkdtemp(prefix="bbqc_", dir=args.outdir)

    msg("ok", "computing GC for backbone tiles")
    gc_map = gc_of_regions(args.backbone, args.reference, tmp)
    msg("ok", "GC available for %d/%d tiles" % (len(gc_map),
        sum(1 for _ in open(args.backbone))))

    summary = []
    tile_depths = defaultdict(list)
    gc_rows = []

    for i, bam in enumerate(bams, 1):
        sample = re.sub(r"\.final\.bam$", "", os.path.basename(bam))
        msg("ok", "[%d/%d] %s" % (i, len(bams), sample))

        bb = mosdepth_regions(bam, args.backbone, os.path.join(tmp, sample + ".bb"),
                              args.threads)
        ex = mosdepth_regions(bam, args.exonic, os.path.join(tmp, sample + ".ex"),
                              args.threads)
        if not bb or not ex:
            msg("warn", "skipping %s (mosdepth produced no output)" % sample)
            continue

        for k, v in bb.items():
            tile_depths[k].append(v)

        bb_vals = list(bb.values())
        ex_vals = list(ex.values())
        bb_med, ex_med = median(bb_vals), median(ex_vals)
        ratio = (bb_med / ex_med) if ex_med else None

        row = OrderedDict([
            ("sample", sample),
            ("backbone_tiles", len(bb_vals)),
            ("backbone_median_depth", "%.1f" % bb_med if bb_med is not None else "NA"),
            ("backbone_mean_depth", "%.1f" % mean(bb_vals)),
            ("exonic_targets", len(ex_vals)),
            ("exonic_median_depth", "%.1f" % ex_med if ex_med is not None else "NA"),
            ("exonic_mean_depth", "%.1f" % mean(ex_vals)),
            ("backbone_to_exonic_ratio", "%.3f" % ratio if ratio is not None else "NA"),
        ])
        for floor in DEPTH_FLOORS:
            frac = sum(1 for v in bb_vals if v < floor) / float(len(bb_vals))
            row["pct_tiles_below_%dx" % floor] = "%.1f" % (100.0 * frac)
        summary.append(row)

        if gc_map:
            by_dec = defaultdict(list)
            for k, v in bb.items():
                if k in gc_map:
                    by_dec[decile(gc_map[k])].append(v)
            for d in sorted(by_dec):
                gc_rows.append(OrderedDict([
                    ("sample", sample),
                    ("gc_decile", d),
                    ("n_tiles", len(by_dec[d])),
                    ("median_depth", "%.1f" % median(by_dec[d])),
                    ("relative_to_exonic",
                     "%.3f" % (median(by_dec[d]) / ex_med) if ex_med else "NA"),
                ]))

    if not summary:
        die("no samples produced usable depth output")

    def write_tsv(path, rows):
        fh = open(path, "w")
        try:
            fh.write("\t".join(rows[0].keys()) + "\n")
            for r in rows:
                fh.write("\t".join(str(v) for v in r.values()) + "\n")
        finally:
            fh.close()
        msg("write", "%s (%d rows)" % (path, len(rows)))

    write_tsv(os.path.join(args.outdir, "backbone_depth_summary.tsv"), summary)
    if gc_rows:
        write_tsv(os.path.join(args.outdir, "backbone_depth_by_gc.tsv"), gc_rows)

    tile_rows = []
    for k in sorted(tile_depths):
        vals = tile_depths[k]
        chrom, rest = k.split(":", 1)
        start, end = rest.split("-", 1)
        tile_rows.append(OrderedDict([
            ("chrom", chrom), ("start", start), ("end", end),
            ("n_samples", len(vals)),
            ("median_depth", "%.1f" % median(vals)),
            ("min_depth", "%.1f" % min(vals)),
            ("max_depth", "%.1f" % max(vals)),
            ("gc", "%.3f" % gc_map[k] if k in gc_map else "NA"),
        ]))
    write_tsv(os.path.join(args.outdir, "backbone_tile_depth.tsv"), tile_rows)

    ratios = [float(r["backbone_to_exonic_ratio"]) for r in summary
              if r["backbone_to_exonic_ratio"] != "NA"]
    msg("ok", "")
    msg("ok", "=== VERDICT ===")
    if ratios:
        m = median(ratios)
        msg("ok", "backbone : exonic median depth ratio = %.3f "
                  "(range %.3f - %.3f across %d samples)"
            % (m, min(ratios), max(ratios), len(ratios)))
        if m >= 0.80:
            msg("ok", "Backbone tracks the main panel closely. Arm-level "
                      "sensitivity is not depth-limited relative to exonic targets.")
        elif m >= 0.50:
            msg("warn", "Backbone runs at roughly half exonic depth. Usable for "
                        "arm-level calls, but focal backbone-only events will be "
                        "noisier. Factor this into segment confidence.")
        else:
            msg("warn", "Backbone runs well below exonic depth. This bounds "
                        "arm-level sensitivity and should be quantified against a "
                        "known-positive before the design is relied upon.")
    dead = [r for r in tile_rows if float(r["median_depth"]) < DEPTH_FLOORS[0]]
    msg("ok", "tiles below %dx median across all samples: %d / %d (%.1f%%)"
        % (DEPTH_FLOORS[0], len(dead), len(tile_rows),
           100.0 * len(dead) / len(tile_rows)))
    if gc_rows:
        pooled = defaultdict(list)
        for r in gc_rows:
            if r["relative_to_exonic"] != "NA":
                pooled[r["gc_decile"]].append(float(r["relative_to_exonic"]))
        msg("ok", "relative depth by GC decile (1 = most AT-rich):")
        for d in sorted(pooled):
            msg("ok", "    decile %2d: %.3f" % (d, median(pooled[d])))
        low = [d for d in sorted(pooled) if median(pooled[d]) < 0.3]
        if low:
            msg("warn", "deciles with <0.3 relative depth: %s -- AT/GC dropout "
                        "persists in these bins" % ", ".join(str(d) for d in low))

    if not args.keep_temp:
        run("rm -rf %s" % tmp)
    else:
        msg("ok", "temp kept at %s" % tmp)


if __name__ == "__main__":
    main()
