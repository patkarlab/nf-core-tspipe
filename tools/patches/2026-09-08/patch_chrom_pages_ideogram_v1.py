#!/usr/bin/env python3
"""tools/patches/<date>/patch_chrom_pages_ideogram_v1.py -- MARKER IDEO_V1

C10: cytoband ideogram and band labels on the per-chromosome CNV pages
(bin/plot_targets_trio.py, --every-chrom pages only; grouped/genes styles unchanged).

What changes on the page:
  * A cytoband strip directly under the targets track, drawn in TARGET SPACE
    (same x as every panel): consecutive targets in one band form one block,
    Giemsa-shaded (gneg white .. gpos100 dark, acen red), band name inside
    when the block is wide enough (rotated when narrow). A dotted divider marks
    a place where untargeted bands were skipped between two blocks.
  * Targets-track footer: "9p21.3  21.97-21.99 Mb" instead of Mb alone.
  * Backbone runs: "9p24.1-p13.1 backbone (n=23)" instead of "backbone (n=23)".
  * The strip sits under the targets rather than above panel 1 because the
    gene names float above panel 1 (clip_on=False) and would collide.

Assets: --cytoband (UCSC cytoBand.txt) is optional; without it the page is
unchanged apart from an empty strip row. Wired from the same params.cytoband
channel as CMX_ANNOT_V1 (ch_cnv_cytoband in workflows/tspipe.nf).

Files touched:
  bin/plot_targets_trio.py         loaders, draw_ideogram, band labels, page layout, --cytoband
  modules/local/chrom_pages.nf     path cytoband input, ideo_arg, cache-bust comment
  workflows/tspipe.nf              CHROM_PAGES call gains ch_cnv_cytoband

Usage:  python3 <this file>            # dry run
        python3 <this file> --apply
Guard:  MARKER IDEO_V1 per file; every anchor exactly once in each remaining
        file before anything is written (all-or-nothing); backups
        <file>.bak_ideo_v1_<stamp>.
"""

import argparse
import sys
import time
from pathlib import Path

MARKER = "IDEO_V1"
TAG = "ideo_v1"
REPO = Path(__file__).resolve().parents[3]

# ---------------------------------------------------------------------------
# bin/plot_targets_trio.py
# ---------------------------------------------------------------------------
PY = "bin/plot_targets_trio.py"

PY_DOC_OLD = (
    "bin/plot_targets_trio.py  (TARGETS_TRIO_V2.7; explicit inputs for the CHROM_PAGES module; "
    "py3.6/matplotlib 3.2 safe)\n"
)
PY_DOC_NEW = PY_DOC_OLD + (
    "MARKER IDEO_V1: --cytoband adds a target-space cytoband strip under the targets track on\n"
    "--every-chrom pages, band names in the targets footer, band ranges on backbone runs.\n"
)

PY_HELPERS_ANCHOR = "def depth_colour(v):\n"
PY_HELPERS_NEW = '''# ---------------------------------------------------------------- IDEO_V1: cytobands
STAIN_COLOURS = {"gneg": "#ffffff", "gpos25": "#c8c8c8", "gpos50": "#9a9a9a", "gpos75": "#666666",
                 "gpos100": "#2b2b2b", "acen": "#c0392b", "gvar": "#dcdcdc", "stalk": "#e9e9e9"}
DARK_STAINS = ("gpos75", "gpos100", "acen")


def read_cytobands(path):
    """IDEO_V1: UCSC cytoBand.txt -> {chrom: [(start, end, band, stain)]} sorted by start."""
    bands = {}
    if not path:
        return bands
    with open(path) as fh:
        for line in fh:
            f = line.rstrip("\\n").split("\\t")
            if len(f) < 5 or f[0].startswith("#"):
                continue
            c = norm_chrom(f[0])
            if c not in CHROM_ORDER:
                continue
            bands.setdefault(c, []).append((int(f[1]), int(f[2]), f[3], f[4]))
    for v in bands.values():
        v.sort()
    print("[ok] cytobands: %d chromosomes" % len(bands))
    return bands


def band_at(bands, c, pos):
    """IDEO_V1: (band, stain, start, end) containing pos, or None."""
    lst = bands.get(c, [])
    if not lst:
        return None
    starts = [b[0] for b in lst]
    i = bisect.bisect_right(starts, pos) - 1
    if i < 0 or pos >= lst[i][1]:
        return None
    s, e, name, stain = lst[i]
    return name, stain, s, e


def chrom_label(c):
    return c[3:] if c.startswith("chr") else c


def band_span(bands, c, s, e):
    """IDEO_V1: '9p21.3' or '9p24.1-p13.1' for the bands overlapping [s, e); '' without a catalog."""
    hits = [b for (bs, be, b, st) in bands.get(c, []) if bs < e and be > s]
    if not hits:
        return ""
    if len(hits) == 1:
        return chrom_label(c) + hits[0]
    return "%s%s-%s" % (chrom_label(c), hits[0], hits[-1])


def draw_ideogram(ax, sel, xs, bands, args):
    """IDEO_V1: cytoband strip in target space; consecutive targets in one band form one block."""
    ax.set_ylim(0, 1); ax.set_yticks([]); ax.set_xticks([])
    for sp in ("top", "right", "left", "bottom"):
        ax.spines[sp].set_visible(False)
    ax.set_ylabel("cytoband", fontsize=8)
    if not bands or not sel:
        return
    total_w = max(x1 for _, x1 in xs) if xs else 1
    runs = []   # [chrom, band, stain, x0, x1, band_start, band_end, n_skipped_before]
    for (c, s, e, name), (x0, x1) in zip(sel, xs):
        hit = band_at(bands, c, (s + e) // 2)
        if hit is None:
            continue
        b, stain, bs, be = hit
        if runs and runs[-1][0] == c and runs[-1][1] == b:
            runs[-1][4] = x1
        else:
            skipped = 0
            if runs and runs[-1][0] == c:
                prev_end = runs[-1][6]
                skipped = sum(1 for (qs, qe, q, st) in bands[c] if qs >= prev_end and qe <= bs)
            runs.append([c, b, stain, x0, x1, bs, be, skipped])
    for c, b, stain, x0, x1, bs, be, skipped in runs:
        w = x1 - x0
        ax.add_patch(plt.Rectangle((x0, 0.12), w, 0.76, facecolor=STAIN_COLOURS.get(stain, "#ffffff"),
                                   edgecolor="0.25", linewidth=0.5, zorder=2))
        lab = chrom_label(c) + b
        col = "white" if stain in DARK_STAINS else "black"
        if w >= 0.035 * total_w:
            ax.text((x0 + x1) / 2.0, 0.5, lab, ha="center", va="center", fontsize=6.5, color=col, zorder=3)
        elif w >= 0.006 * total_w:
            ax.text((x0 + x1) / 2.0, 0.5, lab, ha="center", va="center", fontsize=5, rotation=90, color=col, zorder=3)
        if skipped:
            ax.plot([x0 - args.gap / 2.0, x0 - args.gap / 2.0], [0.02, 0.98], color="0.3", lw=0.7, ls=":", zorder=4)
    print("[ok] ideogram: %d band blocks" % len(runs))


'''

PY_SIG_OLD = "def draw_panels(axes, sel, xs, ctx, args, show_gene_bands=True, colorbar=True):\n"
PY_SIG_NEW = "def draw_panels(axes, sel, xs, ctx, args, show_gene_bands=True, colorbar=True, bands=None):   # IDEO_V1: bands\n"

PY_BB_OLD = '            lab = ("backbone (n=%d)" % n) if (n >= big and wide) else ""\n'
PY_BB_NEW = (
    '            lab = ("backbone (n=%d)" % n) if (n >= big and wide) else ""\n'
    '            if lab and bands:   # IDEO_V1: band range of the run\n'
    '                span_lab = band_span(bands, key[0], gs, ge)\n'
    '                lab = ("%s %s" % (span_lab, lab)) if span_lab else lab\n'
)

PY_FOOT_OLD = (
    '        if key[1] == "exon" or (n >= big and wide):\n'
    '            t.text((g0 + g1) / 2.0, 0.02, "%.2f-%.2f Mb" % (gs / 1e6, ge / 1e6), ha="center", va="bottom", fontsize=5.5, color="0.35")\n'
)
PY_FOOT_NEW = (
    '        if key[1] == "exon" or (n >= big and wide):\n'
    '            foot = "%.2f-%.2f Mb" % (gs / 1e6, ge / 1e6)\n'
    '            if bands and key[1] == "exon":   # IDEO_V1: band in the gene footer\n'
    '                span_lab = band_span(bands, key[0], gs, ge)\n'
    '                foot = ("%s  %s" % (span_lab, foot)) if span_lab else foot\n'
    '            t.text((g0 + g1) / 2.0, 0.02, foot, ha="center", va="bottom", fontsize=5.5, color="0.35")\n'
)

PY_PAGE_OLD = (
    "            inner = outer[0].subgridspec(4, 1, height_ratios=[1.1, 1.0, 1.1, 0.55], hspace=0.1)\n"
    "            axes = [fig.add_subplot(inner[0])]\n"
    "            axes += [fig.add_subplot(inner[i], sharex=axes[0]) for i in range(1, 4)]\n"
    "            n = draw_panels(axes, sel, xs, ctx, args)\n"
)
PY_PAGE_NEW = (
    "            # IDEO_V1: fifth row, the cytoband strip, directly under the targets track\n"
    "            inner = outer[0].subgridspec(5, 1, height_ratios=[1.1, 1.0, 1.1, 0.55, 0.26], hspace=0.1)\n"
    "            axes = [fig.add_subplot(inner[0])]\n"
    "            axes += [fig.add_subplot(inner[i], sharex=axes[0]) for i in range(1, 4)]\n"
    "            n = draw_panels(axes, sel, xs, ctx, args, bands=bands)\n"
    "            ideo = fig.add_subplot(inner[4], sharex=axes[0])\n"
    "            draw_ideogram(ideo, sel, xs, bands, args)\n"
)

PY_ARG_OLD = (
    '    ap.add_argument("--decon-min-bf", type=float, default=5.0, '
    'help="DECoN calls drawn in the gene panels at or above this BF")\n'
)
PY_ARG_NEW = PY_ARG_OLD + (
    '    ap.add_argument("--cytoband", default=None, help="UCSC cytoBand.txt (IDEO_V1): cytoband strip and band labels; optional")\n'
)

PY_LOAD_ANCHOR = "args = ap.parse_args()"
PY_LOAD_NEW = "    bands = read_cytobands(args.cytoband)   # IDEO_V1\n"

# ---------------------------------------------------------------------------
# modules/local/chrom_pages.nf
# ---------------------------------------------------------------------------
NF = "modules/local/chrom_pages.nf"

NF_IN_ANCHOR = "path baf_background"
NF_IN_NEW = "        path cytoband   // MARKER IDEO_V1 (empty list when absent)\n"

NF_DEF_OLD = "        def bg_arg     = baf_background ? \"--background ${baf_background}\" : ''\n"
NF_DEF_NEW = NF_DEF_OLD + "        def ideo_arg   = cytoband       ? \"--cytoband ${cytoband}\" : ''   // IDEO_V1\n"

NF_MKDIR_OLD = "        mkdir -p \\$MPLCONFIGDIR \\$XDG_CACHE_HOME chrom_pages\n"
NF_MKDIR_NEW = NF_MKDIR_OLD + "        # chrom pages: IDEO_V1 cytoband strip (bash comment; busts the task cache)\n"

NF_CMD_OLD = "            --targets ${panel_bed} ${snp_arg} ${bg_arg} \\\\\n"
NF_CMD_NEW = "            --targets ${panel_bed} ${snp_arg} ${bg_arg} ${ideo_arg} \\\\\n"

# ---------------------------------------------------------------------------
# workflows/tspipe.nf
# ---------------------------------------------------------------------------
WF = "workflows/tspipe.nf"
WF_CALL_OLD = "CHROM_PAGES( ch_chrom_pages_in, ch_cp_panel_bed, ch_cp_snp_base, ch_cp_baf_bg )"
WF_CALL_NEW = "CHROM_PAGES( ch_chrom_pages_in, ch_cp_panel_bed, ch_cp_snp_base, ch_cp_baf_bg, ch_cnv_cytoband )   // IDEO_V1"

EDITS = [
    (PY, PY_DOC_OLD, PY_DOC_NEW, "replace"),
    (PY, PY_HELPERS_ANCHOR, PY_HELPERS_NEW, "insert_before"),
    (PY, PY_SIG_OLD, PY_SIG_NEW, "replace"),
    (PY, PY_BB_OLD, PY_BB_NEW, "replace"),
    (PY, PY_FOOT_OLD, PY_FOOT_NEW, "replace"),
    (PY, PY_PAGE_OLD, PY_PAGE_NEW, "replace"),
    (PY, PY_ARG_OLD, PY_ARG_NEW, "replace"),
    (PY, PY_LOAD_ANCHOR, PY_LOAD_NEW, "insert_after_line"),
    (NF, NF_IN_ANCHOR, NF_IN_NEW, "insert_after_line"),
    (NF, NF_DEF_OLD, NF_DEF_NEW, "replace"),
    (NF, NF_MKDIR_OLD, NF_MKDIR_NEW, "replace"),
    (NF, NF_CMD_OLD, NF_CMD_NEW, "replace"),
    (WF, WF_CALL_OLD, WF_CALL_NEW, "replace"),
]


def apply_edit(text, old, new, mode):
    if mode == "insert_after_line":
        lines = text.split("\n")
        hits = [i for i, l in enumerate(lines) if old in l]
        if len(hits) != 1:
            return None, len(hits)
        lines.insert(hits[0] + 1, new.rstrip("\n"))
        return "\n".join(lines), 1
    n = text.count(old)
    if n != 1:
        return None, n
    repl = new + old if mode == "insert_before" else new
    return text.replace(old, repl, 1), 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    args = ap.parse_args()

    stamp = time.strftime("%Y%m%d_%H%M%S")
    staged, skipped, errors = {}, [], []
    for rel, old, new, mode in EDITS:
        if rel in skipped:
            continue
        p = REPO / rel
        if rel not in staged:
            if not p.exists():
                errors.append("%s: file not found" % rel)
                continue
            text = p.read_text()
            if MARKER in text:
                print("SKIP  %s: %s already present" % (rel, MARKER))
                skipped.append(rel)
                continue
            staged[rel] = text
        out, n = apply_edit(staged[rel], old, new, mode)
        if out is None:
            errors.append("%s: anchor matched %d times (need 1): %r" % (rel, n, old[:70]))
            continue
        staged[rel] = out

    if errors:
        print("ABORT -- nothing written:")
        for e in errors:
            print("  " + e)
        sys.exit(1)
    for rel, text in staged.items():
        orig = (REPO / rel).read_text()
        print("PLAN  %s: +%d lines, marker %s" % (rel, text.count("\n") - orig.count("\n"), MARKER))
    if not args.apply:
        print("dry run; re-run with --apply")
        return
    for rel, text in staged.items():
        p = REPO / rel
        bak = p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp))
        bak.write_text(p.read_text())
        p.write_text(text)
        print("WROTE %s (backup %s)" % (rel, bak.name))
    print("done")


if __name__ == "__main__":
    main()
