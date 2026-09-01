#!/usr/bin/env python3
"""Wire CNV_CONSENSUS_MULTI into the gated twist block (marker CMX_V1).
Requires TGC_V1 and BAF_V1 applied.

Edits:
  1. subworkflows/local/cnv_calling.nf -- two additive emits (cnr,
     genemetrics). Emit-only; legacy behaviour byte-identical.
  2. workflows/tspipe.nf -- include line + join chain + invocation
     appended inside the gated block, before its closing brace.

Idempotent, anchor-based, dry-run by default.
"""

import argparse
import os
import shutil
import sys
from datetime import datetime

MARKER = "CMX_V1"

CC = "subworkflows/local/cnv_calling.nf"
CC_ANCHOR = "        cnvkit_calls       = CNVKIT.out.call_cns"
CC_PAYLOAD = [
    "        cnvkit_cnr         = CNVKIT.out.cnr            // " + MARKER,
    "        cnvkit_genemetrics = CNVKIT.out.genemetrics    // " + MARKER,
]

TS = "workflows/tspipe.nf"
INC_ANCHOR = ("include { GATK_CNV_CALLING    } from "
              "'../subworkflows/local/gatk_cnv_calling'   // TGC_V1")
INC_PAYLOAD = [
    "include { CNV_CONSENSUS_MULTI } from '../modules/local/cnv_consensus_multi'   // " + MARKER,
]

TAIL_ANCHOR = [
    "            ch_baf_background,",
    "        )",
    "    }",
]
TAIL_PAYLOAD = [
    "            ch_baf_background,",
    "        )",
    "",
    "        // " + MARKER + ": four-caller consensus + Phase-4 JSON payload.",
    "        ch_consensus_in = CNV_CALLING.out.concordance",
    "            .join( CNV_CALLING.out.cnvkit_cnr,           by: 0 )",
    "            .join( CNV_CALLING.out.cnvkit_calls,         by: 0 )",
    "            .join( GATK_CNV_CALLING.out.genes,           by: 0 )",
    "            .join( GATK_CNV_CALLING.out.called,          by: 0 )",
    "            .join( GATK_CNV_CALLING.out.denoised,        by: 0 )",
    "            .join( GATK_CNV_CALLING.out.baf_summary,     by: 0 )",
    "            .join( GATK_CNV_CALLING.out.baf_sites,       by: 0 )",
    "        CNV_CONSENSUS_MULTI( ch_consensus_in, ch_cnv_loo_summary )",
    "    }",
]


def find_line(lines, anchor):
    return [i for i, l in enumerate(lines) if l.rstrip("\n") == anchor]


def find_block(lines, anchor):
    hits = []
    n = len(anchor)
    for i in range(len(lines) - n + 1):
        if all(lines[i + k].rstrip("\n") == anchor[k] for k in range(n)):
            hits.append(i)
    return hits


def patch_file(path, checks, do_apply, ts):
    with open(path) as fh:
        text = fh.read()
    if MARKER in text:
        print("[skip] {0}: marker {1} already present".format(path, MARKER))
        return True
    lines = text.splitlines(True)
    for label, anchor, _, _ in checks:
        hits = find_block(lines, anchor) if isinstance(anchor, list) \
            else find_line(lines, anchor)
        if len(hits) != 1:
            print("[error] {0}: {1} anchor found {2} times (need 1)".format(
                path, label, len(hits)))
            sys.exit(1)
    print("[plan] {0}: {1} edit(s), all anchors unique".format(path, len(checks)))
    if not do_apply:
        return False

    backup = "{0}.bak_cmx_{1}".format(path, ts)
    shutil.copy2(path, backup)
    print("[backup] {0}".format(backup))
    for label, anchor, payload, kind in checks:
        if kind == "insert_after_line":
            i = find_line(lines, anchor)[0]
            lines[i + 1:i + 1] = [p + "\n" for p in payload]
        elif kind == "replace_block":
            i = find_block(lines, anchor)[0]
            lines[i:i + len(anchor)] = [p + "\n" for p in payload]
    with open(path, "w") as fh:
        fh.write("".join(lines))
    with open(path) as fh:
        verify = fh.read()
    ok = MARKER in verify and \
        (verify.count("{") - verify.count("}")) == (text.count("{") - text.count("}"))
    if not ok:
        print("[error] {0}: post-write verification failed; restore from {1}".format(
            path, backup))
        sys.exit(1)
    print("[patch] {0}: applied ({1})".format(path, MARKER))
    return True


def main():
    ap = argparse.ArgumentParser(description="consensus wiring patch")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    for path in (CC, TS):
        if not os.path.isfile(path):
            print("[error] target not found: {0}".format(path))
            sys.exit(1)
    ts_text = open(TS).read()
    if "TGC_V1" not in ts_text or "BAF_V1" not in ts_text:
        print("[error] TGC_V1/BAF_V1 markers absent in tspipe.nf; apply prior patches")
        sys.exit(1)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    patch_file(CC, [("emit", CC_ANCHOR, CC_PAYLOAD, "insert_after_line")],
               args.apply, ts)
    patch_file(TS, [
        ("include", INC_ANCHOR, INC_PAYLOAD, "insert_after_line"),
        ("gated-tail", TAIL_ANCHOR, TAIL_PAYLOAD, "replace_block"),
    ], args.apply, ts)
    if not args.apply:
        print("[dry-run] no changes written; re-run with --apply")


if __name__ == "__main__":
    main()
