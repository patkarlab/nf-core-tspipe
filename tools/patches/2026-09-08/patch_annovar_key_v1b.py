#!/usr/bin/env python3
"""tools/patches/<date>/patch_annovar_key_v1b.py -- MARKER ANNOVAR_KEY_V1b

After ANNOVAR_KEY_V1, 77 of 5,264 rows on 26CGH1250 still keyed wrongly as
chr1:0:chr1:101808364 -- the Otherinfo scan matched a bookkeeping column
holding the chromosome name followed by a '0'. The candidate is now accepted
only when POS is a positive integer and REF and ALT are allele strings
([ACGTN]+ or '*'); otherwise the scan continues to the real CHROM column.

Usage:  python3 <this file> [--apply]
"""

import argparse
import sys
import time
from pathlib import Path

MARKER = "ANNOVAR_KEY_V1b"
REPO = Path(__file__).resolve().parents[3]
PY = "bin/annotate.py"

OLD = (
    '        pos = (row.get(cols[i + 1]) or "").strip()\n'
    '        if not pos.isdigit():\n'
    '            continue\n'
    '        ref = (row.get(cols[i + 3]) or "").strip()\n'
    '        alt = (row.get(cols[i + 4]) or "").strip()\n'
    '        if not ref or not alt or ref == "." or alt == ".":\n'
    '            continue\n'
)
NEW = (
    '        pos = (row.get(cols[i + 1]) or "").strip()\n'
    '        if not pos.isdigit() or int(pos) <= 0:\n'
    '            continue\n'
    '        ref = (row.get(cols[i + 3]) or "").strip()\n'
    '        alt = (row.get(cols[i + 4]) or "").strip()\n'
    '        # ANNOVAR_KEY_V1b: both must look like alleles, or this was a bookkeeping column\n'
    '        if not (_ALLELE_RE.match(ref) and _ALLELE_RE.match(alt)):\n'
    '            continue\n'
)
RE_ANCHOR = '_ANNOVAR_KEY_STATS = {"vcf": 0, "fallback": 0}   # ANNOVAR_KEY_V1\n'
RE_NEW = RE_ANCHOR + 'import re as _re_annovar\n_ALLELE_RE = _re_annovar.compile(r"^(?:[ACGTNacgtn]+|\\*)$")   # ANNOVAR_KEY_V1b\n'


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--apply", action="store_true"); args = ap.parse_args()
    p = REPO / PY; text = p.read_text()
    if MARKER in text:
        print("SKIP  %s: already applied" % PY); return
    for old in (OLD, RE_ANCHOR):
        if text.count(old) != 1:
            print("ABORT: anchor matched %d times: %r" % (text.count(old), old[:60])); sys.exit(1)
    new = text.replace(OLD, NEW, 1).replace(RE_ANCHOR, RE_NEW, 1)
    print("PLAN  %s: allele-pattern check in _annovar_vcf_key, marker %s" % (PY, MARKER))
    if not args.apply:
        print("dry run; re-run with --apply"); return
    p.with_name(p.name + ".bak_annovar_key_v1b_%s" % time.strftime("%Y%m%d_%H%M%S")).write_text(text)
    p.write_text(new); print("WROTE %s\ndone" % PY)


if __name__ == "__main__":
    main()
