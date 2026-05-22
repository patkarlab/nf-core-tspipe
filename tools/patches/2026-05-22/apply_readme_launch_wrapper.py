#!/usr/bin/env python3
"""
apply_readme_launch_wrapper.py

Update the nf-core-tspipe README.md to document the launch_tspipe.sh
preflight wrapper as the recommended pipeline entry point, and add the
VV troubleshooting SOP to the documentation table.

Two edits, both anchor-based and applied transactionally:

  1. Quick start step 6: replace the bare `nextflow run .` invocation
     with the wrapper as the recommended path, add a paragraph
     explaining what the wrapper does, and move the direct-Nextflow
     invocation into a collapsible block for advanced users.

  2. Documentation table: insert a row for
     docs/sops/vv_troubleshooting.md between the usage.md and
     output.md rows.

Usage
-----
Run from the repository root:

    python tools/patches/2026-05-22/apply_readme_launch_wrapper.py

Properties
----------
- Idempotent: refuses to insert if the wrapper invocation is already
  documented.
- Safe: backs up the file to .bak_apply_readme_launch_wrapper_<ts>
  before writing.
- Transactional: verifies both anchors are unique before any write.
- No external dependencies.
"""

import sys
from datetime import datetime
from pathlib import Path


README_PATH = Path("README.md")

# Used for idempotency check. The wrapper script name appearing in
# the README is the simplest reliable indicator that the patch has
# already been applied.
MARKER = "./launch_tspipe.sh"

# ---- Edit 1: Quick start step 6 ----

QS_OLD = """# 6. Run
nextflow run . \\
    --input /tmp/today.csv \\
    --outdir /data/nfcore_runs/$(date +%Y%m%d_%H%M%S) \\
    -profile mysite,singularity \\
    -resume
```

Each sample produces a clinical deliverable tree at
`<outdir>/<sample>/clinical/` containing the final BAM, clinical
variant TSV, FLT3-ITD consensus, CNV plots, IGV pileup HTML, and
per-sample dashboard."""

QS_NEW = """# 6. Run via the launch wrapper (recommended)
SAMPLESHEET=/tmp/today.csv \\
    OUTDIR=/data/nfcore_runs/$(date +%Y%m%d_%H%M%S) \\
    PROFILE=mysite,singularity \\
    ./launch_tspipe.sh
```

The launch wrapper performs a VariantValidator (VV) health preflight
before invoking Nextflow. If VV is unreachable on the initial probe,
the wrapper attempts one cycle of auto-recovery (starts gunicorn
inside the REST container, waits for worker warm-up, re-probes) and
only launches Nextflow once VV returns `HTTP 200`. If preflight
fails, the wrapper exits with code 10 and no Nextflow tasks are
scheduled. See
[`docs/sops/vv_troubleshooting.md`](docs/sops/vv_troubleshooting.md)
for the manual SOP this wrapper automates.

Each sample produces a clinical deliverable tree at
`<outdir>/<sample>/clinical/` containing the final BAM, clinical
variant TSV, FLT3-ITD consensus, CNV plots, IGV pileup HTML, and
per-sample dashboard.

<details>
<summary><strong>Direct Nextflow invocation</strong> (bypasses VV preflight)</summary>

The wrapper is a thin shell around `nextflow run .`. You can invoke
Nextflow directly:

```bash
nextflow run . \\
    --input /tmp/today.csv \\
    --outdir /data/nfcore_runs/$(date +%Y%m%d_%H%M%S) \\
    -profile mysite,singularity \\
    -resume
```

This bypasses the VV preflight check. If VV is unreachable when the
annotation step runs, the pipeline will fail on the first
`VARIANT_VALIDATOR` task. See
[`docs/sops/vv_troubleshooting.md`](docs/sops/vv_troubleshooting.md)
for the recovery procedure.

</details>"""

# ---- Edit 2: Documentation table ----

DOC_OLD = """| [`docs/usage.md`](docs/usage.md) | Parameter reference and day-to-day operation. |
| [`docs/output.md`](docs/output.md) | Output directory layout in detail. |"""

DOC_NEW = """| [`docs/usage.md`](docs/usage.md) | Parameter reference and day-to-day operation. |
| [`docs/sops/vv_troubleshooting.md`](docs/sops/vv_troubleshooting.md) | Troubleshooting the VariantValidator Docker stack when annotation fails. |
| [`docs/output.md`](docs/output.md) | Output directory layout in detail. |"""


def main() -> int:
    if not README_PATH.exists():
        print(f"ERROR: README not found at relative path {README_PATH}", file=sys.stderr)
        print("  Run this script from the repository root.", file=sys.stderr)
        return 1

    content = README_PATH.read_text()

    # Idempotency
    if MARKER in content:
        print(f"Launch wrapper already documented in {README_PATH}.")
        print("Nothing to do.")
        return 0

    # Anchor uniqueness checks (run BEFORE any write so we never produce
    # a half-patched file)
    qs_count = content.count(QS_OLD)
    doc_count = content.count(DOC_OLD)
    if qs_count != 1:
        print(
            f"ERROR: Quick start anchor not found uniquely in {README_PATH} "
            f"(found {qs_count} occurrences; expected exactly 1).",
            file=sys.stderr,
        )
        print(
            "  The README structure may have changed since this patch was written.",
            file=sys.stderr,
        )
        return 2
    if doc_count != 1:
        print(
            f"ERROR: Documentation table anchor not found uniquely in {README_PATH} "
            f"(found {doc_count} occurrences; expected exactly 1).",
            file=sys.stderr,
        )
        return 2

    # Backup
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak_path = README_PATH.with_name(
        README_PATH.name + f".bak_apply_readme_launch_wrapper_{ts}"
    )
    bak_path.write_text(content)
    print(f"Backed up original to {bak_path}")

    # Apply both edits
    new_content = content.replace(QS_OLD, QS_NEW)
    new_content = new_content.replace(DOC_OLD, DOC_NEW)
    README_PATH.write_text(new_content)

    # Report
    added_lines = new_content.count("\n") - content.count("\n")
    print(f"Patched {README_PATH}: +{added_lines} lines.")
    print("  Edit 1: Quick start now recommends launch_tspipe.sh")
    print("  Edit 2: SOP row added to Documentation table")
    print()
    print("Next steps:")
    print(f"  git diff -- {README_PATH}        # review the change")
    print(f"  git add {README_PATH}")
    print('  git commit -m "docs(readme): document launch_tspipe.sh wrapper + VV SOP"')
    print("  git push")
    return 0


if __name__ == "__main__":
    sys.exit(main())
