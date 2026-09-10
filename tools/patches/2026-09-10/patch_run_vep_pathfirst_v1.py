#!/usr/bin/env python3
"""
patch_run_vep_pathfirst_v1.py -- RUN_VEP_PATHFIRST_V1 (FREEZE A1)

bin/annotate.py run_vep() launches VEP through `conda run -n vep vep`, which needs a conda
installation with an env named vep. Inside local/tspipe-host the vep env is unpacked at
$TSPIPE_ENV_ROOT/vep and TSPIPE_VEP_BIN points at its vep script, and there is no conda. This
patch makes run_vep call that script directly, with the env's bin first on the (already
sanitised) PATH so its own perl and @INC resolve, and keeps `conda run -n vep` as the fallback
when neither variable is set (host conda on gandalf today). The VEP arguments and the Q7
PERL_HASH_SEED handling are untouched.

Anchor-based, MARKER-guarded, dry-run by default; --apply writes and leaves
bin/annotate.py.bak_runvep_<stamp>. Recon: run_vep as pasted from gandalf on 2026-09-10 14:20.
Because bin/annotate.py is invoked by name from VEP_ANNOTATE, this changes that task's hash:
the annotation path re-executes on the next resume (expected -- the image switch does too).
"""

import argparse
import os
import shutil
import sys
import time

MARKER = "MARKER RUN_VEP_PATHFIRST_V1"
TARGET = "bin/annotate.py"

ANCHOR_CMD = '''    cmd = [
        "conda", "run", "-n", "vep", "vep",
        "--input_file", vcf_in,
'''
NEW_CMD = '''    # %s: inside local/tspipe-host the vep env is unpacked at
    # $TSPIPE_ENV_ROOT/vep and TSPIPE_VEP_BIN points at its vep script; call it directly with
    # its own bin first on PATH (set below). Without those variables (host conda on gandalf)
    # the historical `conda run -n vep` launcher is used.
    vep_bin = os.environ.get("TSPIPE_VEP_BIN")
    if not vep_bin and os.environ.get("TSPIPE_ENV_ROOT"):
        vep_bin = os.path.join(os.environ["TSPIPE_ENV_ROOT"], "vep", "bin", "vep")
    if vep_bin and os.path.isfile(vep_bin):
        launcher = [vep_bin]
    else:
        vep_bin = None
        launcher = ["conda", "run", "-n", "vep", "vep"]
    cmd = launcher + [
        "--input_file", vcf_in,
''' % MARKER

ANCHOR_PATH = '''    vep_env["PATH"] = os.pathsep.join(
        p for p in vep_env.get("PATH", "").split(os.pathsep)
        if "envs/targeted-seq/bin" not in p
    )
'''
NEW_PATH = ANCHOR_PATH + '''    if vep_bin:   # %s
        vep_env["PATH"] = os.path.dirname(vep_bin) + os.pathsep + vep_env["PATH"]
''' % MARKER


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    path = os.path.join(args.repo, TARGET)
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    if MARKER in text:
        print("[skip] %s already carries %s" % (TARGET, MARKER))
        return 0
    for name, anchor in (("cmd", ANCHOR_CMD), ("path", ANCHOR_PATH)):
        n = text.count(anchor)
        if n != 1:
            print("[error] anchor %s matches %d times in %s (expected 1)" % (name, n, TARGET))
            return 1
    new = text.replace(ANCHOR_CMD, NEW_CMD).replace(ANCHOR_PATH, NEW_PATH)
    if not args.apply:
        print("[dry-run] would patch %s (+%d lines); re-run with --apply" % (TARGET, new.count("\n") - text.count("\n")))
        return 0
    bak = path + ".bak_runvep_" + time.strftime("%Y%m%d_%H%M%S")
    shutil.copy2(path, bak)
    print("[backup] %s" % bak)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(new)
    print("[patch] %s written (%s)" % (TARGET, MARKER))
    compile(new, path, "exec")
    print("[check] %s compiles" % TARGET)
    return 0


if __name__ == "__main__":
    sys.exit(main())
