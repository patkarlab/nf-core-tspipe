#!/usr/bin/env python3
"""
patch_tspipe_cnv_annotated_join.py

Issue 2 (preserve the orphaned CNV annotated table). Part 3 of 3 (workflow).

Joins CNV_CALLING.out.annotated into ch_organize so the annotated TSV is passed
to ORGANIZE_OUTPUT. It is placed immediately after clinical_report, matching the
new input-tuple position in modules/local/organize_output.nf.

CNV_ANNOTATE.out.tsv always emits (non-optional, same chain as clinical_report),
so a plain .join() is correct here -- no remainder handling needed.

One anchored edit to workflows/tspipe.nf. MUST be applied together with the
organize_output.py and organize_output.nf patches.

Conventions: dry-run by default; --apply writes; backup .bak_cnvannot_<timestamp>;
idempotent via MARKER; status [skip]/[backup]/[patch]/[error]. Python 3.6-safe.
"""

import argparse
import datetime
import os
import sys

TARGET = "/goast/hemat_data/nf-core-tspipe/workflows/tspipe.nf"
MARKER = "CNV_CALLING.out.annotated"

OLD_JOIN = (
    "        .join(CNV_CALLING.out.clinical_report)                               // + cnv_clinical_tsv\n"
    "        .join(CNV_CALLING.out.cnvkit_diagram_pdf)                            // + cnvkit_diagram\n"
)

NEW_JOIN = (
    "        .join(CNV_CALLING.out.clinical_report)                               // + cnv_clinical_tsv\n"
    "        .join(CNV_CALLING.out.annotated)                                     // + cnv_annotated_tsv\n"
    "        .join(CNV_CALLING.out.cnvkit_diagram_pdf)                            // + cnvkit_diagram\n"
)


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

    if OLD_JOIN not in src:
        status("error", "ch_organize CNV join anchor not found; live file differs from expected")
        status("error", "no changes made")
        return 2

    patched = src.replace(OLD_JOIN, NEW_JOIN, 1)

    if patched == src or MARKER not in patched:
        status("error", "patch did not land as expected; aborting")
        return 3

    if not args.apply:
        status("patch", "DRY-RUN ok. would add .join(CNV_CALLING.out.annotated) to ch_organize.")
        status("patch", "re-run with --apply to write.")
        return 0

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = "%s.bak_cnvannot_%s" % (path, ts)
    with open(backup, "w") as f:
        f.write(src)
    status("backup", backup)
    with open(path, "w") as f:
        f.write(patched)
    status("patch", "added CNV_CALLING.out.annotated join in %s" % path)
    status("patch", "verify: grep -n 'CNV_CALLING.out.annotated' %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
