#!/usr/bin/env python3
"""
patch_decon_v1a_include.py -- add the missing DECON include to
workflows/tspipe.nf (MARKER DECON_V1a).

DECON_V1 wired the DECON call and the consensus join but did not add
    include { DECON } from '../modules/local/decon'
Stub runs passed because the gate (pool asset present) was closed; the
first run with the pool built failed with "Missing process or function
DECON()". Inserted after the CNV_CONSENSUS_MULTI include.
"""

import argparse
import datetime
import os
import re
import shutil
import sys

MARKER = "MARKER DECON_V1a"
TARGET = "workflows/tspipe.nf"
ANCHOR = re.compile(r"^include \{ CNV_CONSENSUS_MULTI \} from '\.\./modules/local/cnv_consensus_multi'[^\n]*$", re.M)
LINE = "include { DECON               } from '../modules/local/decon'                 // %s" % MARKER


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default=TARGET)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    t = open(args.target).read()
    if MARKER in t or re.search(r"^include \{ DECON\s*\} from '\.\./modules/local/decon'", t, re.M):
        print("[skip] DECON include already present"); sys.exit(0)
    hits = ANCHOR.findall(t)
    if len(hits) != 1:
        print("[error] CNV_CONSENSUS_MULTI include anchor: %d hits; nothing written" % len(hits)); sys.exit(1)
    new = ANCHOR.sub(lambda m: m.group(0) + "\n" + LINE, t, count=1)
    print("[ok] include line inserted after the CNV_CONSENSUS_MULTI include")
    print("[check] markers %d (expected 1); brace balance %d/%d" % (new.count(MARKER), t.count("{") - t.count("}"), new.count("{") - new.count("}")))
    if not args.apply:
        print("[dry-run] no changes written; re-run with --apply\n+ " + LINE); sys.exit(0)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = "%s.bak_decon_v1a_%s" % (args.target, ts)
    shutil.copy2(args.target, backup)
    open(args.target, "w").write(new)
    print("[backup] %s\n[patch] wrote %s" % (backup, args.target))


if __name__ == "__main__":
    main()
