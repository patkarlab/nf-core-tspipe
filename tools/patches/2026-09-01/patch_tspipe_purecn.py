#!/usr/bin/env python3
"""Wire PureCN into the gated twist block (marker PCN_V1).
Requires TGC_V1, BAF_V1, CMX_V1 applied.

Edits to workflows/tspipe.nf:
  1. Two include lines after the CNV_CONSENSUS_MULTI include.
  2. Gated-block tail rewritten: PureCN reference channels
     (checkIfExists; the twist overlay defines the params), tumor
     coverage, arity-proof Mutect2 VCF map, PURECN, and the consensus
     join extended by the two PureCN tables.
"""

import argparse
import os
import shutil
import sys
from datetime import datetime

MARKER = "PCN_V1"
TARGET = "workflows/tspipe.nf"

INC_ANCHOR = ("include { CNV_CONSENSUS_MULTI } from "
              "'../modules/local/cnv_consensus_multi'   // CMX_V1")
INC_PAYLOAD = [
    "include { PURECN_COVERAGE     } from '../modules/local/purecn_coverage'   // " + MARKER,
    "include { PURECN              } from '../modules/local/purecn'   // " + MARKER,
]

TAIL_ANCHOR = [
    "        // CMX_V1: four-caller consensus + Phase-4 JSON payload.",
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

TAIL_PAYLOAD = [
    "        // " + MARKER + ": PureCN purity/ploidy/integer-CN + LOH (fifth caller).",
    "        // Reference set from the twist overlay params; NormalDB build:",
    "        // tools/build_purecn_normaldb.sh (male stratum, PureCN 2.16.0).",
    "        ch_purecn_intervals = Channel.value(file(params.purecn_intervals, checkIfExists: true))",
    "        ch_purecn_normaldb  = Channel.value(file(params.purecn_normaldb,  checkIfExists: true))",
    "        PURECN_COVERAGE( ch_final_bam, ch_purecn_intervals )",
    "        ch_mutect2_vcf_only = VARIANT_CALLING.out.mutect2_vcf",
    "            .map { it -> tuple(it[0], it[1]) }",
    "        ch_purecn_in = PURECN_COVERAGE.out.coverage",
    "            .join( ch_mutect2_vcf_only, by: 0 )",
    "        PURECN( ch_purecn_in, ch_purecn_normaldb, ch_purecn_intervals )",
    "",
    "        // CMX_V1: five-caller consensus + Phase-4 JSON payload.",
    "        ch_consensus_in = CNV_CALLING.out.concordance",
    "            .join( CNV_CALLING.out.cnvkit_cnr,           by: 0 )",
    "            .join( CNV_CALLING.out.cnvkit_calls,         by: 0 )",
    "            .join( GATK_CNV_CALLING.out.genes,           by: 0 )",
    "            .join( GATK_CNV_CALLING.out.called,          by: 0 )",
    "            .join( GATK_CNV_CALLING.out.denoised,        by: 0 )",
    "            .join( GATK_CNV_CALLING.out.baf_summary,     by: 0 )",
    "            .join( GATK_CNV_CALLING.out.baf_sites,       by: 0 )",
    "            .join( PURECN.out.genes,                     by: 0 )",
    "            .join( PURECN.out.summary,                   by: 0 )",
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


def main():
    ap = argparse.ArgumentParser(description="tspipe.nf PureCN wiring patch")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    if not os.path.isfile(TARGET):
        print("[error] target not found: {0}".format(TARGET))
        sys.exit(1)
    text = open(TARGET).read()
    if MARKER in text:
        print("[skip] {0}: marker {1} already present".format(TARGET, MARKER))
        return
    for req in ("TGC_V1", "BAF_V1", "CMX_V1"):
        if req not in text:
            print("[error] {0} marker absent; apply prior patches first".format(req))
            sys.exit(1)

    lines = text.splitlines(True)
    if len(find_line(lines, INC_ANCHOR)) != 1:
        print("[error] include anchor not unique")
        sys.exit(1)
    if len(find_block(lines, TAIL_ANCHOR)) != 1:
        print("[error] CMX tail block not found uniquely")
        sys.exit(1)
    print("[plan] {0}: 2 includes + gated-tail rewrite "
          "({1} -> {2} lines)".format(TARGET, len(TAIL_ANCHOR), len(TAIL_PAYLOAD)))
    if not args.apply:
        print("[dry-run] no changes written; re-run with --apply")
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = "{0}.bak_pcn_{1}".format(TARGET, ts)
    shutil.copy2(TARGET, backup)
    print("[backup] {0}".format(backup))

    i = find_line(lines, INC_ANCHOR)[0]
    lines[i + 1:i + 1] = [p + "\n" for p in INC_PAYLOAD]
    j = find_block(lines, TAIL_ANCHOR)[0]
    lines[j:j + len(TAIL_ANCHOR)] = [p + "\n" for p in TAIL_PAYLOAD]

    open(TARGET, "w").write("".join(lines))
    verify = open(TARGET).read()
    ok = verify.count(MARKER) >= 2 and "PURECN(" in verify and \
        (verify.count("{") - verify.count("}")) == (text.count("{") - text.count("}"))
    if not ok:
        print("[error] post-write verification failed; restore from {0}".format(backup))
        sys.exit(1)
    print("[patch] {0}: PureCN wired ({1})".format(TARGET, MARKER))


if __name__ == "__main__":
    main()
