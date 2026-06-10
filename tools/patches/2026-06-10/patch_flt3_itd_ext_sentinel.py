#!/usr/bin/env python3
"""
patch_flt3_itd_ext_sentinel.py

ISSUE 3: FLT3_ITD_EXT exits non-zero on FLT3-ITD-negative specimens
("NO ITD CANDIDATE CLUSTERS GENERATED") and writes no VCF. The module declares
`vcf` and `summary` as non-optional outputs, so output collection fails; the
'error_ignore' label keeps it non-fatal, but every ITD-negative sample (the
majority) shows up as a failed task in the execution report, and FLT3_CONSENSUS
falls back to the join placeholder.

Fix (the planned "sentinel output on no-ITD"): in the script block, capture the
tool's exit code, treat the benign no-cluster case as success, and guarantee both
declared outputs exist as valid (possibly empty) files. A real failure (any other
non-zero exit) is still propagated, so genuine breakage stays visible (red)
instead of being masked by a blanket `|| true`.

One anchored edit to modules/local/flt3_itd_ext.nf: replace the script-block
command string.

Conventions:
  - dry-run by default; pass --apply to write
  - backup: <file>.bak_flt3sentinel_<timestamp>
  - idempotent via MARKER line; re-running on a patched file -> [skip]
  - status: [skip] / [backup] / [patch] / [error]

Groovy note: this rewrites a GString triple-quoted script body. Bash variables
are escaped as \\$ so Groovy does not interpolate them; ${meta.id} and ${bam}
are intentionally Groovy-interpolated (matching the existing module). printf
escapes are doubled (\\n, \\t) so they survive into .command.sh for printf.
"""

import argparse
import datetime
import os
import sys

TARGET = "/goast/hemat_data/nf-core-tspipe/modules/local/flt3_itd_ext.nf"
MARKER = "flt3_itd_ext no-ITD sentinel"

OLD_SCRIPT = r'''        """
        mkdir -p flt3_itd_ext_out
        flt3_itd_ext \\
            -b \$(pwd)/${bam} \\
            -o \$(pwd)/flt3_itd_ext_out \\
            -n HC \\
            -g hg38
        """'''

NEW_SCRIPT = r'''        """
        mkdir -p flt3_itd_ext_out

        # [flt3_itd_ext no-ITD sentinel]
        # FLT3_ITD_ext exits non-zero on ITD-negative specimens
        # ("NO ITD CANDIDATE CLUSTERS GENERATED") and writes no VCF. Capture the
        # exit code so the benign no-ITD case is told apart from a genuine
        # failure, then guarantee both declared outputs exist as valid (possibly
        # empty) files. This lets output collection succeed and gives
        # FLT3_CONSENSUS a parseable zero-record VCF instead of the placeholder.
        set +e
        flt3_itd_ext \\
            -b \$(pwd)/${bam} \\
            -o \$(pwd)/flt3_itd_ext_out \\
            -n HC \\
            -g hg38 > flt3_itd_ext_run.log 2>&1
        rc=\$?
        set -e
        cat flt3_itd_ext_run.log

        vcf="flt3_itd_ext_out/${meta.id}.final_FLT3_ITD.vcf"
        summary="flt3_itd_ext_out/${meta.id}.final_FLT3_ITD_summary.txt"

        if [ "\$rc" -ne 0 ]; then
            if grep -q "NO ITD CANDIDATE CLUSTERS GENERATED" flt3_itd_ext_run.log; then
                echo "[flt3_itd_ext] ITD-negative specimen (rc=\$rc); writing header-only sentinel outputs."
            else
                echo "[flt3_itd_ext] failed (rc=\$rc) for a reason other than no-ITD; propagating." >&2
                exit \$rc
            fi
        fi

        if [ ! -s "\$vcf" ]; then
            printf '##fileformat=VCFv4.2\\n##source=FLT3_ITD_ext_sentinel_no_itd\\n#CHROM\\tPOS\\tID\\tREF\\tALT\\tQUAL\\tFILTER\\tINFO\\n' > "\$vcf"
        fi
        if [ ! -f "\$summary" ]; then
            : > "\$summary"
        fi
        """'''


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

    if OLD_SCRIPT not in src:
        status("error", "script-block anchor not found; the live file differs from expected")
        status("error", "no changes made")
        return 2

    patched = src.replace(OLD_SCRIPT, NEW_SCRIPT, 1)

    if patched == src:
        status("error", "replace produced no change; aborting")
        return 3
    if MARKER not in patched:
        status("error", "MARKER missing after patch; aborting")
        return 3

    if not args.apply:
        status("patch", "DRY-RUN ok. would replace the FLT3_ITD_EXT script block")
        status("patch", "  - capture rc, treat no-ITD as success, propagate real failures")
        status("patch", "  - write header-only sentinel VCF + empty summary when absent")
        status("patch", "re-run with --apply to write.")
        return 0

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = "%s.bak_flt3sentinel_%s" % (path, ts)
    with open(backup, "w") as f:
        f.write(src)
    status("backup", backup)

    with open(path, "w") as f:
        f.write(patched)
    status("patch", "applied sentinel script block to %s" % path)
    status("patch", "verify: grep -n 'no-ITD sentinel\\|set +e\\|sentinel_no_itd' %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
