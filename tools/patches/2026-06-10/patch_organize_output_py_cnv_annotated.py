#!/usr/bin/env python3
"""
patch_organize_output_py_cnv_annotated.py

Issue 2 (preserve the orphaned CNV annotated table). Part 1 of 3 (bin script).

CNV_ANNOTATE produces a per-gene annotated table (cytoband, ClinGen HI/TS, gene
role, heme significance, CDKN2A/2B + 9p/9q rescue commentary) that is richer than
the tiered clinical report on those axes. It is currently computed for every
sample, published to scratch cnv/annotated, and then deleted by the onComplete
sweep -- never delivered. This routes it into the clinical/ deliverable tree so it
survives the sweep.

Two anchored edits to bin/organize_output.py:
  1. add the --cnv-annotated-tsv argument
  2. hardlink it into clinical/cnv_consensus/<sample>_cnv_annotated.tsv, next to
     the existing <sample>_cnv_clinical.tsv (the dashboard reads _cnv_clinical.tsv
     and is unaffected by the new sibling file)

MUST be applied together with the organize_output.nf and tspipe.nf patches; the
three change ORGANIZE_OUTPUT's interface in lockstep.

Conventions: dry-run by default; --apply writes; backup .bak_cnvannot_<timestamp>;
idempotent via MARKER; status [skip]/[backup]/[patch]/[error]. Python 3.6-safe.
"""

import argparse
import datetime
import os
import sys

TARGET = "/goast/hemat_data/nf-core-tspipe/bin/organize_output.py"
MARKER = "--cnv-annotated-tsv"

OLD_ARG = r'''    parser.add_argument("--cnv-clinical-tsv", required=True)
    parser.add_argument("--cnvkit-diagram-pdf", required=True)
'''

NEW_ARG = r'''    parser.add_argument("--cnv-clinical-tsv", required=True)
    parser.add_argument("--cnv-annotated-tsv", required=True)
    parser.add_argument("--cnvkit-diagram-pdf", required=True)
'''

OLD_LINK = r'''    cnv_dst = out / "cnv_consensus"
    hardlink(args.cnv_clinical_tsv,
             cnv_dst / (s + "_cnv_clinical.tsv"),
             "CNV consensus clinical TSV")
'''

NEW_LINK = r'''    cnv_dst = out / "cnv_consensus"
    hardlink(args.cnv_clinical_tsv,
             cnv_dst / (s + "_cnv_clinical.tsv"),
             "CNV consensus clinical TSV")
    hardlink(args.cnv_annotated_tsv,
             cnv_dst / (s + "_cnv_annotated.tsv"),
             "CNV per-gene annotated table (cytoband, ClinGen HI/TS, gene role, heme significance, CDKN2A/2B + 9p/9q rescue)")
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
    if OLD_ARG not in src:
        problems.append("argparse anchor (--cnv-clinical-tsv / --cnvkit-diagram-pdf) not found")
    if OLD_LINK not in src:
        problems.append("cnv_dst hardlink block anchor not found")
    if problems:
        for p in problems:
            status("error", p)
        status("error", "no changes made; anchors must match the live file exactly")
        return 2

    patched = src.replace(OLD_ARG, NEW_ARG, 1).replace(OLD_LINK, NEW_LINK, 1)

    if patched == src or MARKER not in patched:
        status("error", "patch did not land as expected; aborting")
        return 3

    if not args.apply:
        status("patch", "DRY-RUN ok. would apply 2 edits:")
        status("patch", "  1. add --cnv-annotated-tsv argument")
        status("patch", "  2. hardlink it to clinical/cnv_consensus/<sample>_cnv_annotated.tsv")
        status("patch", "re-run with --apply to write.")
        return 0

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = "%s.bak_cnvannot_%s" % (path, ts)
    with open(backup, "w") as f:
        f.write(src)
    status("backup", backup)
    with open(path, "w") as f:
        f.write(patched)
    status("patch", "added --cnv-annotated-tsv + hardlink in %s" % path)
    status("patch", "verify: grep -n 'cnv_annotated_tsv\\|_cnv_annotated.tsv' %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
