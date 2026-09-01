#!/usr/bin/env python3
"""
patch_builder_filtered_bed.py -- add measured-exclusion support to
bin/build_panel_assets.py.

What it adds
------------
1. CLI: --exclude-exons and --exclude-backbone, taking the TSVs emitted by
   derive_exclusion_list.py.
2. A reader that parses those TSVs (provenance '#' header + keyed rows) and
   dies on duplicates or missing columns.
3. Validation in main(): every excluded exon label must match at least one
   CNV-eligible probe; every excluded tile name must match a parsed backbone
   tile. Drift between the exclusion TSVs and the delivered BEDs is fatal,
   not silent.
4. Emission of panel.combined.filtered.bed -- (exonic minus excluded
   labels) + focal_cnv + (backbone minus excluded tiles), FAI-sorted. The
   single shared artifact behind both the CNVkit targets and the GATK
   interval list for BUILD_PON_TWIST.
5. Manifest section 'exclusions': labels, source paths, md5s, and the
   provenance headers copied verbatim from the TSVs.

Behaviour without the new flags is unchanged.

Conventions: dry run by default (--apply to write), timestamped
.bak_filtered_bed_<ts> backup, MARKER-based skip, anchors must each match
exactly once or nothing is touched. After writing, the result is
py_compile-checked; on failure the backup is restored.

Usage
-----
    cd /goast/hemat_data/nf-core-tspipe
    python3 tools/patches/2026-09-01/patch_builder_filtered_bed.py           # dry run
    python3 tools/patches/2026-09-01/patch_builder_filtered_bed.py --apply
"""

import argparse
import os
import py_compile
import shutil
import sys
import time

TAG = "filtered_bed"
TARGET_DEFAULT = "bin/build_panel_assets.py"
MARKER = "--exclude-exons"


def msg(kind, text):
    sys.stdout.write("[%s] %s\n" % (kind, text))


def die(text):
    msg("error", text)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Edit 1: CLI arguments
# ---------------------------------------------------------------------------

OLD_ARGS = '''    ap.add_argument("--workbook", default=None, help="design workbook .xlsx (optional cross-check)")'''

NEW_ARGS = '''    ap.add_argument("--workbook", default=None, help="design workbook .xlsx (optional cross-check)")
    ap.add_argument("--exclude-exons", default=None,
                    help="exon exclusion TSV from derive_exclusion_list.py; "
                         "with --exclude-backbone, emits panel.combined.filtered.bed")
    ap.add_argument("--exclude-backbone", default=None,
                    help="backbone tile exclusion TSV from derive_exclusion_list.py")'''

# ---------------------------------------------------------------------------
# Edit 2: exclusion TSV reader (inserted before the classification section)
# ---------------------------------------------------------------------------

OLD_READER_ANCHOR = '''# ---------------------------------------------------------------------------
# classification
# ---------------------------------------------------------------------------'''

NEW_READER = '''def read_exclusion_tsv(path, key_col):
    \'\'\'Exclusion TSV from derive_exclusion_list.py: "#" provenance header
    lines, a column header, then rows. Returns (keys, header_lines).\'\'\'
    keys = []
    header_lines = []
    ki = None
    fh = open(path)
    try:
        for line in fh:
            line = line.rstrip("\\n")
            if not line:
                continue
            if line.startswith("#"):
                header_lines.append(line)
                continue
            f = line.split("\\t")
            if ki is None:
                if key_col not in f:
                    die("%s: no '%s' column in header" % (path, key_col))
                ki = f.index(key_col)
                continue
            if len(f) > ki and f[ki].strip():
                keys.append(f[ki].strip())
    finally:
        fh.close()
    if not keys:
        die("%s: no exclusion rows parsed" % path)
    dupes = sorted(k for k, n in Counter(keys).items() if n > 1)
    if dupes:
        die("%s: duplicate exclusion key(s): %s" % (path, ", ".join(dupes)))
    return keys, header_lines


# ---------------------------------------------------------------------------
# classification
# ---------------------------------------------------------------------------'''

# ---------------------------------------------------------------------------
# Edit 3: load and validate exclusions in main(), before the write section
# ---------------------------------------------------------------------------

OLD_WRITE_ANCHOR = '''    # ---- write ------------------------------------------------------------
    if args.apply and not os.path.isdir(args.outdir):
        os.makedirs(args.outdir)'''

NEW_EXCLUSIONS = '''    # ---- exclusions -------------------------------------------------------
    excl_exon_labels = []
    excl_exon_hdr = []
    excl_bb_names = []
    excl_bb_hdr = []
    if args.exclude_exons:
        if not os.path.isfile(args.exclude_exons):
            die("no such file: %s" % args.exclude_exons)
        excl_exon_labels, excl_exon_hdr = read_exclusion_tsv(
            args.exclude_exons, "label")
        eligible = {r[3] for r in cls["exonic"]} | {r[3] for r in cls["focal_cnv"]}
        unmatched = [k for k in excl_exon_labels if k not in eligible]
        if unmatched:
            die("exon exclusion label(s) match no CNV-eligible probe: %s\\n"
                "        The exclusion TSV and the delivered BED have drifted."
                % ", ".join(unmatched))
        msg("ok", "exon exclusions: %d label(s) from %s"
            % (len(excl_exon_labels), args.exclude_exons))
    if args.exclude_backbone:
        if not os.path.isfile(args.exclude_backbone):
            die("no such file: %s" % args.exclude_backbone)
        excl_bb_names, excl_bb_hdr = read_exclusion_tsv(
            args.exclude_backbone, "name")
        tiles = {r[3] for r in bb_rows}
        unmatched = [k for k in excl_bb_names if k not in tiles]
        if unmatched:
            die("backbone exclusion name(s) match no parsed tile: %s%s"
                % (", ".join(unmatched[:10]),
                   " ..." if len(unmatched) > 10 else ""))
        msg("ok", "backbone exclusions: %d tile(s) from %s"
            % (len(excl_bb_names), args.exclude_backbone))

    # ---- write ------------------------------------------------------------
    if args.apply and not os.path.isdir(args.outdir):
        os.makedirs(args.outdir)'''

# ---------------------------------------------------------------------------
# Edit 4: emit panel.combined.filtered.bed after panel.combined.bed
# ---------------------------------------------------------------------------

OLD_COMBINED = '''    # depth-pipeline input: CNV-eligible targets + backbone
    combined = cls["exonic"] + cls["focal_cnv"] + bb_rows
    write_bed(j("panel.combined.bed"), combined, fai_order, args.apply, written)'''

NEW_COMBINED = '''    # depth-pipeline input: CNV-eligible targets + backbone
    combined = cls["exonic"] + cls["focal_cnv"] + bb_rows
    write_bed(j("panel.combined.bed"), combined, fai_order, args.apply, written)

    # filtered depth-pipeline input: measured exclusions removed. Single
    # shared artifact behind both the CNVkit targets and the GATK interval
    # list for BUILD_PON_TWIST -- one file, no engine-specific exclude
    # mechanics, no drift.
    if args.exclude_exons or args.exclude_backbone:
        ex_set = set(excl_exon_labels)
        bb_set = set(excl_bb_names)
        filt_exonic = [r for r in cls["exonic"] if r[3] not in ex_set]
        filt_focal = [r for r in cls["focal_cnv"] if r[3] not in ex_set]
        filt_bb = [r for r in bb_rows if r[3] not in bb_set]
        n_probes_removed = (len(cls["exonic"]) - len(filt_exonic)) \\
            + (len(cls["focal_cnv"]) - len(filt_focal))
        n_tiles_removed = len(bb_rows) - len(filt_bb)
        if excl_exon_labels and n_probes_removed == 0:
            die("exon exclusions removed zero probes; refusing to write a "
                "filtered BED identical to panel.combined.bed")
        if excl_bb_names and n_tiles_removed != len(excl_bb_names):
            die("backbone exclusions: %d name(s) listed but %d tile(s) removed"
                % (len(excl_bb_names), n_tiles_removed))
        filtered = filt_exonic + filt_focal + filt_bb
        msg("ok", "filtered: removed %d probe(s) across %d exon label(s) and "
                  "%d backbone tile(s); %d rows remain of %d"
            % (n_probes_removed, len(excl_exon_labels), n_tiles_removed,
               len(filtered), len(combined)))
        write_bed(j("panel.combined.filtered.bed"), filtered, fai_order,
                  args.apply, written)'''

# ---------------------------------------------------------------------------
# Edit 5: manifest section
# ---------------------------------------------------------------------------

OLD_MANIFEST = '''    manifest["known_design_gaps"] = KNOWN_DESIGN_GAPS'''

NEW_MANIFEST = '''    manifest["known_design_gaps"] = KNOWN_DESIGN_GAPS
    if args.exclude_exons or args.exclude_backbone:
        excl_manifest = OrderedDict()
        if args.exclude_exons:
            excl_manifest["exon_labels"] = excl_exon_labels
            excl_manifest["exon_source"] = {
                "path": os.path.abspath(args.exclude_exons),
                "md5": md5_of(args.exclude_exons),
                "provenance": excl_exon_hdr,
            }
        if args.exclude_backbone:
            excl_manifest["backbone_tiles_removed"] = len(excl_bb_names)
            excl_manifest["backbone_source"] = {
                "path": os.path.abspath(args.exclude_backbone),
                "md5": md5_of(args.exclude_backbone),
                "provenance": excl_bb_hdr,
            }
        manifest["exclusions"] = excl_manifest'''


EDITS = [
    ("CLI arguments",            OLD_ARGS,          NEW_ARGS),
    ("exclusion TSV reader",     OLD_READER_ANCHOR, NEW_READER),
    ("load/validate exclusions", OLD_WRITE_ANCHOR,  NEW_EXCLUSIONS),
    ("filtered BED emission",    OLD_COMBINED,      NEW_COMBINED),
    ("manifest section",         OLD_MANIFEST,      NEW_MANIFEST),
]


def main():
    ap = argparse.ArgumentParser(
        description="Patch bin/build_panel_assets.py for measured exclusions.")
    ap.add_argument("--target", default=TARGET_DEFAULT)
    ap.add_argument("--apply", action="store_true",
                    help="write the patch (default: dry run)")
    args = ap.parse_args()

    if not os.path.isfile(args.target):
        die("target not found: %s (run from the repo root)" % args.target)

    fh = open(args.target)
    try:
        src = fh.read()
    finally:
        fh.close()

    if MARKER in src:
        msg("skip", "%s already contains %s; nothing to do"
            % (args.target, MARKER))
        return

    bad = False
    for name, old, _new in EDITS:
        n = src.count(old)
        if n != 1:
            msg("error", "anchor for '%s' matches %d time(s); expected exactly 1"
                % (name, n))
            bad = True
    if bad:
        die("anchor mismatch: the target has drifted from the version this "
            "patch was written against. Nothing was modified.")

    for name, old, new in EDITS:
        src = src.replace(old, new)
        msg("patch", "%s: '%s'" % ("applied" if args.apply else "would apply",
                                   name))

    if not args.apply:
        msg("ok", "dry run complete; re-run with --apply to write")
        return

    bak = "%s.bak_%s_%s" % (args.target, TAG, time.strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(args.target, bak)
    msg("backup", bak)

    fh = open(args.target, "w")
    try:
        fh.write(src)
    finally:
        fh.close()

    try:
        py_compile.compile(args.target, doraise=True)
    except py_compile.PyCompileError as e:
        shutil.copy2(bak, args.target)
        die("patched file failed to compile; backup restored.\n%s" % e)

    msg("ok", "patched and compile-checked: %s" % args.target)


if __name__ == "__main__":
    main()
