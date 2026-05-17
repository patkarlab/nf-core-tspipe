#!/usr/bin/env python3
"""
apply_qc_publishdir_routing.py - 2026-05-17 morning

Add publishDir routing for HSMETRICS and EXON_COVERAGE in
conf/modules.config. Without these blocks, the modules run and their
outputs land in the work dir, but Nextflow never copies them into
${outdir}/${sample}/.

Two new withName: blocks inserted immediately after the ABRA2 block.
This places them logically inside the "preprocessing" section, before
the variant-calling section header at line 53.

Output destinations:
  HSMETRICS      ->  ${outdir}/${sample}/hsmetrics/
  EXON_COVERAGE  ->  ${outdir}/${sample}/exon_coverage/

EXON_COVERAGE's pattern is permissive: mosdepth emits multiple
files (.regions.bed.gz, .thresholds.bed.gz, .mosdepth.summary.txt,
.mosdepth.global.dist.txt) in addition to the final
_exon_coverage.tsv that the bin script writes. Keeping the
intermediates is useful for audit (regenerating the TSV without
re-running mosdepth) and costs almost no disk -- each file is small.

Idempotent: refuses to re-apply if either new withName: block is
already present.
"""

import datetime
import pathlib
import sys

TARGET = pathlib.Path(
    "/goast/hemat_data/nf-core-tspipe/conf/modules.config"
)

# The ABRA2 block as it appears in lines 45-52. This is the OLD
# anchor; the patch inserts the two new blocks immediately after it.
OLD_BLOCK = """    withName: 'ABRA2' {
        publishDir = [
            path: { "${params.outdir}/${meta.id}/abra2" },
            mode: params.publish_dir_mode,
            pattern: '*.{bam,bai}'
        ]
        ext.args = '--mer 0.025 --mad 5000'
    }"""

# Same block + two new withName: blocks below it. Style matches the
# surrounding file: 4-space indent for `withName`, 8-space indent
# for `publishDir` body, single blank line separator between blocks.
NEW_BLOCK = """    withName: 'ABRA2' {
        publishDir = [
            path: { "${params.outdir}/${meta.id}/abra2" },
            mode: params.publish_dir_mode,
            pattern: '*.{bam,bai}'
        ]
        ext.args = '--mer 0.025 --mad 5000'
    }

    withName: 'HSMETRICS' {
        publishDir = [
            path: { "${params.outdir}/${meta.id}/hsmetrics" },
            mode: params.publish_dir_mode,
            pattern: '*.{txt,interval_list}'
        ]
    }

    withName: 'EXON_COVERAGE' {
        publishDir = [
            path: { "${params.outdir}/${meta.id}/exon_coverage" },
            mode: params.publish_dir_mode,
            pattern: '*.{tsv,bed.gz,bed.gz.csi,summary.txt,dist.txt}'
        ]
    }"""


def main() -> int:
    if not TARGET.is_file():
        print(f"ERROR: target file not found: {TARGET}", file=sys.stderr)
        return 1

    text = TARGET.read_text()

    if "withName: 'HSMETRICS'" in text or "withName: 'EXON_COVERAGE'" in text:
        print("ERROR: patch already applied (HSMETRICS or EXON_COVERAGE "
              "withName: block already present). Refusing to re-apply.",
              file=sys.stderr)
        return 1

    n = text.count(OLD_BLOCK)
    if n != 1:
        print(f"ERROR: OLD anchor (ABRA2 block) appears {n} times "
              "(expected 1). Aborting without modification.",
              file=sys.stderr)
        return 1

    new_text = text.replace(OLD_BLOCK, NEW_BLOCK)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.parent / f"{TARGET.name}.bak_qc_publishdir_{ts}"
    backup.write_text(text)
    print(f"backup: {backup}")

    TARGET.write_text(new_text)
    print(f"patched: {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
