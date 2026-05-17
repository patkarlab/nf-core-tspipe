#!/usr/bin/env python3
"""
apply_exon_coverage_split_bundle1.py - 2026-05-17 morning

Bundle 1 of the EXON_COVERAGE container-fix refactor.

Stages three new files (the parser script + two new modules) into the
nf-core repo, retires the obsolete combined-module file. Wiring of
the new modules into PREPROCESSING / modules.config is handled by
Bundle 2 (apply_exon_coverage_split_bundle2.py), which is shipped
separately.

Source location (where Claude transfers files to):
    /home/hemat/inbox/from_claude/parse_exon_coverage.py
    /home/hemat/inbox/from_claude/mosdepth.nf
    /home/hemat/inbox/from_claude/parse_exon_coverage.nf

Destination layout:
    /goast/hemat_data/nf-core-tspipe/bin/parse_exon_coverage.py
    /goast/hemat_data/nf-core-tspipe/modules/local/mosdepth.nf
    /goast/hemat_data/nf-core-tspipe/modules/local/parse_exon_coverage.nf

Files retired (backed up, not deleted):
    /goast/hemat_data/nf-core-tspipe/modules/local/exon_coverage.nf
        -> .bak_split_into_mosdepth_and_parse_<ts>

The old bin/exon_coverage.py is kept (user decision: redundancy for
standalone use); only the .nf module is retired.

Idempotent: refuses to re-apply if all destination files already
exist with the expected content.
"""

import datetime
import hashlib
import pathlib
import shutil
import sys

REPO = pathlib.Path("/goast/hemat_data/nf-core-tspipe")
INBOX = pathlib.Path("/home/hemat/inbox/from_claude")

# (source filename in inbox, destination path inside repo)
NEW_FILES = [
    ("parse_exon_coverage.py", REPO / "bin"           / "parse_exon_coverage.py"),
    ("mosdepth.nf",            REPO / "modules/local" / "mosdepth.nf"),
    ("parse_exon_coverage.nf", REPO / "modules/local" / "parse_exon_coverage.nf"),
]

RETIRE = REPO / "modules/local/exon_coverage.nf"


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def main() -> int:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # Step 1: verify all source files exist in the inbox.
    for src_name, _ in NEW_FILES:
        src = INBOX / src_name
        if not src.is_file():
            print(f"ERROR: source not found: {src}", file=sys.stderr)
            print("Did you copy the bundle to /home/hemat/inbox/from_claude/ ?",
                  file=sys.stderr)
            return 1

    # Step 2: check idempotency. If every destination already exists with
    # matching content, this patch has already been applied.
    all_match = True
    for src_name, dst in NEW_FILES:
        src = INBOX / src_name
        if not dst.is_file() or sha256(src) != sha256(dst):
            all_match = False
            break
    if all_match and not RETIRE.is_file():
        print("ERROR: all destinations already match inbox sources, and the "
              "obsolete exon_coverage.nf is already retired. Patch appears "
              "to be already applied. Refusing to re-apply.", file=sys.stderr)
        return 1

    # Step 3: install the new files. Existing files at destination get
    # backed up first.
    for src_name, dst in NEW_FILES:
        src = INBOX / src_name
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            backup = dst.parent / f"{dst.name}.bak_split_{ts}"
            shutil.copy2(dst, backup)
            print(f"backup: {backup}")
        shutil.copy2(src, dst)
        # Make .py executable; .nf doesn't matter.
        if dst.suffix == ".py":
            dst.chmod(0o755)
        print(f"installed: {dst}")

    # Step 4: retire the obsolete module file.
    if RETIRE.is_file():
        backup = RETIRE.parent / f"{RETIRE.name}.bak_split_into_mosdepth_and_parse_{ts}"
        shutil.move(str(RETIRE), str(backup))
        print(f"retired: {RETIRE.name} -> {backup.name}")
    else:
        print(f"note: {RETIRE.name} already retired (no action)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
