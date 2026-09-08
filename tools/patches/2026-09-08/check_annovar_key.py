#!/usr/bin/env python3
"""tools/patches/<date>/check_annovar_key.py -- offline verification for ANNOVAR_KEY_V1 (A18)

Usage: python3 check_annovar_key.py <VEP_ANNOTATE task dir> [--repo /goast/hemat_data/nf-core-tspipe]

Loads bin/annotate.py from the repo (patched or not), keys the cached
<sample>.hg38_multianno.txt both the old way (ANNOVAR Chr/Start/Ref/Alt) and the
new way (Otherinfo VCF record when available), and reports how many keys match
the records in <sample>.somaticseq.vcf. Also prints the CBL-type example.
Stdlib only.
"""

import argparse
import csv
import glob
import importlib.util
import os
import sys


def vcf_keys(path):
    keys = set()
    with open(path) as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            f = line.rstrip("\n").split("\t")
            if len(f) < 5:
                continue
            for alt in f[4].split(","):
                keys.add("%s:%s:%s:%s" % (f[0], f[1], f[3], alt))
    return keys


def old_keys(multianno):
    out = {}
    with open(multianno) as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            out["%s:%s:%s:%s" % (row.get("Chr", ""), row.get("Start", ""), row.get("Ref", ""), row.get("Alt", ""))] = row
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("taskdir")
    ap.add_argument("--repo", default="/goast/hemat_data/nf-core-tspipe")
    a = ap.parse_args()
    multianno = glob.glob(os.path.join(a.taskdir, "*.hg38_multianno.txt"))
    vcf = glob.glob(os.path.join(a.taskdir, "*.somaticseq.vcf"))
    if not multianno or not vcf:
        sys.exit("multianno / somaticseq.vcf not found in %s" % a.taskdir)
    spec = importlib.util.spec_from_file_location("annotate", os.path.join(a.repo, "bin", "annotate.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    patched = hasattr(mod, "_annovar_vcf_key")

    vk = vcf_keys(vcf[0])
    old = old_keys(multianno[0])
    print("VCF records: %d   ANNOVAR rows: %d" % (len(vk), len(old)))
    print("OLD keying: %d matched, %d orphan ANNOVAR rows (%.1f%%)"
          % (len(set(old) & vk), len(set(old) - vk), 100.0 * len(set(old) - vk) / max(1, len(old))))
    if patched:
        new = mod.parse_annovar_txt(multianno[0])
        print("NEW keying: %d matched, %d orphan ANNOVAR rows (%.1f%%), %d VCF records without ANNOVAR"
              % (len(set(new) & vk), len(set(new) - vk), 100.0 * len(set(new) - vk) / max(1, len(new)), len(vk - set(new))))
        leftovers = sorted(set(new) - vk)[:8]
        if leftovers:
            print("  remaining orphans (first 8):", leftovers)
        ex = [k for k in new if k.startswith("chr11:119278645:")]
        if ex:
            r = new[ex[0]]
            print("  CBL example key %s -> ANNOVAR row Chr/Start/Ref/Alt = %s %s %s %s, ClinVar-ish cols: %s"
                  % (ex[0], r.get("Chr"), r.get("Start"), r.get("Ref"), r.get("Alt"),
                     {k: v for k, v in r.items() if k and ("CLN" in k.upper() or "cosmic" in k.lower())}))
    else:
        print("bin/annotate.py is not patched (no _annovar_vcf_key); apply patch_annovar_key_v1.py first")


if __name__ == "__main__":
    main()
