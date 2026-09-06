#!/usr/bin/env python3
"""
patch_preprocessing_sex_check_logonce.py -- log the SEX_CHECK resolution once
per sample.

MARKER SEX_CHECK_V1a. Requires SEX_CHECK_V1 to be applied. Idempotent,
anchor-based, dry run by default; --apply writes with a timestamped backup.

Why: ch_sex_by_id is consumed by ten joins and DSL2 replays the map closure
per consumer, so the log.warn/log.info fired 14 times per sample in the stub
run. A set of sample ids shared by the closure gates the message.

Usage:
    python3 tools/patches/2026-09-06/patch_preprocessing_sex_check_logonce.py          # dry run
    python3 tools/patches/2026-09-06/patch_preprocessing_sex_check_logonce.py --apply
"""

import argparse
import datetime
import os
import re
import shutil
import sys

MARKER_V1 = "MARKER SEX_CHECK_V1"
MARKER = "MARKER SEX_CHECK_V1a"
TARGET_DEFAULT = "subworkflows/local/preprocessing.nf"

OLD_BLOCK = re.compile(
    r"^(?P<indent>[ \t]+)ch_sex_by_id = SEX_CHECK\.out\.tsv\n"
    r"(?P=indent)    \.splitCsv\(header: true, sep: '\\t', elem: 1\)\n"
    r"(?P=indent)    \.map \{ meta, row ->\n"
    r"(?P=indent)        if\( row\.status == 'MISMATCH' \)\n"
    r"(?P=indent)            log\.warn (?P<warn>.*)\n"
    r"(?P=indent)        else if\( row\.sheet_sex == 'unknown' \)\n"
    r"(?P=indent)            log\.info (?P<info>.*)\n"
    r"(?P=indent)        \[ meta\.id, row\.resolved_sex \]\n"
    r"(?P=indent)    \}\n",
    re.M)

NEW_BLOCK = '''{i}// {m}: the map closure is replayed per consumer of ch_sex_by_id; log once.
{i}def sex_check_logged = java.util.concurrent.ConcurrentHashMap.newKeySet()
{i}ch_sex_by_id = SEX_CHECK.out.tsv
{i}    .splitCsv(header: true, sep: '\\t', elem: 1)
{i}    .map {{ meta, row ->
{i}        if( sex_check_logged.add(meta.id) ) {{
{i}            if( row.status == 'MISMATCH' )
{i}                log.warn {warn}
{i}            else if( row.sheet_sex == 'unknown' )
{i}                log.info {info}
{i}        }}
{i}        [ meta.id, row.resolved_sex ]
{i}    }}
'''


def patch(text):
    if MARKER in text:
        return None, "[skip] %s already present" % MARKER
    if MARKER_V1 not in text:
        return None, "[error] %s not present; apply patch_preprocessing_sex_check.py first" % MARKER_V1
    m = OLD_BLOCK.search(text)
    if not m:
        return None, "[error] ch_sex_by_id block (V1 form) not found"
    new = NEW_BLOCK.format(i=m.group("indent"), m=MARKER,
                           warn=m.group("warn"), info=m.group("info"))
    text = text[:m.start()] + new + text[m.end():]
    return text, "[patch] ch_sex_by_id logging gated to once per sample"


def brace_balance(text):
    return text.count("{") - text.count("}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default=TARGET_DEFAULT)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    if not os.path.isfile(args.target):
        print("[error] target not found: %s" % args.target)
        sys.exit(1)
    original = open(args.target).read()
    before = brace_balance(original)

    new_text, msg = patch(original)
    print(msg)
    if new_text is None:
        sys.exit(0 if msg.startswith("[skip]") else 1)

    after = brace_balance(new_text)
    print("[check] markers: %d (expected 1); brace balance before/after: %d/%d"
          % (new_text.count(MARKER), before, after))
    if new_text.count(MARKER) != 1 or after != before:
        print("[error] verification failed; nothing written")
        sys.exit(1)

    if not args.apply:
        print("[dry-run] no changes written; re-run with --apply")
        old_set = set(original.splitlines())
        for line in new_text.splitlines():
            if line not in old_set:
                print("+ " + line)
        sys.exit(0)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = "%s.bak_sex_check_logonce_%s" % (args.target, ts)
    shutil.copy2(args.target, backup)
    print("[backup] %s" % backup)
    with open(args.target, "w") as fh:
        fh.write(new_text)
    print("[patch] wrote %s" % args.target)


if __name__ == "__main__":
    main()
