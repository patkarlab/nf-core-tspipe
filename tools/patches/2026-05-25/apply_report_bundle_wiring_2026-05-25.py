#!/usr/bin/env python3
"""
apply_report_bundle_wiring_2026-05-25.py

Wires the REPORT_BUNDLE module into the nf-core-tspipe workflow.

This script makes three edits across two files. Each edit is matched
by an exact block (whitespace included) and applied at most once.
Each file gets its own timestamped .bak backup before editing.

Edit 1 - modules/local/dashboard.nf
    Adds a new output emit for the patched per-sample clinical/
    directories. REPORT_BUNDLE consumes these.

Edit 2 - workflows/tspipe.nf
    Adds the REPORT_BUNDLE include line near the other module
    includes at the top of the file.

Edit 3 - workflows/tspipe.nf
    Adds the REPORT_BUNDLE process call after the DASHBOARD call at
    the end of the workflow.

Behaviour
---------
- Idempotent: if all three markers are present, exits clean.
- Refuses to run if any expected source block is not found verbatim
  (the file may have been edited since this patch was written).
- Backups: <file>.bak_apply_report_bundle_wiring_<timestamp>.
- On any failure, rolls back from backup.

Usage
-----
    python3 apply_report_bundle_wiring_2026-05-25.py
"""

from __future__ import annotations

import ast
import datetime as dt
import shutil
import sys
from pathlib import Path

# --------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------

REPO_ROOT       = Path("/goast/hemat_data/nf-core-tspipe")
DASHBOARD_FILE  = REPO_ROOT / "modules/local/dashboard.nf"
WORKFLOW_FILE   = REPO_ROOT / "workflows/tspipe.nf"
MODULE_FILE     = REPO_ROOT / "modules/local/report_bundle.nf"

# Marker strings used for idempotency checks
DASHBOARD_MARKER = "emit: clinical_dirs"
INCLUDE_MARKER   = "include { REPORT_BUNDLE"
CALL_MARKER      = "REPORT_BUNDLE("

# Edit 1: dashboard.nf - add new emit between sample_reports and caches
EDIT1_OLD = '''        path '*/clinical/*_report.html',                   emit: sample_reports
        path "*/clinical/*_cache.json",   emit: caches,          optional: true
'''

EDIT1_NEW = '''        path '*/clinical/*_report.html',                   emit: sample_reports
        path '*/clinical',                                 emit: clinical_dirs
        path "*/clinical/*_cache.json",   emit: caches,          optional: true
'''

# Edit 2: tspipe.nf - add include line right after DASHBOARD include
EDIT2_OLD = '''include { DASHBOARD           } from '../modules/local/dashboard'
'''

EDIT2_NEW = '''include { DASHBOARD           } from '../modules/local/dashboard'
include { REPORT_BUNDLE       } from '../modules/local/report_bundle'
'''

# Edit 3: tspipe.nf - add REPORT_BUNDLE call after DASHBOARD call.
# We anchor on the closing of DASHBOARD's call. Be careful to match
# exact indentation and the closing brace of the workflow block.
EDIT3_OLD = '''    DASHBOARD(
        ch_dashboard_in.sample_ids,
        ch_dashboard_in.clinical_dirs,
    )
}
'''

EDIT3_NEW = '''    DASHBOARD(
        ch_dashboard_in.sample_ids,
        ch_dashboard_in.clinical_dirs,
    )

    // ----- 9. REPORT_BUNDLE: zip per-sample shareable bundles ---------
    REPORT_BUNDLE(
        ch_dashboard_in.sample_ids,
        DASHBOARD.out.clinical_dirs,
        DASHBOARD.out.assets,
    )
}
'''


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------

def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def ok(msg: str) -> None:
    print(f"OK:    {msg}")


def info(msg: str) -> None:
    print(f"INFO:  {msg}")


def warn(msg: str) -> None:
    print(f"WARN:  {msg}", file=sys.stderr)


def backup_file(target: Path, label: str) -> Path:
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = target.with_suffix(target.suffix + f".bak_apply_{label}_{ts}")
    shutil.copy2(target, backup)
    return backup


def apply_edit(
    target: Path,
    old: str,
    new: str,
    label: str,
    marker: str,
) -> tuple[bool, Path]:
    """
    Apply a single string-replacement edit to target if marker is not
    yet present. Returns (changed, backup_path_or_None).

    Refuses to run if marker is absent AND old block not found verbatim.
    """
    text = target.read_text()

    if marker in text:
        ok(f"{target.name}: marker '{marker}' already present, skipping")
        return False, None

    if old not in text:
        fail(
            f"{target.name}: could not find the expected source block "
            f"verbatim for edit '{label}'. The file may have been edited "
            f"since this patch was written. Aborting."
        )
    if text.count(old) != 1:
        fail(
            f"{target.name}: expected exactly 1 occurrence of source "
            f"block for edit '{label}', found {text.count(old)}."
        )

    backup = backup_file(target, label)
    info(f"{target.name}: backup written -> {backup.name}")

    new_text = text.replace(old, new, 1)
    target.write_text(new_text)
    info(f"{target.name}: edit '{label}' applied")
    return True, backup


def rollback(target: Path, backup: Path) -> None:
    if backup and backup.exists():
        shutil.copy2(backup, target)
        info(f"{target.name}: rolled back from {backup.name}")


# --------------------------------------------------------------------
# Main
# --------------------------------------------------------------------

def main() -> int:
    # Pre-flight checks
    for p in (DASHBOARD_FILE, WORKFLOW_FILE, MODULE_FILE):
        if not p.is_file():
            fail(f"required file not found: {p}")

    backups = []
    try:
        # Edit 1: dashboard.nf emit
        _, b1 = apply_edit(
            DASHBOARD_FILE,
            EDIT1_OLD, EDIT1_NEW,
            label="report_bundle_wiring_edit1",
            marker=DASHBOARD_MARKER,
        )
        if b1: backups.append((DASHBOARD_FILE, b1))

        # Edit 2: tspipe.nf include
        _, b2 = apply_edit(
            WORKFLOW_FILE,
            EDIT2_OLD, EDIT2_NEW,
            label="report_bundle_wiring_edit2",
            marker=INCLUDE_MARKER,
        )
        if b2: backups.append((WORKFLOW_FILE, b2))

        # Edit 3: tspipe.nf process call
        _, b3 = apply_edit(
            WORKFLOW_FILE,
            EDIT3_OLD, EDIT3_NEW,
            label="report_bundle_wiring_edit3",
            marker=CALL_MARKER,
        )
        if b3: backups.append((WORKFLOW_FILE, b3))

    except SystemExit:
        # Bubble up after rolling back any partial changes
        for target, backup in reversed(backups):
            rollback(target, backup)
        raise

    # Post-flight verification
    dash_text = DASHBOARD_FILE.read_text()
    wf_text   = WORKFLOW_FILE.read_text()

    if DASHBOARD_MARKER not in dash_text:
        fail("post-check: DASHBOARD_MARKER not present after edit")
    if INCLUDE_MARKER not in wf_text:
        fail("post-check: INCLUDE_MARKER not present after edit")
    if CALL_MARKER not in wf_text:
        fail("post-check: CALL_MARKER not present after edit")

    ok("all three edits present and verified")
    info("")
    info("Next steps:")
    info(f"  1. Make sure {MODULE_FILE.name} exists at {MODULE_FILE}")
    info(f"  2. Stub-run to verify wiring (no real work):")
    info(f"     nextflow run nf-core-tspipe -profile test -stub-run -resume")
    info(f"  3. Real run to test on data:")
    info(f"     nextflow run nf-core-tspipe -profile <yours> -resume")
    info("  4. To roll back: copy each .bak_apply_report_bundle_wiring_* "
         "file back over its target.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
