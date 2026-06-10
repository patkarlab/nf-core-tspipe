#!/usr/bin/env python3
"""
patch_nextflow_config_blacklist_skipfrom.py

Two anchored edits to nextflow.config.

ISSUE 1 (clinical): the default snv_blacklist points at the legacy 4-column
file references/blacklist_snvs_hg38.tsv (Chr/Start/Ref/Alt). bin/apply_blacklist.py
parses an 11-column schema and SKIPS every non-conforming line, so any run that
does not load conf/gandalf.config (which overrides to blacklist_file.tsv) silently
applies an empty blacklist and lets known artefacts through. Repoint the default
to the 11-column references/blacklist_file.tsv so the documented default matches
the parser.

ISSUE 4 (cleanup): remove the dead `skip_from` param. The README states there is
no --skip-from in the Nextflow port (-resume replaces it) and nothing in the
codebase reads params.skip_from.

Conventions:
  - dry-run by default; pass --apply to write
  - backup: <file>.bak_blklist_skipfrom_<timestamp>
  - idempotent via MARKER line; re-running on a patched file -> [skip]
  - status: [skip] / [backup] / [patch] / [error]

Target Python: 3.6-safe (no f-strings required, no walrus, no PEP 585 generics).
"""

import argparse
import datetime
import os
import sys

TARGET = "/goast/hemat_data/nf-core-tspipe/nextflow.config"
MARKER = "11-column schema; matcher in bin/apply_blacklist.py"

# --- Edit 1: repoint the snv_blacklist default ------------------------------
OLD_BLK = '    snv_blacklist      = "${projectDir}/references/blacklist_snvs_hg38.tsv"\n'
NEW_BLK = ('    snv_blacklist      = "${projectDir}/references/blacklist_file.tsv"   '
           '// %s\n' % MARKER)

# --- Edit 2: delete the dead skip_from param --------------------------------
OLD_SKIP = '    skip_from          = 0      // matches --skip-from in the Python runner\n'
NEW_SKIP = ''


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
    if OLD_BLK not in src:
        problems.append("snv_blacklist default anchor not found (Edit 1)")
    if OLD_SKIP not in src:
        problems.append("skip_from param anchor not found (Edit 2)")
    if problems:
        for p in problems:
            status("error", p)
        status("error", "no changes made; anchors must match the live file exactly")
        return 2

    patched = src
    patched = patched.replace(OLD_BLK, NEW_BLK, 1)
    patched = patched.replace(OLD_SKIP, NEW_SKIP, 1)

    if patched == src:
        status("error", "replace produced no change; aborting")
        return 3
    if MARKER not in patched:
        status("error", "MARKER missing after patch; aborting")
        return 3

    if not args.apply:
        status("patch", "DRY-RUN ok. 2 edits would apply:")
        status("patch", "  1. snv_blacklist default -> references/blacklist_file.tsv")
        status("patch", "  2. remove dead skip_from param")
        status("patch", "re-run with --apply to write.")
        return 0

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = "%s.bak_blklist_skipfrom_%s" % (path, ts)
    with open(backup, "w") as f:
        f.write(src)
    status("backup", backup)

    with open(path, "w") as f:
        f.write(patched)
    status("patch", "applied 2 edits to %s" % path)
    status("patch", "verify: grep -n 'snv_blacklist\\|skip_from' %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
