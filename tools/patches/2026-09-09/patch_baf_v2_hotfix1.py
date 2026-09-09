#!/usr/bin/env python3
"""BAF_V2_HOTFIX1 -- cnv_consensus_multi.py: the end-of-run summary line still referenced the
V1 single-arm variable baf_verdict (NameError on the first sample with a call). It now prints the
17p row's verdict (compat) and the number of arm calls."""
import os, shutil, sys, time
P = "bin/cnv_consensus_multi.py"
OLD = "              len(intersect), baf_verdict,\n"
NEW = ('              len(intersect), "%s|%d arm call(s)" % (baf.get("verdict", "NA"),\n'
       '                  sum(1 for _, _, _, r in baf_arms if r.get("verdict") not in ("NEUTRAL", "INDETERMINATE", None))),   # BAF_V2_HOTFIX1\n')
s = open(P).read()
if "BAF_V2_HOTFIX1" in s:
    print("[skip] %s" % P); sys.exit(0)
if s.count(OLD) != 1:
    print("[error] anchor found %d times" % s.count(OLD)); sys.exit(1)
apply = "--apply" in sys.argv
print("[%s] %s" % ("patch" if apply else "plan", P))
if apply:
    bak = "%s.bak_BAF_V2_HOTFIX1_%s" % (P, time.strftime("%Y%m%d_%H%M%S")); shutil.copy2(P, bak)
    open(P, "w").write(s.replace(OLD, NEW)); os.chmod(P, 0o755); print("[done] BAF_V2_HOTFIX1 applied")
