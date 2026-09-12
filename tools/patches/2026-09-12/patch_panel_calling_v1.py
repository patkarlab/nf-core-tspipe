#!/usr/bin/env python3
"""
patch_panel_calling_v1.py   (MARKER: PANEL_CALLING_V1)

Problem
-------
conf/twist_apply.config sets params.bed = assets/twist_myeloid/panel.combined.filtered.bed.
That file is missing two classes of target:

  1. The whole targets.hotspot.bed category (15 tiles / 9 regions) was never
     merged into panel.combined.bed, together with targets.17p_snp.bed (370)
     and targets.baf_autosomal.bed (4). Lost as a result: IDH1 exon 4,
     IDH2 exon 4, BRAF exon 15, ANKRD26 5'UTR, MLH1 5'UTR, KLHDC8B 5'UTR,
     DKC1 5'UTR, GATA3 intronic, FANCI intron 31.

  2. panel.combined.filtered.bed is panel.combined.bed minus 81 intervals
     removed by the CNV panel-of-normals noise filter. That filter is correct
     for CNV and wrong for variant calling: it removes AKT1 exon 1,
     PTEN exon 3, CCNC exons 6-7 and ANKRD26 exons 5/19/28/29 from the
     callable space.

All of these regions are captured and sequenced at full depth; they are simply
never examined by any caller.

Fix
---
Build assets/twist_myeloid/panel.calling.bed as the merged capture space
(Main probe BED + CNV backbone probe BED), alt-contig filtered and FAI-sorted,
and point params.bed at it. panel.combined.filtered.bed keeps its CNV role.

Conventions
-----------
Dry-run by default, --apply to write, MARKER guard for idempotency,
.bak_panelcalling_<timestamp> backups, all-or-nothing.

Usage
-----
    python3 patch_panel_calling_v1.py --repo /goast/hemat_data/nf-core-tspipe
    python3 patch_panel_calling_v1.py --repo ... --apply

Run this on gandalf (the development host), then re-tag. Do not patch a
deployed clinical clone in place.
"""

import argparse
import os
import shutil
import sys
import time

MARKER = "PANEL_CALLING_V1"

MAIN_BED = "probes_ok_ACTREC_Myeloid_TE-99430185_hg38_Main_260602213057.bed"
BACKBONE_BED = "probes_ok_ACTREC_Myeloid_TE-99430185_CNV_Backbone_Spikein_260603122240.bed"
OUT_BED = "panel.calling.bed"
CONFIG = os.path.join("conf", "twist_apply.config")

OLD_BED_REF = 'assets/twist_myeloid/panel.combined.filtered.bed'
NEW_BED_REF = 'assets/twist_myeloid/' + OUT_BED

# Clinically load-bearing coordinates asserted by name, for a readable check.
# Codon spans, hg38, 1-based inclusive.
NAMED_HOTSPOTS = [
    ("IDH1 R132", "chr2", 208248387, 208248389, "ivosidenib / olutasidenib"),
    ("IDH2 R140", "chr15", 90088701, 90088703, "enasidenib"),
    ("IDH2 R172", "chr15", 90088605, 90088607, "enasidenib"),
    ("BRAF V600", "chr7", 140753335, 140753337, "hairy cell leukaemia"),
]

FAI_CANDIDATES = [
    "/goast/hemat_data/targeted-seq-pipeline/references/hg38_broad/"
    "Homo_sapiens_assembly38.masked.fasta.fai",
    os.path.expanduser("~/references/hg38_broad/"
                       "Homo_sapiens_assembly38.masked.fasta.fai"),
]


def log(tag, msg):
    print("[%s] %s" % (tag, msg))


def read_bed(path):
    """Return list of (chrom, start, end, name). Skips headers and junk."""
    out = []
    with open(path) as fh:
        for line in fh:
            if not line.strip():
                continue
            if line.startswith(("#", "track", "browser")):
                continue
            f = line.rstrip("\n").split("\t")
            if len(f) < 3:
                continue
            try:
                start, end = int(f[1]), int(f[2])
            except ValueError:
                continue
            if end <= start:
                continue
            out.append((f[0], start, end, f[3] if len(f) > 3 else ""))
    return out


def fai_order(fai_path):
    """Contig -> rank, in FAI order."""
    order = {}
    with open(fai_path) as fh:
        for i, line in enumerate(fh):
            name = line.split("\t")[0]
            order[name] = i
    return order


def is_primary(chrom):
    if "_" in chrom or chrom.endswith("_alt") or chrom.startswith("HLA"):
        return False
    body = chrom[3:] if chrom.startswith("chr") else chrom
    return body in [str(i) for i in range(1, 23)] + ["X", "Y", "M", "MT"]


def merge(intervals):
    """Merge overlapping and bookended intervals per contig."""
    by_chrom = {}
    for c, s, e, n in intervals:
        by_chrom.setdefault(c, []).append((s, e, n))
    merged = {}
    for c, rows in by_chrom.items():
        rows.sort()
        cur_s, cur_e, names = rows[0][0], rows[0][1], {rows[0][2]}
        acc = []
        for s, e, n in rows[1:]:
            if s <= cur_e:
                cur_e = max(cur_e, e)
                names.add(n)
            else:
                acc.append((cur_s, cur_e, names))
                cur_s, cur_e, names = s, e, {n}
        acc.append((cur_s, cur_e, names))
        merged[c] = acc
    return merged


def label(names):
    """One deterministic name per merged interval, free of commas.

    Twist's Main probe BED carries compound names for probes spanning two
    named targets (ANKRD26_5UTR,ANKRD26_5-UTR). Several CNV scripts
    comma-split compound BED name fields, and the previous calling BED had
    none, so compound names are split here and the shortest part taken,
    ties broken alphabetically. That keeps the established bb.<chrom>.<pos>
    form for backbone tiles. The full compound name is preserved in the
    probe BED, which is the provenance record."""
    parts = set()
    for n in names:
        if not n:
            continue
        for piece in n.split(";")[0].split(","):
            piece = piece.strip()
            if piece:
                parts.add(piece)
    if not parts:
        return "."
    return sorted(parts, key=lambda s: (len(s), s))[0]


def covered(merged, chrom, lo, hi):
    """Is the 1-based inclusive span lo..hi fully inside merged intervals?"""
    for s, e, _ in merged.get(chrom, []):
        if lo > s and hi <= e:
            return True
    return False


def decode_range(contig):
    """Twist probe-space rows encode the locus in the contig name:
       CNVbb_chr10_10019761_range=chr10_10019761_10019880  0  120  .
       Columns 2-3 are offsets inside the probe, not genomic coordinates.
       Returns (chrom, start0, end) in BED convention, or None."""
    if "range=" not in contig:
        return None
    tail = contig.split("range=")[-1]
    parts = tail.rsplit("_", 2)
    if len(parts) != 3:
        return None
    chrom, s, e = parts
    try:
        s, e = int(s), int(e)
    except ValueError:
        return None
    if e <= s:
        return None
    return (chrom, s - 1, e)          # name is 1-based inclusive


def normalise(intervals):
    """Return (genomic_rows, decoded_count, unusable_rows)."""
    out, decoded, bad = [], 0, []
    for c, s, e, n in intervals:
        if is_primary(c):
            out.append((c, s, e, n))
            continue
        d = decode_range(c)
        if d and is_primary(d[0]):
            label_ = c.split("_range=")[0]
            out.append((d[0], d[1], d[2], label_))
            decoded += 1
        else:
            bad.append((c, s, e, n))
    return out, decoded, bad


def find_asset(root, basename, override=None):
    """Locate an asset by basename anywhere under root, shallowest first."""
    if override:
        return override if os.path.exists(override) else None
    matches = []
    for dirpath, _dirnames, filenames in os.walk(root):
        if basename in filenames:
            full = os.path.join(dirpath, basename)
            depth = full[len(root):].count(os.sep)
            matches.append((depth, full))
    if not matches:
        return None
    matches.sort()
    return matches[0][1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="nf-core-tspipe clone")
    ap.add_argument("--fai", help="reference .fai for contig ordering")
    ap.add_argument("--main-bed", help="override: Main probe BED")
    ap.add_argument("--backbone-bed", help="override: CNV backbone probe BED")
    ap.add_argument("--current-bed", help="override: current calling BED")
    ap.add_argument("--apply", action="store_true", help="write changes")
    ap.add_argument("--allow-loss", action="store_true",
                    help="proceed even if currently callable intervals would "
                         "be lost (requires a documented reason)")
    ap.add_argument("--report", help="write the added-interval list here")
    args = ap.parse_args()

    assets = os.path.join(args.repo, "assets", "twist_myeloid")
    if not os.path.isdir(assets):
        log("error", "panel asset directory not found: %s" % assets)
        return 1

    main_bed = find_asset(assets, MAIN_BED, args.main_bed)
    back_bed = find_asset(assets, BACKBONE_BED, args.backbone_bed)
    old_bed = find_asset(assets, "panel.combined.filtered.bed",
                         args.current_bed)
    out_bed = os.path.join(assets, OUT_BED)
    cfg = os.path.join(args.repo, CONFIG)

    missing = False
    for label_, p, hint in (("Main probe BED", main_bed, MAIN_BED),
                            ("backbone probe BED", back_bed, BACKBONE_BED),
                            ("current calling BED", old_bed,
                             "panel.combined.filtered.bed"),
                            ("config", cfg, CONFIG)):
        if not p or not os.path.exists(p):
            log("error", "%s not found (looked for %s under %s)"
                % (label_, hint, assets))
            missing = True
        else:
            log("info", "%-20s %s" % (label_ + ":", p))
    if missing:
        log("error", "pass explicit paths with --main-bed / --backbone-bed / "
                     "--current-bed if the layout differs")
        return 1

    fai = args.fai
    if not fai:
        for c in FAI_CANDIDATES:
            if os.path.exists(c):
                fai = c
                break
    if not fai or not os.path.exists(fai):
        log("error", "reference .fai not found; pass --fai")
        return 1
    log("info", "fai: %s" % fai)

    # ---------------------------------------------------------------- build
    probes = read_bed(main_bed) + read_bed(back_bed)
    log("info", "probe intervals read: %d" % len(probes))

    primary, decoded, dropped = normalise(probes)
    if decoded:
        log("info", "probe-space rows decoded from the range= suffix: %d"
            % decoded)

    # Cross-check the decoded backbone against the pre-converted asset, if any.
    bb_genomic = find_asset(assets, "backbone.hg38.bed")
    if bb_genomic:
        bb_rows = read_bed(bb_genomic)
        bb_set = set((c, s, e) for c, s, e, _n in bb_rows)
        dec_set = set((c, s, e) for c, s, e, _n in
                      normalise(read_bed(back_bed))[0])
        log("check", "backbone.hg38.bed: %d rows; decoded probe file: %d rows"
            % (len(bb_set), len(dec_set)))
        only_bb = bb_set - dec_set
        only_dec = dec_set - bb_set
        if not only_bb and not only_dec:
            log("check", "  the two agree exactly")
        else:
            log("warn", "  %d only in backbone.hg38.bed, %d only in the "
                        "decoded probe file" % (len(only_bb), len(only_dec)))
            for r in sorted(only_bb)[:5]:
                log("warn", "    asset only : %s:%d-%d" % r)
            for r in sorted(only_dec)[:5]:
                log("warn", "    decoded only: %s:%d-%d" % r)
            log("info", "  taking the union of both, so neither is lost")
        for c, s, e, n in bb_rows:
            if is_primary(c):
                primary.append((c, s, e, n))

    if dropped:
        tally = {}
        for c, _s, _e, _n in dropped:
            tally[c] = tally.get(c, 0) + 1
        log("info", "rows neither genomic nor decodable, dropped: %d"
            % len(dropped))
        for c in sorted(tally, key=lambda k: -tally[k])[:12]:
            log("info", "    %-46s %d rows" % (c[:46], tally[c]))
        if len(tally) > 12:
            log("info", "    ... and %d more contigs" % (len(tally) - 12))
        if len(dropped) > 0.05 * len(probes):
            log("warn", "that is %.1f%% of all probes - check the input format"
                % (100.0 * len(dropped) / len(probes)))

    merged = merge(primary)
    order = fai_order(fai)
    unknown = [c for c in merged if c not in order]
    if unknown:
        log("error", "contigs absent from the .fai: %s" % ", ".join(unknown))
        return 1

    rows = []
    for chrom in sorted(merged, key=lambda c: order[c]):
        for s, e, names in merged[chrom]:
            rows.append((chrom, s, e, label(names)))
    log("info", "merged calling intervals: %d  (%d bp)"
        % (len(rows), sum(e - s for _, s, e, _ in rows)))

    # ------------------------------------------------------------- verify
    ok = True
    log("check", "named hotspot containment")
    for name, chrom, lo, hi, why in NAMED_HOTSPOTS:
        hit = covered(merged, chrom, lo, hi)
        log("check", "  %-10s %s:%d-%d  %s   (%s)"
            % (name, chrom, lo, hi, "OK" if hit else "MISSING", why))
        ok = ok and hit

    # Structural check: every probe interval must be inside the new BED.
    bad = [p for p in primary if not covered(merged, p[0], p[1] + 1, p[2])]
    log("check", "probe intervals fully inside the calling BED: %d of %d"
        % (len(primary) - len(bad), len(primary)))
    if bad:
        ok = False
        for p in bad[:10]:
            log("check", "  NOT CONTAINED %s:%d-%d %s" % p)

    if not ok:
        log("error", "verification failed; nothing written")
        return 1

    # ------------------------------------------------- regression check
    # Nothing currently callable may become uncallable. This is the check
    # whose absence let an earlier version silently drop the CNV backbone.
    old_rows = read_bed(old_bed)
    lost = [r for r in old_rows
            if not covered(merged, r[0], r[1] + 1, r[2])]
    log("check", "current calling intervals retained: %d of %d"
        % (len(old_rows) - len(lost), len(old_rows)))
    if lost:
        lost_bp = sum(e - s for _c, s, e, _n in lost)
        log("error", "%d intervals (%d bp) callable today would become "
                     "uncallable" % (len(lost), lost_bp))
        tally = {}
        for c, s, e, n in lost:
            key = n.split(";")[0] if n else c
            tally[key] = tally.get(key, 0) + (e - s)
        for k in sorted(tally, key=lambda x: -tally[x])[:15]:
            log("error", "    %-32s %d bp" % (k, tally[k]))
        if len(tally) > 15:
            log("error", "    ... and %d more" % (len(tally) - 15))
        if not args.allow_loss:
            log("error", "refusing to proceed; this is a regression, not a fix")
            log("error", "investigate, or pass --allow-loss if every loss "
                         "above is genuinely intended")
            return 1
        log("warn", "--allow-loss given; proceeding despite the losses above")

    # ------------------------------------------------- what this restores
    old = merge(read_bed(old_bed))
    added = []
    for chrom, s, e, name in rows:
        gained = e - s
        for os_, oe, _ in old.get(chrom, []):
            if oe <= s or os_ >= e:
                continue
            gained -= min(e, oe) - max(s, os_)
        if gained > 0:
            added.append((chrom, s, e, name, gained))

    tot = sum(a[4] for a in added)
    log("info", "intervals gaining callable bases vs the current BED: %d"
        % len(added))
    log("info", "callable bases restored: %d" % tot)

    genes = {}
    for chrom, s, e, name, gained in added:
        g = name.split("_exon")[0].split("_intron")[0].split(",")[0]
        genes[g] = genes.get(g, 0) + gained
    log("info", "regions affected: %d" % len(genes))
    for g in sorted(genes, key=lambda k: -genes[k])[:25]:
        log("info", "    %-16s +%d bp" % (g, genes[g]))
    if len(genes) > 25:
        log("info", "    ... and %d more" % (len(genes) - 25))

    if args.report:
        with open(args.report, "w") as fh:
            fh.write("chrom\tstart\tend\tname\tbases_restored\n")
            for r in added:
                fh.write("%s\t%d\t%d\t%s\t%d\n" % r)
        log("info", "report written: %s" % args.report)

    # ---------------------------------------------------------- config
    with open(cfg) as fh:
        cfg_text = fh.read()

    cfg_changed = False
    cfg_new = cfg_text

    if MARKER in cfg_text:
        log("skip", "%s already present in %s" % (MARKER, CONFIG))
    else:
        lines = cfg_text.split("\n")
        hits = [i for i, ln in enumerate(lines)
                if OLD_BED_REF in ln and ln.split("=")[0].strip() == "bed"]
        if len(hits) != 1:
            log("error",
                "expected exactly one params.bed line referencing %s in %s; "
                "found %d" % (OLD_BED_REF, CONFIG, len(hits)))
            return 1
        i = hits[0]
        old_line = lines[i]
        indent = old_line[:len(old_line) - len(old_line.lstrip())]
        lines[i] = (
            '%sbed                = "${projectDir}/%s"   // MARKER %s: '
            'calling interval list is the capture space; '
            'panel.combined.filtered.bed stays the CNV asset'
            % (indent, NEW_BED_REF, MARKER))
        log("patch", "  old: %s" % old_line.strip())
        log("patch", "  new: %s" % lines[i].strip())
        cfg_new = "\n".join(lines)
        cfg_changed = True

    # ------------------------------------------------------------- write
    if not args.apply:
        log("dry-run", "would write %s (%d intervals)" % (out_bed, len(rows)))
        if cfg_changed:
            log("dry-run", "would repoint params.bed in %s" % CONFIG)
        log("dry-run", "re-run with --apply to make these changes")
        return 0

    stamp = time.strftime("%Y%m%d_%H%M%S")
    if os.path.exists(out_bed):
        shutil.copy2(out_bed, "%s.bak_panelcalling_%s" % (out_bed, stamp))
        log("backup", "%s.bak_panelcalling_%s" % (out_bed, stamp))

    tmp = out_bed + ".tmp"
    with open(tmp, "w") as fh:
        for chrom, s, e, name in rows:
            fh.write("%s\t%d\t%d\t%s\n" % (chrom, s, e, name))
    os.replace(tmp, out_bed)
    log("patch", "wrote %s (%d intervals)" % (out_bed, len(rows)))

    if cfg_changed:
        shutil.copy2(cfg, "%s.bak_panelcalling_%s" % (cfg, stamp))
        log("backup", "%s.bak_panelcalling_%s" % (cfg, stamp))
        with open(cfg, "w") as fh:
            fh.write(cfg_new)
        log("patch", "params.bed -> %s" % NEW_BED_REF)

    log("done", "apply complete")
    print()
    print("Next:")
    print("  1. md5sum %s   and record it" % out_bed)
    print("  2. nextflow config -c conf/twist_apply.config  (check it parses)")
    print("  3. stub DAG run, then a full run8 re-run - params.bed is in every")
    print("     task hash, so this re-executes the whole pipeline")
    print("  4. confirm IDH1/IDH2/BRAF rows now appear for 26CGH799 / 26CGH885")
    print("  5. add the structural containment check to tools/verify_install.sh")
    print("  6. re-tag; the v1.0.1 qualification does not cover this change")
    return 0


if __name__ == "__main__":
    sys.exit(main())
