#!/usr/bin/env python3
"""
apply_build_sex_pon_filename_and_threshold_fix.py

Fixes two coupled bugs in BUILD_SEX_PON that together stopped the
2026-05-24 BUILD_PON --panel myeloid_cnv run after CNV_LOO_QC succeeded.

Bug A: output filename mismatch
-------------------------------
modules/local/build_sex_pon.nf declares outputs:
    path "cnvkit_pon_male.cnn"
    path "cnvkit_pon_female.cnn"
but bin/build_sex_pon.py wrote:
    cnvkit_hg38_pon_male.cnn
    cnvkit_hg38_pon_female.cnn

Nextflow then failed with "Missing output file(s) cnvkit_pon_male.cnn"
even though the script produced the file under a different name.

The module is canonical here: nextflow.config defines the asset-fallback
paths as assets/${panel}/cnvkit_pon_male.cnn (no _hg38_), and TSPIPE's
params.cnv_pon_male wiring matches. So we strip _hg38_ from the script's
output filenames. The production-side scripts/12c_build_sex_pon.py is a
separate copy (per the 2026-05-15 split) and is NOT modified.

Bug B: chrX threshold calibrated for the wrong reference type
-------------------------------------------------------------
The script's --chrx-threshold default is -0.4, which is correct for a
female reference (males chrX log2 ~ -1, females ~ 0). But CNV_LOO_QC
runs with -y when params.male_reference=true (the gandalf default), so
the .cnr log2 values that BUILD_SEX_PON reads are in the male-reference
frame: males ~ 0, females ~ +1. Under -y the threshold should be ~+0.5.

The 2026-05-24 run showed this pattern clearly:
    13 known males:   chrX log2 in [0.07, 0.13]
    12 known females: chrX log2 in [0.92, 0.99]
A threshold of -0.4 classified all 25 as female -> 0 males -> male PON
file never created -> Nextflow error.

This fix derives the threshold from params.male_reference in the module,
with an explicit params.chrx_threshold override:

    def thresh = params.chrx_threshold ?: (params.male_reference ? 0.5 : -0.5)

and registers params.chrx_threshold = null in nextflow.config.

Why pick params over task.ext for the override
----------------------------------------------
task.ext.* values are typically wired in conf/modules.config under a
withName block. That's fine for things like exclude_samples that get
set once and forgotten. The chrX threshold is the kind of knob a user
might genuinely want to twist per-run (different panels can shift the
chrX cluster centers), so a params.* override is more discoverable.

Safety
------
- Each of the four edits is independently checked: if its baseline isn't
  exactly present, the edit aborts before any file is touched.
- One .bak_* backup per modified file (three files total).
- Idempotent: re-running detects a post-fix marker in each file and
  skips edits that have already been applied. Partial-reapply works.

Usage
-----
    python3 tools/patches/2026-05-24/apply_build_sex_pon_filename_and_threshold_fix.py

Rollback (per file)
-------------------
    cp <file>.bak_apply_build_sex_pon_filename_and_threshold_fix_<ts> <file>
"""

import datetime
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path("/goast/hemat_data/nf-core-tspipe")
TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK_SUFFIX = f".bak_apply_build_sex_pon_filename_and_threshold_fix_{TS}"

SCRIPT = REPO_ROOT / "bin" / "build_sex_pon.py"
MODULE = REPO_ROOT / "modules" / "local" / "build_sex_pon.nf"
CONFIG = REPO_ROOT / "nextflow.config"

# Each edit is (path, label, old_str, new_str, post_fix_marker).
# The marker is a string that appears in the file ONLY after the edit;
# if marker is in the file, the edit is skipped (idempotent).
EDITS = [
    {
        "path": SCRIPT,
        "label": "bin/build_sex_pon.py: rename male PON output",
        "old": '            male_out = out_dir / "cnvkit_hg38_pon_male.cnn"',
        "new": '            male_out = out_dir / "cnvkit_pon_male.cnn"',
        "marker": 'male_out = out_dir / "cnvkit_pon_male.cnn"',
    },
    {
        "path": SCRIPT,
        "label": "bin/build_sex_pon.py: rename female PON output",
        "old": '            female_out = out_dir / "cnvkit_hg38_pon_female.cnn"',
        "new": '            female_out = out_dir / "cnvkit_pon_female.cnn"',
        "marker": 'female_out = out_dir / "cnvkit_pon_female.cnn"',
    },
    {
        "path": MODULE,
        "label": "modules/local/build_sex_pon.nf: derive chrX threshold from params.male_reference",
        "old": """        def excludes = task.ext.exclude_samples ?: 'OCIAML3'
        def thresh   = task.ext.chrx_threshold  ?: -0.4""",
        "new": """        def excludes = task.ext.exclude_samples ?: 'OCIAML3'
        // chrX-log2 threshold depends on the reference type CNV_LOO_QC used:
        //   male_reference=true  -> LOO ran with -y; males X~0, females X~+1; threshold ~+0.5
        //   male_reference=false -> LOO ran without -y; males X~-1, females X~0; threshold ~-0.5
        // params.chrx_threshold overrides the auto-derived default.
        def thresh   = params.chrx_threshold ?: (params.male_reference ? 0.5 : -0.5)""",
        "marker": "params.chrx_threshold ?: (params.male_reference ? 0.5 : -0.5)",
    },
    {
        "path": CONFIG,
        "label": "nextflow.config: register params.chrx_threshold",
        "old": (
            "    male_reference     = true        // pass -y to cnvkit (haploid X "
            "reference); set false for female-only PoN"
        ),
        "new": (
            "    male_reference     = true        // pass -y to cnvkit (haploid X "
            "reference); set false for female-only PoN\n"
            "    chrx_threshold     = null        // chrX log2 cutoff for BUILD_SEX_PON sex classification;\n"
            "                                     // null => derived from male_reference (+0.5 if -y, else -0.5)"
        ),
        "marker": "chrx_threshold     = null",
    },
]


def main() -> int:
    # Pre-flight: every edit must be either applied-able (old present
    # exactly once) or already-applied (marker present). Anything else
    # means the file has drifted and we should abort without touching
    # anything.
    plans = []
    for edit in EDITS:
        path = edit["path"]
        if not path.exists():
            print(f"ERROR: target not found: {path}", file=sys.stderr)
            return 1
        content = path.read_text()
        if edit["marker"] in content:
            plans.append((edit, "skip", content))
            continue
        old_count = content.count(edit["old"])
        if old_count == 1:
            plans.append((edit, "apply", content))
        else:
            print(
                f"ERROR: '{edit['label']}' baseline expected exactly 1 time "
                f"in {path.name}, found {old_count}. Marker also absent. "
                f"File may have drifted; aborting without changes.",
                file=sys.stderr,
            )
            return 2

    # Pre-flight passed. Group edits by file so we make ONE backup per file
    # and apply both string-replacements to the same in-memory content.
    by_path: dict[Path, list] = {}
    for edit, action, content in plans:
        by_path.setdefault(edit["path"], []).append((edit, action, content))

    summary_apply = []
    summary_skip = []

    for path, items in by_path.items():
        # If every edit for this file is skip, nothing to do.
        if all(action == "skip" for _, action, _ in items):
            for edit, _, _ in items:
                summary_skip.append(edit["label"])
            continue

        # Backup before first write
        backup = path.with_name(path.name + BAK_SUFFIX)
        # Use the content snapshot from the first item (all items in
        # this group read the file at the same time during pre-flight).
        original = items[0][2]
        # Defensive: re-read from disk for the actual backup so we never
        # ship a stale snapshot.
        shutil.copy2(path, backup)
        print(f"Backed up: {backup}")

        new_content = original
        for edit, action, _ in items:
            if action == "apply":
                new_content = new_content.replace(edit["old"], edit["new"])
                summary_apply.append(edit["label"])
            else:
                summary_skip.append(edit["label"])

        path.write_text(new_content)
        print(f"Patched:   {path}")

    print()
    print("Edits applied:")
    for s in summary_apply:
        print(f"  + {s}")
    if summary_skip:
        print("Edits skipped (already applied):")
        for s in summary_skip:
            print(f"  = {s}")
    print()
    print("Next:")
    print("  Re-run BUILD_PON with -resume.")
    print("  Only BUILD_SEX_PON re-executes (~30s); upstream is cached.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
