#!/usr/bin/env python3
"""
patch_hotspot_exempt_v1.py   (MARKER: HOTSPOT_EXEMPT_V1)

Problem
-------
bin/variant_filter.py applies three exemptions to a hard-coded U2AF1 test:

    _is_u2af1_hotspot = Gene == "U2AF1" and HGVSp contains S34/Q157

That carve-out exists because U2AF1 S34F sits in a paralogous region where
standard callers fail on MAPQ-0 alignments and the variant is recovered by a
pileup script, i.e. a single non-standard "caller". It was a workaround for
one locus, not a hotspot policy.

Every other filter in the same function uses the general, table-driven
is_hotspot_residue(gene, hgvsp) against myeloid_hotspots.tsv - CLINVAR_BENIGN
and NON_REPORTABLE_CONSEQUENCE both do. Only LOW_CALLERS, LOW_DEPTH and
NO_CALLER_INFO use the U2AF1-specific test.

Consequence, measured on twistval24_20260912 (24 samples):

    NPM1_5Percent  NPM1 p.Trp288CysfsTer12  5.56%  VarDict only   LOW_CALLERS
    26CGH1496      FLT3 p.Asp835Tyr         2.62%  Mutect2 only   LOW_CALLERS

Both are canonical therapy-linked hotspots in myeloid_hotspots.tsv, both are
filtered out of the clinical table, and neither appears in the report.

Change
------
LOW_CALLERS and LOW_DEPTH now exempt any hotspot residue, not just U2AF1.
The exemption is restricted to non-synonymous consequences.

NO_CALLER_INFO keeps the U2AF1-only test deliberately: a row with no caller
information at all has no supporting evidence, and the U2AF1 pileup rescue is
the one legitimate source of such rows.

Why the synonymous guard is load-bearing
----------------------------------------
JAK2 p.Gly554= is FreeBayes-only at 2.8-6.4% in 24 of 24 samples - a
systematic artefact that nonetheless matches a JAK2 hotspot residue range.
Without the guard it would be promoted 41 times. It should also be
blacklisted (A3), but the guard means this patch does not depend on that.

Measured effect on twistval24_20260912: 2 rows promoted across 24 samples.
The general caller threshold is unchanged - two or more callers are still
required for every non-hotspot variant. Requiring three was evaluated and
rejected: it would have removed 22 PASS rows, most of them indels, including
IKZF1 p.Asp64_Glu65insLeuArgGly at 65.7%, IL7R p.Ile241ProfsTer5 at 40.9%
and two SETD2 frameshifts at 35.4% and 29.3%.

Usage
-----
    python3 patch_hotspot_exempt_v1.py --repo /goast/hemat_data/nf-core-tspipe
    python3 patch_hotspot_exempt_v1.py --repo ... --apply

Run on gandalf (the development host), validate, then re-tag. Do not patch a
deployed clinical clone in place.
"""

import argparse
import os
import shutil
import sys
import time

MARKER = "HOTSPOT_EXEMPT_V1"
TARGET = os.path.join("bin", "variant_filter.py")

ANCHOR_DEF = '''        # Check if this is a U2AF1 hotspot (exempt from LOW_CALLERS/LOW_DEPTH)
        _is_u2af1_hotspot = False
        if str(row.get("Gene", "")).strip() == "U2AF1":
            hgvsp = str(row.get("HGVSp", "")).strip()
            if "Ser34" in hgvsp or "S34" in hgvsp or "Gln157" in hgvsp or "Q157" in hgvsp:
                _is_u2af1_hotspot = True
'''

NEW_DEF = '''        # Check if this is a U2AF1 hotspot (exempt from NO_CALLER_INFO)
        _is_u2af1_hotspot = False
        if str(row.get("Gene", "")).strip() == "U2AF1":
            hgvsp = str(row.get("HGVSp", "")).strip()
            if "Ser34" in hgvsp or "S34" in hgvsp or "Gln157" in hgvsp or "Q157" in hgvsp:
                _is_u2af1_hotspot = True

        # MARKER HOTSPOT_EXEMPT_V1: LOW_CALLERS and LOW_DEPTH exempt any
        # hotspot residue from myeloid_hotspots.tsv, not just U2AF1, provided
        # the consequence is non-synonymous. Canonical hotspots called by a
        # single caller are recoverable evidence, not noise: NPM1 type A
        # insertions and FLT3 D835 are routinely single-caller at low VAF
        # because callers disagree on indel representation. The synonymous
        # guard keeps out JAK2 p.Gly554=, a FreeBayes-only artefact present in
        # 24/24 samples at 2.8-6.4% that matches a JAK2 residue range.
        # NO_CALLER_INFO keeps the U2AF1-only test: no caller information at
        # all means no evidence.
        _hotspot_exempt = _is_u2af1_hotspot
        if not _hotspot_exempt:
            _csq_lower = str(row.get("_consequence", "")).lower()
            if "synonymous" not in _csq_lower:
                if is_hotspot_residue(row.get("Gene", ""), row.get("HGVSp", "")):
                    _hotspot_exempt = True
'''

ANCHOR_LC = '''        caller_count = row["_caller_count"]
        if caller_count >= 0 and caller_count < 2 and not _is_u2af1_hotspot:
            filters.append("LOW_CALLERS")
            continue
'''

NEW_LC = '''        caller_count = row["_caller_count"]
        if caller_count >= 0 and caller_count < 2 and not _hotspot_exempt:
            filters.append("LOW_CALLERS")
            continue
'''

ANCHOR_LD = '''        alt_count = row["_alt_count"]
        if alt_count >= 0 and alt_count < 10 and not _is_u2af1_hotspot:
            filters.append("LOW_DEPTH")
            continue
'''

NEW_LD = '''        alt_count = row["_alt_count"]
        if alt_count >= 0 and alt_count < 10 and not _hotspot_exempt:
            filters.append("LOW_DEPTH")
            continue
'''

EDITS = [
    ("exemption definition", ANCHOR_DEF, NEW_DEF),
    ("LOW_CALLERS test", ANCHOR_LC, NEW_LC),
    ("LOW_DEPTH test", ANCHOR_LD, NEW_LD),
]


def log(tag, msg):
    print("[%s] %s" % (tag, msg))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    path = os.path.join(args.repo, TARGET)
    if not os.path.exists(path):
        log("error", "not found: %s" % path)
        return 1
    log("info", "target: %s" % path)

    with open(path) as fh:
        src = fh.read()

    if MARKER in src:
        log("skip", "%s already applied" % MARKER)
        return 0

    if "def is_hotspot_residue" not in src:
        log("error", "is_hotspot_residue() not defined in this file")
        return 1

    out = src
    for label, anchor, replacement in EDITS:
        n = out.count(anchor)
        if n != 1:
            log("error", "%s: anchor matched %d times, expected 1" % (label, n))
            log("error", "the file has drifted; re-read it and update the anchors")
            return 1
        out = out.replace(anchor, replacement, 1)
        log("patch", "%s: ok" % label)

    if not args.apply:
        log("dry-run", "3 edits would be applied to %s" % TARGET)
        log("dry-run", "re-run with --apply to write")
        return 0

    stamp = time.strftime("%Y%m%d_%H%M%S")
    bak = "%s.bak_hotspotexempt_%s" % (path, stamp)
    shutil.copy2(path, bak)
    log("backup", bak)
    with open(path, "w") as fh:
        fh.write(out)
    log("patch", "written")

    print()
    print("Next:")
    print("  1. python3 -c \"import ast;ast.parse(open('%s').read())\"" % TARGET)
    print("  2. variant_filter.py is invoked by name, so it IS in the task")
    print("     hash - a resume re-executes VARIANT_FILTER and downstream")
    print("  3. re-run and confirm exactly two rows are promoted:")
    print("       NPM1 p.Trp288CysfsTer12  5.56%  in NPM1_5Percent")
    print("       FLT3 p.Asp835Tyr         2.62%  in 26CGH1496")
    print("     and that no JAK2 p.Gly554= row reaches the clinical table")
    print("  4. diff clinical tables against the previous run: the only new")
    print("     rows should be at hotspot residues")
    print("  5. commit, tag, then pull on clinical-23")
    return 0


if __name__ == "__main__":
    sys.exit(main())
