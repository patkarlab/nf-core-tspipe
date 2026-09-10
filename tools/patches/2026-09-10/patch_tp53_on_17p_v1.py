#!/usr/bin/env python3
"""TP53_ON_17P_V1 -- the TP53 / 17p observation card moves into the 17p chromosome page (Nikhil, 2026-09-10).

Template-only change to bin/dashboard_builder/templates/sample_report.html.j2 (dry-run unless --apply):
  * the card block (MARKER TP53_OBS_V1 .. before DASH_CNV_TABS_V1) becomes a Jinja macro
    tp53_card(_t, cnv) defined in place (renders nothing where it stands);
  * the Chromosome pages loop renders the card above the figure inside the 'chr17p' pane;
  * when no chr17p page exists (older runs), the card renders at the end of the CNV tab instead;
  * the "17p page" link in the card header is removed (the card is on that page now);
  * the Reporting-tab one-line mirror is untouched.
Requires TP53_OBS_V1 and ARM17P_V2. DASHBOARD + REPORT_BUNDLE re-render only (nocache overlay).

Run from the repo root:  python3 tools/patches/2026-09-10/patch_tp53_on_17p_v1.py [--apply]
"""
import argparse
import datetime as dt
import shutil
import sys
from pathlib import Path

MARKER = "TP53_ON_17P_V1"
TAG = "tp53_on_17p_v1"
TEMPLATE = "bin/dashboard_builder/templates/sample_report.html.j2"

BLOCK_START = "        {# MARKER TP53_OBS_V1: TP53 / 17p observation block -- observations only; the interpretation wording comes from assets/<panel>/tp53_interpretation_rules.tsv #}\n"
BLOCK_END = "        {# DASH_CNV_TABS_V1: five sub-tabs; each source shown once #}\n"
HEAD_OLD = ("        {% if ctx.tp53 %}\n"
            "        {% set _t = ctx.tp53 %}\n")
HEAD_NEW = ("        {# MARKER TP53_ON_17P_V1: the card is a macro, rendered inside the chr17p chromosome page (fallback: end of the CNV tab) #}\n"
            "        {% macro tp53_card(_t, cnv) %}\n")
TAIL_OLD = "        {% endif %}\n"
TAIL_NEW = "        {% endmacro %}\n"
LINK_OLD = ('            <span class="fw-medium">TP53 / 17p observation{% if ctx.cnv and ctx.cnv.arm17p_figure %} <a class="small fw-normal ms-2" href="./{{ ctx.cnv.arm17p_figure }}" target="_blank" rel="noopener" title="Also under Chromosome pages as 17p">17p page</a>{% endif %}</span>\n')
LINK_NEW = '            <span class="fw-medium">TP53 / 17p observation</span>\n'
V2_NOTE_OLD = "            {# MARKER ARM17P_V2: the 17p page lives in the Chromosome pages sub-tab (pill 17p); the card header links to it #}\n"
V2_NOTE_NEW = "            {# MARKER ARM17P_V2: the 17p figure is the chromosome page this card sits on #}\n"

PANE_OLD = ('              <div class="tab-pane fade{% if loop.first %} show active{% endif %}" id="cnv-chrom-{{ item.chrom }}" role="tabpanel">\n'
            '                <div class="row g-3">\n'
            "                  {{ macros.render_cnv_plot_card('chrom_page::' ~ item.chrom, item.chrom ~ ' (' ~ item.n_targets ~ ' targets, ' ~ item.n_baf_sites ~ ' BAF sites)', item.path, 'col-12') }}\n")
PANE_NEW = ('              <div class="tab-pane fade{% if loop.first %} show active{% endif %}" id="cnv-chrom-{{ item.chrom }}" role="tabpanel">\n'
            "                {% if item.chrom == 'chr17p' and ctx.tp53 %}{{ tp53_card(ctx.tp53, ctx.cnv) }}{% endif %}   {# TP53_ON_17P_V1 #}\n"
            '                <div class="row g-3">\n'
            "                  {{ macros.render_cnv_plot_card('chrom_page::' ~ item.chrom, ('17p page' if item.chrom == 'chr17p' else item.chrom) ~ ' (' ~ item.n_targets ~ ' targets, ' ~ item.n_baf_sites ~ ' BAF sites)', item.path, 'col-12') }}\n")

FALLBACK_ANCHOR = ("          // DASH_CNV_TABS_V1: DataTables laid out while hidden need a column adjust once visible\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    p = root / TEMPLATE
    text = p.read_text()
    if MARKER in text:
        print("[skip] template already carries %s" % MARKER)
        return 0
    for needle, what in ((BLOCK_START, "card block start"), (BLOCK_END, "card block end"), (PANE_OLD, "chromosome pane"),
                         (LINK_OLD, "header link (ARM17P_V2)"), (V2_NOTE_OLD, "ARM17P_V2 note")):
        if text.count(needle) != 1:
            print("[error] anchor '%s' found %d times" % (what, text.count(needle)))
            return 2

    s = text.index(BLOCK_START)
    e = text.index(BLOCK_END)
    block = text[s:e]
    if not block.startswith(BLOCK_START + HEAD_OLD):
        print("[error] card block does not start with the expected if/set lines")
        return 2
    if not block.rstrip("\n").endswith(TAIL_OLD.rstrip("\n")):
        print("[error] card block does not end with {% endif %}")
        return 2
    body = block[len(BLOCK_START) + len(HEAD_OLD):]
    body = body.rstrip("\n")
    body = body[: body.rfind(TAIL_OLD.rstrip("\n"))]
    body = body.replace(LINK_OLD, LINK_NEW).replace(V2_NOTE_OLD, V2_NOTE_NEW)
    if "ctx.tp53" in body:
        print("[error] card body still references ctx.tp53; refusing")
        return 2
    body = body.replace("ctx.cnv", "cnv")
    macro = BLOCK_START + HEAD_NEW + body + TAIL_NEW + "\n"

    # 1. card block -> macro definition in place
    new = text[:s] + macro + text[e:]
    # 2. render inside the chr17p pane (+ label)
    new = new.replace(PANE_OLD, PANE_NEW, 1)
    # 3. fallback when there is no chr17p page: card at the end of the CNV tab (before the tab script)
    fb = ("        {# TP53_ON_17P_V1: fallback placement when the run has no chr17p page #}\n"
          "        {% if ctx.tp53 and not (ctx.cnv and ctx.cnv.chrom_pages and (ctx.cnv.chrom_pages | selectattr('chrom', 'equalto', 'chr17p') | list)) %}\n"
          "        <div class=\"mt-3\">{{ tp53_card(ctx.tp53, ctx.cnv) }}</div>\n"
          "        {% endif %}\n\n"
          "        <script>\n")
    script_anchor = "\n        <script>\n" + FALLBACK_ANCHOR
    if new.count(script_anchor) != 1:
        print("[error] fallback anchor (CNV tab script) found %d times" % new.count(script_anchor))
        return 2
    new = new.replace(script_anchor, "\n" + fb + FALLBACK_ANCHOR, 1)

    print("[patch] card block -> macro tp53_card(_t, cnv) (%d chars)" % len(macro))
    print("[patch] chr17p pane renders the card above the figure; label '17p page (...)'")
    print("[patch] fallback at the end of the CNV tab when no chr17p page exists")
    print("[patch] header link removed")
    if not args.apply:
        print("dry run; re-run with --apply")
        return 0
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp))
    shutil.copy2(p, bak)
    p.write_text(new)
    print("[backup] %s" % bak.relative_to(root))
    print("[write] %s (%d x %s)" % (TEMPLATE, new.count(MARKER), MARKER))
    return 0


if __name__ == "__main__":
    sys.exit(main())
