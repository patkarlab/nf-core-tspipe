#!/usr/bin/env python3
"""
patch_dashboard_cnv_v2.py -- CNV tab on the v2 outputs (MARKER DASH_CNV_V1).

Files (2), all-or-nothing:
  bin/dashboard_builder/build.py   imports parsers.cnv_v2; merges its dict into
                                   ctx["cnv"] right after the legacy parse (own try/except)
  bin/dashboard_builder/templates/sample_report.html.j2
                                   v2 block at the top of the CNV tab: PURPLE + sex-check
                                   summary line, consensus table (tiers, arms), DECoN table,
                                   chromosome pages gallery, exon-plot gallery. Legacy
                                   sections stay below until 7b.
parsers/cnv_v2.py is copied alongside (not patched). Dry run by default; --apply
writes .bak_dash_cnv_v2_<ts> backups.
"""

import argparse
import datetime
import os
import re
import shutil
import sys

MARKER = "MARKER DASH_CNV_V1"
TAG = "DASH_CNV_V1"


def sub_once(text, pattern, repl, label, flags=re.M):
    rx = re.compile(pattern, flags)
    n = len(rx.findall(text))
    if n != 1:
        raise ValueError("anchor %s: expected 1 match, found %d (%s)" % ("not found" if n == 0 else "not unique", n, label))
    return rx.sub(repl, text, count=1), "[ok] %s" % label


def patch_build(t):
    notes = []
    t, n = sub_once(t, r"^from parsers import cnv as p_cnv[ \t]*$",
                    lambda m: m.group(0) + "\nfrom parsers import cnv_v2 as p_cnv_v2   # %s" % MARKER, "import cnv_v2")
    notes.append(n)
    t, n = sub_once(t, r'^(?P<i>[ \t]*)ctx\["cnv"\] = p_cnv\.parse\(effective_dir, sample\)[ \t]*$',
                    lambda m: m.group(0) + "\n%s# %s: v2 outputs (clinical/cnv/) merged into the same context; never fatal\n"
                                          "%stry:\n%s    ctx[\"cnv\"].update(p_cnv_v2.parse(effective_dir, sample))\n"
                                          "%sexcept Exception as exc:  # noqa: BLE001\n%s    logging.warning(\"[%%s] cnv v2 parse failed: %%s\", sample, exc)"
                    % (m.group("i"), TAG, m.group("i"), m.group("i"), m.group("i"), m.group("i")),
                    "merge v2 into ctx.cnv")
    notes.append(n)
    return t, notes


TEMPLATE_BLOCK = '''        {# ---- v2: consensus, PURPLE, DECoN, chromosome pages, exon plots (MARKER DASH_CNV_V1) ---- #}
        {% if ctx.cnv.purple or ctx.cnv.sex_check %}
          <div class="alert alert-light border small mb-3">
            {% if ctx.cnv.purple %}
              <strong>PURPLE</strong>: status {{ ctx.cnv.purple.status }}, purity {{ ctx.cnv.purple.purity }},
              ploidy {{ ctx.cnv.purple.ploidy }}, sex {{ ctx.cnv.purple.gender }}
              {% if ctx.cnv.purple.trusted != 'TRUE' %}<span class="badge bg-warning text-dark">advisory</span>{% endif %}
            {% endif %}
            {% if ctx.cnv.sex_check %}
              &nbsp;|&nbsp; <strong>Sex check</strong>: {{ ctx.cnv.sex_check.get('resolved_sex', ctx.cnv.sex_check.get('inferred_sex', '')) }}
              (X/A {{ ctx.cnv.sex_check.get('x_a_ratio', '') }}, {{ ctx.cnv.sex_check.get('status', '') }})
            {% endif %}
            {% if ctx.cnv.consensus_tiers %}
              &nbsp;|&nbsp; <strong>Consensus</strong>:
              {% for k, v in ctx.cnv.consensus_tiers.items() %}<span class="badge bg-secondary">{{ k }} {{ v }}</span> {% endfor %}
            {% endif %}
            {% if ctx.cnv.blacklisted %}
              &nbsp;|&nbsp; blacklisted: {{ ctx.cnv.blacklisted | join(', ') }}
            {% endif %}
          </div>
        {% endif %}

        {% if ctx.cnv.consensus_table and ctx.cnv.consensus_table.rows %}
          <h5 class="mt-2">Consensus CNV calls (K CNVkit, G GATK, B BAF, P PureCN, E DECoN, H PURPLE)</h5>
          <p class="text-muted small mb-2">
            Non-neutral genes from <code>cnv_consensus_multi.py</code>. TIER_1: depth direction plus an
            independent arm; TIER_2: two depth arms or two independent arms; TIER_3: single arm;
            REVIEW: arms disagree. Blacklisted genes are excluded.
          </p>
          {{ macros.render_datatable('cnv-consensus-table', ctx.cnv.consensus_table.columns, ctx.cnv.consensus_table.rows) }}
        {% elif ctx.cnv.consensus_tiers is defined %}
          <div class="tspipe-empty">No non-neutral consensus CNV calls.</div>
        {% endif %}

        {% if ctx.cnv.decon_table and ctx.cnv.decon_table.rows %}
          <h5 class="mt-4">DECoN exon-level calls</h5>
          <p class="text-muted small mb-2">Reportable calls and multi-exon calls at BF &ge; 5 (sub-threshold ones carry decision BELOW_BF).</p>
          {{ macros.render_datatable('cnv-decon-table', ctx.cnv.decon_table.columns, ctx.cnv.decon_table.rows) }}
        {% endif %}

        {% if ctx.cnv.chrom_pages %}
          <h5 class="mt-4">Chromosome pages ({{ ctx.cnv.chrom_pages|length }})</h5>
          <p class="text-muted small mb-2">
            Target space, genomic order: depth per exon/backbone/SNP window (green neutral, red loss, blue gain),
            BAF from the panel's het catalog (grey balanced, green deviated), PURPLE copy number, and one exon
            panel per gene with DECoN brackets.
          </p>
          <div class="row g-3">
            {% for item in ctx.cnv.chrom_pages %}
              {{ macros.render_cnv_plot_card('chrom_page::' ~ item.chrom, item.chrom ~ ' (' ~ item.n_targets ~ ' targets, ' ~ item.n_baf_sites ~ ' BAF sites)', item.path, 'col-12') }}
            {% endfor %}
          </div>
        {% endif %}

        {% if ctx.cnv.exon_plots %}
          <h5 class="mt-4">Exon-level figures ({{ ctx.cnv.exon_plots|length }})</h5>
          <p class="text-muted small mb-2">Chromosomes with a consensus call, a DECoN call at BF &ge; 5, or a focal-CNV gene.</p>
          <div class="row g-3">
            {% for item in ctx.cnv.exon_plots %}
              {{ macros.render_cnv_plot_card('exon_plot::' ~ item.chrom, item.chrom ~ ': ' ~ item.reasons, item.path, 'col-12') }}
            {% endfor %}
          </div>
        {% endif %}

        <hr class="mt-4">
        <h5 class="mt-3 text-muted">Legacy CNV views</h5>

'''


def patch_template(t):
    notes = []
    t, n = sub_once(t, r"^(?P<i>[ \t]*)\{# ---- Clinical CNV calls table ---- #\}[ \t]*$",
                    lambda m: TEMPLATE_BLOCK + m.group(0), "v2 block before the legacy clinical table")
    notes.append(n)
    return t, notes


FILES = [("bin/dashboard_builder/build.py", patch_build),
         ("bin/dashboard_builder/templates/sample_report.html.j2", patch_template)]


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
        if rel.endswith(".j2"):
            try:
                import jinja2
                jinja2.Environment().parse(new_text)
                print("   [check] jinja2 parse ok")
            except ImportError:
                print("   [check] jinja2 not importable here; template not parsed")
            except Exception as exc:  # noqa: BLE001
                print("   [error] template does not parse: %s" % exc); failed = True; continue
        print("   [check] markers %d (expected 1)" % new_text.count(MARKER))
        if new_text.count(MARKER) != 1:
            failed = True; continue
        planned.append((path, original, new_text))
    if failed:
        print("\n[error] one or more files failed; nothing written"); sys.exit(1)
    if not planned:
        print("\n[skip] nothing to do"); sys.exit(0)
    if not args.apply:
        print("\n[dry-run] %d file(s) would change; re-run with --apply" % len(planned)); sys.exit(0)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    for path, original, new_text in planned:
        backup = "%s.bak_dash_cnv_v2_%s" % (path, ts)
        shutil.copy2(path, backup)
        with open(path, "w") as fh:
            fh.write(new_text)
        print("[backup] %s" % os.path.relpath(backup, args.root))
        print("[patch]  wrote %s" % os.path.relpath(path, args.root))


if __name__ == "__main__":
    main()
