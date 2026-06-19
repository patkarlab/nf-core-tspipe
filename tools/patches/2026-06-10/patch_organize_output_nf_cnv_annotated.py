#!/usr/bin/env python3
"""
patch_organize_output_nf_cnv_annotated.py

Issue 2 (preserve the orphaned CNV annotated table). Part 2 of 3 (module).

Adds the CNV annotated TSV to the ORGANIZE_OUTPUT process so it is staged and
passed through to organize_output.py.

Two anchored edits to modules/local/organize_output.nf:
  1. input tuple: add `path(cnv_annotated_tsv)` immediately after cnv_clinical_tsv
  2. script: add `--cnv-annotated-tsv ${cnv_annotated_tsv}` after --cnv-clinical-tsv

The input-tuple position MUST match the new .join() position in tspipe.nf
(annotated is joined immediately after clinical_report). MUST be applied together
with the organize_output.py and tspipe.nf patches.

Conventions: dry-run by default; --apply writes; backup .bak_cnvannot_<timestamp>;
idempotent via MARKER; status [skip]/[backup]/[patch]/[error]. Python 3.6-safe.

Groovy note: ${cnv_annotated_tsv} is intentionally Groovy-interpolated; the
trailing `\\` is a line continuation in the GString script body (matches the
surrounding lines).
"""

import argparse
import datetime
import os
import sys

TARGET = "/goast/hemat_data/nf-core-tspipe/modules/local/organize_output.nf"
MARKER = "cnv_annotated_tsv"

OLD_INPUT = r'''              path(cnv_clinical_tsv),
              path(cnvkit_diagram),
'''

NEW_INPUT = r'''              path(cnv_clinical_tsv),
              path(cnv_annotated_tsv),
              path(cnvkit_diagram),
'''

OLD_CLI = r'''            --cnv-clinical-tsv    ${cnv_clinical_tsv} \\
            --cnvkit-diagram-pdf  ${cnvkit_diagram} \\
'''

NEW_CLI = r'''            --cnv-clinical-tsv    ${cnv_clinical_tsv} \\
            --cnv-annotated-tsv   ${cnv_annotated_tsv} \\
            --cnvkit-diagram-pdf  ${cnvkit_diagram} \\
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
    if OLD_INPUT not in src:
        problems.append("input-tuple anchor (cnv_clinical_tsv / cnvkit_diagram) not found")
    if OLD_CLI not in src:
        problems.append("script CLI anchor (--cnv-clinical-tsv / --cnvkit-diagram-pdf) not found")
    if problems:
        for p in problems:
            status("error", p)
        status("error", "no changes made; anchors must match the live file exactly")
        return 2

    patched = src.replace(OLD_INPUT, NEW_INPUT, 1).replace(OLD_CLI, NEW_CLI, 1)

    if patched == src or MARKER not in patched:
        status("error", "patch did not land as expected; aborting")
        return 3

    if not args.apply:
        status("patch", "DRY-RUN ok. would apply 2 edits:")
        status("patch", "  1. add path(cnv_annotated_tsv) to the input tuple")
        status("patch", "  2. add --cnv-annotated-tsv to the script invocation")
        status("patch", "re-run with --apply to write.")
        return 0

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = "%s.bak_cnvannot_%s" % (path, ts)
    with open(backup, "w") as f:
        f.write(src)
    status("backup", backup)
    with open(path, "w") as f:
        f.write(patched)
    status("patch", "wired cnv_annotated_tsv through ORGANIZE_OUTPUT in %s" % path)
    status("patch", "verify: grep -n 'cnv_annotated_tsv\\|cnv-annotated-tsv' %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
