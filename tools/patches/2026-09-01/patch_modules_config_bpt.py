#!/usr/bin/env python3
"""Insert the BUILD_PON_TWIST config section into conf/modules.config
(marker BPT_MODULES_CONFIG_V1).

The section is inserted immediately BEFORE the existing anchor comment
    // ---- Legacy-tree modules: run on host via production conda env ------
so it lands inside the top-level process { } scope alongside the other
withName blocks.

Contents:
  - Umbrella selector withName 'BPT_.*': conda = params.legacy_python_env,
    container = null. Every BPT_ process therefore runs from the host
    conda env and can never inherit a container directive (2026-08-31
    lesson: modules.config withName selectors override module bodies).
    beforeScript is deliberately NOT set so the global PATH export from
    conf/gandalf.config survives.
  - Per-module publishDir blocks. Stratum-scoped outputs resolve
    ${stratum} from the process 'val stratum' input inside the closures.

Idempotent, anchor-based, dry-run by default. Run from the repo root:
    python tools/patches/2026-09-01/patch_modules_config_bpt.py           # dry-run
    python tools/patches/2026-09-01/patch_modules_config_bpt.py --apply
"""

import argparse
import os
import shutil
import sys
from datetime import datetime

TARGET = "conf/modules.config"
MARKER = "BPT_MODULES_CONFIG_V1"
ANCHOR_STRIPPED = "// ---- Legacy-tree modules: run on host via production conda env ------"

BLOCK = """\
    // =====================================================================
    // BPT_MODULES_CONFIG_V1
    // ---- BUILD_PON_TWIST (BPT_*): conda-only execution -------------------
    //
    // Umbrella: every BPT_ process runs from the host conda env
    // (params.legacy_python_env) and never inherits a container directive.
    // beforeScript intentionally not set here so the site-level PATH
    // export (conf/gandalf.config) is preserved. Per-module blocks below
    // add publishDir only; tool arguments stay in the modules (ext.args
    // hooks available). Design record: docs/audit/2026-09-01/.
    // =====================================================================

    withName: 'BPT_.*' {
        conda     = params.legacy_python_env
        container = null
    }

    withName: 'BPT_CHECK_SAMPLESHEET' {
        publishDir = [
            path: { "${params.outdir}/samplesheet" },
            mode: params.publish_dir_mode
        ]
    }

    withName: 'BPT_CNVKIT_PREP' {
        publishDir = [
            path: { "${params.outdir}/cnvkit/targets" },
            mode: params.publish_dir_mode
        ]
    }

    withName: 'BPT_CNVKIT_COVERAGE' {
        publishDir = [
            path: { "${params.outdir}/cnvkit/coverage" },
            mode: params.publish_dir_mode,
            pattern: '*.cnn'
        ]
    }

    withName: 'BPT_CNVKIT_REFERENCE' {
        publishDir = [
            path: { "${params.outdir}/references/twist_myeloid/${stratum}" },
            mode: params.publish_dir_mode
        ]
    }

    withName: 'BPT_GATK_PREPROCESS_INTERVALS' {
        publishDir = [
            path: { "${params.outdir}/references/twist_myeloid/intervals" },
            mode: params.publish_dir_mode
        ]
    }

    withName: 'BPT_GATK_ANNOTATE_INTERVALS' {
        publishDir = [
            path: { "${params.outdir}/references/twist_myeloid/intervals" },
            mode: params.publish_dir_mode
        ]
    }

    withName: 'BPT_GATK_COLLECT_READ_COUNTS' {
        publishDir = [
            path: { "${params.outdir}/gatk/read_counts" },
            mode: params.publish_dir_mode,
            pattern: '*.hdf5'
        ]
    }

    withName: 'BPT_GATK_CREATE_RC_PON' {
        publishDir = [
            path: { "${params.outdir}/references/twist_myeloid/${stratum}" },
            mode: params.publish_dir_mode
        ]
    }

    withName: 'BPT_GATK_COLLECT_ALLELIC_COUNTS' {
        publishDir = [
            path: { "${params.outdir}/gatk/allelic_counts" },
            mode: params.publish_dir_mode,
            pattern: '*.allelicCounts.tsv'
        ]
    }

    withName: 'BPT_AGGREGATE_BAF' {
        publishDir = [
            path: { "${params.outdir}/references/twist_myeloid/baf" },
            mode: params.publish_dir_mode
        ]
    }

    withName: 'BPT_CNV_LOO_QC' {
        publishDir = [
            [
                path: { "${params.outdir}/references/twist_myeloid/${stratum}" },
                mode: params.publish_dir_mode,
                pattern: 'references/**',
                saveAs: { fn -> fn.tokenize('/')[-1] }
            ],
            [
                path: { "${params.outdir}/qc/loo_${stratum}" },
                mode: params.publish_dir_mode,
                pattern: 'loo_qc/**',
                saveAs: { fn -> fn.startsWith('loo_qc/') ? fn.substring(7) : fn }
            ],
            [
                // noise profile is also reference-grade (TSPIPE consumes it
                // as cnv_noise_profile); co-locate with the stratum PoN so
                // asset seeding is a single directory copy
                path: { "${params.outdir}/references/twist_myeloid/${stratum}" },
                mode: params.publish_dir_mode,
                pattern: 'loo_qc/loo_bin_noise_profile.tsv',
                saveAs: { fn -> fn.tokenize('/')[-1] }
            ]
        ]
    }

    withName: 'BPT_CONFORMITY_SAMPLE' {
        publishDir = [
            path: { "${params.outdir}/qc/conformity/per_sample" },
            mode: params.publish_dir_mode,
            pattern: '*.conformity.tsv'
        ]
    }

    withName: 'BPT_CONFORMITY_REPORT' {
        publishDir = [
            path: { "${params.outdir}/qc/conformity" },
            mode: params.publish_dir_mode
        ]
    }

    withName: 'BPT_TOOL_VERSIONS' {
        publishDir = [
            path: { "${params.outdir}/references/twist_myeloid" },
            mode: params.publish_dir_mode
        ]
    }

"""


def main():
    ap = argparse.ArgumentParser(description="Patch conf/modules.config: BPT section")
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry-run)")
    ap.add_argument("--file", default=TARGET, help="target file (default: conf/modules.config)")
    args = ap.parse_args()

    if not os.path.isfile(args.file):
        print("[error] target not found: {0} (run from the repo root)".format(args.file))
        sys.exit(1)

    with open(args.file) as fh:
        text = fh.read()

    if MARKER in text:
        print("[skip] marker {0} already present in {1}; nothing to do".format(MARKER, args.file))
        return

    if BLOCK.count("{") != BLOCK.count("}"):
        print("[error] internal: insertion block braces unbalanced ({0} open, {1} close)".format(
            BLOCK.count("{"), BLOCK.count("}")))
        sys.exit(1)

    lines = text.splitlines(True)
    hits = [i for i, line in enumerate(lines) if line.strip() == ANCHOR_STRIPPED]
    if len(hits) != 1:
        print("[error] anchor found {0} times (need exactly 1): {1}".format(
            len(hits), ANCHOR_STRIPPED))
        sys.exit(1)
    anchor_idx = hits[0]

    new_lines = lines[:anchor_idx] + [BLOCK] + lines[anchor_idx:]
    new_text = "".join(new_lines)

    block_n = BLOCK.count("\n")
    print("[plan] insert {0} lines before line {1} of {2}:".format(
        block_n, anchor_idx + 1, args.file))
    print("       anchor: {0}".format(lines[anchor_idx].rstrip()))
    print("       block head: {0}".format(BLOCK.splitlines()[1].strip()))
    print("       block selectors: umbrella 'BPT_.*' + 14 publishDir blocks")

    if not args.apply:
        print("[dry-run] no changes written; re-run with --apply")
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = "{0}.bak_bpt_modules_{1}".format(args.file, ts)
    shutil.copy2(args.file, backup)
    print("[backup] {0}".format(backup))

    with open(args.file, "w") as fh:
        fh.write(new_text)

    with open(args.file) as fh:
        verify = fh.read()
    ok_marker = verify.count(MARKER) == 1
    ok_braces = (verify.count("{") - verify.count("}")) == (text.count("{") - text.count("}"))
    if not (ok_marker and ok_braces):
        print("[error] post-write verification failed (marker={0}, brace_delta_ok={1}); "
              "restore from {2}".format(verify.count(MARKER), ok_braces, backup))
        sys.exit(1)
    print("[patch] {0}: BPT section inserted ({1})".format(args.file, MARKER))


if __name__ == "__main__":
    main()
