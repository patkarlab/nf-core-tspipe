#!/usr/bin/env python3
"""
patch_baf_catalog_v1_publish.py -- publish the merged BAF catalog beside
baf_background.tsv (MARKER BAF_CATALOG_V1_PUBLISH), conf/modules.config.
Inserts a withName: 'BPT_MERGE_HET_SITES' block after BPT_AGGREGATE_BAF's,
same path and mode.
"""
import argparse, datetime, re, shutil, sys

MARKER = "MARKER BAF_CATALOG_V1_PUBLISH"
TARGET = "conf/modules.config"
HEADER = re.compile(r"^(?P<i>[ \t]*)withName: 'BPT_AGGREGATE_BAF' \{[ \t]*$", re.M)
BLOCK = '''
{i}// {m}: het catalog (snp_sites.baf.bed v2, het_catalog.tsv) beside baf_background.tsv
{i}withName: 'BPT_MERGE_HET_SITES' {{
{i}    publishDir = [
{i}        path: {{ "${{params.outdir}}/references/twist_myeloid/baf" }},
{i}        mode: params.publish_dir_mode
{i}    ]
{i}}}
'''


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--target", default=TARGET); ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(); t = open(a.target).read()
    if MARKER in t:
        print("[skip] already applied"); sys.exit(0)
    m = HEADER.search(t)
    if not m or len(HEADER.findall(t)) != 1:
        print("[error] BPT_AGGREGATE_BAF block not found once; nothing written"); sys.exit(1)
    close = re.compile(r"^%s\}[ \t]*$" % re.escape(m.group("i")), re.M).search(t, m.end())
    if not close:
        print("[error] closing brace not found; nothing written"); sys.exit(1)
    t2 = t[:close.end()] + BLOCK.format(i=m.group("i"), m=MARKER) + t[close.end():]
    print("[ok] BPT_MERGE_HET_SITES publishDir inserted after BPT_AGGREGATE_BAF")
    print("[check] markers %d (expected 1); brace balance %d/%d" % (t2.count(MARKER), t.count("{") - t.count("}"), t2.count("{") - t2.count("}")))
    if t.count("{") - t.count("}") != t2.count("{") - t2.count("}"):
        print("[error] verification failed"); sys.exit(1)
    if not a.apply:
        print("[dry-run] no changes written"); sys.exit(0)
    b = "%s.bak_baf_catalog_publish_%s" % (a.target, datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(a.target, b); open(a.target, "w").write(t2); print("[backup] %s\n[patch] wrote %s" % (b, a.target))


if __name__ == "__main__":
    main()
