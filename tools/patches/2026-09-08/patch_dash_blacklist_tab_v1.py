#!/usr/bin/env python3
"""tools/patches/<date>/patch_dash_blacklist_tab_v1.py -- MARKER DASH_BLACKLIST_V1 (D16)

Adds a "Blacklisted" tab to the sample report: every row of the sample's
somaticseq.filtered.tsv with Filter == BLACKLIST, with gene, HGVSc/p, class,
VAF, callers, the blacklist reason (curated ARTIFACT or the cohort-derived
UBIQUITOUS_IN_NORMALS / RECURRENT_IN_NORMALS_LOWVAF / POPULATION_POLYMORPHISM_LOCAL),
its evidence string and date. The nav badge counts rows with >= 2 callers;
single-caller blips are in the table but not in the badge. DataTable with
search, so a reviewer can look up the CBL/ASXL1/GATA2 rows that no longer
appear in the clinical table and see exactly why.

Template only; re-render with -c /tmp/dash_nocache.config.

Usage:  python3 <this file> [--apply]
"""

import argparse
import sys
import time
from pathlib import Path

MARKER = "DASH_BLACKLIST_V1"
TAG = "dash_blacklist_v1"
REPO = Path(__file__).resolve().parents[3]
TPL = "bin/dashboard_builder/templates/sample_report.html.j2"

NAV_OLD = (
    "      <li class=\"nav-item\"><button class=\"nav-link\"        data-bs-toggle=\"pill\" data-bs-target=\"#tab-filtered\"  "
    "type=\"button\" role=\"tab\">Variants &mdash; All Filtered</button></li>\n"
)
NAV_NEW = NAV_OLD + (
    "      {# DASH_BLACKLIST_V1 (D16) #}\n"
    "      {% set _bl_rows = (ctx.filtered.rows if ctx.filtered and ctx.filtered.rows else []) | selectattr('Filter', 'equalto', 'BLACKLIST') | list %}\n"
    "      {% set _bl_supported = _bl_rows | selectattr('VariantCaller_Count', 'ne', '-1') | selectattr('VariantCaller_Count', 'ne', '1') | selectattr('VariantCaller_Count', 'ne', '0') | list %}\n"
    "      <li class=\"nav-item\"><button class=\"nav-link\"        data-bs-toggle=\"pill\" data-bs-target=\"#tab-blacklist\" type=\"button\" role=\"tab\">"
    "Blacklisted <span class=\"badge bg-secondary ms-1\">{{ _bl_supported | length }}</span></button></li>\n"
)

PANE_ANCHOR = "      <div class=\"tab-pane fade\" id=\"tab-filtered\" role=\"tabpanel\">\n"
PANE_NEW = (
    "      {# ===== Blacklisted tab (DASH_BLACKLIST_V1, D16) ===== #}\n"
    "      <div class=\"tab-pane fade\" id=\"tab-blacklist\" role=\"tabpanel\">\n"
    "        <h4>Blacklisted variants</h4>\n"
    "        <p class=\"text-muted small mb-2\">\n"
    "          Calls removed from the clinical table by the SNV blacklist (<code>references/blacklist_file.tsv</code>): curated artefacts, and\n"
    "          loci derived from the panel-of-normals cohort\n"
    "          (<code>UBIQUITOUS_IN_NORMALS</code>: same allele in at least half the normals; <code>RECURRENT_IN_NORMALS_LOWVAF</code>: in at least 10% of normals\n"
    "          below 25% VAF with caller support; <code>POPULATION_POLYMORPHISM_LOCAL</code>: germline-range VAF in at least 10% of normals). The evidence column\n"
    "          gives the cohort count and VAF range. {{ _bl_supported | length }} of {{ _bl_rows | length }} rows have two or more callers.\n"
    "        </p>\n"
    "        {% if _bl_rows %}\n"
    "          <div class=\"table-responsive\">\n"
    "            <table id=\"blacklist-table\" class=\"table table-sm table-striped table-hover w-100\">\n"
    "              <thead><tr><th>gene</th><th>position</th><th>HGVSc</th><th>HGVSp</th><th>class</th><th>VAF %</th><th>callers</th><th>n</th><th>reason</th><th>evidence</th><th>added</th></tr></thead>\n"
    "              <tbody>\n"
    "                {% for r in _bl_rows %}\n"
    "                  {% set _parts = (r.Blacklist_Reason or '') | string | replace('|', '\\u0001') | string %}\n"
    "                  {% set _p = _parts.split('\\u0001') %}\n"
    "                  <tr><td>{{ r.Gene }}</td><td class=\"text-nowrap\">{{ r.Chr }}:{{ r.Start }} {{ r.Ref }}&gt;{{ r.Alt }}</td>\n"
    "                      <td>{{ r.HGVSc if r.HGVSc != '-1' else '' }}</td><td>{{ r.HGVSp if r.HGVSp != '-1' else '' }}</td>\n"
    "                      <td>{{ r.Variant_Class if r.Variant_Class is defined else '' }}</td><td>{{ r.VAF_pct if r.VAF_pct != '-1' else '' }}</td>\n"
    "                      <td>{{ r.Callers if r.Callers != '-1' else '' }}</td><td>{{ r.VariantCaller_Count if r.VariantCaller_Count != '-1' else '' }}</td>\n"
    "                      <td>{{ _p[1] if _p | length > 1 else _p[0] }}</td><td class=\"small\">{{ _p[2] if _p | length > 2 else '' }}</td><td>{{ r.Blacklist_Date }}</td></tr>\n"
    "                {% endfor %}\n"
    "              </tbody>\n"
    "            </table>\n"
    "          </div>\n"
    "        {% else %}\n"
    "          <div class=\"tspipe-empty\">No blacklisted variants in this sample.</div>\n"
    "        {% endif %}\n"
    "      </div>\n"
    "\n"
) + PANE_ANCHOR

JS_OLD = "    if ($('#coverage-table').length)     { $('#coverage-table').DataTable({ pageLength: 25, order: [] }); }\n"
JS_NEW = JS_OLD + "    if ($('#blacklist-table').length)    { $('#blacklist-table').DataTable({ pageLength: 25, order: [[7, 'desc'], [5, 'desc']] }); }   // DASH_BLACKLIST_V1\n"

EDITS = [(NAV_OLD, NAV_NEW), (PANE_ANCHOR, PANE_NEW), (JS_OLD, JS_NEW)]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    p = REPO / TPL
    text = p.read_text()
    if MARKER in text:
        print("SKIP  %s: already applied" % TPL); return
    new = text
    for old, rep in EDITS:
        if new.count(old) != 1:
            print("ABORT -- nothing written: anchor matched %d times: %r" % (new.count(old), old[:70])); sys.exit(1)
        new = new.replace(old, rep, 1)
    print("PLAN  %s: %+d lines, marker %s" % (TPL, new.count("\n") - text.count("\n"), MARKER))
    if not args.apply:
        print("dry run; re-run with --apply"); return
    p.with_name(p.name + ".bak_%s_%s" % (TAG, time.strftime("%Y%m%d_%H%M%S"))).write_text(text)
    p.write_text(new); print("WROTE %s\ndone" % TPL)


if __name__ == "__main__":
    main()
