#!/usr/bin/env python3
"""ARM17P_V1 -- dedicated 17p figure (Nikhil, 2026-09-10).

Patches (anchor-based, all-or-nothing, MARKER-guarded, dry-run unless --apply):
  modules/local/chrom_pages.nf                 plot_arm_17p.py after the genome overview -> chrom_pages/<S>.17p.png
  bin/dashboard_builder/parsers/cnv_v2.py      ctx["cnv"]["arm17p_figure"] when the PNG exists
  bin/dashboard_builder/templates/sample_report.html.j2
                                               report-selectable plot card inside the TP53 / 17p observation card
File delivered alongside (copied by hand): bin/plot_arm_17p.py (chmod +x).
The module script changes, so CHROM_PAGES re-executes for every sample on resume, followed by
ORGANIZE_OUTPUT, DASHBOARD and REPORT_BUNDLE. The figure lands in clinical/cnv/chrom_pages/ and
therefore in the report bundle (whole cnv/ tree is copied).

Run from the repo root:  python3 tools/patches/2026-09-10/patch_arm17p_v1.py [--apply]
"""
import argparse
import datetime as dt
import shutil
import sys
from pathlib import Path

MARKER = "ARM17P_V1"
TAG = "arm17p_v1"

EDITS = {
    "modules/local/chrom_pages.nf": [
        (' * modules/local/chrom_pages.nf  (CHROM_PAGES_V1; MARKER VIZ_V1b: genome overview)\n',
         ' * modules/local/chrom_pages.nf  (CHROM_PAGES_V1; MARKER VIZ_V1b: genome overview; MARKER ARM17P_V1: 17p figure)\n',
         "header"),
        ('        def ideo_arg   = cytoband       ? "--cytoband ${cytoband}" : \'\'   // IDEO_V1\n',
         '        def ideo_arg   = cytoband       ? "--cytoband ${cytoband}" : \'\'   // IDEO_V1\n'
         '        def snp17_arg  = snp_base_bed   ? "--snp-bed ${snp_base_bed}" : \'\'   // ARM17P_V1\n',
         "snp arg"),
        ('            plot_genome_overview.py --sample ${meta.id} --consensus-json ${consensus_json} --allelic ${allelic} \\\\\n'
         '                ${purple_arg} --out chrom_pages/${meta.id}.genome.png\n',
         '            plot_genome_overview.py --sample ${meta.id} --consensus-json ${consensus_json} --allelic ${allelic} \\\\\n'
         '                ${purple_arg} --out chrom_pages/${meta.id}.genome.png\n'
         '\n'
         '            # dedicated 17p figure: depth bins + CNVkit segments, BAF per catalog site with the BAF_V2 band,\n'
         '            # PURPLE total/minor CN, panel genes (ARM17P_V1)\n'
         '            plot_arm_17p.py --sample ${meta.id} --consensus-json ${consensus_json} ${purple_arg} ${snp17_arg} \\\\\n'
         '                --out chrom_pages/${meta.id}.17p.png\n',
         "17p figure command"),
    ],
    "bin/dashboard_builder/parsers/cnv_v2.py": [
        ('    go = v2 / "chrom_pages" / ("%s.genome.png" % sample)\n'
         '    if go.exists():\n'
         '        out["genome_overview"] = _rel(go, sample_dir)\n',
         '    go = v2 / "chrom_pages" / ("%s.genome.png" % sample)\n'
         '    if go.exists():\n'
         '        out["genome_overview"] = _rel(go, sample_dir)\n'
         '    a17 = v2 / "chrom_pages" / ("%s.17p.png" % sample)   # ARM17P_V1: dedicated 17p figure\n'
         '    if a17.exists():\n'
         '        out["arm17p_figure"] = _rel(a17, sample_dir)\n',
         "arm17p_figure"),
    ],
    "bin/dashboard_builder/templates/sample_report.html.j2": [
        ('            <details class="small">\n'
         '              <summary class="text-muted">Fields available to the rule table (this sample\'s values)</summary>\n',
         '            {# MARKER ARM17P_V1: dedicated 17p figure, report-selectable like any CNV plot #}\n'
         '            {% if ctx.cnv and ctx.cnv.arm17p_figure %}\n'
         '            <div class="row g-3 mt-1 mb-2">\n'
         '              {{ macros.render_cnv_plot_card(\'arm17p::1\', \'17p: depth bins and CNVkit segments, BAF per catalog site with the BAF_V2 band, PURPLE total / minor copy number, panel genes (TP53 in bold)\', ctx.cnv.arm17p_figure, \'col-12\') }}\n'
         '            </div>\n'
         '            {% endif %}\n'
         '            <details class="small">\n'
         '              <summary class="text-muted">Fields available to the rule table (this sample\'s values)</summary>\n',
         "figure card in the TP53 block"),
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
