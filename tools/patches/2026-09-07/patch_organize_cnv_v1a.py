#!/usr/bin/env python3
"""patch_organize_cnv_v1a.py -- consensus emit names in the ORGANIZE joins (MARKER ORG_CNV_V1a):
CNV_CONSENSUS_MULTI.out.g/s/j -> .out.genes/.out.segments/.out.json (the recon had truncated the names)."""
import argparse, datetime, re, shutil, sys
MARKER = "MARKER ORG_CNV_V1a"; TARGET = "workflows/tspipe.nf"
EDITS = [(r"\.join\(CNV_CONSENSUS_MULTI\.out\.g\)(\s*)// \+ cnv_consensus_genes \(MARKER ORG_CNV_V1\)",
          r".join(CNV_CONSENSUS_MULTI.out.genes)\1// + cnv_consensus_genes (MARKER ORG_CNV_V1; %s)" % MARKER, "genes"),
         (r"\.join\(CNV_CONSENSUS_MULTI\.out\.s\)(\s*)// \+ cnv_consensus_segments", r".join(CNV_CONSENSUS_MULTI.out.segments)\1// + cnv_consensus_segments", "segments"),
         (r"\.join\(CNV_CONSENSUS_MULTI\.out\.j\)(\s*)// \+ cnv_consensus_json", r".join(CNV_CONSENSUS_MULTI.out.json)\1// + cnv_consensus_json", "json")]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--target", default=TARGET); ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(); t = open(a.target).read()
    if MARKER in t:
        print("[skip] already applied"); sys.exit(0)
    for pat, rep, label in EDITS:
        n = len(re.findall(pat, t))
        if n != 1:
            print("[error] %s: %d matches; nothing written" % (label, n)); sys.exit(1)
        t = re.sub(pat, rep, t, count=1); print("[ok] %s" % label)
    if not a.apply:
        print("[dry-run]"); sys.exit(0)
    b = "%s.bak_org_cnv_v1a_%s" % (a.target, datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(a.target, b); open(a.target, "w").write(t); print("[patch] wrote %s" % a.target)

if __name__ == "__main__":
    main()
