#!/usr/bin/env python3
"""
patch_hmf_purple_v1a.py -- option names for COBALT 3.0 and PURPLE 4.4
(MARKER HMF_PURPLE_V1a).
  hmf_cobalt.nf: -target_region -> -target_region_norm_file
  hmf_purple.nf: -amber/-cobalt -> -amber_dir/-cobalt_dir; -target_regions_ratios
                 removed (no longer a PURPLE option; the input stays declared, unused)
"""
import argparse, datetime, os, re, shutil, sys

MARKER = "MARKER HMF_PURPLE_V1a"
EDITS = {
    "modules/local/hmf_cobalt.nf": [
        (r"-target_region \$\{target_norm\} -pcf_gamma", "-target_region_norm_file ${target_norm} -pcf_gamma", "cobalt option"),
        (r"^( \* modules/local/hmf_cobalt\.nf  \(HMF_PURPLE_V1)\)", r"\1; %s: -target_region_norm_file)" % MARKER, "cobalt header"),
    ],
    "modules/local/hmf_purple.nf": [
        (r"-amber \$\{amber_dir\} -cobalt \$\{cobalt_dir\}", "-amber_dir ${amber_dir} -cobalt_dir ${cobalt_dir}", "purple dir options"),
        (r"-target_regions_bed \$\{target_bed\} -target_regions_ratios \$\{target_norm\}", "-target_regions_bed ${target_bed}", "purple ratios option removed"),
        (r"^( \* modules/local/hmf_purple\.nf  \(HMF_PURPLE_V1)\)", r"\1; %s: PURPLE 4.4 option names)" % MARKER, "purple header"),
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
            blocks = t.split('"""'); bad = [l for b in blocks[1::2] for l in b.splitlines() if re.search(r'\S\s+//', l)]
            print("   [check] markers %d; '//' in script blocks: %d" % (t.count(MARKER), len(bad)))
            if t.count(MARKER) != 1 or bad:
                print("   [error] verification failed"); failed = True; continue
            planned.append((p, t))
    if failed:
        print("[error] nothing written"); sys.exit(1)
    if not a.apply:
        print("[dry-run] %d file(s) would change" % len(planned)); sys.exit(0)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    for p, t in planned:
        shutil.copy2(p, "%s.bak_hmf_purple_v1a_%s" % (p, ts)); open(p, "w").write(t); print("[patch] wrote %s" % p)


if __name__ == "__main__":
    main()
