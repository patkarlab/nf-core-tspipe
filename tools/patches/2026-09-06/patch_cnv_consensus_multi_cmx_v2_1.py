#!/usr/bin/env python3
"""
patch_cnv_consensus_multi_cmx_v2_1.py -- sex-aware expected copy number
for the CNVkit arm (MARKER CMX_V2_1).

Why: cnvkit.py call --sex male reports absolute copy number, so a normal
male chrX is cn 1 and the consensus's "cn < 2 -> LOSS" turned every chrX
gene of 26CGH60 (log2 -0.02 vs the male PoN) into a TIER_3 loss. GATK,
being relative to the sex-matched PoN, was neutral.

Edits to bin/cnv_consensus_multi.py:
  1. --sex argument (male|female|unknown; default unknown)
  2. expected_cn(chrom, sex): autosomes 2; chrX 1 male / 2 female; chrY
     1 male / 0 female; None on X/Y when sex is unknown (call -> NA)
  3. cnvkit_gene_call() compares cn to the expected value
  4. segment-intersection k_call uses the same rule
Also modules/local/cnv_consensus_multi.nf passes --sex ${meta.sex}.
Requires CMX_V2. Dry run by default; --apply writes .bak_cmx_v2_1_<ts> backups.
"""

import argparse
import datetime
import os
import re
import shutil
import sys

MARKER = "MARKER CMX_V2_1"


def sub_once(text, pattern, repl, label, flags=re.M):
    rx = re.compile(pattern, flags)
    n = len(rx.findall(text))
    if n != 1:
        raise ValueError("anchor %s: expected 1 match, found %d (%s)" % ("not found" if n == 0 else "not unique", n, label))
    return rx.sub(repl, text, count=1), "[ok] %s" % label


EXPECTED_CN = '''def expected_cn(chrom, sex):
    """CMX_V2_1: expected integer copy number of a chromosome for the sample's sex.
    None means not interpretable (X/Y with unknown sex, or chrY in a female)."""
    c = chrom.replace("chr", "")
    if c not in ("X", "Y"):
        return 2
    if sex == "male":
        return 1
    if sex == "female":
        return 2 if c == "X" else None
    return None


def cn_call(cn, exp):
    if cn is None:
        return "NEUTRAL"
    if exp is None:
        return "NA"
    if cn > exp:
        return "GAIN"
    if cn < exp:
        return "LOSS"
    return "NEUTRAL"


'''

OLD_GENE_CALL = r'''def cnvkit_gene_call\(segs, chrom, gs, ge\):
    """Length-weighted call from call\.cns integer CN over a gene span\."""
    w = \{"GAIN": 0, "LOSS": 0, "NEUTRAL": 0\}
    hits = \[\]
    for s in segs:
        if s\["chromosome"\] != chrom:
            continue
        o = overlap\(gs, ge, s\["start"\], s\["end"\]\)
        if o <= 0:
            continue
        hits\.append\(\(o, s\)\)
        if s\["cn"\] is None:
            w\["NEUTRAL"\] \+= o
        elif s\["cn"\] > 2:
            w\["GAIN"\] \+= o
        elif s\["cn"\] < 2:
            w\["LOSS"\] \+= o
        else:
            w\["NEUTRAL"\] \+= o
    if not hits:
        return "NA", None, None
'''
NEW_GENE_CALL = '''def cnvkit_gene_call(segs, chrom, gs, ge, exp=2):
    """Length-weighted call from call.cns integer CN over a gene span,
    relative to the expected copy number `exp` (CMX_V2_1; None -> NA)."""
    w = {"GAIN": 0, "LOSS": 0, "NEUTRAL": 0}
    hits = []
    for s in segs:
        if s["chromosome"] != chrom:
            continue
        o = overlap(gs, ge, s["start"], s["end"])
        if o <= 0:
            continue
        hits.append((o, s))
        call = cn_call(s["cn"], exp)
        w[call if call in w else "NEUTRAL"] += o
    if not hits:
        return "NA", None, None
    if exp is None:
        top = max(hits)[1]
        return "NA", top["cn"], top["log2"]
'''


def patch_script(t):
    notes = []
    t, n = sub_once(t, r'^def overlap\(a1, a2, b1, b2\):\n    return max\(0, min\(a2, b2\) - max\(a1, b1\)\)\n\n\n',
                    lambda m: m.group(0) + EXPECTED_CN, "helpers expected_cn / cn_call")
    notes.append(n)
    t, n = sub_once(t, OLD_GENE_CALL, lambda m: NEW_GENE_CALL, "cnvkit_gene_call vs expected cn")
    notes.append(n)
    t, n = sub_once(t, r'^    ap\.add_argument\("--loo-fp-max", type=float, default=0\.10,\n[^\n]*\n',
                    lambda m: m.group(0) + '    ap.add_argument("--sex", default="unknown",\n'
                    '                    help="sample sex (male|female|unknown) for the expected chrX/chrY copy number (CMX_V2_1)")\n',
                    "argparse --sex")
    notes.append(n)
    t, n = sub_once(t, r'^        k_call, k_cn, k_log2 = cnvkit_gene_call\(\n            k_segs, g\["chrom"\], g\["start"\], g\["end"\]\)\n',
                    '        k_call, k_cn, k_log2 = cnvkit_gene_call(\n            k_segs, g["chrom"], g["start"], g["end"],\n            expected_cn(g["chrom"], args.sex))   # CMX_V2_1\n',
                    "per-gene call passes expected cn")
    notes.append(n)
    t, n = sub_once(t, r'^        k_call = "NEUTRAL" if ks\["cn"\] in \(None, 2\) else \(\n            "GAIN" if ks\["cn"\] > 2 else "LOSS"\)\n',
                    '        k_call = cn_call(ks["cn"], expected_cn(ks["chromosome"], args.sex))   # CMX_V2_1\n',
                    "segment intersection k_call")
    notes.append(n)
    t, n = sub_once(t, r'^(MARKER CMX_V2: Z-score is no longer an arm;)', r'%s (expected chrX/chrY copy number by --sex)\n\1' % MARKER, "docstring marker")
    notes.append(n)
    return t, notes


def patch_module(t):
    notes = []
    t, n = sub_once(t, r'^(?P<i>[ \t]*)--sample \$\{meta\.id\} \\\\\n(?P<j>[ \t]*)--concordance \$\{concordance\} \\\\\n',
                    lambda m: "%s--sample ${meta.id} \\\\\n%s--sex ${meta.sex ?: 'unknown'} \\\\\n%s--concordance ${concordance} \\\\\n" % (m.group("i"), m.group("i"), m.group("j")),
                    "cnv_consensus_multi.nf: --sex")
    notes.append(n)
    t, n = sub_once(t, r'^ \* modules/local/cnv_consensus_multi\.nf  \((.*)\)$',
                    lambda m: " * modules/local/cnv_consensus_multi.nf  (%s; %s: --sex)" % (m.group(1), MARKER), "cnv_consensus_multi.nf: header marker")
    notes.append(n)
    return t, notes


FILES = [("bin/cnv_consensus_multi.py", patch_script), ("modules/local/cnv_consensus_multi.nf", patch_module)]


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
        backup = "%s.bak_cmx_v2_1_%s" % (path, ts)
        shutil.copy2(path, backup)
        with open(path, "w") as fh:
            fh.write(new_text)
        print("[backup] %s" % os.path.relpath(backup, args.root))
        print("[patch]  wrote %s" % os.path.relpath(path, args.root))


if __name__ == "__main__":
    main()
