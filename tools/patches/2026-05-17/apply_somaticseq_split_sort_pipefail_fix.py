#!/usr/bin/env python3
"""
apply_somaticseq_split_sort_pipefail_fix.py - 2026-05-17

Patch modules/local/somaticseq.nf to make the inner split-VCF sort
loop tolerant of header-only inputs.

Bug. After Patch B re-enabled Pindel + DeepSomatic in the arbitrary-
caller loop and inserted the SV pre-filter, the first real-mode run
on 25NGS1307 failed inside SOMATICSEQ_ENSEMBLE. The work dir at
work/17/1e41...329 shows pindel_snvs.vcf and pindel_snvs_sorted.vcf
both at 1267 bytes (a Pindel VCF header block, nothing else) and
no pindel_indels_sorted.vcf at all. The inner sort loop entered the
SNV iteration, created the _sorted file with the header, then died
before reaching the INDEL iteration.

The killer is this pipeline inside the inner loop:

    grep -v '^#' "$VCF" | sort -k1,1V -k2,2g >> "$OUT"

When $VCF is header-only, grep -v finds no matches and exits 1.
Under `set -eo pipefail`, that's a pipeline failure, and `set -e`
kills the task. FreeBayes and Platypus did not trigger this because
both produce SNVs and INDELs in normal runs; their split files
always have non-header content. Pindel in this pipeline's FLT3+UBTF
scope is almost entirely INDELs and SVs; after the SV pre-filter
strips the SVs, the SNV split file is empty (header-only) and the
pipefail trap fires.

The SOMATICSEQ_POSTPROCESS module uses the same grep | sort pattern
and already has `|| true` appended to its lines for exactly this
reason. The ensemble module's inner loop is missing that defense.

Fix. Append `|| true` to the one offending pipeline, mirroring the
existing convention in somaticseq_postprocess.nf and matching the
effective behavior of production's 07_somaticseq.py (which calls
sort_vcf in a wrapper that logs sort failures but does not propagate
them). A real sort failure (memory, segfault) would be masked at
this single line; downstream consumers (splitVcf for the outer loop,
SomaticSeq itself for the arbitrary-caller passes) would catch a
real failure at the next step. Same trade-off the postprocess module
already accepted.

Implementation note. The offending line lives inside the inner
for-loop body of the script block, which sits at exactly 16 spaces
of indentation. We build OLD_LINE and NEW_LINE from an explicit
INDENT prefix to eliminate any whitespace drift.

Idempotent: refuses to re-apply if NEW_LINE is already present.

Writes a timestamped backup next to the target:
  somaticseq.nf.bak_split_sort_pipefail_<YYYYMMDD_HHMMSS>
"""

import datetime
import pathlib
import sys

TARGET = pathlib.Path(
    "/goast/hemat_data/nf-core-tspipe/modules/local/somaticseq.nf"
)

# Inner-loop body indentation: 8 (script block) + 8 (two nested for
# loops) = 16 spaces. Empirically verified against the live file.
INDENT = " " * 16

# The single offending line, exactly as it appears in the module.
# `\$` represents the literal two-character sequence on disk that
# Nextflow's Groovy renderer turns into `$` at task runtime.
OLD_LINE = (
    INDENT + "grep -v '^#' \"\\$VCF\" | sort -k1,1V -k2,2g >> \"\\$OUT\"\n"
)

# The replacement: a rationale comment block plus the same line with
# ` || true` appended. Every line gets the same 16-space INDENT.
NEW_LINE = (
    INDENT + "# `|| true` tolerates header-only split VCFs. Pindel\n"
    + INDENT + "# after the SV pre-filter often has zero plain SNVs\n"
    + INDENT + "# in its FLT3+UBTF scope, so $VCF here can be\n"
    + INDENT + "# header-only. Under `set -eo pipefail`, grep -v's\n"
    + INDENT + "# no-match exit code 1 would otherwise kill the task.\n"
    + INDENT + "# Same convention as the sort step in\n"
    + INDENT + "# modules/local/somaticseq_postprocess.nf.\n"
    + INDENT + "grep -v '^#' \"\\$VCF\" | sort -k1,1V -k2,2g >> \"\\$OUT\" || true\n"
)


def main() -> int:
    if not TARGET.is_file():
        print(f"ERROR: target file not found: {TARGET}", file=sys.stderr)
        return 1

    text = TARGET.read_text()

    if NEW_LINE in text:
        print("ERROR: patch already applied (NEW_LINE present). Refusing "
              "to double-apply.", file=sys.stderr)
        return 1

    n_old = text.count(OLD_LINE)
    if n_old == 0:
        print("ERROR: OLD_LINE not found in target. The file may have "
              "been modified since this patch was written. Inspect "
              "manually before retrying.", file=sys.stderr)
        return 1
    if n_old > 1:
        print(f"ERROR: OLD_LINE appears {n_old} times in target "
              "(expected exactly 1). Refusing to apply an ambiguous "
              "patch.", file=sys.stderr)
        return 1

    new_text = text.replace(OLD_LINE, NEW_LINE)
    if new_text == text:
        print("ERROR: no substitution took effect. Refusing to write.",
              file=sys.stderr)
        return 1

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.parent / f"{TARGET.name}.bak_split_sort_pipefail_{ts}"
    backup.write_text(text)
    print(f"backup: {backup}")

    TARGET.write_text(new_text)
    print(f"patched: {TARGET}")
    print("inspect with:")
    print(f"  diff {backup} {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
