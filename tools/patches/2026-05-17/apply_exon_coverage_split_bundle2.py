#!/usr/bin/env python3
"""
apply_exon_coverage_split_bundle2.py - 2026-05-17 morning

Bundle 2 of the EXON_COVERAGE container-fix refactor (Bundle 1 staged
the new modules + parser script; this bundle rewires the workflow to
use them).

Two files modified:

  subworkflows/local/preprocessing.nf
    - Replace `include { EXON_COVERAGE } from ...` with `include
      { MOSDEPTH }` and `include { PARSE_EXON_COVERAGE }` lines.
    - Replace the single EXON_COVERAGE(...) call inside main: with
      MOSDEPTH(...) followed by PARSE_EXON_COVERAGE(...) that
      consumes MOSDEPTH.out.regions_thresholds + bed_ch.
    - Update the emit: alias so `exon_coverage` now points at
      PARSE_EXON_COVERAGE.out.tsv (workflow-level callers don't
      need to know the wiring changed).

  conf/modules.config
    - Remove the EXON_COVERAGE withName block.
    - Add MOSDEPTH withName block (publishes mosdepth intermediates
      to ${outdir}/${sample}/mosdepth/).
    - Add PARSE_EXON_COVERAGE withName block (publishes the TSV to
      ${outdir}/${sample}/exon_coverage/).

After this bundle: `nextflow inspect main.nf` should parse cleanly
and report MOSDEPTH + PARSE_EXON_COVERAGE in the module list.

Atomic: verifies every OLD anchor exists exactly once in its target
file before any modification. If any check fails, exits with no
files modified.
"""

import datetime
import pathlib
import sys

REPO = pathlib.Path("/goast/hemat_data/nf-core-tspipe")
PREPROCESSING = REPO / "subworkflows/local/preprocessing.nf"
MODULES_CONFIG = REPO / "conf/modules.config"


# ---- preprocessing.nf edits (3 anchors) ------------------------------------

# (A) include statement: replace single EXON_COVERAGE include with two
# new includes (MOSDEPTH + PARSE_EXON_COVERAGE).
PP_OLD_INCLUDE = (
    "include { EXON_COVERAGE          } from '../../modules/local/exon_coverage'"
)
PP_NEW_INCLUDE = (
    "include { MOSDEPTH               } from '../../modules/local/mosdepth'\n"
    "include { PARSE_EXON_COVERAGE    } from '../../modules/local/parse_exon_coverage'"
)

# (B) main: block. Replace the EXON_COVERAGE call with MOSDEPTH then
# PARSE_EXON_COVERAGE chained on its output.
PP_OLD_CALL = (
    "        // QC: per-target capture metrics + per-exon coverage. Both\n"
    "        // consume the post-ABRA2 BAM in parallel.\n"
    "        HSMETRICS(ABRA2.out.bam, reference_ch, bed_ch)\n"
    "        EXON_COVERAGE(ABRA2.out.bam, bed_ch)"
)
PP_NEW_CALL = (
    "        // QC: per-target capture metrics + per-exon coverage.\n"
    "        // HSMETRICS runs in the GATK container. Per-exon coverage\n"
    "        // is a two-step pipeline because the mosdepth biocontainer\n"
    "        // has no Python: MOSDEPTH writes regions/thresholds bed.gz,\n"
    "        // then PARSE_EXON_COVERAGE (GATK container, has Python)\n"
    "        // joins them with the panel BED labels into a per-exon TSV.\n"
    "        HSMETRICS(ABRA2.out.bam, reference_ch, bed_ch)\n"
    "        MOSDEPTH(ABRA2.out.bam, bed_ch)\n"
    "        PARSE_EXON_COVERAGE(MOSDEPTH.out.regions_thresholds, bed_ch)"
)

# (C) emit alias: rebind exon_coverage to the new producer. Single
# line replace; preserves the equals-sign alignment.
PP_OLD_EMIT = (
    "        exon_coverage = EXON_COVERAGE.out.tsv"
)
PP_NEW_EMIT = (
    "        exon_coverage = PARSE_EXON_COVERAGE.out.tsv"
)


# ---- conf/modules.config edits (1 anchor, replaces a whole block) ----------

# The EXON_COVERAGE withName block as it currently appears, from the
# patch we applied earlier this morning (apply_qc_publishdir_routing).
MC_OLD_BLOCK = """    withName: 'EXON_COVERAGE' {
        publishDir = [
            path: { "${params.outdir}/${meta.id}/exon_coverage" },
            mode: params.publish_dir_mode,
            pattern: '*.{tsv,bed.gz,bed.gz.csi,summary.txt,dist.txt}'
        ]
    }"""

# Replacement: two blocks. MOSDEPTH publishes intermediates;
# PARSE_EXON_COVERAGE publishes the final TSV.
MC_NEW_BLOCK = """    withName: 'MOSDEPTH' {
        publishDir = [
            path: { "${params.outdir}/${meta.id}/mosdepth" },
            mode: params.publish_dir_mode,
            pattern: '*.{bed.gz,bed.gz.csi,summary.txt,dist.txt}'
        ]
    }

    withName: 'PARSE_EXON_COVERAGE' {
        publishDir = [
            path: { "${params.outdir}/${meta.id}/exon_coverage" },
            mode: params.publish_dir_mode,
            pattern: '*.tsv'
        ]
    }"""


def check_anchor(text: str, anchor: str, label: str) -> bool:
    """Return True if anchor appears exactly once; print error and return
    False otherwise."""
    n = text.count(anchor)
    if n != 1:
        print(f"ERROR: anchor '{label}' appears {n} times in target "
              "(expected exactly 1). Aborting without modification.",
              file=sys.stderr)
        return False
    return True


def main() -> int:
    if not PREPROCESSING.is_file():
        print(f"ERROR: target not found: {PREPROCESSING}", file=sys.stderr)
        return 1
    if not MODULES_CONFIG.is_file():
        print(f"ERROR: target not found: {MODULES_CONFIG}", file=sys.stderr)
        return 1

    pp_text = PREPROCESSING.read_text()
    mc_text = MODULES_CONFIG.read_text()

    # Idempotency: if any of the new content is already present, refuse.
    if "MOSDEPTH(ABRA2.out.bam" in pp_text \
            or "PARSE_EXON_COVERAGE(MOSDEPTH.out" in pp_text \
            or "withName: 'MOSDEPTH'" in mc_text \
            or "withName: 'PARSE_EXON_COVERAGE'" in mc_text:
        print("ERROR: patch appears to be already applied. Refusing to re-apply.",
              file=sys.stderr)
        return 1

    # Verify all four anchors exist before modifying anything.
    ok = True
    ok &= check_anchor(pp_text, PP_OLD_INCLUDE, "preprocessing include")
    ok &= check_anchor(pp_text, PP_OLD_CALL,    "preprocessing main: call")
    ok &= check_anchor(pp_text, PP_OLD_EMIT,    "preprocessing emit alias")
    ok &= check_anchor(mc_text, MC_OLD_BLOCK,   "modules.config EXON_COVERAGE block")
    if not ok:
        return 1

    # All anchors verified. Apply substitutions.
    new_pp = (pp_text
              .replace(PP_OLD_INCLUDE, PP_NEW_INCLUDE)
              .replace(PP_OLD_CALL,    PP_NEW_CALL)
              .replace(PP_OLD_EMIT,    PP_NEW_EMIT))
    new_mc = mc_text.replace(MC_OLD_BLOCK, MC_NEW_BLOCK)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    pp_backup = PREPROCESSING.parent / f"{PREPROCESSING.name}.bak_split_wiring_{ts}"
    pp_backup.write_text(pp_text)
    print(f"backup: {pp_backup}")
    PREPROCESSING.write_text(new_pp)
    print(f"patched: {PREPROCESSING}")

    mc_backup = MODULES_CONFIG.parent / f"{MODULES_CONFIG.name}.bak_split_wiring_{ts}"
    mc_backup.write_text(mc_text)
    print(f"backup: {mc_backup}")
    MODULES_CONFIG.write_text(new_mc)
    print(f"patched: {MODULES_CONFIG}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
