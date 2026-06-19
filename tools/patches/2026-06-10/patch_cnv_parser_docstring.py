#!/usr/bin/env python3
"""
patch_cnv_parser_docstring.py

Issue 2 (documentation correctness; independent of the 3-part wiring change).

The dashboard CNV parser docstring claims the clinical CNV TSV columns it expects
come "from the pipeline's cnv_annotate.py". They do not: the column set it lists
(gene, tier, call, ..., LOO_FP_pct, clinical_significance, arm_level_event;
lowercase) is the cnv_clinical_report.py (12f) schema. cnv_annotate.py (18) emits
a different, capitalized schema (Gene, Cytoband, CNV_Direction, Tier, LOO_FP_Rate,
...). The parser reads <sample>_cnv_clinical.tsv, which the pipeline populates from
clinical_report. Correct the attribution.

One anchored edit to bin/dashboard_builder/parsers/cnv.py (comment only).

Conventions: dry-run by default; --apply writes; backup .bak_cnvdoc_<timestamp>;
idempotent via MARKER; status [skip]/[backup]/[patch]/[error]. Python 3.6-safe.
"""

import argparse
import datetime
import os
import sys

TARGET = "/goast/hemat_data/nf-core-tspipe/bin/dashboard_builder/parsers/cnv.py"
MARKER = "from the pipeline's cnv_clinical_report.py"

OLD_DOC = "The CNV clinical TSV columns we expect (from the pipeline's cnv_annotate.py)::"
NEW_DOC = "The CNV clinical TSV columns we expect (from the pipeline's cnv_clinical_report.py)::"


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

    if OLD_DOC not in src:
        status("error", "docstring anchor not found; live file differs from expected")
        status("error", "no changes made")
        return 2

    patched = src.replace(OLD_DOC, NEW_DOC, 1)

    if patched == src or MARKER not in patched:
        status("error", "patch did not land as expected; aborting")
        return 3

    if not args.apply:
        status("patch", "DRY-RUN ok. would correct CNV schema attribution (cnv_annotate.py -> cnv_clinical_report.py).")
        status("patch", "re-run with --apply to write.")
        return 0

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = "%s.bak_cnvdoc_%s" % (path, ts)
    with open(backup, "w") as f:
        f.write(src)
    status("backup", backup)
    with open(path, "w") as f:
        f.write(patched)
    status("patch", "corrected CNV schema attribution in %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
