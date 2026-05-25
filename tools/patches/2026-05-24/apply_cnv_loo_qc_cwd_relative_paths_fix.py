#!/usr/bin/env python3
"""
apply_cnv_loo_qc_cwd_relative_paths_fix.py

Fixes bin/cnv_loo_qc.py so panel-namespaced output artifacts
(cnvkit_loo_summary.tsv, cnvkit_noisy_bins.bed) are written CWD-relative
instead of PIPELINE_DIR-relative.

Background
----------
The 2026-05-24 BUILD_PON run failed at CNV_LOO_QC with:
    Missing output file(s) `references/myeloid_cnv/cnvkit_loo_summary.tsv`
    expected by process `BUILD_PON:CNV_LOO_QC (loo_qc)`

The script ran cleanly (exit 0, all stats produced), but it wrote outputs to
    /goast/hemat_data/nf-core-tspipe/references/myeloid_cnv/...
i.e. the *repo root*, not the Nextflow work directory. The Nextflow module
declares its outputs as `path "references/${params.panel}/..."` which is
work-dir-relative, so `publishDir` could never see the files.

The offending line (bin/cnv_loo_qc.py:606) is:
    ref_dir = os.path.join(PIPELINE_DIR, "references", args.panel)

This script changes it to a CWD-relative path:
    ref_dir = os.path.join("references", args.panel)

Why this is also correct for the production pipeline
----------------------------------------------------
The production runner cd's to the pipeline root before invoking the script.
So in production:
    CWD == PIPELINE_DIR
    "references/<panel>"  resolves the same as  "<PIPELINE_DIR>/references/<panel>"
Behavior is unchanged. The hidden coupling to PIPELINE_DIR was a latent bug
all along: a script that writes outside the directory the user cd'd into is
surprising at best.

Safety
------
- str_replace pre-flight aborts if the exact baseline isn't found.
- Writes bin/cnv_loo_qc.py.bak_apply_cnv_loo_qc_cwd_relative_paths_fix_<ts>.
- Idempotent: re-running detects the post-fix marker and exits 0.

Usage
-----
    python3 tools/patches/2026-05-24/apply_cnv_loo_qc_cwd_relative_paths_fix.py

After applying
--------------
    cd /goast/hemat_data/nf-core-tspipe
    # Re-run with -resume; cached preprocessing + CNVKIT_PON_BUILD are
    # untouched, only CNV_LOO_QC and downstream BUILD_SEX_PON re-execute.
    nextflow run main.nf -entry BUILD_PON ... -resume

Rollback
--------
    cp bin/cnv_loo_qc.py.bak_apply_cnv_loo_qc_cwd_relative_paths_fix_<ts> \\
       bin/cnv_loo_qc.py
"""

import datetime
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path("/goast/hemat_data/nf-core-tspipe")
TARGET = REPO_ROOT / "bin" / "cnv_loo_qc.py"
TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK_SUFFIX = f".bak_apply_cnv_loo_qc_cwd_relative_paths_fix_{TS}"

# -----------------------------------------------------------------------------
# Edit: rewrite the ref_dir construction. We replace the comment line too so
# the docstring stays accurate after the change.
# -----------------------------------------------------------------------------

OLD = """    # Panel-namespaced reference directory (e.g. references/myeloid/).
    ref_dir = os.path.join(PIPELINE_DIR, "references", args.panel)"""

NEW = """    # Panel-namespaced reference directory (e.g. references/myeloid/),
    # CWD-relative so the script works in both:
    #   - Production pipeline (the runner cd's to the pipeline root before
    #     invoking, so CWD == PIPELINE_DIR and behavior is unchanged).
    #   - nf-core BUILD_PON (CWD == Nextflow work dir; publishDir expects
    #     outputs at <work>/references/<panel>/).
    ref_dir = os.path.join("references", args.panel)"""

# Idempotency marker = a string that only exists post-fix.
ALREADY_APPLIED_MARKER = 'ref_dir = os.path.join("references", args.panel)'


def main() -> int:
    if not TARGET.exists():
        print(f"ERROR: target not found: {TARGET}", file=sys.stderr)
        return 1

    content = TARGET.read_text()

    if ALREADY_APPLIED_MARKER in content:
        print(f"No-op: {TARGET} already uses the CWD-relative ref_dir.")
        return 0

    count = content.count(OLD)
    if count != 1:
        print(
            f"ERROR: expected exactly 1 occurrence of the baseline ref_dir "
            f"block, found {count}. File may have drifted; aborting without "
            f"changes.",
            file=sys.stderr,
        )
        return 2

    # Backup
    backup = TARGET.with_name(TARGET.name + BAK_SUFFIX)
    shutil.copy2(TARGET, backup)
    print(f"Backed up: {backup}")

    # Apply
    new_content = content.replace(OLD, NEW)
    TARGET.write_text(new_content)
    print(f"Patched:   {TARGET}")
    print()
    print("Edit applied:")
    print("  ref_dir is now CWD-relative instead of PIPELINE_DIR-relative.")
    print("  Production behavior unchanged (runner cd's to pipeline root).")
    print("  Nextflow CNV_LOO_QC will now find its outputs in the work dir.")
    print()
    print("Next:")
    print("  Re-run BUILD_PON with -resume to pick up where it failed.")
    print()
    print(f"To rollback:")
    print(f"  cp {backup} {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
