#!/usr/bin/env python3
"""
patch_publish_clinical_v2.py -- supersedes PUBLISH_CLINICAL_V1
(MARKER PUBLISH_CLINICAL_V2).

V1 published the consensus, DECON and sex_check tables into
<outdir>/<sample>/clinical/<subdir>/. That directory is materialised whole by
ORGANIZE_OUTPUT (publishDir of its clinical/ output, copy mode), which
replaces the target and wiped the earlier copies; the stub run showed it.
Until ORGANIZE_OUTPUT routes these files itself (with the item 12 layout
change), they publish at sample level in directories the main.nf sweep
does not touch, beside cnv_baf/, cnv_gatk/ and purecn/:

    CNV_CONSENSUS_MULTI -> <outdir>/<sample>/cnv_consensus_multi/
    DECON               -> <outdir>/<sample>/cnv_decon/
    SEX_CHECK           -> <outdir>/<sample>/sex_check/

Mode stays 'copy' (small files; no symlink-downgrade risk).
Requires PUBLISH_CLINICAL_V1. Dry run by default; --apply writes with
.bak_publish_clinical_v2_<ts> backups.
"""

import argparse
import datetime
import os
import re
import shutil
import sys

MARKER_V1 = "MARKER PUBLISH_CLINICAL_V1"
MARKER = "MARKER PUBLISH_CLINICAL_V2"
NOTE = "// %s: sample-level, outside the main.nf sweep list; moves under clinical/ when ORGANIZE_OUTPUT routes it (item 12)" % MARKER

EDITS = {
    "conf/twist_apply.config": [
        (r'/clinical/cnv_consensus" \},', '/cnv_consensus_multi" },', "consensus path"),
        (r'/clinical/cnv_decon" \},',     '/cnv_decon" },',           "DECON path"),
    ],
    "conf/modules.config": [
        (r'/clinical/sex_check" \},',     '/sex_check" },',           "SEX_CHECK path"),
    ],
}


def patch(text, edits):
    notes = []
    for pat, rep, label in edits:
        rx = re.compile(pat)
        n = len(rx.findall(text))
        if n != 1:
            raise ValueError("anchor %s: expected 1, found %d" % (label, n))
        text = rx.sub(rep, text, count=1)
        notes.append("[ok] %s" % label)
    v1_lines = re.findall(r"^[ \t]*// %s:.*$" % MARKER_V1, text, re.M)
    if len(v1_lines) != len(edits):
        raise ValueError("expected %d %s note lines, found %d" % (len(edits), MARKER_V1, len(v1_lines)))
    text = re.sub(r"^(?P<i>[ \t]*)// %s:.*$" % MARKER_V1, lambda m: m.group("i") + NOTE, text, flags=re.M)
    notes.append("[ok] %d note line(s) updated" % len(v1_lines))
    return text, notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    planned, failed = [], False
    for rel, edits in EDITS.items():
        path = os.path.join(args.root, rel)
        print("== %s" % rel)
        if not os.path.isfile(path):
            print("   [error] file not found"); failed = True; continue
        original = open(path).read()
        if MARKER in original:
            print("   [skip] %s already present" % MARKER); continue
        if MARKER_V1 not in original:
            print("   [error] %s not present; nothing to supersede" % MARKER_V1); failed = True; continue
        try:
            new_text, notes = patch(original, edits)
        except ValueError as exc:
            print("   [error] %s" % exc); failed = True; continue
        for n in notes:
            print("   %s" % n)
        b0, b1 = original.count("{") - original.count("}"), new_text.count("{") - new_text.count("}")
        print("   [check] markers %d (expected %d); brace balance %d/%d" % (new_text.count(MARKER), len(edits), b0, b1))
        if new_text.count(MARKER) != len(edits) or b0 != b1 or "clinical/" in "".join(re.findall(r"path: \{ [^\n]*(?:cnv_consensus_multi|cnv_decon|sex_check)[^\n]*", new_text)):
            print("   [error] verification failed"); failed = True; continue
        planned.append((path, original, new_text))
    if failed:
        print("\n[error] one or more files failed; nothing written"); sys.exit(1)
    if not planned:
        print("\n[skip] nothing to do"); sys.exit(0)
    if not args.apply:
        print("\n[dry-run] %d file(s) would change; re-run with --apply" % len(planned))
        for path, original, new_text in planned:
            old_set = set(original.splitlines())
            print("## %s" % os.path.relpath(path, args.root))
            for line in new_text.splitlines():
                if line not in old_set:
                    print("+ " + line)
        sys.exit(0)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    for path, original, new_text in planned:
        backup = "%s.bak_publish_clinical_v2_%s" % (path, ts)
        shutil.copy2(path, backup)
        with open(path, "w") as fh:
            fh.write(new_text)
        print("[backup] %s" % os.path.relpath(backup, args.root))
        print("[patch]  wrote %s" % os.path.relpath(path, args.root))


if __name__ == "__main__":
    main()
