#!/usr/bin/env python3
"""
patch_viz_v1.py -- styled CNVkit scatter and reconCNV into the pipeline, the
clinical tree and the CNV tab (MARKER VIZ_V1). Handoff item 12, remaining half.

Files (7), all-or-nothing:
  workflows/tspipe.nf            includes; STYLED_SCATTER and RECONCNV after CHROM_PAGES
                                 (CNVkit cnr/call.cns/genemetrics + raw Mutect2 VCF;
                                 reference tuple and the reconCNV config as values);
                                 ORGANIZE joins gain the two directories
  conf/twist_apply.config        params reconcnv_template/reconcnv_env; process blocks
                                 (STYLED_SCATTER publish; RECONCNV host env + publish)
  modules/local/organize_output.nf   tuple gains styled_scatter_dir, reconcnv_dir
  bin/organize_output.py         --styled-scatter-dir, --reconcnv-dir -> clinical/cnv/{styled_scatter,reconcnv}
  bin/dashboard_builder/parsers/cnv_v2.py   styled_scatter {overview, per_chromosome, per_gene}, reconcnv path
  bin/dashboard_builder/templates/sample_report.html.j2
                                 after the DECoN table: genome-wide styled scatter cards,
                                 reconCNV card (iframe + open link), collapsed
                                 per-chromosome and per-gene scatter galleries
Dry run by default; --apply writes .bak_viz_v1_<ts> backups.
"""

import argparse
import datetime
import os
import re
import shutil
import sys

MARKER = "MARKER VIZ_V1"
TAG = "VIZ_V1"


def sub_once(text, pattern, repl, label, flags=re.M):
    rx = re.compile(pattern, flags)
    n = len(rx.findall(text))
    if n != 1:
        raise ValueError("anchor %s: expected 1 match, found %d (%s)" % ("not found" if n == 0 else "not unique", n, label))
    return rx.sub(repl, text, count=1), "[ok] %s" % label


# ------------------------------------------------------------------ tspipe
TSPIPE_CALL = '''
{i}// {m}: styled CNVkit scatters (BAF panel from the raw Mutect2 VCF) and reconCNV
{i}ch_viz_vcf = VARIANT_CALLING.out.mutect2_vcf.map {{ it -> [ it[0], it[1] ] }}
{i}ch_styled_in = CNV_CALLING.out.cnvkit_cnr
{i}    .join( CNV_CALLING.out.cnvkit_calls,       by: 0 )
{i}    .join( ch_viz_vcf,                         by: 0 )
{i}    .join( CNV_CALLING.out.cnvkit_genemetrics, by: 0 )
{i}STYLED_SCATTER( ch_styled_in )
{i}def reconcnv_tpl = params.containsKey('reconcnv_template') ? params.reconcnv_template : "${{projectDir}}/assets/reconcnv/reconcnv_config_twist_myeloid.json"
{i}ch_reconcnv_tpl = Channel.value(file(reconcnv_tpl, checkIfExists: true))
{i}ch_recon_in = CNV_CALLING.out.cnvkit_cnr
{i}    .join( CNV_CALLING.out.cnvkit_calls, by: 0 )
{i}    .join( ch_viz_vcf,                   by: 0 )
{i}RECONCNV( ch_recon_in, ch_reference, ch_reconcnv_tpl )'''


def patch_tspipe(t):
    notes = []
    t, n = sub_once(t, r"^include \{ CHROM_PAGES\s*\} from '\.\./modules/local/chrom_pages'[^\n]*$",
                    lambda m: m.group(0) + "\ninclude { STYLED_SCATTER      } from '../modules/local/styled_scatter'        // %s\ninclude { RECONCNV            } from '../modules/local/reconcnv'" % MARKER,
                    "includes")
    notes.append(n)
    t, n = sub_once(t, r"^(?P<i>[ \t]*)CHROM_PAGES\( ch_chrom_pages_in, ch_cp_panel_bed, ch_cp_snp_base, ch_cp_baf_bg \)[ \t]*$",
                    lambda m: m.group(0) + TSPIPE_CALL.format(i=m.group("i"), m=TAG), "STYLED_SCATTER and RECONCNV after CHROM_PAGES")
    notes.append(n)
    t, n = sub_once(t, r"^(?P<i>[ \t]*)\.join\(PREPROCESSING\.out\.sex_check\)[ \t]*// \+ sex_check[ \t]*$",
                    lambda m: m.group(0) + "\n%s.join(STYLED_SCATTER.out.dir)                                        // + styled_scatter_dir (%s)\n%s.join(RECONCNV.out.dir)                                              // + reconcnv_dir" % (m.group("i"), TAG, m.group("i")),
                    "ORGANIZE joins")
    notes.append(n)
    return t, notes


# ------------------------------------------------------------------ twist_apply
PARAMS = '''
{i}// {m}: reconCNV (host env; py3.6 + bokeh 1.4) and the panel config
{i}reconcnv_env      = '/home/hemat/anaconda3/envs/reconCNV'
{i}reconcnv_template = "${{projectDir}}/assets/reconcnv/reconcnv_config_twist_myeloid.json"'''

PROCESS = '''{i}// {m}: styled scatters beside the consensus; reconCNV on the host env
{i}withName: 'STYLED_SCATTER' {{
{i}    publishDir = [
{i}        path: {{ "${{params.outdir}}/${{meta.id}}/cnv_consensus_multi" }},
{i}        mode: 'copy',
{i}        pattern: 'styled_scatter'
{i}    ]
{i}}}
{i}withName: 'RECONCNV' {{
{i}    container    = null
{i}    beforeScript = 'export PATH=/home/hemat/anaconda3/envs/reconCNV/bin:/home/hemat/anaconda3/envs/targeted-seq/bin:$PATH'
{i}    publishDir = [
{i}        path: {{ "${{params.outdir}}/${{meta.id}}/cnv_consensus_multi" }},
{i}        mode: 'copy',
{i}        pattern: 'reconcnv'
{i}    ]
{i}}}
'''


def patch_twist_apply(t):
    notes = []
    t, n = sub_once(t, r"^(?P<i>[ \t]*)hmf_pcf_gamma[ \t]*=[ \t]*50[ \t]*$",
                    lambda m: m.group(0) + PARAMS.format(i=m.group("i"), m=MARKER), "params")
    notes.append(n)
    t, n = sub_once(t, r"^(?P<i>[ \t]*)withName: 'CNV_CONSENSUS_MULTI' \{[ \t]*$",
                    lambda m: PROCESS.format(i=m.group("i"), m=TAG) + m.group(0), "process blocks")
    notes.append(n)
    return t, notes


# ------------------------------------------------------------------ organize module + script
def patch_org_nf(t):
    notes = []
    t, n = sub_once(t, r"^(?P<i>[ \t]*)path\(sex_check\)[ \t]*$",
                    lambda m: "%spath(sex_check),\n%spath(styled_scatter_dir), path(reconcnv_dir)   // %s" % (m.group("i"), m.group("i"), MARKER),
                    "input tuple")
    notes.append(n)
    t, n = sub_once(t, r"^(?P<i>[ \t]*)def sex_check_arg = sex_check \? \"--sex-check \$\{sex_check\}\" : ''[ \t]*$",
                    lambda m: m.group(0) + "\n%sdef styled_scatter_dir_arg = styled_scatter_dir ? \"--styled-scatter-dir ${styled_scatter_dir}\" : ''\n%sdef reconcnv_dir_arg = reconcnv_dir ? \"--reconcnv-dir ${reconcnv_dir}\" : ''" % (m.group("i"), m.group("i")),
                    "arg definitions")
    notes.append(n)
    t, n = sub_once(t, r"^(?P<i>[ \t]*)\$\{sex_check_arg\}[ \t]*$",
                    lambda m: "%s${sex_check_arg} \\\\\n%s${styled_scatter_dir_arg} \\\\\n%s${reconcnv_dir_arg}" % (m.group("i"), m.group("i"), m.group("i")),
                    "script args")
    notes.append(n)
    return t, notes


def patch_org_py(t):
    notes = []
    t, n = sub_once(t, r'^    parser\.add_argument\("--sex-check", default=None, help="SEX_CHECK table \(optional; ORG_CNV_V1\)"\)\n',
                    lambda m: m.group(0) + '    parser.add_argument("--styled-scatter-dir", default=None, help="STYLED_SCATTER directory (optional; %s)")\n'
                                          '    parser.add_argument("--reconcnv-dir", default=None, help="RECONCNV directory (optional; %s)")\n' % (TAG, TAG),
                    "argparse")
    notes.append(n)
    t, n = sub_once(t, r'^            \(args\.purple_dir,      "purple",      "PURPLE outputs"\)\):\n',
                    '            (args.purple_dir,      "purple",      "PURPLE outputs"),\n'
                    '            (args.styled_scatter_dir, "styled_scatter", "styled CNVkit scatters"),\n'
                    '            (args.reconcnv_dir,    "reconcnv",    "reconCNV")):   # %s\n' % MARKER,
                    "routing tuple")
    notes.append(n)
    return t, notes


# ------------------------------------------------------------------ parser
PARSER_BLOCK = '''    # ---- styled scatters and reconCNV (%s) ----
    ss = v2 / "styled_scatter"
    if ss.is_dir():
        def _pngs(sub):
            d = ss / sub
            return sorted([_rel(p, sample_dir) for p in d.glob("*.png")]) if d.is_dir() else []
        per_chrom = []
        for p in _pngs("per_chromosome"):
            m = re.search(r"chr([0-9XY]+)", Path(p).name)
            per_chrom.append({"chrom": ("chr" + m.group(1)) if m else Path(p).stem, "path": p})
        per_chrom.sort(key=lambda x: _chrom_key(x["chrom"]))
        per_gene = [{"gene": Path(p).stem.split("_gene_")[-1].split(".")[0], "path": p} for p in _pngs("per_gene")]
        out["styled_scatter"] = {"overview": _pngs("overview"), "per_chromosome": per_chrom, "per_gene": per_gene}
    rc = v2 / "reconcnv" / ("%%s.reconcnv.html" %% sample)
    if rc.exists():
        out["reconcnv"] = _rel(rc, sample_dir)
    return out
''' % MARKER


def patch_parser(t):
    notes = []
    t, n = sub_once(t, r"^import csv\nfrom pathlib import Path\n", "import csv\nimport re\nfrom pathlib import Path\n", "import re")
    notes.append(n)
    t, n = sub_once(t, r"^        out\[\"exon_plots\"\] = plots\n    return out\n", lambda m: '        out["exon_plots"] = plots\n' + PARSER_BLOCK, "styled scatter + reconCNV parse")
    notes.append(n)
    return t, notes


# ------------------------------------------------------------------ template
TEMPLATE_BLOCK = '''        {# ---- genome-wide styled scatter + reconCNV (MARKER VIZ_V1) ---- #}
        {% if ctx.cnv.styled_scatter and ctx.cnv.styled_scatter.overview %}
          <h5 class="mt-4">Genome-wide (styled CNVkit scatter with BAF)</h5>
          <div class="row g-3">
            {% for p in ctx.cnv.styled_scatter.overview %}
              {{ macros.render_cnv_plot_card('styled_overview::' ~ loop.index, 'Genome-wide scatter ' ~ loop.index, p, 'col-12') }}
            {% endfor %}
          </div>
        {% endif %}
        {% if ctx.cnv.reconcnv %}
          <h5 class="mt-4">reconCNV (interactive)</h5>
          <p class="text-muted small mb-2">Bokeh view of the CNVkit ratio, segments and het SNPs. <a href="{{ ctx.cnv.reconcnv }}" target="_blank">Open in a new tab</a>.</p>
          <div class="ratio" style="--bs-aspect-ratio: 60%;"><iframe src="{{ ctx.cnv.reconcnv }}" loading="lazy" style="border:1px solid #dee2e6;"></iframe></div>
        {% endif %}
        {% if ctx.cnv.styled_scatter and ctx.cnv.styled_scatter.per_chromosome %}
          <details class="mt-4"><summary class="h6">Per-chromosome styled scatters ({{ ctx.cnv.styled_scatter.per_chromosome|length }})</summary>
            <div class="row g-3 mt-1">
              {% for item in ctx.cnv.styled_scatter.per_chromosome %}
                {{ macros.render_cnv_plot_card('styled_chrom::' ~ item.chrom, item.chrom ~ ' (styled scatter)', item.path, 'col-md-6 col-xl-4') }}
              {% endfor %}
            </div>
          </details>
        {% endif %}
        {% if ctx.cnv.styled_scatter and ctx.cnv.styled_scatter.per_gene %}
          <details class="mt-3"><summary class="h6">Per-gene styled scatters ({{ ctx.cnv.styled_scatter.per_gene|length }})</summary>
            <div class="row g-3 mt-1">
              {% for item in ctx.cnv.styled_scatter.per_gene %}
                {{ macros.render_cnv_plot_card('styled_gene::' ~ item.gene, item.gene, item.path, 'col-md-6 col-xl-3') }}
              {% endfor %}
            </div>
          </details>
        {% endif %}

'''


def patch_template(t):
    notes = []
    t, n = sub_once(t, r"^(?P<i>[ \t]*)\{% if ctx\.cnv\.chrom_pages %\}[ \t]*$", lambda m: TEMPLATE_BLOCK + m.group(0), "cards before the chromosome pages")
    notes.append(n)
    return t, notes


FILES = [
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
        print("   [check] markers %d (expected 1); brace balance %d/%d" % (new_text.count(MARKER), b0, b1))
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
        backup = "%s.bak_viz_v1_%s" % (path, ts)
        shutil.copy2(path, backup)
        with open(path, "w") as fh:
            fh.write(new_text)
        print("[backup] %s" % os.path.relpath(backup, args.root))
        print("[patch]  wrote %s" % os.path.relpath(path, args.root))


if __name__ == "__main__":
    main()
