#!/usr/bin/env python3
"""
apply_mosdepth_include_duplicates.py

Add --flag 772 to every mosdepth invocation so duplicate-flagged reads
are INCLUDED in coverage calculations, per clinical convention here.

WHY:
  Mosdepth's default --flag is 1796, which excludes reads with any of
  these SAM flag bits set:
      0x004 (4)    unmapped
      0x100 (256)  secondary alignment
      0x200 (512)  QC fail
      0x400 (1024) PCR/optical duplicate    <-- the problem

  For hybrid-capture targeted sequencing, dup-flagged reads are real
  observations of bases that hit the panel; excluding them deflates
  reported coverage by 5-10x and is inconsistent with how the legacy
  clinical reports framed coverage. Override with --flag 772:
      772 = 1796 - 1024 = drop the DUP bit, keep the other three.

FILES MODIFIED (3 call sites):
  - port/modules/local/mosdepth.nf       (Nextflow shell script)
  - port/bin/exon_coverage.py            (Python subprocess.run)
  - production/scripts/10b_exon_coverage.py
                                         (Python subprocess.run; byte-identical
                                          to bin/exon_coverage.py)

The two Python files share identical md5sums; the same OLD/NEW string
pair patches both.

FILES NOT MODIFIED (verified by exhaustive grep):
  - bin/parse_exon_coverage.py        only PARSES mosdepth output
  - scripts/run_sample_pipeline.py    orchestrator; mosdepth not invoked
  - any tools/ utility                no mosdepth invocations

AUTHORING DISCIPLINE (from 2026-05-17 morning lessons, same as prior
patches):
  - Pre-flight md5 verification on every target
  - Anchor classification (PRE / POST / MISSING / DUPLICATE / MIXED)
  - All-or-nothing: load + classify everything BEFORE writing
  - Atomic write via .tmp + os.replace
  - .bak_pre_mosdepth_include_dup_<ts> backups
  - Idempotent: re-run after success exits 0 with "nothing to do"

USAGE:
    python3 apply_mosdepth_include_duplicates.py            # dry-run
    python3 apply_mosdepth_include_duplicates.py --apply    # write
    python3 apply_mosdepth_include_duplicates.py --apply --archive
                                                            # also copy this
                                                            # script into
                                                            # tools/patches/
                                                            # on both trees

ROLLBACK:
    Each modified file gets a .bak_pre_mosdepth_include_dup_<timestamp>
    sibling; mv the .bak back to roll back.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Tree roots (override via --port-root / --production-root if needed)
# ---------------------------------------------------------------------------
DEFAULT_PORT_ROOT = Path("/goast/hemat_data/nf-core-tspipe")
DEFAULT_PRODUCTION_ROOT = Path("/home/hemat/targeted-seq-pipeline")


# ---------------------------------------------------------------------------
# Anchor strings. Every OLD must appear exactly once in its target file.
# ---------------------------------------------------------------------------

# --- modules/local/mosdepth.nf ---------------------------------------------
# Single-anchor patch: insert "--flag 772 \\" between "--no-per-base \\" and
# "--thresholds 100,250,500 \\". The 12-space indent matches the .nf style.
MOSDEPTH_NF_PRE_MD5 = "b2bf2361ae1425b9d3e88a646e359550"

OLD_MOSDEPTH_NF = (
    "            --no-per-base \\\\\n"
    "            --thresholds 100,250,500 \\\\\n"
)
NEW_MOSDEPTH_NF = (
    "            --no-per-base \\\\\n"
    "            --flag 772 \\\\\n"
    "            --thresholds 100,250,500 \\\\\n"
)


# --- bin/exon_coverage.py  AND  scripts/10b_exon_coverage.py ---------------
# Both files are byte-identical (md5 a8a8...) and share the same anchor.
EXON_COVERAGE_PY_PRE_MD5 = "a8a825352c7f331bda277b8c4cfca2aa"

OLD_EXON_COVERAGE_PY = (
    '        "--no-per-base",          # We only need region summaries\n'
    '        "--thresholds", ",".join(str(t) for t in COVERAGE_THRESHOLDS),\n'
)
NEW_EXON_COVERAGE_PY = (
    '        "--no-per-base",          # We only need region summaries\n'
    '        "--flag", "772",          # Include duplicates (clinical convention; 1796 default - 1024 DUP)\n'
    '        "--thresholds", ",".join(str(t) for t in COVERAGE_THRESHOLDS),\n'
)


# ---------------------------------------------------------------------------
# TARGETS table: filled in main() once we know the roots.
# ---------------------------------------------------------------------------
def build_targets(port_root: Path, production_root: Path):
    return [
        {
            "label": "port:modules/local/mosdepth.nf",
            "path": port_root / "modules" / "local" / "mosdepth.nf",
            "pre_md5": MOSDEPTH_NF_PRE_MD5,
            "edits": [
                ("flag_772", OLD_MOSDEPTH_NF, NEW_MOSDEPTH_NF),
            ],
        },
        {
            "label": "port:bin/exon_coverage.py",
            "path": port_root / "bin" / "exon_coverage.py",
            "pre_md5": EXON_COVERAGE_PY_PRE_MD5,
            "edits": [
                ("flag_772", OLD_EXON_COVERAGE_PY, NEW_EXON_COVERAGE_PY),
            ],
        },
        {
            "label": "production:scripts/10b_exon_coverage.py",
            "path": production_root / "scripts" / "10b_exon_coverage.py",
            "pre_md5": EXON_COVERAGE_PY_PRE_MD5,
            "edits": [
                ("flag_772", OLD_EXON_COVERAGE_PY, NEW_EXON_COVERAGE_PY),
            ],
        },
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
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


def classify_anchor(content: str, old: str, new: str) -> str:
    """Return 'pre' | 'post' | 'duplicate' | 'missing' | 'mixed'."""
    n_old = content.count(old)
    n_new = content.count(new)
    if n_old == 1 and n_new == 0:
        return "pre"
    if n_old == 0 and n_new == 1:
        return "post"
    if n_old > 1 or n_new > 1:
        return "duplicate"
    if n_old == 1 and n_new == 1:
        # If OLD is a substring of NEW, finding both means we're already in
        # post-state and the OLD substring lives inside NEW.
        if old in new:
            return "post"
        return "mixed"
    return "missing"


def color(s: str, code: str) -> str:
    if not sys.stdout.isatty():
        return s
    return f"\033[{code}m{s}\033[0m"


def green(s):  return color(s, "32")
def yellow(s): return color(s, "33")
def red(s):    return color(s, "31")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port-root", type=Path, default=DEFAULT_PORT_ROOT,
                    help=f"nf-core-tspipe repo root (default: {DEFAULT_PORT_ROOT})")
    ap.add_argument("--production-root", type=Path, default=DEFAULT_PRODUCTION_ROOT,
                    help=f"production pipeline root (default: {DEFAULT_PRODUCTION_ROOT})")
    ap.add_argument("--apply", action="store_true",
                    help="Actually modify files. Without this flag, the "
                         "script only prints the plan.")
    ap.add_argument("--archive", action="store_true",
                    help="On --apply success, also copy THIS patch script into "
                         "<port-root>/tools/patches/2026-05-17/ AND "
                         "<production-root>/tools/patches/2026-05-17/ for "
                         "the project audit trail.")
    args = ap.parse_args()

    port_root: Path = args.port_root
    prod_root: Path = args.production_root

    print("Patch: mosdepth --flag 772 (include duplicates)")
    print(f"  Port root:       {port_root}")
    print(f"  Production root: {prod_root}")
    print()

    targets = build_targets(port_root, prod_root)

    # ---- Phase 1: load, classify, plan ----------------------------------
    print("Phase 1: loading and classifying anchors")
    print()

    plan = []
    any_pre = False
    any_blocking = False
    already_applied_count = 0

    for spec in targets:
        label = spec["label"]
        path = spec["path"]
        if not path.is_file():
            print(f"  {red('MISSING')}: {label} -> {path}")
            any_blocking = True
            continue

        raw = read_bytes(path)
        actual_md5 = md5sum_bytes(raw)
        content = raw.decode("utf-8")

        print(f"  {label}")
        print(f"    path:        {path}")
        print(f"    current md5: {actual_md5}")
        if actual_md5 == spec["pre_md5"]:
            print(f"    state:       {green('PRE-PATCH')} (matches expected pre-md5)")
        else:
            print(f"    expected:    {spec['pre_md5']} (pre-patch)")
            print(f"    state:       {yellow('MODIFIED')} (md5 differs; checking anchors)")

        new_content = content
        n_pre = 0
        n_post = 0
        for name, old, new in spec["edits"]:
            state = classify_anchor(new_content, old, new)
            if state == "pre":
                print(f"      {name:12s} {green('PRE')}  (will apply)")
                new_content = new_content.replace(old, new, 1)
                n_pre += 1
            elif state == "post":
                print(f"      {name:12s} {yellow('POST')} (already applied; skip)")
                n_post += 1
            elif state == "duplicate":
                print(f"      {name:12s} {red('DUPLICATE')} (OLD or NEW found multiple times)")
                any_blocking = True
            elif state == "missing":
                print(f"      {name:12s} {red('MISSING')} (anchor not found; drift)")
                any_blocking = True
            elif state == "mixed":
                print(f"      {name:12s} {red('MIXED')} (both OLD and NEW non-overlapping; corrupt)")
                any_blocking = True

        if n_pre > 0:
            any_pre = True
            plan.append((path, new_content.encode("utf-8"), n_pre, n_post, label))
        else:
            already_applied_count += 1
        print()

    if any_blocking:
        print(red("ABORT: one or more anchors did not classify cleanly. No files written."))
        return 1

    if not any_pre:
        print(green("All anchors already in POST state. Patch is fully applied; nothing to do."))
        return 0

    # ---- Phase 2: gate --------------------------------------------------
    print(f"Phase 2: ready to write {len(plan)} file(s).")
    if already_applied_count:
        print(f"  ({already_applied_count} file(s) already fully applied; will be left alone)")
    print()
    if not args.apply:
        print(yellow("DRY-RUN. No files written. Re-run with --apply to execute."))
        return 0

    # ---- Phase 3: apply -------------------------------------------------
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak_suffix = f".bak_pre_mosdepth_include_dup_{ts}"
    print("Phase 3: applying")
    for path, new_bytes, n_pre, n_post, label in plan:
        bak = path.with_name(path.name + bak_suffix)
        shutil.copy2(path, bak)
        write_bytes_atomic(path, new_bytes)
        post_md5 = md5sum_bytes(read_bytes(path))
        print(f"  {green('APPLIED')} {label}")
        print(f"    backup:   {bak}")
        print(f"    new md5:  {post_md5}")
        print(f"    edits:    {n_pre} applied, {n_post} skipped (already post)")
    print()

    # ---- Phase 4 (optional): archive ------------------------------------
    if args.archive:
        for root in (port_root, prod_root):
            archive_dir = root / "tools" / "patches" / "2026-05-17"
            archive_dir.mkdir(parents=True, exist_ok=True)
            archive_dest = archive_dir / Path(sys.argv[0]).name
            shutil.copy2(sys.argv[0], archive_dest)
            print(f"Phase 4: archived patch script to {archive_dest}")
        print()

    print(green("Done."))
    print()
    print("Next steps:")
    print("  1. Verify diffs:")
    print(f"       cd {port_root} && git diff modules/local/mosdepth.nf bin/exon_coverage.py")
    print(f"       cd {prod_root} && git diff scripts/10b_exon_coverage.py")
    print("  2. Re-run validation against 25NGS1307 (port):")
    print("       MOSDEPTH should re-run (its command line changed); PARSE_EXON_COVERAGE")
    print("       inherits the new mosdepth output and re-runs too.")
    print("       Expected: ~5-10x higher Mean_Coverage values than the previous run.")
    print("  3. Commit (suggested message):")
    print("       fix(coverage): include duplicates in mosdepth (--flag 772)")
    print()
    print("To roll back: ")
    print(f"  for f in $(find {port_root} {prod_root} -name '*{bak_suffix}'); do")
    print('      mv "$f" "${f%' + bak_suffix + '}"')
    print("  done")

    return 0


if __name__ == "__main__":
    sys.exit(main())
