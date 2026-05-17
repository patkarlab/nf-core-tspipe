#!/usr/bin/env python3
"""
apply_exon_coverage_port.py - 2026-05-17 morning

Fill the EXON_COVERAGE stub in modules/local/exon_coverage.nf by calling
bin/exon_coverage.py. The bin script is already a verbatim port of
production's scripts/10b_exon_coverage.py and handles mosdepth
invocation + per-exon parsing + TSV emission internally. Nextflow
auto-adds bin/ to PATH inside processes, so the module just calls
exon_coverage.py with the right flags.

Script CLI (from bin/exon_coverage.py):
    exon_coverage.py
        --sample SAMPLE
        --bam BAM
        --bed BED
        --output-dir DIR
        [--threads N]

Output: ${output-dir}/${sample}_exon_coverage.tsv

In the Nextflow context we set --output-dir to the current task work
dir (.) so the file lands where Nextflow expects to publish from.

Container: quay.io/biocontainers/mosdepth:0.3.10--h4e814b3_1 -- this
specific tag is on bioconda and matches the gandalf conda env version.
The script is bundled into the work dir by Nextflow's bin/ mechanism;
it runs under the mosdepth container's Python interpreter (python3 is
present in the biocontainers base).

Idempotent: refuses to re-apply if the new body is already in the
file. Writes a timestamped backup next to the target.
"""

import datetime
import pathlib
import sys

TARGET = pathlib.Path(
    "/goast/hemat_data/nf-core-tspipe/modules/local/exon_coverage.nf"
)

OLD_BODY = r'''process EXON_COVERAGE {
    tag        "${meta.id}"
    label      'process_medium'

    input:
        tuple val(meta), path(bam), path(bai)
        path bed

    output:
        tuple val(meta), path("${meta.id}_exon_coverage.tsv"), emit: tsv
    stub:
        // nf-core stub blocks v1 (apply_nfcore_add_stub_blocks)
        """
        touch ${meta.id}_exon_coverage.tsv
        """


    script:
        """
        # TODO: replace this stub with the tool invocation from the source script.
        echo "STUB: EXON_COVERAGE for ${meta.id}" >&2
        # Touch output filename(s) so downstream channels don't break during DAG validation:
        touch ${meta.id}_exon_coverage.tsv
        """
}'''

NEW_BODY = r'''process EXON_COVERAGE {
    tag        "${meta.id}"
    label      'process_medium'
    container  'quay.io/biocontainers/mosdepth:0.3.10--h4e814b3_1'

    input:
        tuple val(meta), path(bam), path(bai)
        path bed

    output:
        tuple val(meta), path("${meta.id}_exon_coverage.tsv"), emit: tsv
        path  "versions.yml",                                  emit: versions

    stub:
        // nf-core stub blocks v1 (apply_nfcore_add_stub_blocks)
        """
        touch ${meta.id}_exon_coverage.tsv versions.yml
        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            stub: true
        END_VERSIONS
        """

    script:
        """
        set -eo pipefail

        # bin/exon_coverage.py is auto-staged onto PATH by Nextflow.
        # It runs mosdepth (--by panel BED, no per-base output,
        # thresholds 100,250,500), then parses regions.bed.gz and
        # thresholds.bed.gz into a per-exon TSV. Output filename is
        # \${SAMPLE}_exon_coverage.tsv inside --output-dir.
        exon_coverage.py \\
            --sample ${meta.id} \\
            --bam ${bam} \\
            --bed ${bed} \\
            --output-dir . \\
            --threads ${task.cpus}

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            mosdepth: \$(mosdepth --version 2>&1 | awk '{print \$2}')
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
    backup = TARGET.parent / f"{TARGET.name}.bak_exon_coverage_port_{ts}"
    backup.write_text(text)
    print(f"backup: {backup}")

    TARGET.write_text(new_text)
    print(f"patched: {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
