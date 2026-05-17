#!/usr/bin/env python3
"""
apply_render_py36_fix.py

Swap bin/render_dashboard.py with a Python 3.6 compatible version.

WHY:
The original renderer used `from __future__ import annotations` (Python
3.7+) and PEP 585 collection generics (`list[dict]`, Python 3.9+). The
GATK 4.5 container that SAMPLE_DASHBOARD now uses ships Python 3.6,
which rejects both:

    File "/goast/hemat_data/nf-core-tspipe/bin/render_dashboard.py", line 23
        from __future__ import annotations
        ^
    SyntaxError: future feature annotations is not defined

FIX:
The replacement file removes the __future__ import and strips PEP 585
type hints from 5 function signatures (they were documentation only, not
functional). Everything else in the file is unchanged. The renderer
produces byte-similar HTML output (verified locally).

Same authoring discipline:
  - md5-verified pre-flight on the existing file
  - md5-verified post-state to confirm the swap completed atomically
  - .bak_pre_render_py36_<ts> backup
  - idempotent re-run detection via destination md5 check

USAGE:
    python3 apply_render_py36_fix.py            # dry-run
    python3 apply_render_py36_fix.py --apply
    python3 apply_render_py36_fix.py --apply --archive
"""

import argparse
import hashlib
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_PORT_ROOT = Path("/goast/hemat_data/nf-core-tspipe")
TARGET_REL = "bin/render_dashboard.py"

# Pre-state md5 (the file currently on gandalf, installed by the earlier
# dashboard patch)
PRE_MD5 = "c700328c4f2c857dee2407e314b899cd"

# Post-state md5 (the Python 3.6 compatible replacement)
POST_MD5 = "af7e577ccb18692a31a665daae4a3b76"


def md5(b):
    return hashlib.md5(b).hexdigest()


def color(s, code):
    return s if not sys.stdout.isatty() else f"\033[{code}m{s}\033[0m"


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

    bundle_root = Path(__file__).resolve().parent
    src = bundle_root / "render_dashboard.py"
    dest = args.port_root / TARGET_REL

    print("Patch: bin/render_dashboard.py -> Python 3.6 compatible")
    print(f"  Source: {src}")
    print(f"  Target: {dest}")
    print()

    if not src.is_file():
        print(red(f"ABORT: bundle source missing: {src}"))
        return 1
    if not dest.is_file():
        print(red(f"ABORT: target missing on gandalf: {dest}"))
        return 1

    src_md5 = md5(src.read_bytes())
    dest_md5 = md5(dest.read_bytes())

    print("Phase 1: md5 check")
    print(f"  bundle source md5: {src_md5}")
    print(f"  on gandalf md5:    {dest_md5}")

    if src_md5 != POST_MD5:
        print(red(f"  ABORT: bundle source md5 disagrees with hardcoded POST_MD5"))
        return 1

    if dest_md5 == POST_MD5:
        print(green("  POST: target already matches the 3.6-compatible version (nothing to do)"))
        return 0
    elif dest_md5 == PRE_MD5:
        print(green(f"  PRE:  target matches the known pre-patch md5 ({PRE_MD5})"))
    else:
        print(yellow(f"  DRIFT: target md5 ({dest_md5}) is neither pre nor post state"))
        print(yellow("         Will still overwrite, but a .bak will be kept."))
    print()

    if not args.apply:
        print("Phase 2: ready to overwrite 1 file")
        print(yellow("DRY-RUN. Re-run with --apply to execute."))
        return 0

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = dest.with_name(dest.name + f".bak_pre_render_py36_{ts}")
    shutil.copy2(dest, bak)
    # Use atomic replace
    tmp = dest.with_suffix(dest.suffix + ".tmp_patch")
    shutil.copy2(src, tmp)
    # Preserve executable bit
    tmp.chmod(tmp.stat().st_mode | 0o755)
    os.replace(tmp, dest)
    post = md5(dest.read_bytes())

    if post != POST_MD5:
        print(red(f"  INTEGRITY FAIL: post md5 = {post} (expected {POST_MD5})"))
        return 2

    print(f"  {green('REPLACED')} {dest}")
    print(f"    backup:  {bak}")
    print(f"    new md5: {post}")
    print()

    if args.archive:
        d = args.port_root / "tools" / "patches" / "2026-05-17"
        d.mkdir(parents=True, exist_ok=True)
        dest_archive = d / Path(sys.argv[0]).name
        shutil.copy2(sys.argv[0], dest_archive)
        print(f"Archived patch script to {dest_archive}")
        print()

    print(green("Done."))
    print()
    print("Re-run validation in a fresh RUN_OUT:")
    print()
    print('  RUN_OUT="/goast/hemat_data/nfcore_runs/25NGS1307_dashboard_$(date +%Y%m%d_%H%M%S)"')
    print('  mkdir -p "$RUN_OUT"')
    print('  cd /goast/hemat_data/nf-core-tspipe')
    print('  nextflow run main.nf -profile gandalf,singularity \\')
    print('      --input /tmp/cnv_wiring/validation_samplesheet.csv \\')
    print('      --outdir "$RUN_OUT" -resume -ansi-log false 2>&1 | tee /tmp/log_dashboard.log')
    print()
    print(f"Rollback: mv '{bak}' '{dest}'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
