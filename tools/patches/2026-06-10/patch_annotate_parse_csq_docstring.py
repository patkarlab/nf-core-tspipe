#!/usr/bin/env python3
"""
patch_annotate_parse_csq_docstring.py

ISSUE 4 (docs): the parse_vep_csq() docstring in bin/annotate.py still says VEP
was invoked with --pick and that the function is "bit-for-bit identical to
production". After the 2026-06-09 flag_pick patch this is false: VEP now runs
with --flag_pick and the parser selects one CSQ block by consequence severity
(via _pick_csq), deliberately diverging from production. Correct the docstring so
the description matches the clinically load-bearing behaviour.

One anchored edit to bin/annotate.py (docstring text only; no logic change).

Conventions: dry-run by default; --apply writes; backup .bak_csqdoc_<timestamp>;
idempotent via MARKER; status [skip]/[backup]/[patch]/[error]. Python 3.6-safe.
"""

import argparse
import datetime
import os
import sys

TARGET = "/goast/hemat_data/nf-core-tspipe/bin/annotate.py"
MARKER = "VEP is invoked with --flag_pick (not --pick)"

OLD_DOC = r'''    VEP was invoked with --pick, so only the first CSQ annotation per
    variant is taken (VEP's pick algorithm chooses the canonical
    consequence). PORT NOTE: bit-for-bit identical to production's
    parse_vep_csq().
'''

NEW_DOC = r'''    VEP is invoked with --flag_pick (not --pick), so every transcript
    consequence is emitted; selection is severity-based over all CSQ blocks
    (see _pick_csq), so an overlapping neighbouring transcript can no longer
    mask a co-located coding call. PORT NOTE: this DIVERGES from production's
    parse_vep_csq(), which took the first CSQ block.
'''


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

    if OLD_DOC not in src:
        status("error", "stale docstring anchor not found; live file differs from expected")
        status("error", "no changes made")
        return 2

    patched = src.replace(OLD_DOC, NEW_DOC, 1)

    if patched == src or MARKER not in patched:
        status("error", "patch did not land as expected; aborting")
        return 3

    if not args.apply:
        status("patch", "DRY-RUN ok. would correct parse_vep_csq() docstring (--pick -> --flag_pick).")
        status("patch", "re-run with --apply to write.")
        return 0

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = "%s.bak_csqdoc_%s" % (path, ts)
    with open(backup, "w") as f:
        f.write(src)
    status("backup", backup)

    with open(path, "w") as f:
        f.write(patched)
    status("patch", "corrected parse_vep_csq() docstring in %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
