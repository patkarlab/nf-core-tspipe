#!/usr/bin/env python3
"""
patch_build_cnv_fallback_annotated.py

Surface the CNV annotated table in the per-sample report. Part 2 of 3 (build).

When cnv.parse() raises, build.py substitutes a minimal ctx["cnv"] dict. Add the
new annotated_table key there so the template's `ctx.cnv.annotated_table` test is
explicitly None on the failure path (defensive; Jinja already treats a missing key
as falsy, but this keeps the fallback shape consistent with the parser).

One anchored edit to bin/dashboard_builder/build.py.

Conventions: dry-run by default; --apply writes; backup .bak_cnvannottab_<ts>;
idempotent via MARKER; status [skip]/[backup]/[patch]/[error].
"""

import argparse
import datetime
import os
import sys

TARGET = "/goast/hemat_data/nf-core-tspipe/bin/dashboard_builder/build.py"
MARKER = "annotated_table"

OLD = r'''        ctx["cnv"] = {"clinical_table": None, "scatter_png": None, "diagram_pdf": None,
                      "per_chrom_pngs": [], "per_gene_pngs": []}
'''

NEW = r'''        ctx["cnv"] = {"clinical_table": None, "annotated_table": None,
                      "scatter_png": None, "diagram_pdf": None,
                      "per_chrom_pngs": [], "per_gene_pngs": []}
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

    if OLD not in src:
        status("error", "cnv fallback dict anchor not found; live file differs from expected")
        status("error", "no changes made")
        return 2

    patched = src.replace(OLD, NEW, 1)

    if patched == src or MARKER not in patched:
        status("error", "patch did not land as expected; aborting")
        return 3

    if not args.apply:
        status("patch", "DRY-RUN ok. would add annotated_table: None to the cnv parse-failure fallback.")
        status("patch", "re-run with --apply to write.")
        return 0

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = "%s.bak_cnvannottab_%s" % (path, ts)
    with open(backup, "w") as f:
        f.write(src)
    status("backup", backup)
    with open(path, "w") as f:
        f.write(patched)
    status("patch", "added annotated_table to cnv fallback in %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
