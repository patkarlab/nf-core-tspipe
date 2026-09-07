#!/usr/bin/env python3
"""
patch_baf_catalog_v1a.py -- base catalog under its own name (MARKER BAF_CATALOG_V1a).

The merge task staged the base catalog as snp_sites.baf.bed, the same name as
its output, so the merge wrote through the staged symlink into the asset.
Fix: the base asset is assets/<panel>/snp_sites.baf.base.bed (git mv done by
hand), the workflow reads that name, and the module stages it as
base_catalog.bed. Files: workflows/build_pon_twist.nf, modules/local/bpt_merge_het_sites.nf.
"""
import argparse, datetime, os, re, shutil, sys

MARKER = "MARKER BAF_CATALOG_V1a"
EDITS = {
    "workflows/build_pon_twist.nf": [
        (r'file\("\$\{params\.pon_assets\}/snp_sites\.baf\.bed", checkIfExists: true\)\)   // BAF_CATALOG_V1: 17p probe windows; ch_snp_bed is built below',
         'file("${params.pon_assets}/snp_sites.baf.base.bed", checkIfExists: true))   // BAF_CATALOG_V1: 17p probe windows (base); ch_snp_bed is built below; %s' % MARKER,
         "base catalog path"),
    ],
    "modules/local/bpt_merge_het_sites.nf": [
        (r"^(?P<i>[ \t]*)path base_bed[ \t]*$",
         lambda m: "%spath base_bed, stageAs: 'base_catalog.bed'   // %s: never the output's name" % (m.group("i"), MARKER),
         "stageAs for base_bed"),
    ],
}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--root", default="."); ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(); planned = []; failed = False
    for rel, edits in EDITS.items():
        p = os.path.join(a.root, rel); print("== %s" % rel)
        if not os.path.isfile(p):
            print("   [error] not found"); failed = True; continue
        t = open(p).read()
        if MARKER in t:
            print("   [skip] already applied"); continue
        for pat, rep, label in edits:
            rx = re.compile(pat, re.M); n = len(rx.findall(t))
            if n != 1:
                print("   [error] %s: %d matches" % (label, n)); failed = True; break
            t = rx.sub(rep, t, count=1); print("   [ok] %s" % label)
        else:
            planned.append((p, t))
    if failed:
        print("[error] nothing written"); sys.exit(1)
    if not a.apply:
        print("[dry-run] %d file(s) would change" % len(planned)); sys.exit(0)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    for p, t in planned:
        shutil.copy2(p, "%s.bak_baf_catalog_v1a_%s" % (p, ts)); open(p, "w").write(t); print("[patch] wrote %s" % p)


if __name__ == "__main__":
    main()
