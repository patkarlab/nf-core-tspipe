#!/usr/bin/env python3
"""Per-stratum haploid-X flag for BUILD_PON_TWIST CNVkit steps
(marker BPT_HAPLOID_X_V1).

Background (2026-09-01, build_v2 empirical check): CNVkit sex-normalises
each input to the reference's target scale, so the flagless build from 24
male normals produced a DIPLOID-X reference (ref chrX mean log2 +0.111 vs
chr1 -0.113). LOO iterations therefore showed chrX at mean_log2 -0.947
with fp_loss_rate 0.916 -- a systematic hemizygous offset, not variance --
and 409/416 chrX bins were blacklisted. The application layer
(cnvkit_wrapper.py) passes -y for male samples, which against a diploid-X
reference yields false chrX loss calls.

Fix: the male stratum reference and its LOO QC are built with -y
(haploid-X); the female stratum stays flagless (diploid-X). This matches
the wrapper contract and production convention.

Edits:
  1. modules/local/bpt_cnvkit_reference.nf -- yflag def + command flag,
     corrected header and echo.
  2. modules/local/bpt_cnv_loo_qc.nf -- yflag def + command flag,
     corrected header bullet.
  3. subworkflows/local/bpt_stratum.nf -- corrected header comment only.

Idempotent, anchor-based, dry-run by default. Run from the repo root:
    python tools/patches/2026-09-01/patch_bpt_haploid_x.py           # dry-run
    python tools/patches/2026-09-01/patch_bpt_haploid_x.py --apply
"""

import argparse
import os
import shutil
import sys
from datetime import datetime

MARKER = "BPT_HAPLOID_X_V1"
BS = chr(92)                      # backslash, built programmatically
CONT = " " + BS + BS              # ' \\' line-continuation tail

REF_MOD = "modules/local/bpt_cnvkit_reference.nf"
LOO_MOD = "modules/local/bpt_cnv_loo_qc.nf"
STRAT_SW = "subworkflows/local/bpt_stratum.nf"

# Each op: {kind, anchor: [lines], payload: [lines]}
#   replace_block : anchor lines replaced by payload lines
#   insert_after  : payload inserted after the single anchor line
#   insert_before : payload inserted before the single anchor line
EDITS = {
    REF_MOD: [
        {
            "kind": "replace_block",
            "anchor": [
                " * Pooled CNVkit reference for one stratum. NO -y, ever: sex is handled by",
                " * stratification, not by the haploid-X flag. params.male_reference is",
                " * retired for this panel (2026-08-30 design doc v3).",
            ],
            "payload": [
                " * Pooled CNVkit reference for one stratum. The male stratum is built",
                " * with -y (haploid-X reference) so the stored chrX scale matches what",
                " * the application layer declares; the female stratum is built flagless",
                " * (diploid-X). See the " + MARKER + " note in the script block.",
            ],
        },
        {
            "kind": "insert_after",
            "anchor": ["        def extra = task.ext.args ?: ''"],
            "payload": [
                "        // " + MARKER + ": the male stratum reference is built haploid-X",
                "        // (-y) to match the application layer (cnvkit_wrapper.py passes -y",
                "        // for male samples). CNVkit sex-normalises inputs to the",
                "        // reference's target scale, so a flagless build from male inputs",
                "        // yields a diploid-X reference. Verified 2026-09-01 on build_v2:",
                "        // ref chrX mean log2 +0.111 vs chr1 -0.113; LOO chrX mean -0.947,",
                "        // fp_loss_rate 0.916 -- systematic offset, not variance.",
                "        def yflag = (stratum == 'male') ? '-y' : ''",
            ],
        },
        {
            "kind": "insert_before",
            "anchor": ["            -o cnvkit_pon_${stratum}.cnn"],
            "payload": ["            ${yflag}" + CONT],
        },
        {
            "kind": "replace_block",
            "anchor": [
                "        echo \"[ok] wrote cnvkit_pon_${stratum}.cnn (no -y; sex handled by stratification)\"",
            ],
            "payload": [
                "        echo \"[ok] wrote cnvkit_pon_${stratum}.cnn (haploid-X flag: '${yflag}')\"",
            ],
        },
    ],
    LOO_MOD: [
        {
            "kind": "replace_block",
            "anchor": [" *   - never passes -y,"],
            "payload": [
                " *   - passes -y for the male stratum only (haploid-X reference;",
                " *     " + MARKER + "),",
            ],
        },
        {
            "kind": "insert_after",
            "anchor": ["    script:"],
            "payload": [
                "        def yflag = (stratum == 'male') ? '-y' : ''",
            ],
        },
        {
            "kind": "insert_before",
            "anchor": ["            -j ${task.cpus}"],
            "payload": ["            ${yflag}" + CONT],
        },
    ],
    STRAT_SW: [
        {
            "kind": "replace_block",
            "anchor": [
                " * One stratum of the Twist myeloid PoN: pooled CNVkit reference (no -y;",
                " * params.male_reference retired for this panel), GATK read-count PoN, and",
            ],
            "payload": [
                " * One stratum of the Twist myeloid PoN: pooled CNVkit reference",
                " * (haploid-X -y for the male stratum; " + MARKER + "), GATK",
                " * read-count PoN, and",
            ],
        },
    ],
}


def find_block(lines, anchor):
    """Return list of start indices where anchor lines match contiguously."""
    hits = []
    n = len(anchor)
    for i in range(len(lines) - n + 1):
        if all(lines[i + k].rstrip("\n") == anchor[k] for k in range(n)):
            hits.append(i)
    return hits


def apply_edits(lines, ops, path):
    for op in ops:
        hits = find_block(lines, op["anchor"])
        if len(hits) != 1:
            print("[error] {0}: anchor found {1} times (need exactly 1):".format(
                path, len(hits)))
            print("        {0}".format(op["anchor"][0]))
            sys.exit(1)
        i = hits[0]
        n = len(op["anchor"])
        payload = [p + "\n" for p in op["payload"]]
        if op["kind"] == "replace_block":
            lines[i:i + n] = payload
        elif op["kind"] == "insert_after":
            lines[i + n:i + n] = payload
        elif op["kind"] == "insert_before":
            lines[i:i] = payload
        else:
            print("[error] unknown edit kind: {0}".format(op["kind"]))
            sys.exit(1)
    return lines


def main():
    ap = argparse.ArgumentParser(description="Per-stratum haploid-X patch")
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry-run)")
    args = ap.parse_args()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    for path, ops in EDITS.items():
        if not os.path.isfile(path):
            print("[error] target not found: {0} (run from the repo root)".format(path))
            sys.exit(1)
        with open(path) as fh:
            text = fh.read()
        if MARKER in text:
            print("[skip] {0}: marker {1} already present".format(path, MARKER))
            continue

        lines = text.splitlines(True)
        # Validate all anchors before touching anything.
        for op in ops:
            hits = find_block(lines, op["anchor"])
            if len(hits) != 1:
                print("[error] {0}: anchor found {1} times (need exactly 1):".format(
                    path, len(hits)))
                print("        {0}".format(op["anchor"][0]))
                sys.exit(1)
        print("[plan] {0}: {1} edits, all anchors unique".format(path, len(ops)))

        if not args.apply:
            continue

        backup = "{0}.bak_bpt_haploid_x_{1}".format(path, ts)
        shutil.copy2(path, backup)
        print("[backup] {0}".format(backup))

        lines = apply_edits(lines, ops, path)
        with open(path, "w") as fh:
            fh.write("".join(lines))

        with open(path) as fh:
            verify = fh.read()
        n_marker = verify.count(MARKER)
        n_yflag = verify.count("yflag")
        ok = n_marker >= 1 and (path == STRAT_SW or n_yflag >= 2)
        if not ok:
            print("[error] {0}: post-write verification failed "
                  "(marker={1}, yflag={2}); restore from {3}".format(
                      path, n_marker, n_yflag, backup))
            sys.exit(1)
        print("[patch] {0}: haploid-X handling applied (marker x{1}, yflag x{2})".format(
            path, n_marker, n_yflag))

    if not args.apply:
        print("[dry-run] no changes written; re-run with --apply")


if __name__ == "__main__":
    main()
