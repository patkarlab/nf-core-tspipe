#!/usr/bin/env python3
"""
apply_tspipe_qc_channels.py - 2026-05-17 morning

Surface PREPROCESSING's new QC outputs as named channel handles in
the top-level workflow. This is a tiny patch — it just gives the new
channels named references that downstream modules (SAMPLE_DASHBOARD,
ORGANIZE_OUTPUT) can use later.

Functionally a no-op on its own: HSMETRICS and EXON_COVERAGE already
run as part of PREPROCESSING. This just makes their outputs
addressable in tspipe.nf the same way ch_final_bam is.

One change: extend the existing
    ch_final_bam = PREPROCESSING.out.final_bam   // [meta, bam, bai]
line with two new handles.

Idempotent: refuses to re-apply if NEW pattern already exists.
"""

import datetime
import pathlib
import sys

TARGET = pathlib.Path(
    "/goast/hemat_data/nf-core-tspipe/workflows/tspipe.nf"
)

OLD_HANDLES = (
    "    ch_final_bam = PREPROCESSING.out.final_bam   // [meta, bam, bai]"
)
NEW_HANDLES = (
    "    ch_final_bam     = PREPROCESSING.out.final_bam      // [meta, bam, bai]\n"
    "    ch_hsmetrics     = PREPROCESSING.out.hsmetrics       // [meta, hs_metrics.txt]\n"
    "    ch_exon_coverage = PREPROCESSING.out.exon_coverage   // [meta, exon_coverage.tsv]"
)


def main() -> int:
    if not TARGET.is_file():
        print(f"ERROR: target file not found: {TARGET}", file=sys.stderr)
        return 1

    text = TARGET.read_text()

    if "ch_hsmetrics" in text or "ch_exon_coverage" in text:
        print("ERROR: patch already applied (ch_hsmetrics or "
              "ch_exon_coverage already present). Refusing to re-apply.",
              file=sys.stderr)
        return 1

    n = text.count(OLD_HANDLES)
    if n != 1:
        print(f"ERROR: OLD anchor appears {n} times (expected 1).",
              file=sys.stderr)
        return 1

    new_text = text.replace(OLD_HANDLES, NEW_HANDLES)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.parent / f"{TARGET.name}.bak_qc_channels_{ts}"
    backup.write_text(text)
    print(f"backup: {backup}")

    TARGET.write_text(new_text)
    print(f"patched: {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
