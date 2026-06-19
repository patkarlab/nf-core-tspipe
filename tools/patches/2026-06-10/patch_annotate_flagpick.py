#!/usr/bin/env python3
"""
patch_annotate_flagpick.py

Fix: VEP --pick collapsed all consequences to one block and could select a
non-coding neighbour (e.g. MRPS15 upstream_gene_variant) over a co-located
coding consequence (e.g. CSF3R T618I missense), so the variant was annotated
to the wrong gene with an empty HGVSp and then down-filtered as LOW_IMPACT.
The variant was never lost - it was mislabelled.

This patch makes annotation keep ALL CSQ blocks and choose the most clinically
meaningful one by consequence severity. Gene-agnostic: no driver/panel list.

Three anchored edits to bin/annotate.py:
  1. run_vep(): "--pick" -> "--flag_pick"   (emit all CSQ, tag one PICK=1)
  2. add module-level CONSEQUENCE_RANK + _pick_csq() helper
  3. parse_vep_csq(): replace split(",")[0] with severity-based selection

Conventions:
  - dry-run by default; pass --apply to write
  - backup: <file>.bak_flagpick_<timestamp>
  - idempotent via MARKER lines; re-running on a patched file -> [skip]
  - status: [skip] / [backup] / [patch] / [error]

Target Python: 3.6 (vep env / GATK container safe) - no f-strings required here,
no walrus, no PEP 585 generics.
"""

import argparse
import datetime
import os
import sys

TARGET = "/goast/hemat_data/nf-core-tspipe/bin/annotate.py"
MARKER = "flagpick severity-based CSQ selection"

# ----------------------------------------------------------------------------
# Edit 1: run_vep flag swap
# ----------------------------------------------------------------------------
OLD_PICK = '        "--pick",            # one consequence per variant (canonical-ish pick)\n'
NEW_PICK = (
    '        "--flag_pick",       # [%s] keep ALL CSQ, tag one PICK=1; parser selects by severity\n'
    % MARKER
)

# ----------------------------------------------------------------------------
# Edit 2: constant + helper, inserted immediately before "def parse_vep_csq("
# ----------------------------------------------------------------------------
HELPER_BLOCK = '''# [{marker}]
# Ensembl VEP consequence severity ordering (most severe first). Index = rank;
# lower index = more severe. Used to choose ONE CSQ block per variant when VEP
# is run with --flag_pick (which emits every transcript consequence). This is
# gene-agnostic: a coding consequence (missense/stop/frameshift) outranks a
# neighbouring transcript's upstream/downstream/intergenic MODIFIER, so an
# overlapping gene can no longer mask the clinically relevant call.
CONSEQUENCE_RANK = {{
    name: i for i, name in enumerate([
        "transcript_ablation",
        "splice_acceptor_variant",
        "splice_donor_variant",
        "stop_gained",
        "frameshift_variant",
        "stop_lost",
        "start_lost",
        "transcript_amplification",
        "feature_elongation",
        "feature_truncation",
        "inframe_insertion",
        "inframe_deletion",
        "missense_variant",
        "protein_altering_variant",
        "splice_donor_5th_base_variant",
        "splice_region_variant",
        "splice_donor_region_variant",
        "splice_polypyrimidine_tract_variant",
        "incomplete_terminal_codon_variant",
        "start_retained_variant",
        "stop_retained_variant",
        "synonymous_variant",
        "coding_sequence_variant",
        "mature_miRNA_variant",
        "5_prime_UTR_variant",
        "3_prime_UTR_variant",
        "non_coding_transcript_exon_variant",
        "intron_variant",
        "NMD_transcript_variant",
        "non_coding_transcript_variant",
        "coding_transcript_variant",
        "upstream_gene_variant",
        "downstream_gene_variant",
        "TFBS_ablation",
        "TFBS_amplification",
        "TF_binding_site_variant",
        "regulatory_region_ablation",
        "regulatory_region_amplification",
        "regulatory_region_variant",
        "intergenic_variant",
        "sequence_variant",
    ])
}}
_CONSEQUENCE_WORST = len(CONSEQUENCE_RANK) + 1


def _csq_severity(consequence):
    """Most-severe rank among the &-joined consequence terms of one CSQ block.

    VEP joins multiple terms with '&' (e.g. 'missense_variant&splice_region_variant').
    Returns the lowest (= most severe) rank; unknown terms sort last.
    """
    best = _CONSEQUENCE_WORST
    for term in str(consequence).split("&"):
        r = CONSEQUENCE_RANK.get(term, _CONSEQUENCE_WORST)
        if r < best:
            best = r
    return best


def _pick_csq(csq_blocks, csq_fields):
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


'''.format(marker=MARKER)

HELPER_ANCHOR = "def parse_vep_csq(vep_vcf):\n"

# ----------------------------------------------------------------------------
# Edit 3: replace the single-block selection inside parse_vep_csq().
# We replace the exact CSQ-handling stanza (the comment + first_csq line +
# the value/loop), swapping in a parse-all-then-select implementation.
# ----------------------------------------------------------------------------
OLD_SELECT = '''            csq_data = {}
            for field in info.split(";"):
                if field.startswith("CSQ="):
                    csq_str = field[4:]
                    # --pick gives us one annotation; comma-split and
                    # keep the first to be defensive.
                    first_csq = csq_str.split(",")[0]
                    values = first_csq.split("|")
                    for i, val in enumerate(values):
                        if i < len(csq_fields):
                            csq_data[csq_fields[i]] = val
                    break
'''

NEW_SELECT = '''            csq_data = {}
            for field in info.split(";"):
                if field.startswith("CSQ="):
                    csq_str = field[4:]
                    # [%s]
                    # --flag_pick emits every transcript consequence (comma-
                    # separated). Parse them all, then choose one by severity
                    # so an overlapping neighbour cannot mask a coding call.
                    blocks = []
                    for one in csq_str.split(","):
                        values = one.split("|")
                        d = {}
                        for i, val in enumerate(values):
                            if i < len(csq_fields):
                                d[csq_fields[i]] = val
                        blocks.append(d)
                    if blocks:
                        csq_data = _pick_csq(blocks, csq_fields)
                    break
''' % MARKER


def status(tag, msg):
    sys.stdout.write("[%s] %s\n" % (tag, msg))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true",
                    help="Write changes. Default is dry-run (shows what would change).")
    ap.add_argument("--file", default=TARGET, help="Target file (default: %s)" % TARGET)
    args = ap.parse_args()

    path = args.file
    if not os.path.isfile(path):
        status("error", "target not found: %s" % path)
        return 1

    with open(path, "r") as f:
        src = f.read()

    if MARKER in src:
        status("skip", "MARKER already present; file looks patched. No changes.")
        return 0

    problems = []
    if OLD_PICK not in src:
        problems.append('run_vep() "--pick" anchor not found (Edit 1)')
    if HELPER_ANCHOR not in src:
        problems.append('"def parse_vep_csq(" anchor not found (Edit 2)')
    if OLD_SELECT not in src:
        problems.append("single-block CSQ selection stanza not found (Edit 3)")
    if problems:
        for p in problems:
            status("error", p)
        status("error", "no changes made; anchors must match the live file exactly")
        return 2

    patched = src
    patched = patched.replace(OLD_PICK, NEW_PICK, 1)
    patched = patched.replace(HELPER_ANCHOR, HELPER_BLOCK + HELPER_ANCHOR, 1)
    patched = patched.replace(OLD_SELECT, NEW_SELECT, 1)

    # sanity: all three edits landed
    if patched == src:
        status("error", "replace produced no change; aborting")
        return 3
    if patched.count(MARKER) < 3:
        status("error", "expected 3 MARKER insertions, found %d; aborting"
               % patched.count(MARKER))
        return 3

    if not args.apply:
        status("patch", "DRY-RUN ok. 3 edits would apply:")
        status("patch", '  1. run_vep: --pick -> --flag_pick')
        status("patch", '  2. add CONSEQUENCE_RANK + _pick_csq() before parse_vep_csq()')
        status("patch", '  3. parse_vep_csq: parse all CSQ blocks, select by severity')
        status("patch", "re-run with --apply to write.")
        return 0

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = "%s.bak_flagpick_%s" % (path, ts)
    with open(backup, "w") as f:
        f.write(src)
    status("backup", backup)

    with open(path, "w") as f:
        f.write(patched)
    status("patch", "applied 3 edits to %s" % path)
    status("patch", "verify: grep -n 'flag_pick\\|CONSEQUENCE_RANK\\|_pick_csq' %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
