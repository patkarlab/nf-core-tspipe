#!/usr/bin/env python3
"""
patch_cnv_consensus_multi_cmx_v2_4.py -- tier rule refinements from the first
eight-case run with PURPLE (MARKER CMX_V2_4).

1. H trust: WARN_LOW_PURITY makes arm H advisory (H support omitted) like FAIL_;
   a low-purity fit projects minor-allele CN < 0.5 genome-wide (26CGH1292 at
   0.15 produced 30 H-only cnLOH calls).
2. cnLOH tier: single-arm cnLOH is TIER_2 only when the arm is B (direct 17p
   BAF against the cohort background); P- or H-only cnLOH is TIER_3.
   Two or more allelic arms remain TIER_1.
3. Independent-only calls: two or more independent arms agreeing without a
   depth arm are TIER_2 (IKZF1 in 26CGH60: DECoN and PURPLE); one arm stays TIER_3.
"""
import argparse, datetime, os, re, shutil, sys

MARKER = "MARKER CMX_V2_4"
TARGET = "bin/cnv_consensus_multi.py"
MODULE = "modules/local/cnv_consensus_multi.nf"


def sub_once(text, pattern, repl, label):
    rx = re.compile(pattern, re.M); n = len(rx.findall(text))
    if n != 1:
        raise ValueError("anchor %s: %d matches (%s)" % ("not found" if n == 0 else "not unique", n, label))
    return rx.sub(lambda m: repl, text, count=1), "[ok] %s" % label


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--target", default=TARGET); ap.add_argument("--module", default=MODULE); ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(); t = open(a.target).read()
    if MARKER in t:
        print("[skip] already applied"); sys.exit(0)
    # module: a bash comment with the rule version inside the script so the task hash changes
    # (Nextflow does not hash bin/ scripts; a consensus-only change would stay cached on resume)
    mod = open(a.module).read()
    rx_mod = re.compile(r"^(?P<i>[ \t]*)cnv_consensus_multi\.py \\\\$", re.M)
    if len(rx_mod.findall(mod)) != 1:
        print("[error] module anchor: %d matches; nothing written" % len(rx_mod.findall(mod))); sys.exit(1)
    mod2 = rx_mod.sub(lambda m: "%s# consensus rule version: CMX_V2_4 (bash comment; busts the task cache)\n%scnv_consensus_multi.py \\\\" % (m.group("i"), m.group("i")), mod, count=1)
    notes = ["[ok] module: rule-version comment in the script block"]
    try:
        t, n = sub_once(t,
            r'        h_trusted = str\(purple_h_sum\.get\("trusted", ""\)\)\.strip\(\)\.upper\(\) == "TRUE"\n',
            '        h_trusted = str(purple_h_sum.get("trusted", "")).strip().upper() == "TRUE" \\\n'
            '            and "WARN_LOW_PURITY" not in str(purple_h_sum.get("status", ""))   # %s\n' % MARKER,
            "H trust excludes WARN_LOW_PURITY"); notes.append(n)
        t, n = sub_once(t,
            r'            tier = "TIER_1" if len\(cnloh_arms\) >= 2 else "TIER_2"\n',
            '            # CMX_V2_4: single-arm cnLOH is TIER_2 only from B (direct BAF); P/H alone TIER_3\n'
            '            tier = "TIER_1" if len(cnloh_arms) >= 2 else ("TIER_2" if cnloh_arms == ["B"] else "TIER_3")\n',
            "cnLOH single-arm tier"); notes.append(n)
        t, n = sub_once(t,
            r'            consensus, tier = next\(iter\(indep_dirs\)\), "TIER_3"\n',
            '            consensus = next(iter(indep_dirs))\n'
            '            # CMX_V2_4: >= 2 independent arms agreeing without depth -> TIER_2\n'
            '            tier = "TIER_2" if sum(1 for v in indep.values() if v == consensus) >= 2 else "TIER_3"\n',
            "independent-only tier"); notes.append(n)
        t, n = sub_once(t,
            r'^    TIER_3  independent arm\(s\) only, all agreeing \(consensus = direction\)\n',
            '    TIER_2  >= 2 independent arms agreeing, no depth arm (CMX_V2_4)\n'
            '    TIER_3  a single independent arm (consensus = direction)\n',
            "docstring"); notes.append(n)
        t, n = sub_once(t,
            r'^    CNLOH   B and/or P cnLOH support: TIER_1 when both agree, else TIER_2\n',
            '    CNLOH   TIER_1 with >= 2 allelic arms (B/P/H); TIER_2 from B alone; TIER_3 from P or H alone (CMX_V2_4)\n',
            "docstring cnLOH"); notes.append(n)
    except ValueError as exc:
        print("[error] %s; nothing written" % exc); sys.exit(1)
    for n in notes:
        print(n)
    try:
        compile(t, a.target, "exec")
    except SyntaxError as exc:
        print("[error] does not compile: %s" % exc); sys.exit(1)
    print("[check] markers %d (expected 1)" % t.count(MARKER))
    if not a.apply:
        print("[dry-run] no changes written"); sys.exit(0)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    for path, text in ((a.target, t), (a.module, mod2)):
        b = "%s.bak_cmx_v2_4_%s" % (path, ts)
        shutil.copy2(path, b); open(path, "w").write(text); print("[backup] %s\n[patch] wrote %s" % (b, path))


if __name__ == "__main__":
    main()
