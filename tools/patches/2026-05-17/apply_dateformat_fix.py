#!/usr/bin/env python3
"""
apply_dateformat_fix.py

One-line fix to subworkflows/local/preprocessing.nf in the nf-core-tspipe
port. The SAMPLE_DASHBOARD call passes workflow.start formatted as a
yyyy-MM-dd string. The original patch used:

    new java.text.SimpleDateFormat('yyyy-MM-dd').format(workflow.start)

This crashes on Nextflow 25.10.4+ because workflow.start is now an
OffsetDateTime (java.time), not a java.util.Date. SimpleDateFormat
rejects it with:

    java.lang.IllegalArgumentException: Cannot format given Object as a Date

Fix: use Groovy's built-in .format() method, which dispatches to the
correct formatter for whichever java.time type Nextflow returns:

    workflow.start.format('yyyy-MM-dd')

This works on both java.util.Date and java.time.* types.

Same authoring discipline as the prior 2026-05-17 patches.

USAGE:
    python3 apply_dateformat_fix.py            # dry-run
    python3 apply_dateformat_fix.py --apply
    python3 apply_dateformat_fix.py --apply --archive
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_PORT_ROOT = Path("/goast/hemat_data/nf-core-tspipe")

# This is the md5 of preprocessing.nf as it stands on gandalf RIGHT NOW,
# after the dashboard patch was applied earlier today.
PREPROCESSING_PRE_MD5 = "dc3d23e3b5601fd86bd4decec46f136a"

OLD_DATEFMT = (
    "            new java.text.SimpleDateFormat('yyyy-MM-dd').format(workflow.start)\n"
)
NEW_DATEFMT = (
    "            workflow.start.format('yyyy-MM-dd')\n"
)


def md5sum_bytes(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def read_bytes(path: Path) -> bytes:
    with path.open("rb") as fh:
        return fh.read()


def write_bytes_atomic(path: Path, data: bytes) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp_patch")
    with tmp.open("wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def classify_anchor(content, old, new):
    n_old = content.count(old)
    n_new = content.count(new)
    if n_old == 1 and n_new == 0: return "pre"
    if n_old == 0 and n_new == 1: return "post"
    if n_old > 1 or n_new > 1:    return "duplicate"
    if n_old == 1 and n_new == 1:
        if old in new: return "post"
        return "mixed"
    return "missing"


def color(s, code):
    if not sys.stdout.isatty(): return s
    return f"\033[{code}m{s}\033[0m"
def green(s):  return color(s, "32")
def yellow(s): return color(s, "33")
def red(s):    return color(s, "31")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port-root", type=Path, default=DEFAULT_PORT_ROOT)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--archive", action="store_true")
    args = ap.parse_args()

    target = args.port_root / "subworkflows" / "local" / "preprocessing.nf"
    print(f"Patch: workflow.start dateformat fix")
    print(f"  Target: {target}")
    print()

    if not target.is_file():
        print(red(f"ABORT: {target} not found"))
        return 1

    raw = read_bytes(target)
    actual_md5 = md5sum_bytes(raw)
    content = raw.decode("utf-8")

    print("Phase 1: md5 check")
    if actual_md5 == PREPROCESSING_PRE_MD5:
        print(f"  {green('MATCH')}  md5 = {actual_md5}")
    else:
        print(f"  {yellow('DRIFT')}  md5 = {actual_md5}")
        print(f"           expected = {PREPROCESSING_PRE_MD5}")
        print("           Falling back to anchor classification.")
    print()

    print("Phase 2: anchor classification")
    state = classify_anchor(content, OLD_DATEFMT, NEW_DATEFMT)
    if state == "pre":
        print(f"  {green('PRE')}  dateformat (will apply)")
    elif state == "post":
        print(f"  {yellow('POST')} dateformat already fixed; nothing to do")
        return 0
    elif state == "missing":
        print(f"  {red('MISSING')} dateformat anchor not found (drift)")
        return 1
    elif state == "duplicate":
        print(f"  {red('DUPLICATE')} found OLD or NEW multiple times")
        return 1
    elif state == "mixed":
        print(f"  {red('MIXED')} both forms present; corrupt")
        return 1
    print()

    if not args.apply:
        print("Phase 3: ready to write 1 file")
        print(yellow("DRY-RUN. Re-run with --apply to execute."))
        return 0

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak_suffix = f".bak_pre_dateformat_{ts}"
    bak = target.with_name(target.name + bak_suffix)

    new_content = content.replace(OLD_DATEFMT, NEW_DATEFMT, 1)
    shutil.copy2(target, bak)
    write_bytes_atomic(target, new_content.encode("utf-8"))
    post_md5 = md5sum_bytes(read_bytes(target))

    print("Phase 3: applied")
    print(f"  {green('PATCHED')} {target}")
    print(f"    backup:  {bak}")
    print(f"    new md5: {post_md5}")
    print()

    if args.archive:
        archive_dir = args.port_root / "tools" / "patches" / "2026-05-17"
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_dest = archive_dir / Path(sys.argv[0]).name
        shutil.copy2(sys.argv[0], archive_dest)
        print(f"Archived patch script to {archive_dest}")
        print()

    print(green("Done."))
    print()
    print("Next steps:")
    print(f"  cd {args.port_root}")
    print(f"  git diff subworkflows/local/preprocessing.nf")
    print()
    print("Then re-run validation (no need to make a new RUN_OUT — the previous")
    print("one died before any work was done):")
    print(f"  RUN_OUT=\"/goast/hemat_data/nfcore_runs/25NGS1307_dashboard_$(date +%Y%m%d_%H%M%S)\"")
    print(f"  mkdir -p \"$RUN_OUT\"")
    print(f"  nextflow run main.nf -profile gandalf,singularity \\")
    print(f"      --input /tmp/cnv_wiring/validation_samplesheet.csv \\")
    print(f"      --outdir \"$RUN_OUT\" \\")
    print(f"      -resume -ansi-log false 2>&1 | tee /tmp/log_dashboard.log")
    print()
    print(f"Rollback: mv '{bak}' '{target}'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
