#!/usr/bin/env python3
"""
patch_publish_clinical_v1.py -- publish the CMX_V2 consensus, DECON and
SEX_CHECK tables under <outdir>/<sample>/clinical/ (MARKER PUBLISH_CLINICAL_V1).

Why: main.nf's onComplete sweep deletes <outdir>/<sample>/cnv_consensus
(legacy scratch name), which is where conf/twist_apply.config published the
CNV_CONSENSUS_MULTI outputs; the 26CGH60 run lost its consensus table that
way. clinical/ is the documented survivor and is what REPORT_BUNDLE zips.

Edits (all-or-nothing):
  conf/twist_apply.config  CNV_CONSENSUS_MULTI -> clinical/cnv_consensus, mode copy
                           DECON               -> clinical/cnv_decon,     mode copy
  conf/modules.config      SEX_CHECK           -> clinical/sex_check,     mode copy

Dry run by default; --apply writes with .bak_publish_clinical_<ts> backups.
"""

import argparse
import datetime
import os
import re
import shutil
import sys

MARKER = "MARKER PUBLISH_CLINICAL_V1"


def sub_once(text, pattern, repl, label, flags=re.M):
    rx = re.compile(pattern, flags)
    n = len(rx.findall(text))
    if n != 1:
        raise ValueError("anchor %s: expected 1 match, found %d (%s)" % ("not found" if n == 0 else "not unique", n, label))
    return rx.sub(repl, text, count=1), "[ok] %s" % label


def block_edit(t, process, old_sub, new_sub, old_mode_re, label, expected_marker_first=False):
    """Within withName: '<process>' { ... }, rewrite the path line and the mode line."""
    pat = (r"(?P<head>^(?P<i>[ \t]*)withName: '%s' \{[ \t]*\n(?:(?!^\s*withName:).*\n)*?"
           r"(?P<pi>[ \t]*)path: \{ \"\$\{params\.outdir\}/\$\{meta\.id\}/)%s(?P<tail>\" \},[ \t]*\n"
           r"(?P<mi>[ \t]*)mode: )%s(?P<rest>,[ \t]*\n)") % (re.escape(process), re.escape(old_sub), old_mode_re)
    rx = re.compile(pat, re.M)
    n = len(rx.findall(t))
    if n != 1:
        raise ValueError("anchor %s: expected 1 match, found %d (%s)" % ("not found" if n == 0 else "not unique", n, label))

    def repl(m):
        return (m.group("head") + new_sub + m.group("tail") + "'copy'" + m.group("rest")
                + "%s// %s: under clinical/ (survives the main.nf sweep; zipped by REPORT_BUNDLE)\n" % (m.group("mi"), MARKER))
    return rx.sub(repl, t, count=1), "[ok] %s" % label


def patch_twist_apply(t):
    notes = []
    t, n = block_edit(t, "CNV_CONSENSUS_MULTI", "cnv_consensus", "clinical/cnv_consensus", r"'link'",
                      "twist_apply.config: CNV_CONSENSUS_MULTI publishDir")
    notes.append(n)
    t, n = block_edit(t, "DECON", "cnv_decon", "clinical/cnv_decon", r"'link'",
                      "twist_apply.config: DECON publishDir")
    notes.append(n)
    return t, notes, 2


def patch_modules_config(t):
    notes = []
    t, n = block_edit(t, "SEX_CHECK", "sex_check", "clinical/sex_check", r"params\.publish_dir_mode",
                      "modules.config: SEX_CHECK publishDir")
    notes.append(n)
    return t, notes, 1


FILES = [
    ("conf/twist_apply.config", patch_twist_apply),
    ("conf/modules.config",     patch_modules_config),
]


def brace_balance(text):
    return text.count("{") - text.count("}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    planned, failed = [], False
    for rel, fn in FILES:
        path = os.path.join(args.root, rel)
        print("== %s" % rel)
        if not os.path.isfile(path):
            print("   [error] file not found"); failed = True; continue
        original = open(path).read()
        if MARKER in original:
            print("   [skip] %s already present" % MARKER); continue
        try:
            new_text, notes, expected = fn(original)
        except ValueError as exc:
            print("   [error] %s" % exc); failed = True; continue
        for n in notes:
            print("   %s" % n)
        b0, b1 = brace_balance(original), brace_balance(new_text)
        print("   [check] markers %d (expected %d); brace balance %d/%d" % (new_text.count(MARKER), expected, b0, b1))
        if new_text.count(MARKER) != expected or b0 != b1:
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
        backup = "%s.bak_publish_clinical_%s" % (path, ts)
        shutil.copy2(path, backup)
        with open(path, "w") as fh:
            fh.write(new_text)
        print("[backup] %s" % os.path.relpath(backup, args.root))
        print("[patch]  wrote %s" % os.path.relpath(path, args.root))


if __name__ == "__main__":
    main()
