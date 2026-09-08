#!/usr/bin/env python3
"""tools/patches/<date>/patch_dash_tier_filter_v1.py -- MARKER DASH_TIER_V1

C11: the CNV consensus table was rendered as a plain HTML table. Line ~744 of
sample_report.html.j2 still initialised '#cnv-annotated-table' (the CNV_ANNOTATE
table retired in 7b) and nothing initialised '#cnv-consensus-table' or
'#cnv-decon-table', so the consensus table had no sort, search or paging.

Change (template only, bin/dashboard_builder/templates/sample_report.html.j2):
  1. A tier button group above the consensus table:
     Reportable (TIER_1+TIER_2, default) | TIER_1 | TIER_2 | TIER_3 | REVIEW | All.
  2. DataTable init for '#cnv-consensus-table' and '#cnv-decon-table'; the tier
     column is located by header text, so column order changes do not break it.
     The dead '#cnv-annotated-table' init is removed.

bin/ is not hashed: re-render with `-c /tmp/dash_nocache.config`.

Usage:  python3 <this file>            # dry run
        python3 <this file> --apply
Guard:  MARKER DASH_TIER_V1; every anchor exactly once; all-or-nothing;
        backup <file>.bak_dash_tier_v1_<stamp>.
"""

import argparse
import sys
import time
from pathlib import Path

MARKER = "DASH_TIER_V1"
TAG = "dash_tier_v1"
REPO = Path(__file__).resolve().parents[3]
TARGET = "bin/dashboard_builder/templates/sample_report.html.j2"

# 1. tier buttons above the consensus table
TABLE_OLD = (
    "          {{ macros.render_datatable('cnv-consensus-table', "
    "ctx.cnv.consensus_table.columns, ctx.cnv.consensus_table.rows) }}\n"
)
TABLE_NEW = (
    "          {# DASH_TIER_V1: tier filter; first button is the default view #}\n"
    "          <div id=\"cnv-tier-filter\" class=\"btn-group btn-group-sm mb-2\" role=\"group\" aria-label=\"Tier filter\">\n"
    "            <button type=\"button\" class=\"btn btn-outline-secondary\" data-tiers=\"TIER_1,TIER_2\">Reportable (TIER_1 + TIER_2)</button>\n"
    "            <button type=\"button\" class=\"btn btn-outline-secondary\" data-tiers=\"TIER_1\">TIER_1</button>\n"
    "            <button type=\"button\" class=\"btn btn-outline-secondary\" data-tiers=\"TIER_2\">TIER_2</button>\n"
    "            <button type=\"button\" class=\"btn btn-outline-secondary\" data-tiers=\"TIER_3\">TIER_3</button>\n"
    "            <button type=\"button\" class=\"btn btn-outline-secondary\" data-tiers=\"REVIEW\">REVIEW</button>\n"
    "            <button type=\"button\" class=\"btn btn-outline-secondary\" data-tiers=\"\">All</button>\n"
    "          </div>\n"
) + TABLE_OLD

# 2. DataTable init: replace the dead cnv-annotated-table line
INIT_OLD = (
    "    if ($('#cnv-annotated-table').length) { $('#cnv-annotated-table')"
    ".DataTable({ pageLength: 25, order: [] }); }\n"
)
INIT_NEW = (
    "    // DASH_TIER_V1: consensus + DECoN tables as DataTables; tier filter on the consensus table\n"
    "    if ($('#cnv-consensus-table').length) {\n"
    "      const cnvTable = $('#cnv-consensus-table').DataTable({ pageLength: 25, order: [] });\n"
    "      const tierIdx = $('#cnv-consensus-table thead th').toArray()\n"
    "        .findIndex(function (th) { return th.textContent.trim() === 'tier'; });\n"
    "      $('#cnv-tier-filter [data-tiers]').on('click', function () {\n"
    "        $('#cnv-tier-filter .btn').removeClass('active');\n"
    "        $(this).addClass('active');\n"
    "        if (tierIdx < 0) { return; }\n"
    "        const tiers = String($(this).attr('data-tiers') || '');\n"
    "        const rx = tiers ? '^(' + tiers.split(',').join('|') + ')$' : '';\n"
    "        cnvTable.column(tierIdx).search(rx, true, false).draw();\n"
    "      });\n"
    "      $('#cnv-tier-filter [data-tiers]').first().trigger('click');\n"
    "    }\n"
    "    if ($('#cnv-decon-table').length) { $('#cnv-decon-table').DataTable({ pageLength: 25, order: [] }); }\n"
)

EDITS = [(TABLE_OLD, TABLE_NEW), (INIT_OLD, INIT_NEW)]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    args = ap.parse_args()

    p = REPO / TARGET
    if not p.exists():
        print("ABORT: %s not found" % TARGET)
        sys.exit(1)
    text = p.read_text()
    if MARKER in text:
        print("SKIP  %s: %s already present" % (TARGET, MARKER))
        return
    new_text = text
    for old, new in EDITS:
        n = new_text.count(old)
        if n != 1:
            print("ABORT -- nothing written: anchor matched %d times (need 1): %r" % (n, old[:70]))
            sys.exit(1)
        new_text = new_text.replace(old, new, 1)
    print("PLAN  %s: +%d lines, marker %s" % (TARGET, new_text.count("\n") - text.count("\n"), MARKER))
    if not args.apply:
        print("dry run; re-run with --apply")
        return
    stamp = time.strftime("%Y%m%d_%H%M%S")
    bak = p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp))
    bak.write_text(text)
    p.write_text(new_text)
    print("WROTE %s (backup %s)" % (TARGET, bak.name))
    print("done")


if __name__ == "__main__":
    main()
