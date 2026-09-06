#!/usr/bin/env python3
"""
tools/patches/2026-09-06/patch_variant_filter_consequence.py

Add a NON_REPORTABLE_CONSEQUENCE filter to bin/variant_filter.py (MARKER
consequence_filter). Evidence: across 24 female normals, 229 of 382 clinical
rows were synonymous, intron-only or non-coding-transcript consequences that
VEP labels LOW rather than MODIFIER, so the LOW_IMPACT rule passed them.

Rule (agreed 2026-09-06):
  keep   missense, stop gained/lost, start lost, frameshift, in-frame
         insertion/deletion, protein-altering, coding-sequence, canonical
         splice site (splice_acceptor / splice_donor)
  drop   synonymous, intron-only (incl. splice_polypyrimidine_tract and
         splice_region without a coding term), UTR, non-coding transcript
  keep regardless of consequence
         ClinVar Pathogenic / Likely_pathogenic (not conflicting, not benign)
         hotspot residue match (Gene + protein position) against
         myeloid_hotspots.tsv rows of type residue / specific_aa / residue_a_b

Priority: after COMMON_POLYMORPHISM and LOW_IMPACT, before LOW_CALLERS.
Filtered rows stay in the filtered TSV with Filter=NON_REPORTABLE_CONSEQUENCE.

Hotspot table location: $TSPIPE_HOTSPOTS if set, else the first existing of
  <repo>/assets/myeloid_hotspots.tsv, <repo>/assets/myeloid/myeloid_hotspots.tsv,
  <repo>/references/myeloid/myeloid_hotspots.tsv. Missing table = override
  disabled with a log line (never an error).

Dry-run by default; --apply writes with a timestamped backup. Idempotent.
Python 3.6-safe.
"""
import argparse
import datetime
import os
import re
import shutil
import sys

TARGET = "bin/variant_filter.py"
TAG = "csqfilter"
MARKER = "MARKER consequence_filter"

# ---- anchor 1: docstring line ------------------------------------------------
DOC_OLD = "      LOW_IMPACT:          IMPACT == \"MODIFIER\" and not in splice region\n"
DOC_NEW = (
    "      LOW_IMPACT:          IMPACT == \"MODIFIER\" and not in splice region\n"
    "      NON_REPORTABLE_CONSEQUENCE:\n"
    "                           no coding non-synonymous or canonical-splice term\n"
    "                           (synonymous, intron-only, UTR, non-coding transcript),\n"
    "                           unless ClinVar P/LP or a hotspot residue (MARKER consequence_filter)\n"
)

# ---- anchor 2: helpers inserted before apply_filters -------------------------
FUNC_ANCHOR = "def apply_filters(df):\n"
FUNC_NEW = '''# ---------------------------------------------------------------------------
# MARKER consequence_filter: reportable-consequence rule and overrides
# ---------------------------------------------------------------------------

REPORTABLE_CONSEQUENCES = {
    "missense_variant", "stop_gained", "stop_lost", "start_lost",
    "frameshift_variant", "inframe_insertion", "inframe_deletion",
    "protein_altering_variant", "coding_sequence_variant",
    "incomplete_terminal_codon_variant", "transcript_ablation",
    "splice_acceptor_variant", "splice_donor_variant",
}

_HOTSPOT_CACHE = {"loaded": False, "table": {}}


def _hotspot_table_path():
    import os as _os
    env = _os.environ.get("TSPIPE_HOTSPOTS", "")
    if env and _os.path.isfile(env):
        return env
    for rel in ("assets/myeloid_hotspots.tsv",
                "assets/myeloid/myeloid_hotspots.tsv",
                "references/myeloid/myeloid_hotspots.tsv"):
        p = _os.path.join(PIPELINE_DIR, rel)
        if _os.path.isfile(p):
            return p
    return None


def _load_hotspots():
    """Gene -> list of (lo, hi) residue ranges from myeloid_hotspots.tsv."""
    import re as _re
    if _HOTSPOT_CACHE["loaded"]:
        return _HOTSPOT_CACHE["table"]
    _HOTSPOT_CACHE["loaded"] = True
    path = _hotspot_table_path()
    table = {}
    if not path:
        log.info("Hotspot table not found; hotspot override disabled (set TSPIPE_HOTSPOTS)")
        return table
    with open(path) as fh:
        header = fh.readline().rstrip("\\n").split("\\t")
        try:
            gi, hi, mi = header.index("Gene"), header.index("Hotspot"), header.index("Match_Type")
        except ValueError:
            log.info("Hotspot table %s lacks Gene/Hotspot/Match_Type; override disabled", path)
            return table
        for line in fh:
            parts = line.rstrip("\\n").split("\\t")
            if len(parts) <= max(gi, hi, mi):
                continue
            gene, spot, mtype = parts[gi].strip(), parts[hi].strip(), parts[mi].strip()
            if mtype in ("residue", "specific_aa"):
                m = _re.match(r"^[A-Z]?(\\d+)", spot)
                if m:
                    pos = int(m.group(1))
                    table.setdefault(gene, []).append((pos, pos))
            elif mtype.startswith("residue_"):
                m = _re.match(r"^residue_(\\d+)_(\\d+)$", mtype)
                if m:
                    table.setdefault(gene, []).append((int(m.group(1)), int(m.group(2))))
    _HOTSPOT_CACHE["table"] = table
    log.info("Hotspot override: %d genes from %s", len(table), path)
    return table


def _protein_position(hgvsp):
    """Residue number from an HGVSp string, or None."""
    import re as _re
    s = str(hgvsp or "")
    m = _re.search(r"p\\.\\(?[A-Za-z]{1,3}(\\d+)", s)
    return int(m.group(1)) if m else None


def is_hotspot_residue(gene, hgvsp):
    table = _load_hotspots()
    ranges = table.get(str(gene).strip())
    if not ranges:
        return False
    pos = _protein_position(hgvsp)
    if pos is None:
        return False
    return any(lo <= pos <= hi for lo, hi in ranges)


def is_clinvar_pathogenic(clinvar):
    s = str(clinvar or "").strip().lower()
    if not s or s in ("-1", "nan", "."):
        return False
    if "conflicting" in s:
        return False
    if "pathogenic" not in s:
        return False
    # "benign/likely_benign" contains no "pathogenic"; "likely_pathogenic",
    # "pathogenic", "pathogenic/likely_pathogenic" all qualify
    return True


def is_reportable_consequence(consequence):
    terms = set(t.strip() for t in str(consequence or "").lower().split("&"))
    return bool(terms & REPORTABLE_CONSEQUENCES)


'''

# ---- anchor 3: filter block inserted after LOW_IMPACT ------------------------
BLOCK_ANCHOR = (
    "        # Priority 2: Low impact (MODIFIER, not splice)\n"
    "        if row[\"_impact\"] == \"MODIFIER\":\n"
    "            csq = row[\"_consequence\"].lower()\n"
    "            if \"splice\" not in csq:\n"
    "                filters.append(\"LOW_IMPACT\")\n"
    "                continue\n"
)
BLOCK_NEW = BLOCK_ANCHOR + (
    "\n"
    "        # Priority 2b (MARKER consequence_filter): reportable consequence only,\n"
    "        # unless ClinVar P/LP or a hotspot residue\n"
    "        if not is_reportable_consequence(row[\"_consequence\"]):\n"
    "            if not (is_clinvar_pathogenic(row.get(\"ClinVar\", \"\"))\n"
    "                    or is_hotspot_residue(row.get(\"Gene\", \"\"), row.get(\"HGVSp\", \"\"))):\n"
    "                filters.append(\"NON_REPORTABLE_CONSEQUENCE\")\n"
    "                continue\n"
)

# ---- anchor 4: report lists (regex, all occurrences) -------------------------
LIST_RE = re.compile(r'"LOW_IMPACT",(\s*)"LOW_CALLERS"')
LIST_SUB = r'"LOW_IMPACT", "NON_REPORTABLE_CONSEQUENCE",\1"LOW_CALLERS"'


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--apply", action="store_true", help="write changes (default: dry-run)")
    p.add_argument("--repo", default=".", help="repository root")
    args = p.parse_args()

    path = os.path.join(args.repo, TARGET)
    if not os.path.isfile(path):
        print("[error] not found: {}".format(path))
        return 1
    with open(path) as fh:
        text = fh.read()

    if MARKER in text:
        print("[skip] {} already patched ({} present)".format(TARGET, MARKER))
        return 0

    problems = []
    if text.count(DOC_OLD) != 1:
        problems.append("docstring anchor found {} times".format(text.count(DOC_OLD)))
    if text.count(FUNC_ANCHOR) != 1:
        problems.append("apply_filters anchor found {} times".format(text.count(FUNC_ANCHOR)))
    if text.count(BLOCK_ANCHOR) != 1:
        problems.append("LOW_IMPACT block anchor found {} times".format(text.count(BLOCK_ANCHOR)))
    n_lists = len(LIST_RE.findall(text))
    if n_lists < 1:
        problems.append("filter-list pattern not found")
    if "PIPELINE_DIR" not in text:
        problems.append("PIPELINE_DIR not defined in target (hotspot path lookup needs it)")
    if problems:
        for pr in problems:
            print("[error] " + pr)
        print("[error] read the file from disk and update the anchors")
        return 1

    new = text.replace(DOC_OLD, DOC_NEW, 1)
    new = new.replace(FUNC_ANCHOR, FUNC_NEW + FUNC_ANCHOR, 1)
    new = new.replace(BLOCK_ANCHOR, BLOCK_NEW, 1)
    new, n_sub = LIST_RE.subn(LIST_SUB, new)

    if not args.apply:
        print("[dry-run] would patch {}: docstring, helpers, filter block, {} report list(s)".format(TARGET, n_sub))
        print("[dry-run] re-run with --apply to write")
        return 0

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = "{}.bak_{}_{}".format(path, TAG, stamp)
    shutil.copy2(path, backup)
    print("[backup] {}".format(backup))
    with open(path, "w") as fh:
        fh.write(new)
    print("[patch] {}: NON_REPORTABLE_CONSEQUENCE added ({} report lists updated)".format(TARGET, n_sub))
    return 0


if __name__ == "__main__":
    sys.exit(main())
