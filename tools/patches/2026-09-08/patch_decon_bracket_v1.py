#!/usr/bin/env python3
"""tools/patches/<date>/patch_decon_bracket_v1.py -- MARKER DECON_BRACKET_V1

bin/plot_targets_trio.py, gene panels:
  * DECoN writes a multi-gene call once per gene (same CNV.ID, Start, End; the
    Gene column names the gene). draw_gene_panels matched rows by coordinate
    overlap only, so every gene in a multi-gene deletion drew a bracket per row
    (CDKN2A/CDKN2B/PAX5 on 26CGH60: three rows, two visible heights).
    Now: a row is drawn only in the panel of its Gene (rows with no Gene fall
    back to overlap), and each CNV.ID is drawn once per panel.
  * Gene-panel title carries the cytoband when --cytoband is given
    ("CDKN2A (3 ex) 9p21.3").
modules/local/chrom_pages.nf: bash-comment bump so CHROM_PAGES re-executes.

Usage:  python3 <this file> [--apply]
Guard:  MARKER DECON_BRACKET_V1 per file; each anchor exactly once; all-or-nothing.
"""

import argparse
import sys
import time
from pathlib import Path

MARKER = "DECON_BRACKET_V1"
TAG = "decon_bracket_v1"
REPO = Path(__file__).resolve().parents[3]

PY = "bin/plot_targets_trio.py"
NF = "modules/local/chrom_pages.nf"

# read_decon: carry Gene and CNV.ID
RD_OLD = (
    '            calls.append((norm_chrom(r["Chromosome"]), int(float(r["Start"])), int(float(r["End"])), r["CNV.type"], bf,\n'
    '                          float(r.get("Reads.ratio", "nan") or "nan"), r.get("decision", "")))\n'
)
RD_NEW = (
    '            calls.append((norm_chrom(r["Chromosome"]), int(float(r["Start"])), int(float(r["End"])), r["CNV.type"], bf,\n'
    '                          float(r.get("Reads.ratio", "nan") or "nan"), r.get("decision", ""),\n'
    '                          (r.get("Gene") or "").strip(), (r.get("CNV.ID") or "").strip()))   # DECON_BRACKET_V1\n'
)

# draw_gene_panels signature: bands for the title
SIG_OLD = "def draw_gene_panels(gaxes, genes, sel_by_gene, ctx, args, find_seg, decon):\n"
SIG_NEW = "def draw_gene_panels(gaxes, genes, sel_by_gene, ctx, args, find_seg, decon, bands=None):   # DECON_BRACKET_V1: bands\n"

# bracket loop
LOOP_OLD = (
    "        k = 0\n"
    "        for dc, ds, de, typ, bf, ratio, dec in decon:\n"
    "            if dc != c or de < gs or ds > ge:\n"
    "                continue\n"
)
LOOP_NEW = (
    "        k = 0\n"
    "        seen_ids = set()   # DECON_BRACKET_V1\n"
    "        for dc, ds, de, typ, bf, ratio, dec, dgene, cid in decon:\n"
    "            if dc != c or de < gs or ds > ge:\n"
    "                continue\n"
    "            if dgene and dgene != g:   # DECON_BRACKET_V1: DECoN emits one row per gene; draw only this gene's row\n"
    "                continue\n"
    "            if cid:\n"
    "                if cid in seen_ids:\n"
    "                    continue\n"
    "                seen_ids.add(cid)\n"
)

# title with band
TITLE_OLD = '        ax.set_title("%s (%d ex)%s" % (g, len(ex), cn_txt), fontsize=7, pad=3)\n'
TITLE_NEW = (
    '        band_txt = ""\n'
    '        if bands:   # DECON_BRACKET_V1: cytoband in the panel title\n'
    '            bs_ = band_span(bands, c, gs, ge)\n'
    '            band_txt = ("  " + bs_) if bs_ else ""\n'
    '        ax.set_title("%s (%d ex)%s%s" % (g, len(ex), band_txt, cn_txt), fontsize=7, pad=3)\n'
)

# caller on the every-chrom page
CALL_OLD = "                draw_gene_panels(gaxes, glist, sel_by_gene, ctx, args, find_seg, decon)\n"
CALL_NEW = "                draw_gene_panels(gaxes, glist, sel_by_gene, ctx, args, find_seg, decon, bands=bands)   # DECON_BRACKET_V1\n"

# module cache bump
NF_OLD = "        # chrom pages: IDEO_V1 cytoband strip (bash comment; busts the task cache)\n"
NF_NEW = "        # chrom pages: IDEO_V1 cytoband strip; DECON_BRACKET_V1 one bracket per call per gene (bash comment; busts the task cache)\n"

EDITS = [
    (PY, RD_OLD, RD_NEW),
    (PY, SIG_OLD, SIG_NEW),
    (PY, LOOP_OLD, LOOP_NEW),
    (PY, TITLE_OLD, TITLE_NEW),
    (PY, CALL_OLD, CALL_NEW),
    (NF, NF_OLD, NF_NEW),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    staged, errors = {}, []
    for rel, old, new in EDITS:
        p = REPO / rel
        if rel not in staged:
            if not p.exists():
                errors.append("%s: file not found" % rel); continue
            text = p.read_text()
            if MARKER in text:
                print("SKIP  %s: %s already present" % (rel, MARKER)); staged[rel] = None; continue
            staged[rel] = text
        if staged[rel] is None:
            continue
        n = staged[rel].count(old)
        if n != 1:
            errors.append("%s: anchor matched %d times (need 1): %r" % (rel, n, old[:70])); continue
        staged[rel] = staged[rel].replace(old, new, 1)
    if errors:
        print("ABORT -- nothing written:")
        for e in errors:
            print("  " + e)
        sys.exit(1)
    for rel, text in staged.items():
        if text is not None:
            print("PLAN  %s: +%d lines, marker %s" % (rel, text.count("\n") - (REPO / rel).read_text().count("\n"), MARKER))
    if not args.apply:
        print("dry run; re-run with --apply"); return
    stamp = time.strftime("%Y%m%d_%H%M%S")
    for rel, text in staged.items():
        if text is None:
            continue
        p = REPO / rel
        bak = p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp))
        bak.write_text(p.read_text()); p.write_text(text)
        print("WROTE %s (backup %s)" % (rel, bak.name))
    print("done")


if __name__ == "__main__":
    main()
