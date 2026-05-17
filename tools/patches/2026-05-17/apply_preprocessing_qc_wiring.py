#!/usr/bin/env python3
"""
apply_preprocessing_qc_wiring.py - 2026-05-17 morning

Wire HSMETRICS and EXON_COVERAGE into the PREPROCESSING subworkflow.
Both consume ABRA2.out.bam (which already emits the bam+bai tuple).
HSMETRICS additionally needs reference_ch for the fasta + dict;
EXON_COVERAGE just needs bed_ch.

Three changes in subworkflows/local/preprocessing.nf:

  1. Two new include statements after the existing ABRA2 include.
  2. Two new process calls inside main: after the ABRA2 call.
  3. Two new emit handles after final_bam.

The patch is atomic: it verifies all three OLD anchors exist in the
file before making any modifications. If any anchor is missing the
patch exits without writing.

Idempotent: refuses to re-apply if any of the NEW patterns are already
present. Writes a timestamped backup before modifying.
"""

import datetime
import pathlib
import sys

TARGET = pathlib.Path(
    "/goast/hemat_data/nf-core-tspipe/subworkflows/local/preprocessing.nf"
)

# Change 1: extend the include list.
OLD_INCLUDES = (
    "include { ABRA2                  } from '../../modules/local/abra2'"
)
NEW_INCLUDES = (
    "include { ABRA2                  } from '../../modules/local/abra2'\n"
    "include { HSMETRICS              } from '../../modules/local/hsmetrics'\n"
    "include { EXON_COVERAGE          } from '../../modules/local/exon_coverage'"
)

# Change 2: extend the main: block with HSMETRICS and EXON_COVERAGE
# calls after ABRA2.
OLD_MAIN = (
    "        ABRA2(GATK4_BQSR.out.bam, reference_ch, bed_ch)"
)
NEW_MAIN = (
    "        ABRA2(GATK4_BQSR.out.bam, reference_ch, bed_ch)\n"
    "\n"
    "        // QC: per-target capture metrics + per-exon coverage. Both\n"
    "        // consume the post-ABRA2 BAM in parallel.\n"
    "        HSMETRICS(ABRA2.out.bam, reference_ch, bed_ch)\n"
    "        EXON_COVERAGE(ABRA2.out.bam, bed_ch)"
)

# Change 3: extend the emit block with the two QC channels.
OLD_EMIT = (
    "        final_bam = ABRA2.out.bam"
)
NEW_EMIT = (
    "        final_bam     = ABRA2.out.bam\n"
    "        hsmetrics     = HSMETRICS.out.metrics\n"
    "        exon_coverage = EXON_COVERAGE.out.tsv"
)


def main() -> int:
    if not TARGET.is_file():
        print(f"ERROR: target file not found: {TARGET}", file=sys.stderr)
        return 1

    text = TARGET.read_text()

    # Idempotency: any of the new content already present means
    # patch already (at least partially) applied.
    if "HSMETRICS              }" in text or "HSMETRICS(ABRA2.out.bam" in text \
            or "hsmetrics     = HSMETRICS.out.metrics" in text:
        print("ERROR: patch appears to be already applied. Refusing to re-apply.",
              file=sys.stderr)
        return 1

    # Verify all three anchors before any modification.
    for label, anchor in [
        ("include", OLD_INCLUDES),
        ("main",    OLD_MAIN),
        ("emit",    OLD_EMIT),
    ]:
        n = text.count(anchor)
        if n != 1:
            print(f"ERROR: anchor '{label}' appears {n} times "
                  "(expected exactly 1). Aborting without modification.",
                  file=sys.stderr)
            return 1

    # All anchors verified. Apply all three substitutions.
    new_text = (text
                .replace(OLD_INCLUDES, NEW_INCLUDES)
                .replace(OLD_MAIN,     NEW_MAIN)
                .replace(OLD_EMIT,     NEW_EMIT))

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.parent / f"{TARGET.name}.bak_qc_wiring_{ts}"
    backup.write_text(text)
    print(f"backup: {backup}")

    TARGET.write_text(new_text)
    print(f"patched: {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
