#!/usr/bin/env python3
"""
apply_dashboard_primary_genome_scatter.py

Surface the clean genome-wide CNV scatter (introduced 2026-05-24) in the
per-sample HTML dashboard's CNV tab.

What it does
------------
Two-file patch:

  1. bin/dashboard_builder/parsers/cnv.py
       - Detects <sample>_genome_scatter_clean.png in plots/overview/.
       - Exposes it as ctx.cnv.primary_genome_scatter (single string path,
         not a list) for direct template use.
       - Removes it from the generic ctx.cnv.overview list so it doesn't
         render twice.

  2. bin/dashboard_builder/templates/sample_report.html.j2
       - Adds a new "Genome-wide CNV (target + backbone)" section above
         the existing "Genome-wide overview" block.
       - Renders ctx.cnv.primary_genome_scatter at full width
         (col-12) so the chromosome-arm context is the first thing the
         fellow sees in the CNV tab.
       - Plot is includable in the Reporting tab via the standard
         "Include in report" checkbox on the card (card ID:
         primary_scatter::clean).

Why a dedicated slot vs leaving it in the generic overview list
---------------------------------------------------------------
The clean genome scatter is the PRIMARY view for arm-level events (-7,
-5q, +8 etc.) that the backbone PoN was built to detect. Leaving it
mixed in with the heatmap and (broken) CNVkit-native scatter at
half-width does not communicate its clinical role. A dedicated, full-
width slot at the top of the CNV tab gives it the visibility it needs.

The existing scatter_png (CNVkit native .final-scatter.png) stays in
place below as a reference view. It will continue to show with the
known alt-contig / chrM x-axis pollution issues until either the BED is
re-built end-to-end without those contigs, or we switch the template
to suppress it entirely. For now, keeping both is the conservative
choice -- fellows can see the canonical CNVkit output alongside the
clinical-grade clean version.

Safety
------
- Backs up both files with timestamps before any write.
- Idempotent (sentinel: "primary_genome_scatter" appears in parser).
- Atomic-ish: validates all anchors in both files BEFORE writing
  anything. If any anchor is missing, exits with an error and writes
  nothing.
- Dry-run via --dry-run.

Usage
-----
    python3 tools/patches/2026-05-24/apply_dashboard_primary_genome_scatter.py --dry-run
    python3 tools/patches/2026-05-24/apply_dashboard_primary_genome_scatter.py
"""

import argparse
import shutil
import sys
import time
from pathlib import Path


DASHBOARD_BUILDER = Path("/goast/hemat_data/nf-core-tspipe/bin/dashboard_builder")
PARSER_PY = DASHBOARD_BUILDER / "parsers" / "cnv.py"
TEMPLATE_J2 = DASHBOARD_BUILDER / "templates" / "sample_report.html.j2"

PARSER_SENTINEL = "primary_genome_scatter"
TEMPLATE_SENTINEL = "primary_genome_scatter"  # same string works for both


# -------- Parser anchors --------

# We need to insert logic BEFORE `return {` and add a key to the return dict.
# The logic block (computes primary_genome_scatter, removes from overview).
PARSER_LOGIC_ANCHOR = "    return {\n"

PARSER_LOGIC_BLOCK = '''    # ---- Primary genome-wide scatter (added 2026-05-24) ----
    # The clean genome-wide scatter is the primary view for arm-level
    # CNV events. The parser pulls it out of the generic overview list
    # into its own slot so the template can render it at full width as
    # the first thing in the CNV tab.
    primary_genome_scatter = None
    clean_scatter_path = plots_dir / "overview" / f"{sample}_genome_scatter_clean.png"
    if clean_scatter_path.exists():
        primary_genome_scatter = _rel(clean_scatter_path, sample_dir)
        # Remove from the generic overview list to avoid duplicate rendering
        overview = [item for item in overview
                    if item.get("path") != primary_genome_scatter]

'''

# Add a key to the return dict. Insert right after "scatter_png": line.
PARSER_RETURN_ANCHOR = '        "scatter_png":        scatter_png,\n'
PARSER_RETURN_INSERT = '        "primary_genome_scatter": primary_genome_scatter,\n'


# -------- Template anchor --------
# Insert a new section right before the existing "Genome-wide overview"
# comment block in the CNV tab.

TEMPLATE_ANCHOR = "        {# ---- Genome-wide overview ---- #}\n"

TEMPLATE_INSERT = '''        {# ---- Primary genome-wide CNV scatter (target + backbone) (added 2026-05-24) ---- #}
        {% if ctx.cnv.primary_genome_scatter %}
          <h5 class="mt-4">Genome-wide CNV (target + backbone)</h5>
          <p class="text-muted small mb-2">
            Bin-level genome-wide copy number from the backbone PoN.
            Target bins (gene-resolution) and backbone bins are both shown.
            Y-axis is clipped to a clinical range so chromosome-arm events
            (e.g.&nbsp;-7, -5q, +8) are immediately visible. Segment lines
            from the .call.cns are overlaid in colour.
          </p>
          <div class="row g-3 mb-4">
            {{ macros.render_cnv_plot_card(
                 'primary_scatter::clean',
                 'Genome-wide CNV (target + backbone)',
                 ctx.cnv.primary_genome_scatter,
                 'col-12') }}
          </div>
        {% endif %}

'''


def backup(path: Path, ts: str) -> Path:
    bak = path.with_name(
        path.name + f".bak_apply_dashboard_primary_scatter_{ts}"
    )
    shutil.copy2(path, bak)
    return bak


def main():
    ap = argparse.ArgumentParser(
        description="Wire genome_scatter_clean.png into the per-sample dashboard.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--dry-run", action="store_true",
                    help="Print what would change without writing.")
    args = ap.parse_args()

    # ---- Pre-flight: both files must exist ----
    for p in (PARSER_PY, TEMPLATE_J2):
        if not p.is_file():
            sys.exit(f"ERROR: not found: {p}")

    parser_text = PARSER_PY.read_text()
    template_text = TEMPLATE_J2.read_text()

    # ---- Idempotency check ----
    parser_applied = PARSER_SENTINEL in parser_text
    template_applied = TEMPLATE_SENTINEL in template_text
    if parser_applied and template_applied:
        print("Patch already applied to both files. Nothing to do.")
        return 0
    if parser_applied or template_applied:
        # Partial state: one was patched, the other wasn't. Refuse to
        # double-patch the partial one; tell the user what's going on.
        print("WARN: patch is in a partial state:")
        print(f"  parsers/cnv.py:           {'PATCHED' if parser_applied else 'unpatched'}")
        print(f"  sample_report.html.j2:    {'PATCHED' if template_applied else 'unpatched'}")
        print("Re-running will only apply the missing side.")

    # ---- Anchor validation (do everything that could fail BEFORE writing) ----
    errors = []

    if not parser_applied:
        if PARSER_LOGIC_ANCHOR not in parser_text:
            errors.append(
                f"parsers/cnv.py: could not find anchor '{PARSER_LOGIC_ANCHOR.strip()}' "
                "(expected '    return {' at module level inside parse())"
            )
        if PARSER_RETURN_ANCHOR not in parser_text:
            errors.append(
                "parsers/cnv.py: could not find anchor for return-dict insertion "
                "(expected line: '        \"scatter_png\":        scatter_png,')"
            )

    if not template_applied:
        if TEMPLATE_ANCHOR not in template_text:
            errors.append(
                "sample_report.html.j2: could not find anchor '"
                + TEMPLATE_ANCHOR.strip() + "'"
            )

    if errors:
        print("ERROR(S): not writing.")
        for e in errors:
            print(f"  - {e}")
        return 1

    # ---- Compute new contents ----
    new_parser_text = parser_text
    if not parser_applied:
        # Insert logic block before `return {`
        new_parser_text = new_parser_text.replace(
            PARSER_LOGIC_ANCHOR,
            PARSER_LOGIC_BLOCK + PARSER_LOGIC_ANCHOR,
        )
        # Insert new key into return dict (after scatter_png line)
        new_parser_text = new_parser_text.replace(
            PARSER_RETURN_ANCHOR,
            PARSER_RETURN_ANCHOR + PARSER_RETURN_INSERT,
        )

    new_template_text = template_text
    if not template_applied:
        new_template_text = new_template_text.replace(
            TEMPLATE_ANCHOR,
            TEMPLATE_INSERT + TEMPLATE_ANCHOR,
        )

    # ---- Sanity: sentinel must be present in both after substitution ----
    if PARSER_SENTINEL not in new_parser_text:
        sys.exit("ERROR: parser sentinel missing after substitution; aborting.")
    if TEMPLATE_SENTINEL not in new_template_text:
        sys.exit("ERROR: template sentinel missing after substitution; aborting.")

    # ---- Report sizes ----
    print(f"parsers/cnv.py:")
    print(f"  before: {len(parser_text):>7} bytes")
    print(f"  after:  {len(new_parser_text):>7} bytes "
          f"(+{len(new_parser_text) - len(parser_text)})")
    print(f"sample_report.html.j2:")
    print(f"  before: {len(template_text):>7} bytes")
    print(f"  after:  {len(new_template_text):>7} bytes "
          f"(+{len(new_template_text) - len(template_text)})")

    if args.dry_run:
        print("\nDRY-RUN: nothing written.")
        return 0

    # ---- Backup + write ----
    ts = time.strftime("%Y%m%d_%H%M%S")
    parser_bak = backup(PARSER_PY, ts) if not parser_applied else None
    template_bak = backup(TEMPLATE_J2, ts) if not template_applied else None

    if not parser_applied:
        PARSER_PY.write_text(new_parser_text)
    if not template_applied:
        TEMPLATE_J2.write_text(new_template_text)

    print()
    if parser_bak:
        print(f"Backup: {parser_bak}")
        print(f"Wrote:  {PARSER_PY}")
    if template_bak:
        print(f"Backup: {template_bak}")
        print(f"Wrote:  {TEMPLATE_J2}")
    print()
    print("Next steps:")
    print("  - For the existing run, regenerate the dashboard:")
    print("      cd /goast/hemat_data/nf-core-tspipe")
    print("      RUN_DIR=$(ls -dt /goast/hemat_data/nfcore_runs/tspipe_clinical_myeloid_cnv_*"
          " | grep -v _stub | head -1)")
    print("      # Re-running TSPIPE with -resume re-invokes DASHBOARD (since")
    print("      # the parser and template have changed).")
    print("      # Or: re-run just the dashboard manually if you have a helper.")
    print()
    print("  - For future runs: just run; the dashboard picks up the new slot.")
    print()
    print("  - To produce a sharable standalone HTML after the rebuild:")
    print("      python3 tools/make_standalone_report.py --outdir \"$RUN_DIR\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
