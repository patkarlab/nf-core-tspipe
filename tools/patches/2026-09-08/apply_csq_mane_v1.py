#!/usr/bin/env python3
"""
CSQ_MANE_V1 (N3 / D3): VEP consequence selection reports on MANE Select.

Since the CSF3R fix, _pick_csq() in bin/annotate.py chose ONE CSQ block per
variant by consequence severity across every transcript VEP emitted, with MANE
only as a tie-breaker. Run8 with CAVA alongside showed the cost: a missense on
an alternative isoform outranks a synonymous call on the MANE transcript, so
SF1, PAX5, IRF1, U2AF2, PRPF40B and one PASS call (UBTF chr17:44207341 G>A,
reported as p.Thr694Met on ENSP00000431539; p.(Asp732=) on MANE NM_014233)
were reported on non-MANE transcripts with ENSP accessions -- the fellow's D3.

New rule (Nikhil, 2026-09-08): MANE first.
  1. If any CSQ block carries MANE_SELECT, choose among those blocks only,
     by severity (this keeps CSF3R T618I: the CSF3R MANE block is missense,
     the overlapping MRPS15 MANE block is upstream_gene_variant).
  2. Only when no block is MANE (non-MANE genes, backbone tiles, intergenic)
     fall back to severity over all blocks, then PICK, then input order.

Also bumps the cache-bust comment in modules/local/vep_annotate.nf.

Usage:
    python3 tools/patches/2026-09-08/apply_csq_mane_v1.py --apply
"""

import argparse
import shutil
import sys
import time
from pathlib import Path

TAG = "csq_mane_v1"
MARKER = "CSQ_MANE_V1"


def patch_annotate(text):
    if MARKER in text:
        print("  already patched")
        return text
    old = '''def _pick_csq(csq_blocks, csq_fields):
    """Choose ONE CSQ block from a variant's list of blocks.

    Selection order (gene-agnostic):
      1. most severe consequence (lowest _csq_severity)
      2. tie -> MANE Select transcript present
      3. tie -> VEP's own PICK flag (=='1') if a PICK field exists
      4. tie -> first block (input order)

    csq_blocks : list of dicts (field_name -> value)
    csq_fields : list of CSQ subfield names (for PICK/MANE_SELECT presence)
    """
    has_pick = "PICK" in csq_fields
    has_mane = "MANE_SELECT" in csq_fields

    def sort_key(idx_block):
        idx, block = idx_block
        sev = _csq_severity(block.get("Consequence", ""))
        mane = 0 if (has_mane and str(block.get("MANE_SELECT", "")).strip()) else 1
        pick = 0 if (has_pick and str(block.get("PICK", "")).strip() == "1") else 1
        return (sev, mane, pick, idx)

    indexed = list(enumerate(csq_blocks))
    indexed.sort(key=sort_key)
    return indexed[0][1]
'''
    new = '''def _pick_csq(csq_blocks, csq_fields):
    """Choose ONE CSQ block from a variant's list of blocks.

    CSQ_MANE_V1 (2026-09-08): the clinical table reports on the MANE Select
    transcript. Selection order:
      1. if any block carries MANE_SELECT, consider ONLY those blocks
         (an overlapping neighbour's MANE block is still outranked by severity,
         so CSF3R T618I is not masked by MRPS15 upstream_gene_variant)
      2. most severe consequence (lowest _csq_severity)
      3. tie -> VEP's own PICK flag (=='1') if a PICK field exists
      4. tie -> first block (input order)
    Blocks without MANE_SELECT are used only when no MANE block exists for the
    variant (genes without a MANE transcript, backbone tiles, intergenic).

    Before this change severity came first and MANE was a tie-breaker, so a
    missense on an alternative isoform outranked a synonymous call on MANE
    (SF1, UBTF, PAX5, IRF1 in run8), reported with ENSP accessions.

    csq_blocks : list of dicts (field_name -> value)
    csq_fields : list of CSQ subfield names (for PICK/MANE_SELECT presence)
    """
    has_pick = "PICK" in csq_fields
    has_mane = "MANE_SELECT" in csq_fields

    def is_mane(block):
        return has_mane and bool(str(block.get("MANE_SELECT", "")).strip())

    def sort_key(idx_block):
        idx, block = idx_block
        sev = _csq_severity(block.get("Consequence", ""))
        pick = 0 if (has_pick and str(block.get("PICK", "")).strip() == "1") else 1
        return (sev, pick, idx)

    indexed = list(enumerate(csq_blocks))
    mane_blocks = [ib for ib in indexed if is_mane(ib[1])]   # CSQ_MANE_V1
    candidates = mane_blocks if mane_blocks else indexed
    candidates.sort(key=sort_key)
    return candidates[0][1]
'''
    assert text.count(old) == 1, "anchor (_pick_csq) not found exactly once"
    return text.replace(old, new)


def patch_module(text):
    if MARKER in text:
        print("  already patched")
        return text
    old = "        # CAVA_V1b (N3): --cava-vcf merges CAVA_* columns; CAVA_V1b2 multi-transcript split fix (bash comment; busts the task cache)\n"
    new = ("        # CAVA_V1b (N3): --cava-vcf merges CAVA_* columns; CAVA_V1b2 multi-transcript split fix; "
           "CSQ_MANE_V1 MANE-first CSQ selection (bash comment; busts the task cache)\n")
    assert text.count(old) == 1, "anchor (module comment; apply CAVA_V1b2 first) not found exactly once"
    return text.replace(old, new)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    root = Path(args.root)
    ts = time.strftime("%Y%m%d_%H%M%S")
    for path, fn in [(root / "bin/annotate.py", patch_annotate),
                     (root / "modules/local/vep_annotate.nf", patch_module)]:
        print(path)
        text = path.read_text()
        new = fn(text)
        if new == text:
            continue
        if args.apply:
            backup = path.with_name(path.name + f".bak_{TAG}_{ts}")
            shutil.copy2(path, backup)
            path.write_text(new)
            print(f"  patched (backup {backup.name})")
        else:
            print("  would patch (dry run; use --apply)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
