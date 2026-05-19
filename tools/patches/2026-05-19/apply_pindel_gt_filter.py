#!/usr/bin/env python3
"""
apply_pindel_gt_filter.py  --  2026-05-19

Drop reference-genotype Pindel records from the FLT3 consensus input.

On the 25NGS1307 real-data validation today, parse_pindel() in
bin/flt3_consensus.py accepted every record that passed the SVTYPE
filter. The PINDEL_FLT3_FILTER output for that sample contains one
bona-fide ITD at chr13:28034132 (GT=0/1) plus ~37 sub-1%-VAF noise
records, all with GT=0/0. The noise was folded into the consensus
and produced misleading vaf_pct_min values and false REVIEW_REQUIRED
rows downstream.

Fix: after the existing SVTYPE check in parse_pindel(), parse
FORMAT/GT from the sample column and skip records whose genotype is
0/0, 0|0, or ./.. No VAF or alt-read filtering is introduced; the
contract is strictly genotype-based.

Anchor: the two-line block that ends the SVTYPE check and starts
the SVLEN parse. The GT-filter block is inserted between those.

Backup tag: .bak_pindel_gt_filter_<UTC-timestamp>

Audit memo: docs/audit/2026-05-19/d1d2_real_data_findings.md
"""
import shutil
import sys
from datetime import datetime
from pathlib import Path

REPO = Path("/goast/hemat_data/nf-core-tspipe")
F = REPO / "bin" / "flt3_consensus.py"

# A substring that is unique to the patched version. If present, the
# patcher exits early without modifying the file. This is what makes
# the patcher idempotent.
MARKER = 'gt in ("0/0", "0|0", "./.")'

OLD = (
    '            if svtype not in ("DUP", "INS"):\n'
    '                continue\n'
    '            length_str = info.get("SVLEN", "0").lstrip("+-")\n'
)

NEW = (
    '            if svtype not in ("DUP", "INS"):\n'
    '                continue\n'
    '            fmt_keys = parts[8].split(":") if len(parts) > 8 else []\n'
    '            sample_vals = parts[9].split(":") if len(parts) > 9 else []\n'
    '            fmt = dict(zip(fmt_keys, sample_vals))\n'
    '            gt = fmt.get("GT", "")\n'
    '            if gt in ("0/0", "0|0", "./."):\n'
    '                continue\n'
    '            length_str = info.get("SVLEN", "0").lstrip("+-")\n'
)


def main():
    if not F.exists():
        sys.exit("missing: {}".format(F))
    text = F.read_text()
    if MARKER in text:
        print("[skip]   {} already patched (marker present)".format(F.name))
        return
    if OLD not in text:
        sys.exit("[error] anchor not found in {}".format(F.name))
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = F.with_suffix(F.suffix + ".bak_pindel_gt_filter_" + stamp)
    shutil.copy2(F, backup)
    print("[backup] {}".format(backup.name))
    text = text.replace(OLD, NEW, 1)
    F.write_text(text)
    print("[patch]  {}".format(F.name))


if __name__ == "__main__":
    main()
