#!/usr/bin/env python3
"""tools/patches/<date>/patch_filter_syn_benign_cosmic_v1.py -- MARKER FILTER_D14_D15_A19_V1

Three changes on the annotation-to-clinical path, one VARIANT_FILTER/VEP_ANNOTATE re-run.

D14  bin/variant_filter.py: `synonymous_variant` joins REPORTABLE_CONSEQUENCES. Every row gets a
     `Variant_Class` column (nonsynonymous | splice | synonymous | other) so the clinical table
     and reporting tab can group synonymous calls separately.
D15  bin/variant_filter.py: new filter CLINVAR_BENIGN, applied after COMMON_POLYMORPHISM /
     LOW_IMPACT and before the consequence rule: ClinVar exactly Benign, Likely_benign or
     Benign/Likely_benign (no "conflicting", "pathogenic" or "uncertain" in the string) demotes
     the row unless it is a hotspot residue. Counted in both filter tallies.
A19  bin/annotate.py: COSMIC_ID taken from VEP Existing_variation (COSV*/COSM* tokens, joined by
     '&') because the ANNOVAR cosmic103 table carries occurrence counts, not identifiers; the
     ANNOVAR value is used only when it looks like an identifier.
Module bumps: variant_filter.nf (bash comment), vep_annotate.nf (extends the A18 comment).

Usage:  python3 <this file> [--apply]
Guard:  MARKER per file; anchors are blank-line-free; all-or-nothing.
"""

import argparse
import sys
import time
from pathlib import Path

MARKER = "FILTER_D14_D15_A19_V1"
TAG = "filter_d14_d15_a19_v1"
REPO = Path(__file__).resolve().parents[3]
VF = "bin/variant_filter.py"
AN = "bin/annotate.py"
NF_VF = "modules/local/variant_filter.nf"
NF_AN = "modules/local/vep_annotate.nf"

# ---- variant_filter.py ----------------------------------------------------
VF_SET_OLD = '    "splice_acceptor_variant", "splice_donor_variant",\n}\n'
VF_SET_NEW = (
    '    "splice_acceptor_variant", "splice_donor_variant",\n'
    '    "synonymous_variant",   # D14 (FILTER_D14_D15_A19_V1): coding synonymous are reportable, tagged in Variant_Class\n'
    '}\n'
    '\n'
    'NONSYNONYMOUS_TERMS = {   # D14: terms that make a row "nonsynonymous" for Variant_Class\n'
    '    "missense_variant", "stop_gained", "stop_lost", "start_lost", "frameshift_variant",\n'
    '    "inframe_insertion", "inframe_deletion", "protein_altering_variant",\n'
    '    "incomplete_terminal_codon_variant", "transcript_ablation",\n'
    '}\n'
    'SPLICE_TERMS = {"splice_acceptor_variant", "splice_donor_variant"}\n'
)

VF_HELPERS_ANCHOR = "def is_reportable_consequence(consequence):\n"
VF_HELPERS_NEW = '''def is_clinvar_benign(clinvar):
    """D15: True for ClinVar Benign / Likely_benign / Benign/Likely_benign only."""
    s = str(clinvar or "").strip().lower()
    if not s or s in ("-1", "nan", "."):
        return False
    if "conflicting" in s or "pathogenic" in s or "uncertain" in s:
        return False
    return "benign" in s


def variant_class(consequence):
    """D14: nonsynonymous | splice | synonymous | other, from the VEP consequence terms."""
    terms = set(t.strip() for t in str(consequence or "").lower().split("&"))
    if terms & NONSYNONYMOUS_TERMS:
        return "nonsynonymous"
    if terms & SPLICE_TERMS:
        return "splice"
    if "synonymous_variant" in terms:
        return "synonymous"
    return "other"


'''

VF_DOC_OLD = (
    "      NON_REPORTABLE_CONSEQUENCE:\n"
    "                           no coding non-synonymous or canonical-splice term\n"
    "                           (synonymous, intron-only, UTR, non-coding transcript),\n"
    "                           unless ClinVar P/LP or a hotspot residue (MARKER consequence_filter)\n"
)
VF_DOC_NEW = (
    "      CLINVAR_BENIGN:      ClinVar Benign / Likely_benign, unless a hotspot residue (D15)\n"
    "      NON_REPORTABLE_CONSEQUENCE:\n"
    "                           no coding term (non-synonymous, synonymous since D14) and no\n"
    "                           canonical-splice term (intron-only, UTR, non-coding transcript),\n"
    "                           unless ClinVar P/LP or a hotspot residue (MARKER consequence_filter)\n"
)

VF_CLASS_ANCHOR = '    df["_consequence"] = df["Consequence"].astype(str).str.strip()\n'
VF_CLASS_NEW = VF_CLASS_ANCHOR + '    df["Variant_Class"] = df["_consequence"].map(variant_class)   # D14 (FILTER_D14_D15_A19_V1)\n'

VF_RULE_OLD = '        if not is_reportable_consequence(row["_consequence"]):\n'
VF_RULE_NEW = (
    '        # Priority 2a (D15 CLINVAR_BENIGN): ClinVar Benign / Likely_benign demotes, unless a hotspot residue\n'
    '        if is_clinvar_benign(row.get("ClinVar", "")) and not is_hotspot_residue(row.get("Gene", ""), row.get("HGVSp", "")):\n'
    '            filters.append("CLINVAR_BENIGN")\n'
    '            continue\n'
    '\n'
    '        if not is_reportable_consequence(row["_consequence"]):\n'
)

VF_TALLY_OLD = '    for filt in ["PASS", "BLACKLIST", "COMMON_POLYMORPHISM", "LOW_IMPACT", "NON_REPORTABLE_CONSEQUENCE",\n'
VF_TALLY_NEW = '    for filt in ["PASS", "BLACKLIST", "COMMON_POLYMORPHISM", "LOW_IMPACT", "CLINVAR_BENIGN", "NON_REPORTABLE_CONSEQUENCE",\n'

# ---- annotate.py (A19) ----------------------------------------------------
AN_HELPER_ANCHOR = "def _clean(val):\n"
AN_HELPER_NEW = '''def _cosmic_id(annovar_val, existing_variation):
    """A19 (FILTER_D14_D15_A19_V1): COSMIC identifier(s) for the merged row.

    The ANNOVAR cosmic103 table in use carries occurrence counts ('1', '10'), not
    identifiers, so the ANNOVAR value is used only when it looks like one. VEP's
    Existing_variation lists COSV/COSM identifiers alongside rsIDs; those are
    taken, joined by '&'. Returns '-1' when nothing is found.
    """
    a = str(annovar_val or "").strip()
    if a.upper().startswith(("COSV", "COSM", "COSN")):
        return a
    ids = [t for t in str(existing_variation or "").replace(",", "&").split("&")
           if t.strip().upper().startswith(("COSV", "COSM", "COSN"))]
    return "&".join(t.strip() for t in ids) if ids else "-1"


'''
AN_COSMIC_OLD = '            "COSMIC_ID": _clean(ann.get("cosmic103", "")),\n'
AN_COSMIC_NEW = '            "COSMIC_ID": _cosmic_id(ann.get("cosmic103", ""), vep.get("Existing_variation", "")),   # A19\n'

# ---- module bumps -----------------------------------------------------------
NF_VF_OLD = "        variant_filter.py \\\\\n"
NF_VF_NEW = (
    "        # variant_filter.py FILTER_D14_D15_A19_V1: synonymous reportable + Variant_Class, CLINVAR_BENIGN (bash comment; busts the task cache)\n"
    "        variant_filter.py \\\\\n"
)
NF_AN_OLD = "        # annotate.py ANNOVAR_KEY_V1: ANNOVAR rows keyed on the VCF record (bash comment; busts the task cache)\n"
NF_AN_NEW = "        # annotate.py ANNOVAR_KEY_V1: ANNOVAR rows keyed on the VCF record; A19 COSMIC_ID from VEP Existing_variation (bash comment; busts the task cache)\n"

# (path, old, new, expected count)
EDITS = [
    (VF, VF_SET_OLD, VF_SET_NEW, 1),
    (VF, VF_HELPERS_ANCHOR, VF_HELPERS_NEW + VF_HELPERS_ANCHOR, 1),
    (VF, VF_DOC_OLD, VF_DOC_NEW, 1),
    (VF, VF_CLASS_ANCHOR, VF_CLASS_NEW, 1),
    (VF, VF_RULE_OLD, VF_RULE_NEW, 1),
    (VF, VF_TALLY_OLD, VF_TALLY_NEW, 2),
    (AN, AN_HELPER_ANCHOR, AN_HELPER_NEW + AN_HELPER_ANCHOR, 1),
    (AN, AN_COSMIC_OLD, AN_COSMIC_NEW, 1),
    (NF_VF, NF_VF_OLD, NF_VF_NEW, 1),
    (NF_AN, NF_AN_OLD, NF_AN_NEW, 1),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    staged, skipped, errors = {}, [], []
    for rel, old, new, want in EDITS:
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
        if n != want:
            errors.append("%s: anchor matched %d times (need %d): %r" % (rel, n, want, old[:70])); continue
        staged[rel] = staged[rel].replace(old, new)
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
