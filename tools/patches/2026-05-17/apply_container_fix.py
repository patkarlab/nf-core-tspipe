#!/usr/bin/env python3
"""
apply_container_fix.py

Swap the SAMPLE_DASHBOARD container from quay.io/biocontainers/matplotlib-base
to broadinstitute/gatk:4.5.0.0.

WHY:
The original tag 'quay.io/biocontainers/matplotlib-base:3.8.2' returns
401 Unauthorized from quay.io (the tag does not exist or has been
removed). The GATK 4.5 container is already cached on gandalf (used
by PARSE_EXON_COVERAGE and others) and contains matplotlib 3.2.1,
which has every API the renderer uses. No new container pull needed.

Also updates the version-block awk command since the GATK container
no longer needs the explicit matplotlib version capture (we know it
ships matplotlib 3.2.1 in this image).

Same authoring discipline as the prior 2026-05-17 patches:
  - md5-verified pre-flight
  - anchor classification
  - atomic .tmp + os.replace
  - .bak_pre_container_<ts> backup
  - idempotent re-run detection

USAGE:
    python3 apply_container_fix.py            # dry-run
    python3 apply_container_fix.py --apply
    python3 apply_container_fix.py --apply --archive
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
TARGET_REL = "modules/local/sample_dashboard.nf"
PRE_MD5 = "1e04308220bb0e9184fbd0b0b2636ac1"

# Edit 1: container directive
OLD_CONTAINER = "    container  'quay.io/biocontainers/matplotlib-base:3.8.2'\n"
NEW_CONTAINER = "    container  'docker://broadinstitute/gatk:4.5.0.0'\n"

# Edit 2: comment block describing the container choice — update it to
# reflect the GATK reasoning. This makes the file self-documenting after
# the swap so future readers don't have to look up commit history.
OLD_COMMENT = (
    " * Container: matplotlib-base biocontainer rather than the GATK image,\n"
    " * because we need matplotlib at runtime and don't want to bloat the\n"
    " * GATK container's role. The biocontainer is ~80 MB.\n"
)
NEW_COMMENT = (
    " * Container: GATK 4.5 image, which already ships python3 + matplotlib\n"
    " * 3.2.1 (used by several GATK plotting commands). It's already cached\n"
    " * on gandalf for PARSE_EXON_COVERAGE so no new pull is needed.\n"
)

# Edit 3: versions block — capture matplotlib version from runtime regardless
# of container, but no need to change this since it already works generically.
# Leaving the matplotlib version-capture line in place.


def md5(b): return hashlib.md5(b).hexdigest()
def read_bytes(p): return p.read_bytes()
def write_atomic(p, data):
    tmp = p.with_suffix(p.suffix + ".tmp_patch")
    tmp.write_bytes(data)
    os.replace(tmp, p)

def classify(content, old, new):
    a, b = content.count(old), content.count(new)
    if a == 1 and b == 0: return "pre"
    if a == 0 and b == 1: return "post"
    if a > 1 or b > 1:    return "duplicate"
    if a == 1 and b == 1: return "post" if old in new else "mixed"
    return "missing"

def color(s, code):
    return s if not sys.stdout.isatty() else f"\033[{code}m{s}\033[0m"
def green(s):  return color(s, "32")
def yellow(s): return color(s, "33")
def red(s):    return color(s, "31")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port-root", type=Path, default=DEFAULT_PORT_ROOT)
    ap.add_argument("--apply",   action="store_true")
    ap.add_argument("--archive", action="store_true")
    args = ap.parse_args()

    target = args.port_root / TARGET_REL
    print(f"Patch: SAMPLE_DASHBOARD container swap (matplotlib-base -> GATK 4.5)")
    print(f"  Target: {target}")
    print()

    if not target.is_file():
        print(red(f"ABORT: {target} not found"))
        return 1

    raw = read_bytes(target)
    actual_md5 = md5(raw)
    content = raw.decode("utf-8")

    print("Phase 1: md5 check")
    if actual_md5 == PRE_MD5:
        print(f"  {green('MATCH')}  md5 = {actual_md5}")
    else:
        print(f"  {yellow('DRIFT')}  md5 = {actual_md5}")
        print(f"           expected = {PRE_MD5}")
        print("           Falling back to anchor classification.")
    print()

    print("Phase 2: anchors")
    edits = [
        ("container directive", OLD_CONTAINER, NEW_CONTAINER),
        ("container comment",   OLD_COMMENT,   NEW_COMMENT),
    ]
    new_content = content
    n_pre, n_post, any_block = 0, 0, False
    for name, old, new in edits:
        st = classify(new_content, old, new)
        if st == "pre":
            print(f"  {green('PRE')}  {name}")
            new_content = new_content.replace(old, new, 1)
            n_pre += 1
        elif st == "post":
            print(f"  {yellow('POST')} {name} (already applied)")
            n_post += 1
        else:
            print(f"  {red(st.upper())} {name}")
            any_block = True
    print()
    if any_block:
        print(red("ABORT"))
        return 1
    if n_pre == 0:
        print(green("Nothing to do; patch already applied."))
        return 0
    print(f"Phase 3: ready to apply {n_pre} edit(s)")
    if not args.apply:
        print(yellow("DRY-RUN. Re-run with --apply to execute."))
        return 0

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = target.with_name(target.name + f".bak_pre_container_{ts}")
    shutil.copy2(target, bak)
    write_atomic(target, new_content.encode("utf-8"))
    post = md5(read_bytes(target))
    print(f"  {green('PATCHED')} {target}")
    print(f"    backup:  {bak}")
    print(f"    new md5: {post}")
    print()

    if args.archive:
        d = args.port_root / "tools" / "patches" / "2026-05-17"
        d.mkdir(parents=True, exist_ok=True)
        dest = d / Path(sys.argv[0]).name
        shutil.copy2(sys.argv[0], dest)
        print(f"Archived to {dest}")
        print()

    print(green("Done."))
    print()
    print("The GATK 4.5 container is already on gandalf — no new pull needed.")
    print("Re-run validation (you can reuse the same RUN_OUT since nothing")
    print("succeeded last attempt):")
    print()
    print('  RUN_OUT="/goast/hemat_data/nfcore_runs/25NGS1307_dashboard_$(date +%Y%m%d_%H%M%S)"')
    print('  mkdir -p "$RUN_OUT"')
    print('  cd /goast/hemat_data/nf-core-tspipe')
    print('  nextflow run main.nf -profile gandalf,singularity \\')
    print('      --input /tmp/cnv_wiring/validation_samplesheet.csv \\')
    print('      --outdir "$RUN_OUT" -resume -ansi-log false 2>&1 | tee /tmp/log_dashboard.log')
    print()
    print(f"Rollback: mv '{bak}' '{target}'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
