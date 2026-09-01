#!/usr/bin/env python3
"""Wire the BAF/cnLOH channels into the gated GATK CNV block in
workflows/tspipe.nf (marker BAF_V1). Requires the TGC_V1 patch applied.

Two edits inside the existing gated block:
  1. BAF SNP-catalog and background channels (asset defaults from
     assets/${params.panel}/, overridable via cnv_baf_sites /
     cnv_baf_background params).
  2. Two extra arguments on the GATK_CNV_CALLING invocation.

Idempotent, anchor-based, dry-run by default. Run from the repo root:
    python tools/patches/2026-09-01/patch_tspipe_baf.py           # dry-run
    python tools/patches/2026-09-01/patch_tspipe_baf.py --apply
"""

import argparse
import os
import shutil
import sys
from datetime import datetime

MARKER = "BAF_V1"
TARGET = "workflows/tspipe.nf"

CH_ANCHOR = "        ch_gatk_ilist  = Channel.value(file(gatk_ilist,          checkIfExists: true))"
CH_PAYLOAD = [
    "        // " + MARKER + ": BAF SNP catalog + male-cohort background for the",
    "        // allele-specific track (ModelSegments) and the 17p cnLOH detector.",
    "        def baf_sites = \"${projectDir}/assets/${params.panel}/snp_sites.baf.bed\"",
    "        if( params.containsKey('cnv_baf_sites') && params.cnv_baf_sites )",
    "            baf_sites = params.cnv_baf_sites",
    "        def baf_bg = \"${projectDir}/assets/${params.panel}/baf_background.tsv\"",
    "        if( params.containsKey('cnv_baf_background') && params.cnv_baf_background )",
    "            baf_bg = params.cnv_baf_background",
    "        ch_baf_snp_bed    = Channel.value(file(baf_sites, checkIfExists: true))",
    "        ch_baf_background = Channel.value(file(baf_bg,    checkIfExists: true))",
]

ARG_ANCHOR = "            ch_exonwise_bed,"
ARG_PAYLOAD = [
    "            ch_exonwise_bed,",
    "            ch_baf_snp_bed,",
    "            ch_baf_background,",
]


def find_line(lines, anchor):
    return [i for i, l in enumerate(lines) if l.rstrip("\n") == anchor]


def main():
    ap = argparse.ArgumentParser(description="tspipe.nf BAF wiring patch")
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
    if "TGC_V1" not in text:
        print("[error] TGC_V1 marker absent; apply patch_tspipe_gatk_cnv.py first")
        sys.exit(1)

    lines = text.splitlines(True)
    ch_hits = find_line(lines, CH_ANCHOR)
    arg_hits = find_line(lines, ARG_ANCHOR)
    if len(ch_hits) != 1:
        print("[error] channel anchor found {0} times (need 1)".format(len(ch_hits)))
        sys.exit(1)
    if len(arg_hits) != 1:
        print("[error] call-arg anchor found {0} times (need 1)".format(len(arg_hits)))
        sys.exit(1)
    print("[plan] {0}: channels after line {1}; call args at line {2}".format(
        TARGET, ch_hits[0] + 1, arg_hits[0] + 1))

    if not args.apply:
        print("[dry-run] no changes written; re-run with --apply")
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = "{0}.bak_baf_{1}".format(TARGET, ts)
    shutil.copy2(TARGET, backup)
    print("[backup] {0}".format(backup))

    i = find_line(lines, CH_ANCHOR)[0]
    lines[i + 1:i + 1] = [p + "\n" for p in CH_PAYLOAD]
    j = find_line(lines, ARG_ANCHOR)[0]
    lines[j:j + 1] = [p + "\n" for p in ARG_PAYLOAD]

    with open(TARGET, "w") as fh:
        fh.write("".join(lines))
    with open(TARGET) as fh:
        verify = fh.read()
    ok = (verify.count(MARKER) == 1 and "ch_baf_background," in verify
          and (verify.count("{") - verify.count("}")) == (text.count("{") - text.count("}")))
    if not ok:
        print("[error] post-write verification failed; restore from {0}".format(backup))
        sys.exit(1)
    print("[patch] {0}: BAF channels wired ({1})".format(TARGET, MARKER))


if __name__ == "__main__":
    main()
