#!/usr/bin/env python3
"""
patch_viz_v1b.py -- genome overview with arm medians into CHROM_PAGES; STYLED_SCATTER
removed end to end (MARKER VIZ_V1b).

Files (7), all-or-nothing:
  modules/local/chrom_pages.nf   plot_genome_overview.py after the pages -> chrom_pages/<id>.genome.png
  workflows/tspipe.nf            STYLED_SCATTER include, channel block, call and ORGANIZE join removed
  conf/twist_apply.config        STYLED_SCATTER process block removed
  modules/local/organize_output.nf   styled_scatter_dir removed from the tuple, defs and args
  bin/organize_output.py         styled-scatter routing removed (arg kept, ignored)
  bin/dashboard_builder/parsers/cnv_v2.py   styled_scatter parse removed; genome_overview added
  bin/dashboard_builder/templates/sample_report.html.j2
                                 styled sections removed; genome overview card before reconCNV
Companion files copied alongside: bin/plot_genome_overview.py (new), bin/plot_exon_ratio.py (v1.3, rows).
modules/local/styled_scatter.nf is git rm'd by hand. Dry run by default; --apply writes .bak_viz_v1b_<ts>.
"""

import argparse
import datetime
import os
import re
import shutil
import sys

MARKER = "MARKER VIZ_V1b"
TAG = "VIZ_V1b"


def sub_once(text, pattern, repl, label, flags=re.M):
    rx = re.compile(pattern, flags)
    n = len(rx.findall(text))
    if n != 1:
        raise ValueError("anchor %s: expected 1 match, found %d (%s)" % ("not found" if n == 0 else "not unique", n, label))
    return rx.sub(repl, text, count=1), "[ok] %s" % label


def remove_block(text, start_pat, end_pat, label):
    """Remove from the line matching start_pat through the line matching end_pat (inclusive)."""
    m1 = re.search(start_pat, text, re.M)
    if not m1:
        raise ValueError("%s: start anchor not found" % label)
    m2 = re.compile(end_pat, re.M).search(text, m1.end())
    if not m2:
        raise ValueError("%s: end anchor not found" % label)
    s = text.rfind("\n", 0, m1.start()) + 1
    e = text.find("\n", m2.end()) + 1
    return text[:s] + text[e:], "[ok] %s removed" % label


# ---------------------------------------------------------------- chrom_pages module
def patch_chrom_pages(t):
    notes = []
    t, n = sub_once(t, r'^(?P<i>[ \t]*)--index chrom_pages/\$\{meta\.id\}\.chrom_pages\.tsv[ \t]*$',
                    lambda m: m.group(0) + "\n\n%s# genome overview with arm medians (%s)\n%splot_genome_overview.py --sample ${meta.id} --consensus-json ${consensus_json} --allelic ${allelic} \\\\\n%s    ${purple_arg} --out chrom_pages/${meta.id}.genome.png"
                    % (m.group("i"), TAG, m.group("i"), m.group("i")),
                    "genome overview after the pages")
    notes.append(n)
    t, n = sub_once(t, r"^ \* modules/local/chrom_pages\.nf  \(CHROM_PAGES_V1\)$", " * modules/local/chrom_pages.nf  (CHROM_PAGES_V1; %s: genome overview)" % MARKER, "header")
    notes.append(n)
    return t, notes


# ---------------------------------------------------------------- tspipe
def patch_tspipe(t):
    notes = []
    t, n = sub_once(t, r"^include \{ STYLED_SCATTER\s*\} from '\.\./modules/local/styled_scatter'[^\n]*\n", "", "include removed")
    notes.append(n)
    t, n = remove_block(t, r"^[ \t]*ch_styled_in = CNV_CALLING\.out\.cnvkit_cnr[ \t]*$", r"^[ \t]*STYLED_SCATTER\( ch_styled_in \)[ \t]*$", "STYLED_SCATTER channel and call")
    notes.append(n)
    t, n = sub_once(t, r"^[ \t]*\.join\(STYLED_SCATTER\.out\.dir\)[^\n]*\n", "", "ORGANIZE join removed")
    notes.append(n)
    t, n = sub_once(t, r"^(?P<i>[ \t]*)// VIZ_V1: styled CNVkit scatters \(BAF panel from the raw Mutect2 VCF\) and reconCNV[ \t]*$",
                    lambda m: "%s// VIZ_V1: reconCNV (styled scatters removed by %s; the genome overview lives in CHROM_PAGES)" % (m.group("i"), MARKER), "comment")
    notes.append(n)
    return t, notes


# ---------------------------------------------------------------- twist_apply
def patch_twist_apply(t):
    notes = []
    t, n = remove_block(t, r"^[ \t]*withName: 'STYLED_SCATTER' \{[ \t]*$", r"^[ \t]*\}[ \t]*$", "STYLED_SCATTER process block")
    notes.append(n)
    t, n = sub_once(t, r"^(?P<i>[ \t]*)// VIZ_V1: styled scatters beside the consensus; reconCNV on the host env[ \t]*$",
                    lambda m: "%s// VIZ_V1: reconCNV on the host env (%s: styled scatters removed)" % (m.group("i"), MARKER), "comment")
    notes.append(n)
    return t, notes


# ---------------------------------------------------------------- organize
def patch_org_nf(t):
    notes = []
    t, n = sub_once(t, r"^(?P<i>[ \t]*)path\(styled_scatter_dir\), path\(reconcnv_dir\)   // MARKER VIZ_V1[ \t]*$",
                    lambda m: "%spath(reconcnv_dir)   // MARKER VIZ_V1 (%s: styled_scatter_dir removed)" % (m.group("i"), MARKER), "tuple")
    notes.append(n)
    t, n = sub_once(t, r"^[ \t]*def styled_scatter_dir_arg = styled_scatter_dir \? \"--styled-scatter-dir \$\{styled_scatter_dir\}\" : ''[ \t]*\n", "", "def removed")
    notes.append(n)
    t, n = sub_once(t, r"^[ \t]*\$\{styled_scatter_dir_arg\} \\\\[ \t]*\n", "", "script arg removed")
    notes.append(n)
    return t, notes


def patch_org_py(t):
    notes = []
    t, n = sub_once(t, r'^            \(args\.styled_scatter_dir, "styled_scatter", "styled CNVkit scatters"\),\n', "", "routing entry removed")
    notes.append(n)
    t, n = sub_once(t, r'^    parser\.add_argument\("--styled-scatter-dir", default=None, help="STYLED_SCATTER directory \(optional; VIZ_V1\)"\)\n',
                    '    parser.add_argument("--styled-scatter-dir", default=None, help="unused since %s; accepted for compatibility")\n' % MARKER, "arg kept, inert")
    notes.append(n)
    return t, notes


# ---------------------------------------------------------------- parser
def patch_parser(t):
    notes = []
    t, n = remove_block(t, r'^    ss = v2 / "styled_scatter"$', r'^        out\["styled_scatter"\] = \{"overview": _pngs\("overview"\), "per_chromosome": per_chrom, "per_gene": per_gene\}$', "styled_scatter parse")
    notes.append(n)
    t, n = sub_once(t, r'^    # ---- styled scatters and reconCNV \(MARKER VIZ_V1\) ----\n',
                    '    # ---- genome overview (%s) and reconCNV (MARKER VIZ_V1) ----\n    go = v2 / "chrom_pages" / ("%%s.genome.png" %% sample)\n    if go.exists():\n        out["genome_overview"] = _rel(go, sample_dir)\n' % MARKER,
                    "genome_overview parse")
    notes.append(n)
    return t, notes


# ---------------------------------------------------------------- template
TEMPLATE_BLOCK = '''        {# ---- genome overview (arm medians) + reconCNV (MARKER VIZ_V1b) ---- #}
        {% if ctx.cnv.genome_overview %}
          <h5 class="mt-4">Genome-wide</h5>
          <p class="text-muted small mb-2">Per-bin log2 with one median line per chromosome arm (red below -0.25, green above +0.20), BAF (grey balanced, green deviated), PURPLE copy number. Arm medians are printed under the chromosome labels.</p>
          <div class="row g-3">
            {{ macros.render_cnv_plot_card('genome_overview::1', 'Genome-wide overview', ctx.cnv.genome_overview, 'col-12') }}
          </div>
        {% endif %}
'''


def patch_template(t):
    notes = []
    t, n = remove_block(t, r"^        \{# ---- genome-wide styled scatter \+ reconCNV \(MARKER VIZ_V1\) ---- #\}$",
                        r"^          </div>\n        \{% endif %\}\n        \{% if ctx\.cnv\.reconcnv %\}$", "styled overview section")
    # remove_block cut through the reconcnv opening line; restore it
    t = t.replace("          <h5 class=\"mt-4\">reconCNV (interactive)</h5>", "        {% if ctx.cnv.reconcnv %}\n          <h5 class=\"mt-4\">reconCNV (interactive)</h5>", 1)
    notes.append(n)
    t, n = remove_block(t, r"^        \{% if ctx\.cnv\.styled_scatter and ctx\.cnv\.styled_scatter\.per_chromosome %\}$", r"^          </details>\n        \{% endif %\}\n        \{% if ctx\.cnv\.styled_scatter and ctx\.cnv\.styled_scatter\.per_gene %\}$", "per-chromosome styled section")
    notes.append(n)
    t, n = remove_block(t, r"^          <details class=\"mt-3\"><summary class=\"h6\">Per-gene styled scatters", r"^          </details>\n        \{% endif %\}$", "per-gene styled section")
    notes.append(n)
    t, n = sub_once(t, r"^(?P<i>[ \t]*)\{% if ctx\.cnv\.reconcnv %\}[ \t]*$", lambda m: TEMPLATE_BLOCK + m.group(0), "genome overview card before reconCNV")
    notes.append(n)
    return t, notes


FILES = [
    ("modules/local/chrom_pages.nf",                            patch_chrom_pages),
    ("workflows/tspipe.nf",                                     patch_tspipe),
    ("conf/twist_apply.config",                                 patch_twist_apply),
    ("modules/local/organize_output.nf",                        patch_org_nf),
    ("bin/organize_output.py",                                  patch_org_py),
    ("bin/dashboard_builder/parsers/cnv_v2.py",                 patch_parser),
    ("bin/dashboard_builder/templates/sample_report.html.j2",   patch_template),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    planned, failed = [], False
    for rel, fn in FILES:
        path = os.path.join(args.root, rel)
        print("== %s" % rel)
        if not os.path.isfile(path):
            print("   [error] file not found"); failed = True; continue
        original = open(path).read()
        if MARKER in original:
            print("   [skip] %s already present" % MARKER); continue
        try:
            new_text, notes = fn(original)
        except ValueError as exc:
            print("   [error] %s" % exc); failed = True; continue
        for n in notes:
            print("   %s" % n)
        if rel.endswith(".py"):
            try:
                compile(new_text, path, "exec")
            except SyntaxError as exc:
                print("   [error] does not compile: %s" % exc); failed = True; continue
        if rel.endswith(".nf"):
            blocks = new_text.split('"""')
            bad = [l for b in blocks[1::2] for l in b.splitlines() if re.search(r'\S\s+//', l)]
            if bad:
                print("   [error] '//' inside a script block: %s" % bad[0].strip()); failed = True; continue
        if rel.endswith(".j2"):
            try:
                import jinja2
                jinja2.Environment().parse(new_text); print("   [check] jinja2 parse ok")
            except ImportError:
                print("   [check] jinja2 not importable here")
            except Exception as exc:  # noqa: BLE001
                print("   [error] template does not parse: %s" % exc); failed = True; continue
        b0, b1 = original.count("{") - original.count("}"), new_text.count("{") - new_text.count("}")
        print("   [check] markers %d (expected 1); brace balance %d/%d; 'styled' mentions left: %d" % (new_text.count(MARKER), b0, b1, len(re.findall(r"styled_scatter|STYLED_SCATTER", new_text))))
        if new_text.count(MARKER) != 1 or (rel.endswith((".nf", ".config")) and b0 != b1):
            print("   [error] verification failed"); failed = True; continue
        planned.append((path, original, new_text))
    if failed:
        print("\n[error] one or more files failed; nothing written"); sys.exit(1)
    if not planned:
        print("\n[skip] nothing to do"); sys.exit(0)
    if not args.apply:
        print("\n[dry-run] %d file(s) would change; re-run with --apply" % len(planned)); sys.exit(0)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    for path, original, new_text in planned:
        backup = "%s.bak_viz_v1b_%s" % (path, ts)
        shutil.copy2(path, backup)
        with open(path, "w") as fh:
            fh.write(new_text)
        print("[backup] %s" % os.path.relpath(backup, args.root))
        print("[patch]  wrote %s" % os.path.relpath(path, args.root))


if __name__ == "__main__":
    main()
