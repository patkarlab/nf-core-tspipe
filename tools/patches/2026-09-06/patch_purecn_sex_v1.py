#!/usr/bin/env python3
"""
patch_purecn_sex_v1.py -- sex-stratified PureCN NormalDB selection
(MARKER PCN_SEX_V1). Handoff item 5, pipeline half.

Files (3), all-or-nothing:
  conf/twist_apply.config   purecn_normaldb_female -> normalDB_twist_myeloid_female_hg38.rds
  workflows/tspipe.nf       ch_purecn_normaldb_female via sexstratFemale() (male file
                            until the female asset exists); PURECN call gets it last
  modules/local/purecn.nf   second input staged under female_stratum/; stratum from
                            meta.sex with params.cnv_sex_fallback; [SEXSTRAT] echo

Requires SEXSTRAT_V1 (sexstratFemale helper and params.cnv_sex_fallback).
Dry run by default; --apply writes with .bak_pcn_sex_<ts> backups.
"""

import argparse
import datetime
import os
import re
import shutil
import sys

MARKER = "MARKER PCN_SEX_V1"
TAG = "PCN_SEX_V1"
STRATUM_DEF = "def stratum = (meta.sex in ['male', 'female']) ? meta.sex : (params.cnv_sex_fallback ?: 'male')"


def sub_once(text, pattern, repl, label, flags=re.M, required=True):
    rx = re.compile(pattern, flags)
    n = len(rx.findall(text))
    if n == 0 and not required:
        return text, "[warn] optional anchor not found, skipped: %s" % label
    if n != 1:
        raise ValueError("anchor %s: expected 1 match, found %d (%s)" % ("not found" if n == 0 else "not unique", n, label))
    return rx.sub(repl, text, count=1), "[ok] %s" % label


def patch_twist_apply(t):
    notes = []
    t, n = sub_once(
        t,
        r'^(?P<i>[ \t]*)purecn_normaldb[ \t]*=[ \t]*"(?P<p>[^"]*)normalDB_twist_myeloid_hg38\.rds"[ \t]*$',
        lambda m: m.group(0) + '\n%spurecn_normaldb_female = "%snormalDB_twist_myeloid_female_hg38.rds"   // %s'
        % (m.group("i"), m.group("p"), MARKER),
        "twist_apply.config: purecn_normaldb_female")
    notes.append(n)
    return t, notes, 1


def patch_tspipe(t):
    notes = []
    if "sexstratFemale" not in t:
        raise ValueError("tspipe.nf lacks sexstratFemale (apply SEXSTRAT_V1 first)")
    t, n = sub_once(
        t,
        r'^(?P<i>[ \t]*)ch_purecn_normaldb[ \t]*=[ \t]*Channel\.value\(file\(params\.purecn_normaldb,[ \t]*checkIfExists: true\)\)[ \t]*$',
        lambda m: m.group(0) + "\n"
        + "%s// %s: female PureCN NormalDB; the male file until the female asset exists.\n" % (m.group("i"), MARKER)
        + "%sdef purecn_ndb_female = (params.containsKey('purecn_normaldb_female') && params.purecn_normaldb_female) ? params.purecn_normaldb_female : null\n" % m.group("i")
        + "%sch_purecn_normaldb_female = Channel.value( sexstratFemale(purecn_ndb_female,\n" % m.group("i")
        + "%s    \"${projectDir}/assets/${params.panel}/normalDB_twist_myeloid_female_hg38.rds\", params.purecn_normaldb) )" % m.group("i"),
        "tspipe.nf: ch_purecn_normaldb_female")
    notes.append(n)
    t, n = sub_once(
        t,
        r'PURECN\( ch_purecn_in, ch_purecn_normaldb, ch_purecn_intervals \)',
        'PURECN( ch_purecn_in, ch_purecn_normaldb, ch_purecn_intervals, ch_purecn_normaldb_female )   // %s' % TAG,
        "tspipe.nf: PURECN call")
    notes.append(n)
    t, n = sub_once(t, r"tools/build_purecn_normaldb\.sh \(male stratum, PureCN 2\.16\.0\)\.",
                    "tools/build_purecn_normaldb.sh --sex male|female (PureCN 2.16.0).",
                    "tspipe.nf: comment", required=False)
    notes.append(n)
    return t, notes, 1


def patch_purecn_nf(t):
    notes = []
    t, n = sub_once(
        t,
        r'^(?P<i>[ \t]*)path intervals[ \t]*$',
        lambda m: m.group(0) + "\n%spath normaldb_female, stageAs: 'female_stratum/*'   // %s" % (m.group("i"), MARKER),
        "purecn.nf: input")
    notes.append(n)
    t, n = sub_once(
        t,
        r"^(?P<i>[ \t]*)def extra = task\.ext\.args \?: ''\n(?P<j>[ \t]*)\"\"\"\n(?P<k>[ \t]*)set \+e\n",
        lambda m: "%sdef extra = task.ext.args ?: ''\n%s// %s: NormalDB by stratum (sheet sex, or params.cnv_sex_fallback)\n%s%s\n%sdef ndb_use = (stratum == 'female') ? normaldb_female : normaldb\n%s\"\"\"\n%secho \"[SEXSTRAT] ${meta.id}: sex=${meta.sex} stratum=${stratum} normaldb=${ndb_use}\"\n%sset +e\n"
        % (m.group("i"), m.group("i"), TAG, m.group("i"), STRATUM_DEF, m.group("i"), m.group("j"), m.group("k"), m.group("k")),
        "purecn.nf: stratum selection")
    notes.append(n)
    t, n = sub_once(t, r"--normaldb \$\{normaldb\}", "--normaldb ${ndb_use}", "purecn.nf: --normaldb")
    notes.append(n)
    t, n = sub_once(t, r"^ \* PureCN purity/ploidy/integer-CN \+ LOH, tumor-only, against the\n \* male-stratum NormalDB\.",
                    " * PureCN purity/ploidy/integer-CN + LOH, tumor-only, against the\n * sex-matched NormalDB (%s; male stratum for unknown sex)." % TAG,
                    "purecn.nf: header comment", required=False)
    notes.append(n)
    return t, notes, 1


FILES = [
    ("conf/twist_apply.config", patch_twist_apply),
    ("workflows/tspipe.nf",     patch_tspipe),
    ("modules/local/purecn.nf", patch_purecn_nf),
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
        backup = "%s.bak_pcn_sex_%s" % (path, ts)
        shutil.copy2(path, backup)
        with open(path, "w") as fh:
            fh.write(new_text)
        print("[backup] %s" % os.path.relpath(backup, args.root))
        print("[patch]  wrote %s" % os.path.relpath(path, args.root))


if __name__ == "__main__":
    main()
