#!/usr/bin/env python3
"""
patch_runvep_env.py

Fix a SEPARATE, pre-existing environment-isolation bug exposed when the
annotation stage re-ran under Nextflow + gandalf.config:

  gandalf.config beforeScript prepends the targeted-seq env bin to PATH
  (needed for ANNOVAR's perl). When `conda run -n vep vep` then launches,
  VEP's perl resolves to the targeted-seq perl (first on PATH), which loads
  an incompatible base.pm/@INC and aborts compilation in Bio::EnsEMBL::VEP.

  Proven: running the identical VEP command with a sanitized PATH (targeted-seq
  bin removed) and Perl vars cleared completes successfully.

This is NOT related to the --flag_pick CSQ-selection fix; it is an env leak that
breaks ANY VEP run under this config. The fix scopes a cleaned environment to
the VEP subprocess ONLY. ANNOVAR keeps the targeted-seq perl (it needs it),
so run()'s default behaviour is unchanged.

Edits to bin/annotate.py:
  1. run(): add optional `env=None` param, forward it to subprocess.run.
  2. run_vep(): build a sanitized env (drop targeted-seq bin from PATH, clear
     leaked PERL* vars) and pass env= to the VEP run() call.

Conventions: dry-run default; --apply writes; backup .bak_vepenv_<timestamp>;
idempotent via MARKER; status [skip]/[backup]/[patch]/[error].
Target Python 3.6-safe.
"""

import argparse
import datetime
import os
import sys

TARGET = "/goast/hemat_data/nf-core-tspipe/bin/annotate.py"
MARKER = "vepenv scoped PATH/PERL sanitisation"

# ----------------------------------------------------------------------------
# Edit 1: run() gains an optional env= param, forwarded to subprocess.run.
# ----------------------------------------------------------------------------
OLD_RUN_SIG = "def run(cmd, desc=None):\n"
NEW_RUN_SIG = "def run(cmd, desc=None, env=None):  # [%s]\n" % MARKER

OLD_RUN_CALL = "    result = subprocess.run(cmd, capture_output=True, text=True)\n"
NEW_RUN_CALL = "    result = subprocess.run(cmd, capture_output=True, text=True, env=env)\n"

# ----------------------------------------------------------------------------
# Edit 2: run_vep() builds a sanitized env and passes it to run().
# Anchor on the final return of run_vep(). The original line is:
#     return run(cmd, desc="Running VEP on " + os.path.basename(vcf_in))
# ----------------------------------------------------------------------------
OLD_VEP_RETURN = (
    '    return run(cmd, desc="Running VEP on " + os.path.basename(vcf_in))\n'
)
NEW_VEP_RETURN = (
    '    # [{marker}]\n'
    '    # gandalf.config beforeScript prepends the targeted-seq env bin to PATH\n'
    '    # (for ANNOVAR perl). That shadows VEP\'s own perl and aborts compilation\n'
    '    # in Bio::EnsEMBL::VEP. Scope a cleaned env to the VEP subprocess only:\n'
    '    # drop any targeted-seq bin from PATH and clear leaked Perl lib vars.\n'
    '    vep_env = dict(os.environ)\n'
    '    vep_env["PATH"] = os.pathsep.join(\n'
    '        p for p in vep_env.get("PATH", "").split(os.pathsep)\n'
    '        if "envs/targeted-seq/bin" not in p\n'
    '    )\n'
    '    for _v in ("PERL5LIB", "PERL_LOCAL_LIB_ROOT", "PERL_MM_OPT", "PERL_MB_OPT"):\n'
    '        vep_env.pop(_v, None)\n'
    '    return run(cmd, desc="Running VEP on " + os.path.basename(vcf_in),\n'
    '               env=vep_env)\n'
).format(marker=MARKER)


def status(tag, msg):
    sys.stdout.write("[%s] %s\n" % (tag, msg))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true",
                    help="Write changes. Default is dry-run.")
    ap.add_argument("--file", default=TARGET)
    args = ap.parse_args()

    path = args.file
    if not os.path.isfile(path):
        status("error", "target not found: %s" % path)
        return 1

    with open(path, "r") as f:
        src = f.read()

    if MARKER in src:
        status("skip", "MARKER present; file already patched. No changes.")
        return 0

    problems = []
    if OLD_RUN_SIG not in src:
        problems.append('run() signature anchor not found (Edit 1a)')
    if OLD_RUN_CALL not in src:
        problems.append('subprocess.run(...) call anchor not found (Edit 1b)')
    if OLD_VEP_RETURN not in src:
        problems.append('run_vep() return anchor not found (Edit 2)')
    if problems:
        for p in problems:
            status("error", p)
        status("error", "no changes made; anchors must match the live file exactly")
        return 2

    patched = src
    patched = patched.replace(OLD_RUN_SIG, NEW_RUN_SIG, 1)
    patched = patched.replace(OLD_RUN_CALL, NEW_RUN_CALL, 1)
    patched = patched.replace(OLD_VEP_RETURN, NEW_VEP_RETURN, 1)

    if patched == src:
        status("error", "replace produced no change; aborting")
        return 3
    # MARKER appears in 2 edits: run() signature, and the run_vep() block.
    # (The subprocess.run forwarding line carries no MARKER by design.)
    if patched.count(MARKER) != 2:
        status("error", "expected 2 MARKER insertions, found %d; aborting"
               % patched.count(MARKER))
        return 3
    # Independently confirm all three textual edits actually landed.
    if NEW_RUN_CALL not in patched:
        status("error", "subprocess.run env-forwarding edit did not land; aborting")
        return 3

    if not args.apply:
        status("patch", "DRY-RUN ok. 3 edits would apply:")
        status("patch", "  1a. run(): add env=None param")
        status("patch", "  1b. run(): forward env to subprocess.run")
        status("patch", "  2.  run_vep(): sanitize PATH/PERL, pass env to VEP only")
        status("patch", "re-run with --apply to write.")
        return 0

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = "%s.bak_vepenv_%s" % (path, ts)
    with open(backup, "w") as f:
        f.write(src)
    status("backup", backup)

    with open(path, "w") as f:
        f.write(patched)
    status("patch", "applied 3 edits to %s" % path)
    status("patch", "verify: grep -n 'vepenv\\|env=vep_env\\|env=None' %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
