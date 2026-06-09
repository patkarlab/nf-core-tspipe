#!/usr/bin/env python3
"""
apply_report_bundle_pairing_fix_v2_2026-05-25.py

V2 of the REPORT_BUNDLE pairing fix.

V1 failed Groovy compilation on Nextflow 25.10.4. The bash regex
'_igv_report-dot-html-dollar' (using backslash-dot and backslash-dollar)
inside a triple-quoted GString included an unrecognized Groovy escape
sequence (backslash followed by dot). Some Groovy parser versions
reject unknown backslash escapes in double-quoted GString contexts and
report the error at the next quote-boundary on the next line rather
than at the offending escape itself.

V2 avoids regex entirely. The IGV-report-skipping logic is implemented
in pure bash globbing plus pattern matching. No backslashes appear
inside the Groovy GString other than the standard ones for literal
dollar and literal dollar-brace. This is the same pattern dozens of
existing nf-core modules use without trouble.

Idempotent. Both files get fresh .bak backups (v2 suffix) before the
write. Rolls back on verification failure.

Usage:
    python3 apply_report_bundle_pairing_fix_v2_2026-05-25.py

Precondition: roll back the v1 patch first if it was applied. The
script will detect and refuse to run if it sees the broken v1 content.
"""

from __future__ import annotations

import datetime as dt
import shutil
import sys
from pathlib import Path

# --------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------

REPO_ROOT      = Path("/goast/hemat_data/nf-core-tspipe")
MODULE_FILE    = REPO_ROOT / "modules/local/report_bundle.nf"
WORKFLOW_FILE  = REPO_ROOT / "workflows/tspipe.nf"

# v2 markers (different from v1 so we can tell them apart)
MODULE_MARKER   = "v2: bash-glob skips IGV reports"
WORKFLOW_MARKER = "sample_ids inferred inside the module"

# Detect the v1 broken state (so we refuse to clobber it without rollback)
V1_BROKEN_PATTERN = "_igv_report\\.html\\$"

# Detect that we're starting from the pre-patch state (val sample_ids
# still present in module input block)
PRE_PATCH_MARKER = "val  sample_ids"

# --------------------------------------------------------------------
# New module content (whole-file rewrite, v2)
# --------------------------------------------------------------------

NEW_MODULE_CONTENT = '''/*
 * modules/local/report_bundle.nf
 *
 * Build self-contained, shareable zip bundles of per-sample reports.
 *
 * One zip per sample, published as:
 *     ${params.outdir}/<sample>/<sample>_report.zip
 *
 * Each zip is independently openable: a fellow downloads it, unzips
 * it, and double-clicks <sample>_report.html. All asset paths (CSS,
 * JS, PDFs, sub-iframes) resolve correctly because the bundler script
 * copies the shared assets/ directory into each bundle and rewrites
 * the report's relative paths from ../../assets/ to ./assets/.
 *
 * Design notes:
 *
 * 1. Cohort-level process, like DASHBOARD. Consumes the patched
 *    clinical/ directories DASHBOARD produces, plus the shared
 *    assets/ directory DASHBOARD emits.
 *
 * 2. Sample IDs are inferred from the *_report.html filename inside
 *    each staged clinical/ directory (v2: bash-glob skips IGV reports
 *    without using regex). This is robust against DASHBOARD's
 *    *\\/clinical glob being emitted in an order that does not match
 *    the workflow's original sample channel ordering. Previous
 *    versions of this module took a parallel val sample_ids list and
 *    zipped it positionally with the staged dirs, which could
 *    mis-pair when glob expansion reordered things.
 *
 * 3. Host execution. The bundler is stdlib-only Python 3, no extra
 *    dependencies.
 *
 * 4. publishDir scope: params.outdir is the run directory. The
 *    bundler writes zips as <sample>/<sample>_report.zip; publishDir
 *    copies them to the run directory alongside the existing
 *    clinical/ folder.
 *
 * 5. Symlink staging. cnvkit_plots can be ~35 MB per sample. We
 *    symlink rather than copy so the only real I/O is the zip write.
 *
 * 6. --force at every invocation. A Nextflow re-run that bypasses
 *    cache legitimately wants to replace existing zips, so we always
 *    pass --force. The bundler is idempotent.
 */

process REPORT_BUNDLE {
    tag        'cohort'
    label      'process_low'

    executor   'local'

    publishDir "${params.outdir}",
        mode:    'copy',
        saveAs:  { fn -> fn == 'versions.yml' ? null : fn }

    input:
        // DASHBOARD's patched per-sample clinical/ directories and the
        // shared assets/ directory. Sample IDs are derived from file
        // naming inside each clinical dir (see design note 2).
        path clinical_dirs, stageAs: 'src/?/clinical'
        path assets_dir,    stageAs: 'assets'

    output:
        path '*/*_report.zip', emit: zips
        path 'versions.yml',   emit: versions

    when:
        task.ext.when == null || task.ext.when

    script:
        def bundler_py = "${projectDir}/tools/make_report_bundle.py"
        """
        set -euo pipefail

        # ----------------------------------------------------------------
        # Re-stage: src/<i>/clinical/  +  ./assets/   ->   bundle_view/
        # ----------------------------------------------------------------
        # For each staged clinical dir, find its sample ID by scanning
        # for the per-sample <sid>_report.html file (NOT the IGV one).
        # Pure bash globbing, no regex inside the GString.
        #
        # Symlink rather than copy: cnvkit_plots is ~35 MB per sample
        # and we do not need a duplicate copy before the zip step.

        mkdir -p bundle_view
        ln -sfn "\\$(readlink -f assets)" bundle_view/assets

        for src in src/*/clinical; do
            report=""
            for f in "\\${src}"/*_report.html; do
                # If the glob did not match, f is the literal pattern.
                if [[ ! -f "\\$f" ]]; then
                    continue
                fi
                # Skip the IGV per-sample report.
                if [[ "\\$f" == *_igv_report.html ]]; then
                    continue
                fi
                report="\\$f"
                break
            done

            if [[ -z "\\$report" ]]; then
                echo "ERROR: no per-sample *_report.html in \\${src}" >&2
                exit 1
            fi

            sid=\\$(basename "\\$report" _report.html)
            mkdir -p "bundle_view/\\${sid}"
            ln -sfn "\\$(readlink -f "\\$src")" "bundle_view/\\${sid}/clinical"
        done

        # ----------------------------------------------------------------
        # Run the bundler over all samples.
        # ----------------------------------------------------------------
        python3 ${bundler_py} --outdir bundle_view --force

        # ----------------------------------------------------------------
        # Promote zips to the work-dir root so publishDir's pattern
        # '*/*_report.zip' picks them up at
        #     <outdir>/<sample>/<sample>_report.zip
        # rather than under a bundle_view/ prefix.
        # ----------------------------------------------------------------
        for bundle_zip in bundle_view/*/*_report.zip; do
            if [[ ! -e "\\$bundle_zip" ]]; then
                continue
            fi
            sid=\\$(basename "\\$bundle_zip" _report.zip)
            mkdir -p "\\${sid}"
            mv "\\$bundle_zip" "\\${sid}/\\${sid}_report.zip"
        done

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            python: \\$(python3 --version 2>&1 | awk '{print \\$2}')
            make_report_bundle: '0.2'
        END_VERSIONS
        """

    stub:
        """
        # Stub: emit one placeholder zip per staged clinical dir.
        i=0
        for src in src/*/clinical; do
            i=\\$((i + 1))
            sid="STUB_SAMPLE_\\${i}"
            mkdir -p "\\${sid}"
            touch "\\${sid}/\\${sid}_report.zip"
        done
        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            stub: true
        END_VERSIONS
        """
}
'''

# --------------------------------------------------------------------
# Workflow file edit (single string replacement) -- same as v1
# --------------------------------------------------------------------

OLD_WORKFLOW_BLOCK = '''    // ----- 9. REPORT_BUNDLE: zip per-sample shareable bundles ---------
    REPORT_BUNDLE(
        ch_dashboard_in.sample_ids,
        DASHBOARD.out.clinical_dirs,
        DASHBOARD.out.assets,
    )
'''

NEW_WORKFLOW_BLOCK = '''    // ----- 9. REPORT_BUNDLE: zip per-sample shareable bundles ---------
    // sample_ids inferred inside the module from clinical/ contents,
    // avoiding misalignment with DASHBOARD's glob-ordered output.
    REPORT_BUNDLE(
        DASHBOARD.out.clinical_dirs,
        DASHBOARD.out.assets,
    )
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


def backup_file(target: Path, label: str) -> Path:
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = target.with_suffix(target.suffix + f".bak_apply_{label}_{ts}")
    shutil.copy2(target, backup)
    return backup


# --------------------------------------------------------------------
# Main
# --------------------------------------------------------------------

def main() -> int:
    for p in (MODULE_FILE, WORKFLOW_FILE):
        if not p.is_file():
            fail(f"required file not found: {p}")

    module_text   = MODULE_FILE.read_text()
    workflow_text = WORKFLOW_FILE.read_text()

    # Refuse to run if the v1 broken content is still on disk.
    if V1_BROKEN_PATTERN in module_text:
        fail(
            "Detected v1 broken content in report_bundle.nf "
            f"(found pattern {V1_BROKEN_PATTERN!r}). Roll back v1 first:\n"
            "  cp modules/local/report_bundle.nf.bak_apply_report_bundle_pairing_fix_* "
            "     modules/local/report_bundle.nf\n"
            "  cp workflows/tspipe.nf.bak_apply_report_bundle_pairing_fix_* "
            "     workflows/tspipe.nf\n"
            "Then re-run this script."
        )

    # Idempotency: both markers already present?
    module_done   = MODULE_MARKER in module_text
    workflow_done = WORKFLOW_MARKER in workflow_text

    if module_done and workflow_done:
        ok("Both v2 markers already present; nothing to do.")
        return 0

    # Sanity: starting from pre-patch state? (only required if module not done)
    if not module_done and PRE_PATCH_MARKER not in module_text:
        fail(
            f"Expected pre-patch marker {PRE_PATCH_MARKER!r} in "
            f"{MODULE_FILE.name}. File looks unfamiliar; aborting. "
            "Roll back to the pre-patch state before re-running."
        )

    backups = []

    # 1. Module: whole-file rewrite
    if module_done:
        ok(f"{MODULE_FILE.name}: marker already present, skipping rewrite")
    else:
        backup = backup_file(MODULE_FILE, "report_bundle_pairing_fix_v2")
        backups.append((MODULE_FILE, backup))
        info(f"{MODULE_FILE.name}: backup -> {backup.name}")
        MODULE_FILE.write_text(NEW_MODULE_CONTENT)
        info(f"{MODULE_FILE.name}: rewritten")

    # 2. Workflow: targeted string replacement
    if workflow_done:
        ok(f"{WORKFLOW_FILE.name}: marker already present, skipping edit")
    else:
        if OLD_WORKFLOW_BLOCK not in workflow_text:
            for target, backup in reversed(backups):
                shutil.copy2(backup, target)
                info(f"rolled back {target.name}")
            fail(
                f"{WORKFLOW_FILE.name}: expected REPORT_BUNDLE block not "
                "found verbatim."
            )
        if workflow_text.count(OLD_WORKFLOW_BLOCK) != 1:
            for target, backup in reversed(backups):
                shutil.copy2(backup, target)
                info(f"rolled back {target.name}")
            fail(
                f"{WORKFLOW_FILE.name}: expected exactly 1 occurrence "
                f"of REPORT_BUNDLE block, found "
                f"{workflow_text.count(OLD_WORKFLOW_BLOCK)}."
            )
        backup = backup_file(WORKFLOW_FILE, "report_bundle_pairing_fix_v2")
        backups.append((WORKFLOW_FILE, backup))
        info(f"{WORKFLOW_FILE.name}: backup -> {backup.name}")
        new_workflow_text = workflow_text.replace(
            OLD_WORKFLOW_BLOCK, NEW_WORKFLOW_BLOCK, 1,
        )
        WORKFLOW_FILE.write_text(new_workflow_text)
        info(f"{WORKFLOW_FILE.name}: edited")

    # 3. Post-edit verification
    module_text   = MODULE_FILE.read_text()
    workflow_text = WORKFLOW_FILE.read_text()

    issues = []
    if MODULE_MARKER not in module_text:
        issues.append(f"{MODULE_FILE.name}: marker missing after edit")
    if WORKFLOW_MARKER not in workflow_text:
        issues.append(f"{WORKFLOW_FILE.name}: marker missing after edit")
    if V1_BROKEN_PATTERN in module_text:
        issues.append(
            f"{MODULE_FILE.name}: v1 broken regex still present"
        )
    # Verify no \. inside any double-quoted region of the module
    # (sanity check against re-introducing the same bug shape).
    if "\\." in module_text:
        issues.append(
            f"{MODULE_FILE.name}: contains literal '\\.' which may "
            "break Groovy GString parsing"
        )

    if issues:
        for target, backup in reversed(backups):
            shutil.copy2(backup, target)
            info(f"rolled back {target.name}")
        for issue in issues:
            print(f"  - {issue}", file=sys.stderr)
        fail("verification failed; both files rolled back")

    ok("verification passed")
    ok("done")
    info("")
    info("Next steps:")
    info("  cd /goast/hemat_data/nf-core-tspipe")
    info("  nextflow run . \\")
    info("      --input samplesheet.csv \\")
    info("      --panel myeloid_cnv \\")
    info("      --bed /goast/hemat_data/targeted-seq-pipeline/bedfiles/myeloid_CNVbackbone_HG38_nf-core-tspipe.bed \\")
    info("      --outdir test_run/20260525_123204 \\")
    info("      -profile gandalf,singularity -resume")
    return 0


if __name__ == "__main__":
    sys.exit(main())
