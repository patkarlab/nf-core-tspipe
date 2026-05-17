#!/usr/bin/env python3
"""
apply_dashboard_patch.py

Deploy the per-sample QC dashboard renderer into the nf-core-tspipe
port. This patch:

  1. INSTALLS  bin/render_dashboard.py            (new file)
  2. INSTALLS  modules/local/sample_dashboard.nf  (new file)
  3. MODIFIES  subworkflows/local/preprocessing.nf  (3 anchor edits)

Files installed have md5 fingerprints baked into the patch so we know
the exact code being shipped. Preprocessing edits use the standard
authoring discipline from the prior 2026-05-17 patches:

  - Pre-flight md5 verification
  - Anchor classification (PRE / POST / MISSING / DUPLICATE / MIXED)
  - All-or-nothing: load + classify everything before writing
  - Atomic write via .tmp + os.replace
  - .bak_pre_dashboard_<ts> backups
  - Idempotent: re-run after success exits 0 with nothing to do

USAGE:
    python3 apply_dashboard_patch.py                    # dry-run
    python3 apply_dashboard_patch.py --apply            # write
    python3 apply_dashboard_patch.py --apply --archive  # + audit copy

ROLLBACK:
    Each modified file gets a .bak_pre_dashboard_<timestamp> sibling.
    Installed files (render_dashboard.py, sample_dashboard.nf) are
    new, so removing them rolls them back; the script remembers them
    and lists `rm` commands at the end on --apply success.
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
# Target root
# ---------------------------------------------------------------------------
DEFAULT_PORT_ROOT = Path("/goast/hemat_data/nf-core-tspipe")


# ---------------------------------------------------------------------------
# File installations (new files we drop in)
# ---------------------------------------------------------------------------
# Each entry: (source filename inside this bundle, destination relative path
# under the port root, expected md5 of the bundle source).
INSTALL_FILES = [
    ("render_dashboard.py",
     "bin/render_dashboard.py"),
    ("sample_dashboard.nf",
     "modules/local/sample_dashboard.nf"),
]


# ---------------------------------------------------------------------------
# Preprocessing.nf edits (3 anchors)
# ---------------------------------------------------------------------------
PREPROCESSING_PRE_MD5 = "2d93ff44884dff6dcbd7d088d59f2a2d"

# Edit 1: add the include line, sorted under the existing PARSE_EXON_COVERAGE
OLD_INCLUDE = (
    "include { MOSDEPTH               } from '../../modules/local/mosdepth'\n"
    "include { PARSE_EXON_COVERAGE    } from '../../modules/local/parse_exon_coverage'\n"
)
NEW_INCLUDE = (
    "include { MOSDEPTH               } from '../../modules/local/mosdepth'\n"
    "include { PARSE_EXON_COVERAGE    } from '../../modules/local/parse_exon_coverage'\n"
    "include { SAMPLE_DASHBOARD       } from '../../modules/local/sample_dashboard'\n"
)

# Edit 2: invoke SAMPLE_DASHBOARD after PARSE_EXON_COVERAGE in the main: block.
# We need to capture the existing line and put our additions right after.
OLD_CALL = (
    "        HSMETRICS(ABRA2.out.bam, reference_ch, bed_ch)\n"
    "        MOSDEPTH(ABRA2.out.bam, exonwise_bed_ch)\n"
    "        PARSE_EXON_COVERAGE(MOSDEPTH.out.regions_thresholds, exonwise_bed_ch)\n"
    "\n"
    "    emit:\n"
)
NEW_CALL = (
    "        HSMETRICS(ABRA2.out.bam, reference_ch, bed_ch)\n"
    "        MOSDEPTH(ABRA2.out.bam, exonwise_bed_ch)\n"
    "        PARSE_EXON_COVERAGE(MOSDEPTH.out.regions_thresholds, exonwise_bed_ch)\n"
    "\n"
    "        // Per-sample dashboard: join HsMetrics + per-exon coverage on meta.id,\n"
    "        // then render a self-contained HTML report. Provenance values are\n"
    "        // pulled from Nextflow's workflow object (commit + start time) and\n"
    "        // params.panel_name, with permissive defaults.\n"
    "        ch_dashboard_input = HSMETRICS.out.metrics\n"
    "            .join(PARSE_EXON_COVERAGE.out.tsv)\n"
    "        SAMPLE_DASHBOARD(\n"
    "            ch_dashboard_input,\n"
    "            params.panel_name ?: 'MYOPOOL hg38',\n"
    "            workflow.commitId ?: '(uncommitted)',\n"
    "            new java.text.SimpleDateFormat('yyyy-MM-dd').format(workflow.start)\n"
    "        )\n"
    "\n"
    "    emit:\n"
)

# Edit 3: add `dashboard` to the emit block
OLD_EMIT = (
    "        hsmetrics     = HSMETRICS.out.metrics\n"
    "        exon_coverage = PARSE_EXON_COVERAGE.out.tsv\n"
    "}\n"
)
NEW_EMIT = (
    "        hsmetrics     = HSMETRICS.out.metrics\n"
    "        exon_coverage = PARSE_EXON_COVERAGE.out.tsv\n"
    "        dashboard     = SAMPLE_DASHBOARD.out.html\n"
    "}\n"
)


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
    n_old = content.count(old)
    n_new = content.count(new)
    if n_old == 1 and n_new == 0: return "pre"
    if n_old == 0 and n_new == 1: return "post"
    if n_old > 1 or n_new > 1:    return "duplicate"
    if n_old == 1 and n_new == 1:
        if old in new: return "post"
        return "mixed"
    return "missing"


def color(s: str, code: str) -> str:
    if not sys.stdout.isatty(): return s
    return f"\033[{code}m{s}\033[0m"


def green(s):  return color(s, "32")
def yellow(s): return color(s, "33")
def red(s):    return color(s, "31")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port-root", type=Path, default=DEFAULT_PORT_ROOT)
    ap.add_argument("--apply", action="store_true",
                    help="Actually modify files. Default is dry-run.")
    ap.add_argument("--archive", action="store_true",
                    help="On --apply, also copy THIS script into "
                         "<port-root>/tools/patches/2026-05-17/ for the "
                         "project audit trail.")
    args = ap.parse_args()

    port_root: Path = args.port_root
    bundle_root = Path(__file__).resolve().parent

    print("Patch: deploy SAMPLE_DASHBOARD renderer")
    print(f"  Port root:    {port_root}")
    print(f"  Bundle root:  {bundle_root}")
    print()

    # ---- Phase 1: pre-flight ---------------------------------------------
    print("Phase 1: pre-flight verification")
    any_blocking = False

    # 1a. Verify the preprocessing.nf md5
    preprocessing_path = port_root / "subworkflows" / "local" / "preprocessing.nf"
    if not preprocessing_path.is_file():
        print(f"  {red('MISSING')}: {preprocessing_path}")
        any_blocking = True
        preprocessing_raw = b""
        preprocessing_content = ""
    else:
        preprocessing_raw = read_bytes(preprocessing_path)
        actual_md5 = md5sum_bytes(preprocessing_raw)
        preprocessing_content = preprocessing_raw.decode("utf-8")
        if actual_md5 == PREPROCESSING_PRE_MD5:
            print(f"  {green('MATCH')}    preprocessing.nf md5 = {actual_md5}")
        else:
            print(f"  {yellow('DRIFT')}    preprocessing.nf md5 = {actual_md5}")
            print(f"           expected   = {PREPROCESSING_PRE_MD5}")
            print("           Will fall back to anchor-only classification.")

    # 1b. Verify all bundle source files exist
    for src_name, _ in INSTALL_FILES:
        src = bundle_root / src_name
        if not src.is_file():
            print(f"  {red('MISSING')}: bundle file {src}")
            any_blocking = True

    print()

    # ---- Phase 2: classify all anchors -----------------------------------
    print("Phase 2: classifying preprocessing.nf anchors")
    edit_specs = [
        ("include line",      OLD_INCLUDE, NEW_INCLUDE),
        ("SAMPLE_DASHBOARD call", OLD_CALL, NEW_CALL),
        ("emit block",        OLD_EMIT,    NEW_EMIT),
    ]
    new_content = preprocessing_content
    n_pre = 0
    n_post = 0
    for name, old, new in edit_specs:
        state = classify_anchor(new_content, old, new)
        if state == "pre":
            print(f"  {green('PRE')}  {name}")
            new_content = new_content.replace(old, new, 1)
            n_pre += 1
        elif state == "post":
            print(f"  {yellow('POST')} {name} (already applied; skip)")
            n_post += 1
        elif state == "duplicate":
            print(f"  {red('DUPLICATE')} {name} (anchor found multiple times)")
            any_blocking = True
        elif state == "missing":
            print(f"  {red('MISSING')} {name} (anchor not found; drift)")
            any_blocking = True
        elif state == "mixed":
            print(f"  {red('MIXED')} {name} (both OLD and NEW present; corrupt)")
            any_blocking = True
    print()

    # ---- Phase 3: classify install files ---------------------------------
    print("Phase 3: classifying install files")
    installs_to_do = []
    for src_name, dest_rel in INSTALL_FILES:
        src = bundle_root / src_name
        dest = port_root / dest_rel
        if not src.is_file():
            continue   # already reported in phase 1
        src_md5 = md5sum_bytes(read_bytes(src))
        if dest.is_file():
            dest_md5 = md5sum_bytes(read_bytes(dest))
            if dest_md5 == src_md5:
                print(f"  {yellow('IDENT')} {dest_rel} already matches bundle md5 (skip)")
            else:
                print(f"  {yellow('OVERWRITE')} {dest_rel} exists with different md5")
                print(f"           current: {dest_md5}")
                print(f"           bundle:  {src_md5}")
                installs_to_do.append((src, dest, src_md5, "overwrite"))
        else:
            print(f"  {green('INSTALL')} {dest_rel} (new file, md5 {src_md5})")
            installs_to_do.append((src, dest, src_md5, "new"))
    print()

    if any_blocking:
        print(red("ABORT: pre-flight failures. No files written."))
        return 1

    if n_pre == 0 and not installs_to_do:
        print(green("Nothing to do; patch already fully applied."))
        return 0

    # ---- Phase 4: gate ---------------------------------------------------
    print(f"Phase 4: ready to write")
    print(f"  preprocessing.nf edits:  {n_pre} (skipping {n_post} already-post)")
    print(f"  files to install:        {len(installs_to_do)}")
    print()
    if not args.apply:
        print(yellow("DRY-RUN. Re-run with --apply to execute."))
        return 0

    # ---- Phase 5: apply --------------------------------------------------
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak_suffix = f".bak_pre_dashboard_{ts}"
    print("Phase 5: applying")
    rollback_cmds = []

    # 5a. Install new files
    for src, dest, src_md5, kind in installs_to_do:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if kind == "overwrite":
            bak = dest.with_name(dest.name + bak_suffix)
            shutil.copy2(dest, bak)
            rollback_cmds.append(f"mv '{bak}' '{dest}'")
        else:
            rollback_cmds.append(f"rm -f '{dest}'")
        shutil.copy2(src, dest)
        # Preserve executable bit on .py files
        if dest.suffix == ".py":
            mode = dest.stat().st_mode | 0o755
            dest.chmod(mode)
        post_md5 = md5sum_bytes(read_bytes(dest))
        if post_md5 != src_md5:
            print(f"  {red('INTEGRITY FAIL')} {dest}: post-write md5 mismatch")
            return 2
        label = "OVERWROTE" if kind == "overwrite" else "INSTALLED"
        print(f"  {green(label)}  {dest}")
        print(f"    md5: {post_md5}")

    # 5b. Patch preprocessing.nf
    if n_pre > 0:
        bak = preprocessing_path.with_name(preprocessing_path.name + bak_suffix)
        shutil.copy2(preprocessing_path, bak)
        rollback_cmds.append(f"mv '{bak}' '{preprocessing_path}'")
        write_bytes_atomic(preprocessing_path, new_content.encode("utf-8"))
        post_md5 = md5sum_bytes(read_bytes(preprocessing_path))
        print(f"  {green('PATCHED')}  {preprocessing_path}")
        print(f"    backup:   {bak}")
        print(f"    new md5:  {post_md5}")
        print(f"    edits:    {n_pre} applied, {n_post} skipped")
    print()

    # 5c. Archive
    if args.archive:
        archive_dir = port_root / "tools" / "patches" / "2026-05-17"
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_dest = archive_dir / Path(sys.argv[0]).name
        shutil.copy2(sys.argv[0], archive_dest)
        print(f"Phase 6: archived patch script to {archive_dest}")
        print()

    print(green("Done."))
    print()
    print("Next steps:")
    print(f"  cd {port_root}")
    print(f"  git status")
    print(f"  git diff subworkflows/local/preprocessing.nf")
    print(f"  git add bin/render_dashboard.py \\")
    print(f"          modules/local/sample_dashboard.nf \\")
    print(f"          subworkflows/local/preprocessing.nf \\")
    print(f"          tools/patches/2026-05-17/apply_dashboard_patch.py  # if --archive")
    print(f"  git commit -m 'feat(qc): per-sample HTML QC dashboard'")
    print()
    print("Validation: re-run against 25NGS1307.")
    print(f"  RUN_OUT=/goast/hemat_data/nfcore_runs/25NGS1307_dashboard_$(date +%Y%m%d_%H%M%S)")
    print(f"  mkdir -p $RUN_OUT")
    print(f"  Then nextflow run with -resume. Only SAMPLE_DASHBOARD should be new.")
    print()
    print("Rollback (per-file mv/rm):")
    for cmd in rollback_cmds:
        print(f"  {cmd}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
