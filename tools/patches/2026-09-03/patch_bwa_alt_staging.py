#!/usr/bin/env python3
"""Stage <fasta>.alt with the bwa-mem2 index (D1 follow-up, 2026-09-03).

PREPROCESSING stages the index files into each BWA_MEM task directory by an
explicit extension list; bwa-mem2 only becomes alt-aware when <prefix>.alt is
present in that directory, so installing the file beside the reference on disk
had no effect inside the pipeline (realign_v3 reproduced MAPQ-0 alignments).
Adds '.alt' to the staged set when the file exists beside the fasta.
Dry-run by default; --apply to write. Idempotent via MARKER.
"""
import argparse, shutil, sys, time
P = "subworkflows/local/preprocessing.nf"; MARKER = "MARKER alt_staging"
OLD = ("            .map { fasta, fai, dict ->\n"
       "                ['.amb', '.ann', '.pac', '.bwt.2bit.64', '.0123']\n"
       "                    .collect { ext -> file(\"${fasta.toString()}${ext}\") }\n"
       "            }\n")
NEW = ("            .map { fasta, fai, dict ->\n"
       "                def exts = ['.amb', '.ann', '.pac', '.bwt.2bit.64', '.0123']\n"
       "                // MARKER alt_staging: bwa-mem2 is alt-aware only when <prefix>.alt is\n"
       "                // staged beside the index in the task dir (audit 2026-09-02 D1).\n"
       "                if( file(\"${fasta.toString()}.alt\").exists() ) exts << '.alt'\n"
       "                exts.collect { ext -> file(\"${fasta.toString()}${ext}\") }\n"
       "            }\n")
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--apply", action="store_true"); a = ap.parse_args()
    s = open(P).read()
    if MARKER in s: print("[skip] already patched"); return 0
    if s.count(OLD) != 1: print("[error] anchor found %d times" % s.count(OLD)); return 1
    if not a.apply: print("[dry-run] anchor found, unique"); return 0
    bak = "%s.bak_alt_staging_%s" % (P, time.strftime("%Y%m%d_%H%M%S")); shutil.copy2(P, bak); print("[backup]", bak)
    open(P, "w").write(s.replace(OLD, NEW)); print("[patch]", P); return 0
if __name__ == "__main__": sys.exit(main())
