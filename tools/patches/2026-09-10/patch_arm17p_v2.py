#!/usr/bin/env python3
"""ARM17P_V2 -- the dedicated 17p figure becomes a chromosome page (Nikhil, 2026-09-10, after seeing V1).

Changes versus V1 (anchor-based, all-or-nothing, MARKER-guarded, dry-run unless --apply):
  modules/local/chrom_pages.nf   plot_arm_17p.py also gets --allelic and --background (SNP-window depth
                                 ratios, computed as on the chromosome pages) and --index so the figure is
                                 registered in chrom_pages.tsv as 'chr17p'
  bin/dashboard_builder/parsers/cnv_v2.py
                                 _chrom_key sorts 'chr17p' right after 'chr17' (3-tuples throughout)
  bin/dashboard_builder/templates/sample_report.html.j2
                                 the figure card leaves the TP53 / 17p observation card; the card header
                                 links to the page instead. The page shows up in the Chromosome pages
                                 sub-tab as pill '17p' with its own Include checkbox.
File delivered alongside (copied by hand): bin/plot_arm_17p.py (V2).
Requires ARM17P_V1 to be applied. Run from the repo root:
    python3 tools/patches/2026-09-10/patch_arm17p_v2.py [--apply]
"""
import argparse
import datetime as dt
import shutil
import sys
from pathlib import Path

MARKER = "ARM17P_V2"
REQUIRES = "ARM17P_V1"
TAG = "arm17p_v2"

EDITS = {
    "modules/local/chrom_pages.nf": [
        ('            # dedicated 17p figure: depth bins + CNVkit segments, BAF per catalog site with the BAF_V2 band,\n'
         '            # PURPLE total/minor CN, panel genes (ARM17P_V1)\n'
         '            plot_arm_17p.py --sample ${meta.id} --consensus-json ${consensus_json} ${purple_arg} ${snp17_arg} \\\\\n'
         '                --out chrom_pages/${meta.id}.17p.png\n',
         '            # dedicated 17p page (ARM17P_V2): gene exon bins + SNP-window depth ratios + CNVkit segments, BAF per\n'
         '            # catalog site with the BAF_V2 band, PURPLE total/minor CN, panel genes; registered in the index as chr17p\n'
         '            plot_arm_17p.py --sample ${meta.id} --consensus-json ${consensus_json} --allelic ${allelic} ${bg_arg} \\\\\n'
         '                ${purple_arg} ${snp17_arg} --index chrom_pages/${meta.id}.chrom_pages.tsv --index-label chr17p \\\\\n'
         '                --out chrom_pages/${meta.id}.17p.png\n',
         "17p page command"),
    ],
    "bin/dashboard_builder/parsers/cnv_v2.py": [
        ('def _chrom_key(c):\n'
         '    c = str(c).replace("chr", "").upper()\n'
         '    if c == "X":\n'
         '        return (1, 23)\n'
         '    if c == "Y":\n'
         '        return (1, 24)\n'
         '    return (0, int(c)) if c.isdigit() else (2, c)\n',
         'def _chrom_key(c):\n'
         '    """Sort key: autosomes, then X, Y, then anything else; an arm suffix sorts right after its\n'
         '    chromosome ("chr17p" after "chr17"). Always a 3-tuple (ARM17P_V2)."""\n'
         '    c = str(c).replace("chr", "").upper()\n'
         '    if c == "X":\n'
         '        return (1, 23, "")\n'
         '    if c == "Y":\n'
         '        return (1, 24, "")\n'
         '    i = 0\n'
         '    while i < len(c) and c[i].isdigit():\n'
         '        i += 1\n'
         '    if i:\n'
         '        return (0, int(c[:i]), c[i:])\n'
         '    return (2, c, "")\n',
         "_chrom_key with arm suffix"),
    ],
    "bin/dashboard_builder/templates/sample_report.html.j2": [
        ('            {# MARKER ARM17P_V1: dedicated 17p figure, report-selectable like any CNV plot #}\n'
         '            {% if ctx.cnv and ctx.cnv.arm17p_figure %}\n'
         '            <div class="row g-3 mt-1 mb-2">\n'
         '              {{ macros.render_cnv_plot_card(\'arm17p::1\', \'17p: depth bins and CNVkit segments, BAF per catalog site with the BAF_V2 band, PURPLE total / minor copy number, panel genes (TP53 in bold)\', ctx.cnv.arm17p_figure, \'col-12\') }}\n'
         '            </div>\n'
         '            {% endif %}\n',
         '            {# MARKER ARM17P_V2: the 17p page lives in the Chromosome pages sub-tab (pill 17p); the card header links to it #}\n',
         "remove the embedded figure"),
        ('            <span class="fw-medium">TP53 / 17p observation</span>\n',
         '            <span class="fw-medium">TP53 / 17p observation{% if ctx.cnv and ctx.cnv.arm17p_figure %} <a class="small fw-normal ms-2" href="./{{ ctx.cnv.arm17p_figure }}" target="_blank" rel="noopener" title="Also under Chromosome pages as 17p">17p page</a>{% endif %}</span>\n',
         "link in the card header"),
    ],
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write the files (default: dry run)")
    ap.add_argument("--root", default=".", help="repo root (default: current directory)")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")

    planned = {}
    for rel, edits in EDITS.items():
        p = root / rel
        if not p.exists():
            print("[error] missing %s" % p)
            return 2
        text = p.read_text()
        if MARKER in text:
            print("[skip]  %s already carries %s" % (rel, MARKER))
            continue
        if REQUIRES not in text:
            print("[error] %s does not carry %s; apply that patch first" % (rel, REQUIRES))
            return 2
        for anchor, repl, desc in edits:
            n = text.count(anchor)
            if n != 1:
                print("[error] %s: anchor for '%s' found %d times (need exactly 1)" % (rel, desc, n))
                return 2
            text = text.replace(anchor, repl, 1)
            print("[patch] %s: %s" % (rel, desc))
        planned[p] = text

    if not planned:
        print("nothing to do")
        return 0
    if not args.apply:
        print("dry run: %d file(s) would change; re-run with --apply" % len(planned))
        return 0
    for p, text in planned.items():
        bak = p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp))
        shutil.copy2(p, bak)
        print("[backup] %s" % bak.relative_to(root))
        p.write_text(text)
        print("[write] %s (%d x %s)" % (p.relative_to(root), text.count(MARKER), MARKER))
    return 0


if __name__ == "__main__":
    sys.exit(main())
