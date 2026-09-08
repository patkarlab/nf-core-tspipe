#!/usr/bin/env python3
"""tools/patches/2026-09-08/patch_mnv_merge_v1.py -- MARKER MNV_MERGE_V1 (N2)

Wires the MNV merge. New files (already copied into place): modules/local/mnv_merge.nf,
bin/mnv_merge.py. This patcher edits three existing files:

  workflows/tspipe.nf        include MNV_MERGE; call it on SOMATICSEQ_POSTPROCESS.out.vcf joined
                             with VARIANT_CALLING.out.mutect2_vcf / vardict_vcf; ch_somaticseq_vcf
                             now comes from MNV_MERGE
  bin/annotate.py            MNV_Note column (INFO MNV_OF / MNV_EVIDENCE / MNV_PARENT -> text)
  bin/variant_filter.py      Filter MNV_COMPONENT for tagged SNVs (after BLACKLIST in priority);
                             an MNV row inherits BLACKLIST from any blacklisted component and
                             COMMON_POLYMORPHISM when every component is common; MNV_COMPONENT in
                             the two filter-count tables

Anchors are single-line substrings that must occur exactly once ('replace_all' anchors must
occur exactly the stated number of times). All anchors are validated before anything is
written; a file that already carries the MARKER is skipped. Dry-run by default; --apply writes
with .bak_mnv_merge_v1_<timestamp> backups.

Cost: MNV_MERGE 8 + VEP_ANNOTATE 8 + everything downstream of the annotated table (~66 tasks).
"""

import argparse
import shutil
import sys
import time
from pathlib import Path

MARKER = "MNV_MERGE_V1"
TAG = "mnv_merge_v1"
REPO = Path(__file__).resolve().parents[3]

# (path, op, anchor, text[, count])   op: after | before | replace | replace_all
EDITS = [
    # ---------------------------------------------------------------- tspipe.nf
    ("workflows/tspipe.nf", "after",
     "include { SOMATICSEQ_POSTPROCESS",
     "include { MNV_MERGE              } from '../modules/local/mnv_merge'   // MARKER MNV_MERGE_V1 (N2)\n"),
    ("workflows/tspipe.nf", "replace",
     "    ch_somaticseq_vcf = SOMATICSEQ_POSTPROCESS.out.vcf",
     "    // MARKER MNV_MERGE_V1 (N2): re-join SomaticSeq-decomposed MNVs before VEP. Evidence from the\n"
     "    // Mutect2 (FilterMutectCalls) VCF -- MNV records and PGT/PID phase sets -- and VarDict MNVs.\n"
     "    MNV_MERGE(\n"
     "        SOMATICSEQ_POSTPROCESS.out.vcf\n"
     "            .join(VARIANT_CALLING.out.mutect2_vcf, by: 0)\n"
     "            .join(VARIANT_CALLING.out.vardict_vcf, by: 0),\n"
     "        ch_reference\n"
     "    )\n"
     "    ch_somaticseq_vcf = MNV_MERGE.out.vcf\n"),

    # ---------------------------------------------------------------- annotate.py
    ("bin/annotate.py", "after",
     '    "MANE_SELECT", "Canonical", "HGVSg", "Existing_variation",',
     '    "MNV_Note",   # MNV_MERGE_V1 (N2): "MNV of <positions> (<evidence>)" or "component of <chrom:pos:ref:alt>"\n'),
    ("bin/annotate.py", "after",
     '            num_tools_str = _get_info_value(info, "NUM_TOOLS")',
     "            # MNV_MERGE_V1 (N2): merged-MNV / component tags written by bin/mnv_merge.py\n"
     "            mnv_note = \"\"\n"
     "            _mnv_of = _get_info_value(info, \"MNV_OF\")\n"
     "            _mnv_parent = _get_info_value(info, \"MNV_PARENT\")\n"
     "            if _mnv_of:\n"
     "                mnv_note = \"MNV of %s (%s)\" % (_mnv_of, _get_info_value(info, \"MNV_EVIDENCE\") or \"\")\n"
     "            elif _mnv_parent:\n"
     "                mnv_note = \"component of %s\" % _mnv_parent\n"),
    ("bin/annotate.py", "after",
     '                "callers": callers,',
     '                "mnv_note": mnv_note,   # MNV_MERGE_V1\n'),
    ("bin/annotate.py", "after",
     '            "Existing_variation": _clean(vep.get("Existing_variation", "")),',
     '            "MNV_Note": _clean(vcf.get("mnv_note", "")),   # MNV_MERGE_V1 (N2)\n'),

    # ---------------------------------------------------------------- variant_filter.py
    ("bin/variant_filter.py", "after",
     '    df["Variant_Class"] = df["_consequence"].map(variant_class)   # D14 (FILTER_D14_D15_A19_V1)',
     "\n"
     "    # MNV_MERGE_V1 (N2): components of a merged MNV are demoted to MNV_COMPONENT; the MNV row\n"
     "    # inherits BLACKLIST from any blacklisted component and COMMON_POLYMORPHISM when every\n"
     "    # component is common (a merged allele rarely matches a gnomAD record on its own).\n"
     "    _mnv_notes = df[\"MNV_Note\"].astype(str).str.strip() if \"MNV_Note\" in df.columns else pd.Series([\"\"] * len(df), index=df.index)\n"
     "    _bl_col = df[\"Blacklist_Reason\"].astype(str).str.strip() if \"Blacklist_Reason\" in df.columns else pd.Series([\"\"] * len(df), index=df.index)\n"
     "    _mnv_comp_af = {}\n"
     "    _mnv_comp_bl = {}\n"
     "    for _i in range(len(df)):\n"
     "        _n = _mnv_notes.iloc[_i]\n"
     "        if _n.startswith(\"component of \"):\n"
     "            _p = _n[len(\"component of \"):]\n"
     "            _mnv_comp_af.setdefault(_p, []).append(df[\"_max_af\"].iloc[_i])\n"
     "            if _bl_col.iloc[_i]:\n"
     "                _mnv_comp_bl.setdefault(_p, []).append(_bl_col.iloc[_i])\n"
     "    _mnv_common = {p for p, afs in _mnv_comp_af.items() if afs and all((not np.isnan(a)) and a > 0.01 for a in afs)}\n"
     "    if _mnv_comp_af:\n"
     "        log.info(\"MNV_MERGE_V1: %d merged MNV(s) with components; %d inherit BLACKLIST, %d inherit COMMON_POLYMORPHISM\",\n"
     "                 len(_mnv_comp_af), len(_mnv_comp_bl), len(_mnv_common))\n"),
    ("bin/variant_filter.py", "after",
     '            filters.append("BLACKLIST")\n            continue',
     "\n"
     "        # MNV_MERGE_V1 (N2): component SNVs of a merged MNV; MNV inheritance from components\n"
     "        _mnv_note = str(row.get(\"MNV_Note\", \"\")).strip()\n"
     "        if _mnv_note.startswith(\"component of \"):\n"
     "            filters.append(\"MNV_COMPONENT\")\n"
     "            continue\n"
     "        if _mnv_note.startswith(\"MNV of \"):\n"
     "            _mnv_key = \"%s:%s:%s:%s\" % (row[\"Chr\"], row[\"Start\"], row[\"Ref\"], row[\"Alt\"])\n"
     "            if _mnv_key in _mnv_comp_bl:\n"
     "                df.at[_, \"Blacklist_Reason\"] = \"MNV|INHERITED_FROM_COMPONENT|\" + _mnv_comp_bl[_mnv_key][0].replace(\"|\", \"/\")\n"
     "                filters.append(\"BLACKLIST\")\n"
     "                continue\n"
     "            if _mnv_key in _mnv_common:\n"
     "                filters.append(\"COMMON_POLYMORPHISM\")\n"
     "                continue\n"),
    ("bin/variant_filter.py", "replace_all",
     '                 "LOW_CALLERS", "LOW_DEPTH", "NO_CALLER_INFO"]:',
     '                 "LOW_CALLERS", "LOW_DEPTH", "NO_CALLER_INFO", "MNV_COMPONENT"]:   # MNV_MERGE_V1\n',
     2),
]


def find_lines(lines, anchor):
    """Indices of lines containing the anchor; multi-line anchors match a contiguous block start."""
    if "\n" in anchor:
        parts = anchor.split("\n")
        hits = []
        for i in range(len(lines) - len(parts) + 1):
            if all(parts[k] in lines[i + k] for k in range(len(parts))):
                hits.append(i)
        return hits, len(parts)
    return [i for i, l in enumerate(lines) if anchor in l], 1


def plan(repo):
    by_file = {}
    for e in EDITS:
        by_file.setdefault(e[0], []).append(e)
    out = {}
    for rel, edits in by_file.items():
        p = repo / rel
        if not p.exists():
            raise RuntimeError("missing file: %s" % p)
        src = p.read_text()
        if MARKER in src:
            print("[skip]   %s already carries %s" % (rel, MARKER))
            continue
        lines = src.splitlines(keepends=True)
        for e in edits:
            op, anchor = e[1], e[2]
            hits, span = find_lines(lines, anchor)
            want = e[4] if op == "replace_all" else 1
            if len(hits) != want:
                raise RuntimeError("%s: anchor matched %d (need %d): %r" % (rel, len(hits), want, anchor))
        for e in edits:
            op, anchor, text = e[1], e[2], e[3]
            hits, span = find_lines(lines, anchor)
            new = text.splitlines(keepends=True)
            if op == "after":
                i = hits[0]
                lines[i + span:i + span] = new
            elif op == "before":
                lines[hits[0]:hits[0]] = new
            elif op == "replace":
                i = hits[0]
                lines[i:i + span] = new
            elif op == "replace_all":
                for i in reversed(hits):
                    lines[i:i + span] = new
            else:
                raise RuntimeError("bad op %s" % op)
        out[rel] = "".join(lines)
        print("[patch]  %s: %d edit(s)" % (rel, len(edits)))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--apply", action="store_true", help="write files (default: dry-run)")
    ap.add_argument("--repo", default=str(REPO))
    args = ap.parse_args()
    repo = Path(args.repo)
    try:
        planned = plan(repo)
    except RuntimeError as exc:
        print("[error]  %s\n[error]  nothing written" % exc)
        return 1
    if not planned:
        print("[done]   nothing to do")
        return 0
    if not args.apply:
        print("[dry]    %d file(s) would change; re-run with --apply" % len(planned))
        return 0
    ts = time.strftime("%Y%m%d_%H%M%S")
    for rel, new in planned.items():
        p = repo / rel
        bak = p.with_name(p.name + ".bak_%s_%s" % (TAG, ts))
        shutil.copy2(p, bak)
        print("[backup] %s" % bak.relative_to(repo))
        p.write_text(new)
        print("[write]  %s" % rel)
    print("[done]   %d file(s) patched with %s" % (len(planned), MARKER))
    return 0


if __name__ == "__main__":
    sys.exit(main())
