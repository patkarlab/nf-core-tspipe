#!/usr/bin/env python3
"""tools/patches/<date>/patch_annovar_key_v1.py -- MARKER ANNOVAR_KEY_V1 (A18)

bin/annotate.py merges SomaticSeq VCF fields, VEP and ANNOVAR on a chr:pos:ref:alt
key built per source. ANNOVAR writes indels in its own representation (start
shifted past the anchor base, '-' for the absent allele: chr11 119278646 ATG -),
while the VCF record is chr11 119278645 TATG T. The keys differ for essentially
every indel, so ~12% of rows per run8 sample (~730 of 6,000) are caller-less
ANNOVAR orphans and the primary indel rows carry no ClinVar, COSMIC_ID or
ANNOVAR gnomAD/1KG values (Max_AF and rsID come from VEP and are unaffected).

Fix: table_annovar.pl is run with -vcfinput, which appends the original VCF
record to each multianno row as Otherinfo columns. parse_annovar_txt() now keys
each row on those VCF fields (CHROM POS ID REF ALT, located by pattern: the
first Otherinfo column equal to the row's Chr followed by an integer), falling
back to the old ANNOVAR key when no Otherinfo is present. merge_annotations()
logs how many ANNOVAR rows matched a VCF record and how many are orphans.
modules/local/vep_annotate.nf gets a bash-comment bump (bin/ is unhashed).

Verification (offline, no Nextflow): tools/patches/<date>/check_annovar_key.py
runs old and new keying on a cached VEP_ANNOTATE task directory.

Usage:  python3 <this file> [--apply]
Guard:  MARKER ANNOVAR_KEY_V1 per file; each anchor exactly once; all-or-nothing.
"""

import argparse
import sys
import time
from pathlib import Path

MARKER = "ANNOVAR_KEY_V1"
TAG = "annovar_key_v1"
REPO = Path(__file__).resolve().parents[3]
PY = "bin/annotate.py"
NF = "modules/local/vep_annotate.nf"

PY_KEY_OLD = (
    '            chrom = row.get("Chr", "")\n'
    '            pos = row.get("Start", "")\n'
    '            ref = row.get("Ref", "")\n'
    '            alt = row.get("Alt", "")\n'
    '            key = "{0}:{1}:{2}:{3}".format(chrom, pos, ref, alt)\n'
    '            variants[key] = row\n'
)
PY_KEY_NEW = (
    '            key = _annovar_vcf_key(row)   # ANNOVAR_KEY_V1 (A18): key on the VCF record when present\n'
    '            if key is None:\n'
    '                chrom = row.get("Chr", "")\n'
    '                pos = row.get("Start", "")\n'
    '                ref = row.get("Ref", "")\n'
    '                alt = row.get("Alt", "")\n'
    '                key = "{0}:{1}:{2}:{3}".format(chrom, pos, ref, alt)\n'
    '                _ANNOVAR_KEY_STATS["fallback"] += 1\n'
    '            else:\n'
    '                _ANNOVAR_KEY_STATS["vcf"] += 1\n'
    '            variants[key] = row\n'
)
PY_LOG_OLD = '    log.info("Parsed %d variants from ANNOVAR txt", len(variants))\n'
PY_LOG_NEW = (
    '    log.info("Parsed %d variants from ANNOVAR txt (%d keyed on the VCF record, %d on ANNOVAR coordinates)",\n'
    '             len(variants), _ANNOVAR_KEY_STATS["vcf"], _ANNOVAR_KEY_STATS["fallback"])   # ANNOVAR_KEY_V1\n'
)
PY_HELPER_ANCHOR = "def parse_annovar_txt(annovar_txt):\n"
PY_HELPER_NEW = """_ANNOVAR_KEY_STATS = {"vcf": 0, "fallback": 0}   # ANNOVAR_KEY_V1


def _annovar_vcf_key(row):
    \"\"\"ANNOVAR_KEY_V1 (A18): chr:pos:ref:alt from the -vcfinput Otherinfo columns, or None.

    ANNOVAR writes indels in its own representation (start past the anchor base,
    '-' for the absent allele: chr11 119278646 ATG -) while the VCF record is
    chr11 119278645 TATG T, so keys built from ANNOVAR's Chr/Start/Ref/Alt never
    match the VCF/VEP key for indels. With -vcfinput, table_annovar.pl appends
    the input VCF record to each row as Otherinfo columns (... CHROM POS ID REF
    ALT QUAL FILTER INFO FORMAT sample). The number of bookkeeping columns before
    CHROM varies between ANNOVAR versions, so CHROM is located by pattern: the
    first Otherinfo column equal to the row's Chr whose successor is an integer.
    \"\"\"
    chrom = (row.get("Chr", "") or "").strip()
    if not chrom:
        return None
    cols = [c for c in row.keys() if c and c.startswith("Otherinfo")]
    try:
        cols.sort(key=lambda c: int(c[len("Otherinfo"):] or 0))
    except ValueError:
        cols.sort()
    for i in range(len(cols) - 4):
        v = (row.get(cols[i]) or "").strip()
        if v != chrom and v != chrom.replace("chr", "") and ("chr" + v) != chrom:
            continue
        pos = (row.get(cols[i + 1]) or "").strip()
        if not pos.isdigit():
            continue
        ref = (row.get(cols[i + 3]) or "").strip()
        alt = (row.get(cols[i + 4]) or "").strip()
        if not ref or not alt or ref == "." or alt == ".":
            continue
        return "{0}:{1}:{2}:{3}".format(chrom, pos, ref, alt)
    return None


"""

PY_MERGE_OLD = "    all_keys = set(vcf_fields.keys()) | set(vep_variants.keys()) | set(annovar_variants.keys())\n"
PY_MERGE_NEW = PY_MERGE_OLD + '''    # ANNOVAR_KEY_V1 (A18): merge diagnostics -- an ANNOVAR row that matches no VCF record is an
    # orphan (it carries no caller evidence and is discarded downstream); a VCF record with no
    # ANNOVAR row has lost ClinVar / COSMIC / ANNOVAR gnomAD for that variant.
    _ann_keys = set(annovar_variants.keys())
    _vcf_keys = set(vcf_fields.keys())
    _orphans = _ann_keys - _vcf_keys
    _unannotated = _vcf_keys - _ann_keys
    log.info("ANNOVAR merge: %d rows, %d matched a VCF record, %d orphan ANNOVAR rows, %d VCF records without ANNOVAR",
             len(_ann_keys), len(_ann_keys & _vcf_keys), len(_orphans), len(_unannotated))
    if _vcf_keys and len(_orphans) > 0.02 * len(_vcf_keys):
        log.warning("ANNOVAR merge: %.1f%% orphan rows -- key mismatch between ANNOVAR and the VCF (see A18)",
                    100.0 * len(_orphans) / len(_vcf_keys))
'''

NF_OLD = "        \"\"\"\n        annotate.py \\\\\n"
NF_NEW = (
    "        \"\"\"\n"
    "        # annotate.py ANNOVAR_KEY_V1: ANNOVAR rows keyed on the VCF record (bash comment; busts the task cache)\n"
    "        annotate.py \\\\\n"
)

EDITS = [(PY, PY_HELPER_ANCHOR, PY_HELPER_NEW + PY_HELPER_ANCHOR), (PY, PY_KEY_OLD, PY_KEY_NEW),
         (PY, PY_LOG_OLD, PY_LOG_NEW), (PY, PY_MERGE_OLD, PY_MERGE_NEW), (NF, NF_OLD, NF_NEW)]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    staged, skipped, errors = {}, [], []
    for rel, old, new in EDITS:
        if rel in skipped:
            continue
        p = REPO / rel
        if rel not in staged:
            if not p.exists():
                errors.append("%s: file not found" % rel); continue
            text = p.read_text()
            if MARKER in text:
                print("SKIP  %s: %s already present" % (rel, MARKER)); skipped.append(rel); continue
            staged[rel] = text
        n = staged[rel].count(old)
        if n != 1:
            errors.append("%s: anchor matched %d times (need 1): %r" % (rel, n, old[:70])); continue
        staged[rel] = staged[rel].replace(old, new, 1)
    if errors:
        print("ABORT -- nothing written:")
        for e in errors:
            print("  " + e)
        sys.exit(1)
    for rel, text in staged.items():
        print("PLAN  %s: %+d lines, marker %s" % (rel, text.count("\n") - (REPO / rel).read_text().count("\n"), MARKER))
    if not args.apply:
        print("dry run; re-run with --apply"); return
    stamp = time.strftime("%Y%m%d_%H%M%S")
    for rel, text in staged.items():
        p = REPO / rel
        bak = p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp))
        bak.write_text(p.read_text()); p.write_text(text)
        print("WROTE %s (backup %s)" % (rel, bak.name))
    print("done")


if __name__ == "__main__":
    main()
