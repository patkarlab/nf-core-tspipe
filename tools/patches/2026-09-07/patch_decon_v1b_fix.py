#!/usr/bin/env python3
"""
patch_decon_v1b_fix.py -- remove the Groovy comment that DECON_V1b placed
inside the DECON shell script (MARKER DECON_V1b_FIX).

"--out X.decon_filtered.tsv   // MARKER DECON_V1b" is inside the process's
triple-quoted script, so the shell passed '//', 'MARKER' and 'DECON_V1b' to
filter_decon_calls.py, which exited 2 on every sample. The marker moves to a
Groovy comment above the script block.
"""

import argparse
import datetime
import re
import shutil
import sys

MARKER = "MARKER DECON_V1b_FIX"
TARGET = "modules/local/decon.nf"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default=TARGET)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    t = open(args.target).read()
    if MARKER in t:
        print("[skip] already applied"); sys.exit(0)
    rx = re.compile(r'^(?P<i>[ \t]*)--out \$\{meta\.id\}\.decon_filtered\.tsv[ \t]*// MARKER DECON_V1b[ \t]*$', re.M)
    if len(rx.findall(t)) != 1:
        print("[error] V1b script line not found once; nothing written"); sys.exit(1)
    t2 = rx.sub(lambda m: "%s--out ${meta.id}.decon_filtered.tsv" % m.group("i"), t, count=1)
    rx2 = re.compile(r'^(?P<i>[ \t]*)script:[ \t]*\n', re.M)
    if len(rx2.findall(t2)) != 1:
        print("[error] script: anchor not found once; nothing written"); sys.exit(1)
    t2 = rx2.sub(lambda m: "%s// DECON_V1b: --del-multi-bf (multi-exon deletions at params.decon_del_multi_bf); %s\n%sscript:\n" % (m.group("i"), MARKER, m.group("i")), t2, count=1)
    bad = re.findall(r'^[ \t]*[^/\n]*\S[ \t]+//[^\n]*$', t2.split('"""')[3] if t2.count('"""') >= 4 else "", re.M)
    print("[ok] comment removed from the script line; marker moved above script:")
    print("[check] markers %d (expected 1); '//' left inside the script block: %d" % (t2.count(MARKER), len(bad)))
    if t2.count(MARKER) != 1 or bad:
        print("[error] verification failed; nothing written"); sys.exit(1)
    if not args.apply:
        print("[dry-run] no changes written; re-run with --apply"); sys.exit(0)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = "%s.bak_decon_v1b_fix_%s" % (args.target, ts)
    shutil.copy2(args.target, backup)
    open(args.target, "w").write(t2)
    print("[backup] %s\n[patch] wrote %s" % (backup, args.target))


if __name__ == "__main__":
    main()
