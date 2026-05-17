#!/usr/bin/env python3
"""
apply_hsmetrics_port.py - 2026-05-17 morning

Fill the HSMETRICS stub in modules/local/hsmetrics.nf with the actual
GATK invocation. Direct port of production's scripts/10_hsmetrics.py
with the wrapper's Python summary-logging dropped (the .txt file IS
the output; readers can parse it downstream).

Two GATK commands run in sequence:

  1. gatk BedToIntervalList: converts the panel BED into a Picard
     interval_list, required by CollectHsMetrics.
  2. gatk CollectHsMetrics: computes target capture metrics using the
     interval_list as BOTH bait_intervals AND target_intervals (matches
     production's choice).

Output: ${meta.id}_hsmetrics.txt — Picard's tab-separated metrics file
with a header block, ~30 metric fields including MEAN_TARGET_COVERAGE,
PCT_TARGET_BASES_100X, PCT_SELECTED_BASES (on-target), etc.

The interval_list file is also written but is a reproducible
intermediate; not emitted as a channel output (would just clutter).

Container note. The current stub does not set a container; in this
patch we set the GATK4 broadinstitute image, same as elsewhere in the
pipeline.

Idempotent: refuses to re-apply if the new script body is already in
the file. Writes a timestamped backup next to the target:
  hsmetrics.nf.bak_hsmetrics_port_<YYYYMMDD_HHMMSS>
"""

import datetime
import pathlib
import sys

TARGET = pathlib.Path(
    "/goast/hemat_data/nf-core-tspipe/modules/local/hsmetrics.nf"
)

# Old: stub container declaration block + stub script block.
#
# Note: the current module has no `container` line. We add one in NEW.
# Also note: the current `output:` block is missing the dict/fasta
# requirement we need (CollectHsMetrics needs a reference for some
# metrics). The input signature in the stub already accepts
# `tuple path(fasta), path(fai), path(dict)` so we just use those.

OLD_BODY = r'''process HSMETRICS {
    tag        "${meta.id}"
    label      'process_medium'

    input:
        tuple val(meta), path(bam), path(bai)
        tuple path(fasta), path(fai), path(dict)
        path bed

    output:
        tuple val(meta), path("${meta.id}_hsmetrics.txt"), emit: metrics
    stub:
        // nf-core stub blocks v1 (apply_nfcore_add_stub_blocks)
        """
        touch ${meta.id}_hsmetrics.txt
        """


    script:
        """
        # TODO: replace this stub with the tool invocation from the source script.
        echo "STUB: HSMETRICS for ${meta.id}" >&2
        # Touch output filename(s) so downstream channels don't break during DAG validation:
        touch ${meta.id}_hsmetrics.txt
        """
}'''

NEW_BODY = r'''process HSMETRICS {
    tag        "${meta.id}"
    label      'process_medium'
    container  'docker://broadinstitute/gatk:4.5.0.0'

    input:
        tuple val(meta), path(bam), path(bai)
        tuple path(fasta), path(fai), path(dict)
        path bed

    output:
        tuple val(meta), path("${meta.id}_hsmetrics.txt"), emit: metrics
        path  "versions.yml",                              emit: versions

    stub:
        // nf-core stub blocks v1 (apply_nfcore_add_stub_blocks)
        """
        touch ${meta.id}_hsmetrics.txt versions.yml
        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            stub: true
        END_VERSIONS
        """

    script:
        """
        set -eo pipefail
        SAMPLE=${meta.id}

        # Step 1. Convert panel BED to a Picard interval_list.
        # CollectHsMetrics requires interval_list format (BED is not
        # accepted directly). Sequence dictionary identifies which
        # contigs are valid for the reference build.
        gatk BedToIntervalList \\
            -I ${bed} \\
            -O \${SAMPLE}.interval_list \\
            -SD ${dict}

        # Step 2. Run CollectHsMetrics. The panel BED is used as both
        # bait and target intervals (matches production's choice in
        # scripts/10_hsmetrics.py). VALIDATION_STRINGENCY=LENIENT lets
        # the run continue past minor BAM header quirks that are not
        # informative for capture metrics.
        gatk CollectHsMetrics \\
            -I ${bam} \\
            -O \${SAMPLE}_hsmetrics.txt \\
            -BAIT_INTERVALS \${SAMPLE}.interval_list \\
            -TARGET_INTERVALS \${SAMPLE}.interval_list \\
            -R ${fasta} \\
            --VALIDATION_STRINGENCY LENIENT

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            gatk4: \$(gatk --version 2>&1 | grep -oE '[0-9]+\\.[0-9]+\\.[0-9]+' | head -n1)
        END_VERSIONS
        """
}'''


def main() -> int:
    if not TARGET.is_file():
        print(f"ERROR: target file not found: {TARGET}", file=sys.stderr)
        return 1

    text = TARGET.read_text()

    if NEW_BODY in text:
        print("ERROR: patch already applied. Refusing to double-apply.",
              file=sys.stderr)
        return 1

    n_old = text.count(OLD_BODY)
    if n_old != 1:
        print(f"ERROR: OLD_BODY appears {n_old} times in target "
              "(expected 1).", file=sys.stderr)
        return 1

    new_text = text.replace(OLD_BODY, NEW_BODY)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.parent / f"{TARGET.name}.bak_hsmetrics_port_{ts}"
    backup.write_text(text)
    print(f"backup: {backup}")

    TARGET.write_text(new_text)
    print(f"patched: {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
