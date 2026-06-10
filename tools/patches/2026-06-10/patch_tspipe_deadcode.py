#!/usr/bin/env python3
"""
patch_tspipe_deadcode.py

ISSUE 4 (cleanup): workflows/tspipe.nf imports SV_CALLING and REPORTING but never
invokes them (SV_CALLING's only call is commented out; final assembly is done
directly via IGV_REPORTS + ORGANIZE_OUTPUT, not through the REPORTING
subworkflow). The header comment also advertises a "-> SV_CALLING" and
"-> REPORTING" flow that does not run. Remove the two dead include lines and
correct the header so the file describes the actual DAG.

No runtime behaviour changes (unused DSL2 includes are inert); this is purely
removing misleading dead code.

Three anchored edits to workflows/tspipe.nf:
  1. rewrite the step-ordering header comment
  2. delete `include { SV_CALLING ... }`
  3. delete `include { REPORTING ... }`

Conventions: dry-run by default; --apply writes; backup .bak_deadcode_<timestamp>;
idempotent via MARKER; status [skip]/[backup]/[patch]/[error]. Python 3.6-safe.
"""

import argparse
import datetime
import os
import sys

TARGET = "/goast/hemat_data/nf-core-tspipe/workflows/tspipe.nf"
MARKER = "SV_CALLING and REPORTING are intentionally not wired into the active"

# --- Edit 1: header comment -------------------------------------------------
OLD_HDR = r''' *     PREPROCESSING -> VARIANT_CALLING -> SOMATICSEQ_ENSEMBLE -> FLT3_ITD
 *                   -> CNV_CALLING -> SV_CALLING
 *                   -> ANNOTATION -> REPORTING
'''

NEW_HDR = r''' *     PREPROCESSING -> VARIANT_CALLING -> SOMATICSEQ_ENSEMBLE -> FLT3_ITD
 *                   -> CNV_CALLING -> ANNOTATION
 *                   -> IGV_REPORTS -> ORGANIZE_OUTPUT -> DASHBOARD -> REPORT_BUNDLE
 *
 * NOTE: SV_CALLING and REPORTING are intentionally not wired into the active
 * DAG. SV calling is disabled (no SV deliverable on this panel yet); final
 * assembly is done directly via IGV_REPORTS + ORGANIZE_OUTPUT below rather than
 * through the REPORTING subworkflow.
'''

# --- Edit 2 + 3: drop the two dead include lines ----------------------------
OLD_SV = "include { SV_CALLING          } from '../subworkflows/local/sv_calling'\n"
OLD_REP = "include { REPORTING           } from '../subworkflows/local/reporting'\n"


def status(tag, msg):
    sys.stdout.write("[%s] %s\n" % (tag, msg))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true",
                    help="Write changes. Default is dry-run.")
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
    if OLD_HDR not in src:
        problems.append("header step-ordering anchor not found (Edit 1)")
    if OLD_SV not in src:
        problems.append("SV_CALLING include anchor not found (Edit 2)")
    if OLD_REP not in src:
        problems.append("REPORTING include anchor not found (Edit 3)")
    if problems:
        for p in problems:
            status("error", p)
        status("error", "no changes made; anchors must match the live file exactly")
        return 2

    patched = src
    patched = patched.replace(OLD_HDR, NEW_HDR, 1)
    patched = patched.replace(OLD_SV, "", 1)
    patched = patched.replace(OLD_REP, "", 1)

    if patched == src or MARKER not in patched:
        status("error", "patch did not land as expected; aborting")
        return 3

    if not args.apply:
        status("patch", "DRY-RUN ok. would apply 3 edits:")
        status("patch", "  1. correct step-ordering header comment")
        status("patch", "  2. remove dead SV_CALLING include")
        status("patch", "  3. remove dead REPORTING include")
        status("patch", "re-run with --apply to write.")
        return 0

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = "%s.bak_deadcode_%s" % (path, ts)
    with open(backup, "w") as f:
        f.write(src)
    status("backup", backup)

    with open(path, "w") as f:
        f.write(patched)
    status("patch", "removed dead includes + corrected header in %s" % path)
    status("patch", "verify: grep -n 'SV_CALLING\\|REPORTING' %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
