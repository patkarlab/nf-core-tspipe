#!/usr/bin/env python3
"""
apply_docs_usage_pon_rewrite.py

Backs up the existing docs/usage_pon.md and replaces it with the rewritten
version that reflects the actual BUILD_PON behavior as of 2026-05-24.

What changed in the doc
-----------------------
The previous doc predated the panel-namespacing refactor (2026-05-15) and
the three patches landed today. It documented:
- An old command line missing --panel and --male_reference
- An old output layout (results/pon/) that no longer matches reality
- The legacy MYOPOOL BED filename as the example
- -profile docker while gandalf uses singularity
- 55-normal cohort guidance from a now-stale recipe

The new doc covers what actually works:
- All required and optional params, with the chrX-threshold derivation
- Real cohort guidance (the 2026-05-24 build used 13M + 12F successfully)
- The actual output layout including the known publishDir gotcha
- The full end-to-end recipe: stub run, real run, seed assets
- The sex-classification math under both --male_reference values
- A troubleshooting section that names every error we hit today

Safety
------
- Writes docs/usage_pon.md.bak_apply_docs_usage_pon_rewrite_<ts> before
  overwriting.
- Idempotent: detects the post-rewrite marker and skips on re-run.

Usage
-----
    python3 tools/patches/2026-05-24/apply_docs_usage_pon_rewrite.py

After applying, the new doc must be accompanied by:
    docs/usage_pon.md.new_content      -- the content this script writes,
                                          delivered alongside as a sibling
                                          file in the same patches dir.

The script reads its replacement content from a NEW_CONTENT_PATH constant
below, which points at the sibling file. Drop both into
tools/patches/2026-05-24/ before running.

Rollback
--------
    cp docs/usage_pon.md.bak_apply_docs_usage_pon_rewrite_<ts> \\
       docs/usage_pon.md
"""

import datetime
import shutil
import sys
from pathlib import Path

REPO_ROOT       = Path("/goast/hemat_data/nf-core-tspipe")
TARGET          = REPO_ROOT / "docs" / "usage_pon.md"
NEW_CONTENT_PATH = REPO_ROOT / "tools" / "patches" / "2026-05-24" / "usage_pon.md.new"

TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK_SUFFIX = f".bak_apply_docs_usage_pon_rewrite_{TS}"

# A unique substring that only appears in the new doc. Used for idempotency.
ALREADY_APPLIED_MARKER = "## Known limitations\n\n### Sex-mixed LOO noise profile"


def main() -> int:
    if not NEW_CONTENT_PATH.exists():
        print(
            f"ERROR: replacement content not found: {NEW_CONTENT_PATH}\n"
            f"Drop usage_pon.md.new into the same directory as this script "
            f"before running.",
            file=sys.stderr,
        )
        return 1
    if not TARGET.exists():
        print(
            f"WARNING: target does not exist: {TARGET}\n"
            f"Will create it (no backup possible).",
            file=sys.stderr,
        )
        new_content = NEW_CONTENT_PATH.read_text()
        TARGET.parent.mkdir(parents=True, exist_ok=True)
        TARGET.write_text(new_content)
        print(f"Created:   {TARGET}")
        return 0

    current = TARGET.read_text()
    if ALREADY_APPLIED_MARKER in current:
        print(f"No-op: {TARGET} already shows the rewritten content.")
        return 0

    new_content = NEW_CONTENT_PATH.read_text()
    if ALREADY_APPLIED_MARKER not in new_content:
        print(
            f"ERROR: idempotency marker not present in replacement content. "
            f"The replacement file may be wrong or corrupt.",
            file=sys.stderr,
        )
        return 2

    # Backup
    backup = TARGET.with_name(TARGET.name + BAK_SUFFIX)
    shutil.copy2(TARGET, backup)
    print(f"Backed up: {backup}")

    # Replace
    TARGET.write_text(new_content)
    print(f"Rewrote:   {TARGET}")
    print()
    print(f"Old doc preserved at: {backup}")
    print(f"Diff to see what changed:")
    print(f"  diff -u {backup} {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
