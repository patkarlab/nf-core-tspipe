#!/usr/bin/env python3
"""
derive_exclusion_list.py -- derive the twist_myeloid BED-level exclusion
lists from measured, protocol-conforming data.

Emits two panel-definition TSVs consumed by build_panel_assets.py
(--exclude-exons / --exclude-backbone):

  exclusions.exons.tsv       exonwise labels excluded from CNV target space
  exclusions.backbone.tsv    backbone tiles excluded from CNV target space

Criteria (signed off 2026-09-01, thresholds read off the male-only
distributions; see docs/audit for the derivation session):

  EXONS:    ratio < DEAD_RATIO
            OR (ratio < SPREAD_GATE and max_spread > SPREAD_MAX)
            where ratio = male exon median depth / male gene median depth,
            and spread comes from the male-only CNVkit reference.
            Two failure modes, one rule: 'dead' bins capture almost nothing
            (log2 is Poisson noise); 'irreproducible' bins capture at a
            different level in every library (baseline wobble exceeds the
            signal sought). Consistently suppressed bins -- low ratio, low
            spread, the CpG first-exon class -- are RETAINED: suppression is
            thermodynamic and identical across libraries, CNVkit
            down-weights them by depth, and the per-stratum LOO blacklist
            adjudicates any residual misbehaviour.

  BACKBONE: male tile median depth < TILE_FLOOR.
            Replaces the retired GC < 0.35 rule, which was derived from a
            nonconforming (12-plex) female batch and mislabelled 760 of 830
            tiles that are alive under conforming capture. GC is carried as
            annotation only.

Cohort: the 24 male normals (8-plex, 16 hr overnight hybridisation --
conforming capture). The 24 female normals were captured at 12-plex and are
excluded as nonconforming; re-derive against conforming female data when it
exists, same command.

Dry run by default: prints the full excluded tables, the near-threshold
band, and the retention checks, writes nothing. Re-run with --apply to
write. Existing outputs are backed up with a timestamp before overwrite.

Python 3.6-safe.

Usage
-----
    cd /goast/hemat_data/nf-core-tspipe
    python3 tools/derive_exclusion_list.py \
        --exon-depth-dir     qc/twist_pon48/exsurvey__jsoadxr \
        --backbone-depth-dir qc/twist_pon48/backbone_male \
        --male-cnn  /goast/hemat_data/pon_twist/pon/cnvkit_pon_male.cnn \
        --gc-table  qc/twist_early/backbone_tile_depth.tsv \
        --outdir    assets/twist_myeloid \
        --expect-exons 8 --expect-tiles 71
    # review, then re-run with --apply
"""

import argparse
import glob
import gzip
import hashlib
import os
import sys
import time
from collections import Counter, OrderedDict, defaultdict

TAG = "derive_exclusion_list"

# Labels the criterion must NOT exclude. These are documented decisions
# (2026-09-01): consistent-suppression cases the old depth flags could not
# distinguish from capture death. If the criterion catches one of these, the
# underlying data has changed and a human must re-inspect -- the script
# stops rather than silently overriding either the rule or the decision.
DOCUMENTED_RETENTIONS = OrderedDict([
    ("JAK2_exon_15", "consistent suppression: male ratio 0.276, spread 0.23 "
                     "at derivation; down-weighted by CNVkit, adjudicated by "
                     "the per-stratum LOO blacklist"),
    ("HRAS_exon_1",  "consistent suppression: male ratio 0.125, spread 0.45 "
                     "at derivation; same handling"),
])


def msg(kind, text):
    sys.stdout.write("[%s] %s\n" % (kind, text))
    sys.stdout.flush()


def die(text):
    msg("error", text)
    sys.exit(1)


def md5_of(path):
    h = hashlib.md5()
    fh = open(path, "rb")
    try:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    finally:
        fh.close()
    return h.hexdigest()


def median(vals):
    if not vals:
        return None
    s = sorted(vals)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def gene_of(name):
    return name.split("_")[0]


def read_regions_dir(dirpath, pattern, expect, what):
    """Read mosdepth *.regions.bed.gz files. Returns (depths, coords, files)
    where depths maps (chrom, name) -> [mean depth per sample] and coords
    maps (chrom, name) -> (start, end)."""
    files = sorted(glob.glob(os.path.join(dirpath, pattern)))
    if expect and len(files) != expect:
        die("%s: expected %d files matching %s, found %d"
            % (what, expect, pattern, len(files)))
    if not files:
        die("%s: no files matching %s under %s" % (what, pattern, dirpath))
    depths = defaultdict(list)
    coords = {}
    for f in files:
        with gzip.open(f, "rt") as fh:
            for line in fh:
                c = line.rstrip("\n").split("\t")
                if len(c) < 5:
                    continue
                key = (c[0], c[3])
                try:
                    depths[key].append(float(c[4]))
                except ValueError:
                    continue
                if key not in coords:
                    coords[key] = (int(c[1]), int(c[2]))
    msg("ok", "%s: %d files, %d regions" % (what, len(files), len(depths)))
    return depths, coords, files


def read_cnn_spread(path):
    """Per-label (max spread, min log2, n bins) from a CNVkit reference."""
    spread = {}
    lo2 = {}
    nbin = Counter()
    fh = open(path)
    try:
        header = fh.readline().rstrip("\n").split("\t")
        for col in ("gene", "log2", "spread"):
            if col not in header:
                die("%s: no '%s' column" % (path, col))
        gi = header.index("gene")
        li = header.index("log2")
        si = header.index("spread")
        for line in fh:
            f = line.rstrip("\n").split("\t")
            if len(f) <= max(gi, li, si):
                continue
            g = f[gi].strip()
            try:
                s = float(f[si])
                l = float(f[li])
            except ValueError:
                continue
            nbin[g] += 1
            if g not in spread or s > spread[g]:
                spread[g] = s
            if g not in lo2 or l < lo2[g]:
                lo2[g] = l
    finally:
        fh.close()
    msg("ok", "male reference: %d labels with spread" % len(spread))
    return spread, lo2, nbin


def write_tsv(path, header_lines, cols, rows, apply_changes):
    if not apply_changes:
        msg("write", "%s (%d rows) [dry-run]" % (path, len(rows)))
        return
    if os.path.exists(path):
        bak = "%s.bak_%s_%s" % (path, TAG, time.strftime("%Y%m%d_%H%M%S"))
        os.rename(path, bak)
        msg("backup", bak)
    fh = open(path, "w")
    try:
        for h in header_lines:
            fh.write(h + "\n")
        fh.write("\t".join(cols) + "\n")
        for r in rows:
            fh.write("\t".join(str(r[c]) for c in cols) + "\n")
    finally:
        fh.close()
    msg("write", "%s (%d rows)" % (path, len(rows)))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exon-depth-dir", required=True,
                    help="exon_depth_survey kept-temp dir (Male*.regions.bed.gz)")
    ap.add_argument("--backbone-depth-dir", required=True,
                    help="backbone_male mosdepth dir (Male*.regions.bed.gz)")
    ap.add_argument("--male-cnn", required=True,
                    help="cnvkit_pon_male.cnn (spread source)")
    ap.add_argument("--gc-table", required=True,
                    help="backbone_tile_depth.tsv (GC annotation ONLY)")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--dead-ratio", type=float, default=0.075)
    ap.add_argument("--spread-gate", type=float, default=0.5)
    ap.add_argument("--spread-max", type=float, default=0.75)
    ap.add_argument("--tile-floor", type=float, default=30.0)
    ap.add_argument("--expect-males", type=int, default=24)
    ap.add_argument("--expect-exons", type=int, default=0,
                    help="die unless exactly this many exon labels excluded (0 = off)")
    ap.add_argument("--expect-tiles", type=int, default=0,
                    help="die unless exactly this many tiles excluded (0 = off)")
    ap.add_argument("--apply", action="store_true", help="write files (default: dry run)")
    args = ap.parse_args()

    for p in (args.male_cnn, args.gc_table):
        if not os.path.isfile(p):
            die("no such file: %s" % p)
    for d in (args.exon_depth_dir, args.backbone_depth_dir):
        if not os.path.isdir(d):
            die("no such directory: %s" % d)

    mode = "APPLY" if args.apply else "DRY RUN (nothing written; re-run with --apply)"
    msg("ok", "mode: %s" % mode)
    msg("ok", "criteria: exon ratio < %.3f OR (ratio < %.2f AND spread > %.2f); "
              "backbone male median < %.0fx"
        % (args.dead_ratio, args.spread_gate, args.spread_max, args.tile_floor))

    # ---- exons ------------------------------------------------------------
    ex_depth, ex_coords, ex_files = read_regions_dir(
        args.exon_depth_dir, "Male*.regions.bed.gz", args.expect_males,
        "exon depths (male)")
    spread, lo2, nbin = read_cnn_spread(args.male_cnn)

    med = {}
    by_gene = defaultdict(list)
    for key, vals in ex_depth.items():
        m = median(vals)
        med[key] = m
        by_gene[gene_of(key[1])].append(m)
    gmed = {}
    for g, v in by_gene.items():
        gmed[g] = median(v)

    exon_rows = []
    band_rows = []
    for key in sorted(med, key=lambda k: (k[0], k[1])):
        chrom, name = key
        m = med[key]
        gm = gmed.get(gene_of(name))
        if not gm:
            continue
        ratio = m / gm
        sp = spread.get(name)
        dead = ratio < args.dead_ratio
        irre = (ratio < args.spread_gate and sp is not None
                and sp > args.spread_max)
        excluded = dead or irre
        rec = OrderedDict([
            ("label", name),
            ("gene", gene_of(name)),
            ("chrom", chrom),
            ("start", ex_coords[key][0]),
            ("end", ex_coords[key][1]),
            ("male_median_depth", "%.1f" % m),
            ("gene_median_depth", "%.1f" % gm),
            ("ratio", "%.3f" % ratio),
            ("n_bins_cnn", nbin.get(name, 0)),
            ("max_spread", "%.3f" % sp if sp is not None else "NA"),
            ("min_log2", "%.3f" % lo2[name] if name in lo2 else "NA"),
            ("arm", "dead" if dead else ("irreproducible" if irre else "")),
        ])
        if excluded:
            if sp is None:
                msg("warn", "%s excluded on depth alone; no spread in reference"
                    % name)
            exon_rows.append(rec)
        if ratio < args.spread_gate or (sp is not None and sp > 0.6):
            band_rows.append((ratio, rec, excluded))

    # Retention guard: documented decisions must survive the criterion.
    caught = [r["label"] for r in exon_rows if r["label"] in DOCUMENTED_RETENTIONS]
    if caught:
        die("criterion now excludes documented retention(s): %s\n"
            "        The underlying data has changed since 2026-09-01. "
            "Re-inspect before proceeding." % ", ".join(caught))

    exon_rows.sort(key=lambda r: float(r["ratio"]))
    msg("ok", "")
    msg("ok", "=== EXCLUDED EXON LABELS: %d ===" % len(exon_rows))
    for r in exon_rows:
        msg("ok", "  %-20s %-15s ratio=%-6s med=%-8s spread=%-6s %s"
            % (r["label"], r["arm"], r["ratio"], r["male_median_depth"],
               r["max_spread"], "%s:%s-%s" % (r["chrom"], r["start"], r["end"])))
    if args.expect_exons and len(exon_rows) != args.expect_exons:
        die("expected %d excluded exon labels, derived %d. Review before "
            "applying." % (args.expect_exons, len(exon_rows)))

    msg("ok", "")
    msg("ok", "=== NEAR-THRESHOLD BAND (ratio < %.2f or spread > 0.60) ==="
        % args.spread_gate)
    band_rows.sort(key=lambda t: t[0])
    for ratio, r, excluded in band_rows:
        msg("ok", "  %-9s %-20s ratio=%-6s med=%-8s spread=%-6s bins=%s"
            % ("EXCLUDE" if excluded else "retain", r["label"], r["ratio"],
               r["male_median_depth"], r["max_spread"], r["n_bins_cnn"]))
    msg("ok", "")
    msg("ok", "=== DOCUMENTED RETENTIONS (verified above threshold) ===")
    for name, why in DOCUMENTED_RETENTIONS.items():
        msg("ok", "  %-20s %s" % (name, why))

    # ---- backbone ---------------------------------------------------------
    bb_depth, bb_coords, bb_files = read_regions_dir(
        args.backbone_depth_dir, "Male*.regions.bed.gz", args.expect_males,
        "backbone depths (male)")

    gc = {}
    fh = open(args.gc_table)
    try:
        fh.readline()
        for line in fh:
            c = line.rstrip("\n").split("\t")
            if len(c) >= 8:
                gc["%s:%s:%s" % (c[0], c[1], c[2])] = c[7]
    finally:
        fh.close()

    floors = {30: 0, 50: 0, 100: 0}
    bb_rows = []
    n_gc_na = 0
    for key in sorted(bb_depth, key=lambda k: (k[0], bb_coords[k][0])):
        chrom, name = key
        vals = bb_depth[key]
        m = median(vals)
        for f in floors:
            if m < f:
                floors[f] += 1
        start, end = bb_coords[key]
        g = gc.get("%s:%d:%d" % (chrom, start, end), "NA")
        if g == "NA":
            n_gc_na += 1
        if m < args.tile_floor:
            bb_rows.append(OrderedDict([
                ("name", name),
                ("chrom", chrom),
                ("start", start),
                ("end", end),
                ("male_median_depth", "%.1f" % m),
                ("min_depth", "%.1f" % min(vals)),
                ("max_depth", "%.1f" % max(vals)),
                ("gc", g),
                ("criterion", "male_median<%.0fx" % args.tile_floor),
            ]))
    if n_gc_na:
        msg("warn", "%d tile(s) lack a GC annotation in %s"
            % (n_gc_na, args.gc_table))

    msg("ok", "")
    msg("ok", "=== BACKBONE: male-median floor counts (of %d tiles) ===" % len(bb_depth))
    for f in sorted(floors):
        msg("ok", "  tiles below %3dx: %4d" % (f, floors[f]))
    msg("ok", "")
    msg("ok", "=== EXCLUDED BACKBONE TILES: %d (male median < %.0fx) ==="
        % (len(bb_rows), args.tile_floor))
    for r in bb_rows:
        msg("ok", "  %-22s med=%-7s range=%s-%-8s gc=%s"
            % (r["name"], r["male_median_depth"], r["min_depth"],
               r["max_depth"], r["gc"]))
    if args.expect_tiles and len(bb_rows) != args.expect_tiles:
        die("expected %d excluded tiles, derived %d. Review before applying."
            % (args.expect_tiles, len(bb_rows)))

    # ---- write ------------------------------------------------------------
    if args.apply and not os.path.isdir(args.outdir):
        os.makedirs(args.outdir)

    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    common = [
        "# tool: %s  run: %s" % (TAG, stamp),
        "# cohort: %d male BAMs (8-plex, 16 hr) -- conforming capture. "
        "24 female normals (12-plex) excluded as nonconforming." % len(ex_files),
        "# spread source: %s  md5=%s" % (os.path.abspath(args.male_cnn),
                                         md5_of(args.male_cnn)),
    ]
    exon_hdr = common + [
        "# criterion: ratio < %.3f OR (ratio < %.2f AND max_spread > %.2f); "
        "ratio = male exon median / male gene median"
        % (args.dead_ratio, args.spread_gate, args.spread_max),
        "# exon depth source: %s (%d files)"
        % (os.path.abspath(args.exon_depth_dir), len(ex_files)),
        "# retained_by_decision: %s (2026-09-01, consistent-suppression class)"
        % "; ".join(DOCUMENTED_RETENTIONS),
    ]
    bb_hdr = common + [
        "# criterion: male tile median depth < %.0fx. Replaces retired "
        "GC<0.35 rule (derived from nonconforming 12-plex female batch)."
        % args.tile_floor,
        "# backbone depth source: %s (%d files)"
        % (os.path.abspath(args.backbone_depth_dir), len(bb_files)),
        "# gc column: annotation only, from %s  md5=%s"
        % (os.path.abspath(args.gc_table), md5_of(args.gc_table)),
    ]

    write_tsv(os.path.join(args.outdir, "exclusions.exons.tsv"),
              exon_hdr, list(exon_rows[0].keys()), exon_rows, args.apply)
    write_tsv(os.path.join(args.outdir, "exclusions.backbone.tsv"),
              bb_hdr, list(bb_rows[0].keys()), bb_rows, args.apply)

    msg("ok", "")
    msg("ok", "done. %s" % ("exclusion TSVs written." if args.apply
                            else "nothing written; re-run with --apply."))


if __name__ == "__main__":
    main()
