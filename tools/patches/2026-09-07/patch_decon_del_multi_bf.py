#!/usr/bin/env python3
"""
patch_decon_del_multi_bf.py -- lower DECoN reporting threshold for
multi-exon deletions (MARKER DECON_V1b).

Evidence (2026-09-07): the male (23) and female (8) pool LOO calls contain
no multi-exon call at any BF; the eight validation cases had real multi-exon
deletions at BF 9.9 (26CGH60 IKZF1 exons 4-7, FISH-confirmed) and BF 10.6
(26CGH1043 NRAS, called by CNVkit and GATK) below the BF 12 line, while the
only artefacts in the 8-12 band were two-exon SUZ12 duplications.

Edits (all-or-nothing):
  bin/filter_decon_calls.py   --del-multi-bf (default 8; -1 disables): deletions
                              with N.exons >= 2 are reportable at BF >= this
                              value, decision PASS_MULTIDEL when admitted only by
                              it; everything else keeps --bf (12)
  modules/local/decon.nf      passes --del-multi-bf ${params.decon_del_multi_bf}
  conf/twist_apply.config     decon_del_multi_bf = 8

Dry run by default; --apply writes .bak_decon_v1b_<ts> backups.
"""

import argparse
import datetime
import os
import re
import shutil
import sys

MARKER = "MARKER DECON_V1b"


def sub_once(text, pattern, repl, label, flags=re.M):
    rx = re.compile(pattern, flags)
    n = len(rx.findall(text))
    if n != 1:
        raise ValueError("anchor %s: expected 1 match, found %d (%s)" % ("not found" if n == 0 else "not unique", n, label))
    return rx.sub(repl, text, count=1), "[ok] %s" % label


def patch_filter(t):
    notes = []
    t, n = sub_once(
        t,
        r'^def classify\(bf, n_exons, exon_hits, variant_hits, args\):\n'
        r'    flags = sorted\(set\(e\["flag"\] for e in exon_hits if e\["flag"\] != "OK"\)\)\n'
        r'    min_depth = min\(\(e\["depth"\] for e in exon_hits\), default=float\("nan"\)\)\n\n'
        r'    if bf < args\.bf:\n'
        r'        return "BELOW_BF", False, flags, min_depth\n'
        r'    if n_exons > 1:\n'
        r'        return "PASS", True, flags, min_depth\n',
        '''def classify(bf, n_exons, exon_hits, variant_hits, args, cnv_type=""):
    flags = sorted(set(e["flag"] for e in exon_hits if e["flag"] != "OK"))
    min_depth = min((e["depth"] for e in exon_hits), default=float("nan"))

    # %s: multi-exon deletions may report at a lower BF (no multi-exon
    # call of any kind in 31 normals' LOO; real Delta-exon deletions sat at 9.9-10.6)
    multi_del = n_exons > 1 and cnv_type.lower().startswith("del") and args.del_multi_bf >= 0
    threshold = args.del_multi_bf if multi_del else args.bf
    if bf < threshold:
        return "BELOW_BF", False, flags, min_depth
    if n_exons > 1:
        if multi_del and bf < args.bf:
            return "PASS_MULTIDEL", True, flags, min_depth
        return "PASS", True, flags, min_depth
''' % MARKER,
        "classify(): multi-exon deletion threshold")
    notes.append(n)
    t, n = sub_once(
        t,
        r'^    p\.add_argument\("--bf", type=float, default=12\.0, help="reporting threshold \(default 12\)"\)\n',
        lambda m: m.group(0) + '    p.add_argument("--del-multi-bf", type=float, default=8.0,\n'
        '                   help="BF at which deletions of >= 2 exons are reportable (default 8; -1 disables)")\n',
        "argparse --del-multi-bf")
    notes.append(n)
    t, n = sub_once(
        t,
        r'^            decision, reportable, flags, min_depth = classify\(bf, n_ex, exon_hits, variant_hits, args\)\n',
        '            decision, reportable, flags, min_depth = classify(bf, n_ex, exon_hits, variant_hits, args,\n'
        '                                                              cnv_type=row.get("CNV.type", ""))\n',
        "classify call passes CNV.type")
    notes.append(n)
    t, n = sub_once(
        t,
        r'\["PASS", "BELOW_BF", "LOW_POWER_EXON", "PARALOG_EXON", "PROBE_VARIANT"\]\)\)',
        '["PASS", "PASS_MULTIDEL", "BELOW_BF", "LOW_POWER_EXON", "PARALOG_EXON", "PROBE_VARIANT"]))',
        "summary classes")
    notes.append(n)
    return t, notes


def patch_module(t):
    notes = []
    t, n = sub_once(t, r'^(?P<i>[ \t]*)--bf \$\{params\.decon_bf\} --out \$\{meta\.id\}\.decon_filtered\.tsv[ \t]*$',
                    lambda m: "%s--bf ${params.decon_bf} --del-multi-bf ${params.decon_del_multi_bf} \\\\\n%s--out ${meta.id}.decon_filtered.tsv   // %s" % (m.group("i"), m.group("i"), MARKER),
                    "decon.nf: --del-multi-bf")
    notes.append(n)
    return t, notes


def patch_config(t):
    notes = []
    t, n = sub_once(t, r'^(?P<i>[ \t]*)decon_bf[ \t]*=[ \t]*12[ \t]*$',
                    lambda m: m.group(0) + "\n%sdecon_del_multi_bf = 8    // %s: deletions of >= 2 exons report at this BF" % (m.group("i"), MARKER),
                    "twist_apply.config: decon_del_multi_bf")
    notes.append(n)
    return t, notes


FILES = [("bin/filter_decon_calls.py", patch_filter), ("modules/local/decon.nf", patch_module), ("conf/twist_apply.config", patch_config)]


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
            new_text, notes = fn(original)
        except ValueError as exc:
            print("   [error] %s" % exc); failed = True; continue
        for n in notes:
            print("   %s" % n)
        if rel.endswith(".py"):
            try:
                compile(new_text, path, "exec")
            except SyntaxError as exc:
                print("   [error] does not compile: %s" % exc); failed = True; continue
        print("   [check] markers %d (expected 1)" % new_text.count(MARKER))
        if new_text.count(MARKER) != 1:
            print("   [error] verification failed"); failed = True; continue
        planned.append((path, original, new_text))
    if failed:
        print("\n[error] one or more files failed; nothing written"); sys.exit(1)
    if not planned:
        print("\n[skip] nothing to do"); sys.exit(0)
    if not args.apply:
        print("\n[dry-run] %d file(s) would change; re-run with --apply" % len(planned)); sys.exit(0)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    for path, original, new_text in planned:
        backup = "%s.bak_decon_v1b_%s" % (path, ts)
        shutil.copy2(path, backup)
        with open(path, "w") as fh:
            fh.write(new_text)
        print("[backup] %s" % os.path.relpath(backup, args.root))
        print("[patch]  wrote %s" % os.path.relpath(path, args.root))


if __name__ == "__main__":
    main()
