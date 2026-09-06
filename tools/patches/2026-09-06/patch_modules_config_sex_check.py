#!/usr/bin/env python3
"""
patch_modules_config_sex_check.py -- publishDir for SEX_CHECK.

MARKER SEX_CHECK_MODULES_V1. Idempotent, anchor-based. Dry run by default;
--apply writes with a timestamped backup (.bak_sex_check_<timestamp>).

Inserts one withName block directly after the MOSDEPTH block in
conf/modules.config, publishing <sample>.sex_check.tsv to
<outdir>/<sample>/sex_check/ with params.publish_dir_mode.

Usage:
    python3 tools/patches/2026-09-06/patch_modules_config_sex_check.py            # dry run
    python3 tools/patches/2026-09-06/patch_modules_config_sex_check.py --apply
"""

import argparse
import datetime
import os
import re
import shutil
import sys

MARKER = "MARKER SEX_CHECK_MODULES_V1"
TARGET_DEFAULT = "conf/modules.config"

# The MOSDEPTH withName block: from its header line to the first line that is
# exactly '<indent>}' at the same indent as the header.
MOSDEPTH_HEADER = re.compile(r"^(?P<indent>[ \t]*)withName:\s*'MOSDEPTH'\s*\{[ \t]*$", re.M)

BLOCK = '''
{i}// {m}
{i}withName: 'SEX_CHECK' {{
{i}    publishDir = [
{i}        path: {{ "${{params.outdir}}/${{meta.id}}/sex_check" }},
{i}        mode: params.publish_dir_mode,
{i}        pattern: '*.sex_check.tsv'
{i}    ]
{i}}}
'''


def patch(text):
    if MARKER in text:
        return None, "[skip] %s already present" % MARKER
    m = MOSDEPTH_HEADER.search(text)
    if not m:
        return None, "[error] withName: 'MOSDEPTH' block not found"
    indent = m.group("indent")
    close = re.compile(r"^%s\}[ \t]*$" % re.escape(indent), re.M)
    c = close.search(text, m.end())
    if not c:
        return None, "[error] closing brace of MOSDEPTH block not found"
    insert_at = c.end()
    text = text[:insert_at] + BLOCK.format(i=indent, m=MARKER) + text[insert_at:]
    return text, "[patch] SEX_CHECK publishDir block inserted after MOSDEPTH"


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
    before_balance = brace_balance(original)

    new_text, msg = patch(original)
    print(msg)
    if new_text is None:
        sys.exit(0 if msg.startswith("[skip]") else 1)

    n_markers = new_text.count(MARKER)
    after_balance = brace_balance(new_text)
    print("[check] markers: %d (expected 1); brace balance before/after: %d/%d"
          % (n_markers, before_balance, after_balance))
    if n_markers != 1 or after_balance != before_balance:
        print("[error] verification failed; nothing written")
        sys.exit(1)

    if not args.apply:
        print("[dry-run] no changes written; re-run with --apply")
        print("---- inserted block ----")
        old_set = set(original.splitlines())
        for line in new_text.splitlines():
            if line not in old_set:
                print("+ " + line)
        sys.exit(0)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = "%s.bak_sex_check_%s" % (args.target, ts)
    shutil.copy2(args.target, backup)
    print("[backup] %s" % backup)
    with open(args.target, "w") as fh:
        fh.write(new_text)
    print("[patch] wrote %s" % args.target)


if __name__ == "__main__":
    main()
