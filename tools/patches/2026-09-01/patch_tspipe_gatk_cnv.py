#!/usr/bin/env python3
"""Wire the gated GATK CNV caller into workflows/tspipe.nf (marker TGC_V1).

Two edits:
  1. include line for GATK_CNV_CALLING after the CNV_CALLING include.
  2. Guarded invocation block before the SV-calling banner. The block
     runs only when params.cnv_gatk_pon is defined (set in
     conf/twist_apply.config); the containsKey guard means legacy panels
     never evaluate it and never see an undefined-parameter warning.

Idempotent, anchor-based, dry-run by default. Run from the repo root:
    python tools/patches/2026-09-01/patch_tspipe_gatk_cnv.py           # dry-run
    python tools/patches/2026-09-01/patch_tspipe_gatk_cnv.py --apply
"""

import argparse
import os
import shutil
import sys
from datetime import datetime

MARKER = "TGC_V1"
TARGET = "workflows/tspipe.nf"

INCLUDE_ANCHOR = "include { CNV_CALLING         } from '../subworkflows/local/cnv_calling'"
INCLUDE_LINE = ("include { GATK_CNV_CALLING    } from "
                "'../subworkflows/local/gatk_cnv_calling'   // " + MARKER)

BLOCK_ANCHOR = "    // ----- 5. SV calling -----------------------------------------------"

BLOCK = [
    "    // ----- 4b. GATK CNV calling (" + MARKER + "; twist_myeloid) ---------------",
    "    // Gated on params.cnv_gatk_pon, defined only in conf/twist_apply.config.",
    "    // Legacy panels never evaluate this block; the containsKey guard also",
    "    // avoids undefined-parameter warnings.",
    "    if( params.containsKey('cnv_gatk_pon') && params.cnv_gatk_pon ) {",
    "        def gatk_ilist = \"${projectDir}/assets/${params.panel}/targets.preprocessed.interval_list\"",
    "        if( params.containsKey('cnv_gatk_intervals') && params.cnv_gatk_intervals )",
    "            gatk_ilist = params.cnv_gatk_intervals",
    "        ch_gatk_rc_pon = Channel.value(file(params.cnv_gatk_pon, checkIfExists: true))",
    "        ch_gatk_ilist  = Channel.value(file(gatk_ilist,          checkIfExists: true))",
    "        GATK_CNV_CALLING(",
    "            ch_final_bam,",
    "            ch_reference,",
    "            ch_gatk_ilist,",
    "            ch_gatk_rc_pon,",
    "            ch_exonwise_bed,",
    "        )",
    "    }",
    "",
]


def find_line(lines, anchor):
    return [i for i, l in enumerate(lines) if l.rstrip("\n") == anchor]


def main():
    ap = argparse.ArgumentParser(description="tspipe.nf GATK CNV wiring patch")
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry-run)")
    args = ap.parse_args()

    if not os.path.isfile(TARGET):
        print("[error] target not found: {0} (run from the repo root)".format(TARGET))
        sys.exit(1)
    with open(TARGET) as fh:
        text = fh.read()
    if MARKER in text:
        print("[skip] {0}: marker {1} already present".format(TARGET, MARKER))
        return

    lines = text.splitlines(True)
    inc_hits = find_line(lines, INCLUDE_ANCHOR)
    blk_hits = find_line(lines, BLOCK_ANCHOR)
    if len(inc_hits) != 1:
        print("[error] include anchor found {0} times (need 1)".format(len(inc_hits)))
        sys.exit(1)
    if len(blk_hits) != 1:
        print("[error] SV-banner anchor found {0} times (need 1)".format(len(blk_hits)))
        sys.exit(1)
    print("[plan] {0}: include after line {1}; gated block before line {2} "
          "({3} lines)".format(TARGET, inc_hits[0] + 1, blk_hits[0] + 1, len(BLOCK)))

    if not args.apply:
        print("[dry-run] no changes written; re-run with --apply")
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = "{0}.bak_tgc_{1}".format(TARGET, ts)
    shutil.copy2(TARGET, backup)
    print("[backup] {0}".format(backup))

    i = find_line(lines, INCLUDE_ANCHOR)[0]
    lines[i + 1:i + 1] = [INCLUDE_LINE + "\n"]
    j = find_line(lines, BLOCK_ANCHOR)[0]
    lines[j:j] = [b + "\n" for b in BLOCK]

    with open(TARGET, "w") as fh:
        fh.write("".join(lines))
    with open(TARGET) as fh:
        verify = fh.read()
    braces_ok = (verify.count("{") - verify.count("}")) == (text.count("{") - text.count("}") + 0)
    ok = verify.count(MARKER) == 2 and "GATK_CNV_CALLING(" in verify and braces_ok
    if not ok:
        print("[error] post-write verification failed (marker={0}, braces_ok={1}); "
              "restore from {2}".format(verify.count(MARKER), braces_ok, backup))
        sys.exit(1)
    print("[patch] {0}: GATK CNV caller wired ({1})".format(TARGET, MARKER))


if __name__ == "__main__":
    main()
