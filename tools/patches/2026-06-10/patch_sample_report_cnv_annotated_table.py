#!/usr/bin/env python3
"""
patch_sample_report_cnv_annotated_table.py

Surface the CNV annotated table in the per-sample report. Part 3 of 3 (template).

Renders ctx.cnv.annotated_table as a second DataTable in the CNV subtab, directly
under the existing tiered "Clinical CNV calls" table, and initialises it.

Two anchored edits to bin/dashboard_builder/templates/sample_report.html.j2:
  1. add the "Per-gene annotation" table block after the clinical-table block
  2. add the #cnv-annotated-table DataTable init next to the clinical one

Apply together with the cnv.py and build.py patches.

Conventions: dry-run by default; --apply writes; backup .bak_cnvannottab_<ts>;
idempotent via MARKER; status [skip]/[backup]/[patch]/[error].
"""

import argparse
import datetime
import os
import sys

TARGET = "/goast/hemat_data/nf-core-tspipe/bin/dashboard_builder/templates/sample_report.html.j2"
MARKER = "cnv-annotated-table"

OLD_BLOCK = r'''        {% if ctx.cnv.clinical_table and ctx.cnv.clinical_table.rows %}
          {{ macros.render_datatable('cnv-clinical-table', ctx.cnv.clinical_table.columns, ctx.cnv.clinical_table.rows) }}
        {% else %}
          <div class="tspipe-empty">No clinical CNV calls table available.</div>
        {% endif %}
'''

NEW_BLOCK = r'''        {% if ctx.cnv.clinical_table and ctx.cnv.clinical_table.rows %}
          {{ macros.render_datatable('cnv-clinical-table', ctx.cnv.clinical_table.columns, ctx.cnv.clinical_table.rows) }}
        {% else %}
          <div class="tspipe-empty">No clinical CNV calls table available.</div>
        {% endif %}

        {# ---- Per-gene CNV annotation table (cytoband, ClinGen dosage, gene role, heme) ---- #}
        {% if ctx.cnv.annotated_table and ctx.cnv.annotated_table.rows %}
          <h5 class="mt-4">Per-gene annotation</h5>
          <p class="text-muted small mb-2">
            Cytoband, ClinGen haploinsufficiency/triplosensitivity, gene role, and heme
            significance from <code>cnv_annotate.py</code>, including CDKN2A/2B and 9p/9q
            co-deletion rescue comments.
          </p>
          {{ macros.render_datatable('cnv-annotated-table', ctx.cnv.annotated_table.columns, ctx.cnv.annotated_table.rows) }}
        {% endif %}
'''

OLD_INIT = r'''    if ($('#cnv-clinical-table').length) { $('#cnv-clinical-table').DataTable({ pageLength: 25, order: [] }); }
'''

NEW_INIT = r'''    if ($('#cnv-clinical-table').length) { $('#cnv-clinical-table').DataTable({ pageLength: 25, order: [] }); }
    if ($('#cnv-annotated-table').length) { $('#cnv-annotated-table').DataTable({ pageLength: 25, order: [] }); }
'''


def status(tag, msg):
    sys.stdout.write("[%s] %s\n" % (tag, msg))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="Write changes. Default is dry-run.")
    ap.add_argument("--file", default=TARGET, help="Target file (default: %s)" % TARGET)
    args = ap.parse_args()

    path = args.file
    if not os.path.isfile(path):
        status("error", "target not found: %s" % path)
        return 1

    with open(path, "r") as f:
        src = f.read()

    if MARKER in src:
        status("skip", "MARKER already present; file looks patched. No changes.")
        return 0

    problems = []
    if OLD_BLOCK not in src:
        problems.append("clinical-table block anchor not found (Edit 1)")
    if OLD_INIT not in src:
        problems.append("DataTable init anchor not found (Edit 2)")
    if problems:
        for p in problems:
            status("error", p)
        status("error", "no changes made; anchors must match the live file exactly")
        return 2

    patched = src.replace(OLD_BLOCK, NEW_BLOCK, 1).replace(OLD_INIT, NEW_INIT, 1)

    if patched == src or MARKER not in patched:
        status("error", "patch did not land as expected; aborting")
        return 3

    if not args.apply:
        status("patch", "DRY-RUN ok. would apply 2 edits:")
        status("patch", "  1. render annotated_table as a second CNV-tab table")
        status("patch", "  2. add #cnv-annotated-table DataTable init")
        status("patch", "re-run with --apply to write.")
        return 0

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = "%s.bak_cnvannottab_%s" % (path, ts)
    with open(backup, "w") as f:
        f.write(src)
    status("backup", backup)
    with open(path, "w") as f:
        f.write(patched)
    status("patch", "rendered annotated CNV table in %s" % path)
    status("patch", "verify: grep -n 'cnv-annotated-table\\|Per-gene annotation' %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
