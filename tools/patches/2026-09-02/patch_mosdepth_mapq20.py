#!/usr/bin/env python3
"""Coverage QC at MAPQ 20 (decision D2, docs/audit/2026-09-02).

Six panel genes carry MAPQ-0 reads under the non-alt-aware index and were
reported as covered because mosdepth counted at MAPQ 0. Adds --mapq 20 to
every mosdepth QC invocation; --flag 772 (duplicates included) unchanged.
Dry-run by default; --apply to write. Idempotent via MARKER.
"""
import argparse, shutil, sys, time
MARKER = "MARKER mapq20_qc"
TAG = "mapq20"
EDITS = [
    ("modules/local/mosdepth.nf",
     "        mosdepth \\\\\n            --by ${bed} \\\\\n            --threads ${task.cpus} \\\\\n            --no-per-base \\\\\n            --flag 772 \\\\\n",
     "        # --mapq 20: MARKER mapq20_qc -- exclude MAPQ<20 reads (alt-contig blind spot, 2026-09-02)\n"
     "        mosdepth \\\\\n            --by ${bed} \\\\\n            --threads ${task.cpus} \\\\\n            --no-per-base \\\\\n            --flag 772 \\\\\n            --mapq 20 \\\\\n"),
    ("bin/backbone_depth_qc.py",
     '    cmd = ("mosdepth --by {bed} --flag 772 --no-per-base',
     '    # MARKER mapq20_qc: --mapq 20 excludes MAPQ<20 reads (alt-contig blind spot, 2026-09-02)\n'
     '    cmd = ("mosdepth --by {bed} --flag 772 --mapq 20 --no-per-base'),
    ("bin/capture_conformity_gate.py",
     '    run(["mosdepth", "-t", str(args.threads), "--flag", "772", "--no-per-base",',
     '    # MARKER mapq20_qc: --mapq 20 excludes MAPQ<20 reads (alt-contig blind spot, 2026-09-02)\n'
     '    run(["mosdepth", "-t", str(args.threads), "--flag", "772", "--mapq", "20", "--no-per-base",'),
]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--apply", action="store_true"); a = ap.parse_args()
    ts = time.strftime("%Y%m%d_%H%M%S"); rc = 0
    for path, old, new in EDITS:
        s = open(path).read()
        if MARKER in s: print("[skip] already patched:", path); continue
        if s.count(old) != 1: print("[error] anchor found %d times in %s" % (s.count(old), path)); rc = 1; continue
        if not a.apply: print("[dry-run] %s: ready" % path); continue
        bak = "%s.bak_%s_%s" % (path, TAG, ts); shutil.copy2(path, bak); print("[backup]", bak)
        open(path, "w").write(s.replace(old, new)); print("[patch]", path)
    return rc
if __name__ == "__main__": sys.exit(main())
