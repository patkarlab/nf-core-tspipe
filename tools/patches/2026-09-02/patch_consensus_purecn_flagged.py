#!/usr/bin/env python3
"""cnv_consensus_multi.py: exclude PureCN from consensus support when the
purity fit is flagged (status OK but flagged TRUE), retaining P calls in
the table as advisory.

Root cause (Female16 pilot, 2026-09-02): on an off-spec normal PureCN
returned status OK, purity 0.46, flagged TRUE (poor GOF, noisy log-ratio,
dropout). P support was counted in full and, correlated with the GATK
arm on the same male reference set, produced consensus LOSS on chr13
and single-arm gains on chr14. Only status was consulted; flagged was
ignored. Schema unchanged.

Dry-run by default; --apply to write. Idempotent via MARKER.
"""
import argparse
import shutil
import sys
import time

TARGET = "bin/cnv_consensus_multi.py"
MARKER = "MARKER: purecn_flagged_degrade"
TAG = "purecn_flagged"

ANCHOR_A = '''    if args.purecn_genes and os.path.isfile(args.purecn_genes) \\
            and purecn_sum.get("status") == "OK":
        for r in read_tsv(args.purecn_genes)[1]:
            purecn[r["gene"]] = r
    elif args.purecn_genes:
        warn("PureCN status={0}; P support omitted".format(
            purecn_sum.get("status")))
'''

REPLACE_A = '''    # MARKER: purecn_flagged_degrade
    # A flagged fit (poor GOF, noisy log-ratio, dropout) keeps its calls in
    # the table as advisory but contributes no consensus support.
    p_trusted = False
    if args.purecn_genes and os.path.isfile(args.purecn_genes) \\
            and purecn_sum.get("status") == "OK":
        for r in read_tsv(args.purecn_genes)[1]:
            purecn[r["gene"]] = r
        if str(purecn_sum.get("flagged", "")).strip().upper() == "TRUE":
            warn("PureCN flagged=TRUE ({0}); P calls retained as advisory, "
                 "P support omitted".format(purecn_sum.get("comment", "")))
        else:
            p_trusted = True
    elif args.purecn_genes:
        warn("PureCN status={0}; P support omitted".format(
            purecn_sum.get("status")))
'''

ANCHOR_B = '"P": p_call if p_call in ("GAIN", "LOSS") else None}'
REPLACE_B = '"P": p_call if (p_trusted and p_call in ("GAIN", "LOSS")) else None}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="write changes (default: dry-run)")
    ap.add_argument("--target", default=TARGET)
    args = ap.parse_args()

    with open(args.target) as fh:
        src = fh.read()
    if MARKER in src:
        print("[skip] marker present; already patched: %s" % args.target)
        return 0
    for label, anchor in (("A", ANCHOR_A), ("B", ANCHOR_B)):
        n = src.count(anchor)
        if n != 1:
            print("[error] anchor %s found %d times in %s (expected 1)"
                  % (label, n, args.target))
            return 1
    if not args.apply:
        print("[dry-run] both anchors found, unique. Re-run with --apply.")
        return 0
    ts = time.strftime("%Y%m%d_%H%M%S")
    bak = "%s.bak_%s_%s" % (args.target, TAG, ts)
    shutil.copy2(args.target, bak)
    print("[backup] %s" % bak)
    new = src.replace(ANCHOR_A, REPLACE_A).replace(ANCHOR_B, REPLACE_B)
    with open(args.target, "w") as fh:
        fh.write(new)
    print("[patch] applied to %s" % args.target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
