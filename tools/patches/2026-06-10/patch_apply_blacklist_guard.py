#!/usr/bin/env python3
"""
patch_apply_blacklist_guard.py

Hardening for ISSUE 1. Two anchored edits to bin/apply_blacklist.py.

1. ZERO-ENTRY GUARD (load_blacklist): if a blacklist file is supplied and
   contains data lines but none parse as valid 11-column entries, raise instead
   of silently returning []. This is the real protection against the silent-no-op
   class of bug: feeding the legacy 4-column file (or any wrong schema) now fails
   the VARIANT_FILTER task loudly with an actionable message rather than producing
   a clinical TSV with artefact filtering quietly disabled. An all-comment /
   header-only file (no data lines) is still allowed through as a legitimately
   empty blacklist, so that intentional case keeps working.

   Note: VARIANT_FILTER is NOT label 'error_ignore', so a raise here correctly
   fails that sample rather than emitting unfiltered calls. bin/variant_filter.py
   calls load_blacklist() outside its try/except (only the import is guarded), so
   the exception propagates as intended.

2. STALE PATH REFERENCES: the docstring examples and the --blacklist argparse
   help string still name references/blacklist_snvs_hg38.tsv (the wrong-schema
   file). Repoint every occurrence to references/blacklist_file.tsv so nobody
   copy-pastes the broken example.

Conventions:
  - dry-run by default; pass --apply to write
  - backup: <file>.bak_blkguard_<timestamp>
  - idempotent via MARKER line; re-running on a patched file -> [skip]
  - status: [skip] / [backup] / [patch] / [error]

Target Python: 3.6-safe.
"""

import argparse
import datetime
import os
import sys

TARGET = "/goast/hemat_data/nf-core-tspipe/bin/apply_blacklist.py"
MARKER = "blacklist zero-entry guard"

# Stale path occurrences -> repoint (global; appears in two docstring examples
# and the argparse help). Functionally inert (docs/help only) but misleading.
OLD_PATH = "references/blacklist_snvs_hg38.tsv"
NEW_PATH = "references/blacklist_file.tsv"

# --- Edit A: add the candidate counter to the top of load_blacklist ---------
OLD_TOP = r'''    entries = []
    with open(path) as fh:
        for line_num, raw in enumerate(fh, start=1):
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            fields = line.split("\t")
'''

NEW_TOP = r'''    entries = []
    n_candidates = 0   # non-blank, non-comment lines actually attempted (zero-entry guard)
    with open(path) as fh:
        for line_num, raw in enumerate(fh, start=1):
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            n_candidates += 1
            fields = line.split("\t")
'''

# --- Edit B: replace the bare `return entries` with the guard ---------------
OLD_RET = r'''            entries.append(entry)
    return entries
'''

NEW_RET = r'''            entries.append(entry)
    # [blacklist zero-entry guard]
    # A blacklist supplied with data lines but zero parsed entries almost always
    # means a schema mismatch (e.g. the legacy 4-column Chr/Start/Ref/Alt file
    # fed to this 11-column parser), which would silently disable artefact
    # filtering. Fail loudly. An all-comment / header-only file (no data lines)
    # is still allowed through as a legitimately empty blacklist.
    if n_candidates > 0 and not entries:
        raise ValueError(
            "blacklist %s: %d data line(s) present but none parsed as valid "
            "11-column entries (expected: chrom start end match_mode pos_exact "
            "ref_exact alt_exact gene reason evidence date_added). Refusing to "
            "run with a silently-empty blacklist." % (path, n_candidates)
        )
    return entries
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

    problems = []
    if OLD_TOP not in src:
        problems.append("load_blacklist loop-top anchor not found (Edit A)")
    if OLD_RET not in src:
        problems.append("load_blacklist `return entries` anchor not found (Edit B)")
    if OLD_PATH not in src:
        problems.append("stale path %s not found (path repoint)" % OLD_PATH)
    if problems:
        for p in problems:
            status("error", p)
        status("error", "no changes made; anchors must match the live file exactly")
        return 2

    n_paths = src.count(OLD_PATH)
    patched = src
    patched = patched.replace(OLD_TOP, NEW_TOP, 1)
    patched = patched.replace(OLD_RET, NEW_RET, 1)
    patched = patched.replace(OLD_PATH, NEW_PATH)   # all occurrences

    if patched == src:
        status("error", "replace produced no change; aborting")
        return 3
    if MARKER not in patched:
        status("error", "MARKER missing after patch; aborting")
        return 3

    if not args.apply:
        status("patch", "DRY-RUN ok. would apply:")
        status("patch", "  A. add n_candidates counter to load_blacklist")
        status("patch", "  B. raise on data-present-but-zero-entries before return")
        status("patch", "  C. repoint %d occurrence(s) of %s -> %s"
               % (n_paths, OLD_PATH, NEW_PATH))
        status("patch", "re-run with --apply to write.")
        return 0

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = "%s.bak_blkguard_%s" % (path, ts)
    with open(backup, "w") as f:
        f.write(src)
    status("backup", backup)

    with open(path, "w") as f:
        f.write(patched)
    status("patch", "applied guard + repointed %d path reference(s) in %s"
           % (n_paths, path))
    status("patch", "verify: grep -n 'n_candidates\\|zero-entry guard\\|blacklist_file.tsv' %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
