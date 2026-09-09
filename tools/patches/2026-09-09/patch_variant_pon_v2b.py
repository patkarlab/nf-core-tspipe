#!/usr/bin/env python3
"""VARIANT_PON_V2b -- applies on top of VARIANT_PON_V2 in tools/build_variant_pon_blacklist.py.

The V2 dry run on the 48 normals proposed 6,364 auto rows (V1: 259) because counting every
consequence pulls in the CNV backbone: 3,069 tiles placed on common SNPs, heterozygous in most
people. Those are germline polymorphisms, not artefacts, and must not be blacklisted.

Rule after V2b:
  - coding alleles: classified exactly as in V1 (UBIQUITOUS_IN_NORMALS, RECURRENT_IN_NORMALS_LOWVAF,
    POPULATION_POLYMORPHISM_LOCAL) plus the V2 UBIQUITOUS_SINGLE_CALLER tier.
  - non-coding alleles: blacklisted only through the low-VAF artefact tiers (median < --lowvaf-max):
    UBIQUITOUS_IN_NORMALS at low VAF, RECURRENT_IN_NORMALS_LOWVAF, UBIQUITOUS_SINGLE_CALLER.
    Non-coding alleles recurrent at germline VAF are written to the cohort table as
    NONCODING_POLYMORPHISM and left to the spike-in germline lens.
Dry-run by default; --apply writes; .bak_VARIANT_PON_V2B_<timestamp> backup.
"""
import argparse
import os
import shutil
import sys
import time

TAG = "VARIANT_PON_V2B"
STAMP = time.strftime("%Y%m%d_%H%M%S")
TARGET = "tools/build_variant_pon_blacklist.py"


class PatchError(Exception):
    pass


def replace_once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise PatchError("%s: anchor found %d times (expected 1): %r" % (label, n, old[:80]))
    return text.replace(old, new)


def patch(text):
    if TAG in text:
        return text, "skip"
    if "VARIANT_PON_V2" not in text:
        raise PatchError("VARIANT_PON_V2 not applied yet")
    text = replace_once(
        text,
        "Every consequence is counted (VARIANT_PON_V2). Non-coding alleles recurrent in the\n"
        "normals -- the TERC-region family in the spike-in regions, for one -- are blacklisted\n"
        "too, so they show as BLACKLIST with their evidence instead of an unexplained LOW_IMPACT.\n",
        "Every consequence is counted (VARIANT_PON_V2), but a non-coding allele is blacklisted\n"
        "only through the low-VAF artefact tiers (VARIANT_PON_V2B): the TERC-region family in\n"
        "the spike-in regions shows as BLACKLIST with its evidence instead of an unexplained\n"
        "LOW_IMPACT, while the CNV backbone's common SNPs and other non-coding alleles recurrent\n"
        "at germline VAF are written to the cohort table as NONCODING_POLYMORPHISM, not blacklisted.\n",
        "docstring")
    text = replace_once(
        text,
        '    rows, mid, hot, low_weak, below = [], [], [], [], []\n',
        '    rows, mid, hot, low_weak, below, noncoding_poly = [], [], [], [], [], []\n',
        "lists")
    text = replace_once(
        text,
        '        rec["n_supported"] = sum(1 for c in e["ncall"] if c >= a.min_callers)\n'
        '        if k < min_n:\n',
        '        rec["n_supported"] = sum(1 for c in e["ncall"] if c >= a.min_callers)\n'
        '        rec["coding"] = bool(CODING_RE.search(e["csq"]))   # VARIANT_PON_V2B\n'
        '        if k < min_n:\n',
        "coding flag")
    text = replace_once(
        text,
        '        if k >= a.ubiquitous_frac * n and (med >= a.lowvaf_max or rec["n_supported"] >= min_n):\n',
        '        if not rec["coding"] and med >= a.lowvaf_max:\n'
        '            noncoding_poly.append(rec); continue   # VARIANT_PON_V2B: germline-VAF non-coding recurrence, not an artefact\n'
        '        if k >= a.ubiquitous_frac * n and (med >= a.lowvaf_max or rec["n_supported"] >= min_n):\n',
        "noncoding branch")
    text = replace_once(
        text,
        '          "%d mid-band (not blacklisted), %d hotspot-exempt; %d loci in 2..%d normals reported as BELOW_MIN_FRAC"\n',
        '          "%d mid-band (not blacklisted), %d hotspot-exempt; %d loci in 2..%d normals reported as BELOW_MIN_FRAC; "\n'
        '          "%d non-coding germline-VAF recurrences reported as NONCODING_POLYMORPHISM (V2b, not blacklisted)"\n',
        "summary text")
    text = replace_once(
        text,
        '             sum(1 for r in rows if r["reason"].startswith("POPULATION")), len(low_weak), len(mid), len(hot), len(below), min_n - 1))\n',
        '             sum(1 for r in rows if r["reason"].startswith("POPULATION")), len(low_weak), len(mid), len(hot), len(below), min_n - 1,\n'
        '             len(noncoding_poly)))\n',
        "summary args")
    text = replace_once(
        text,
        '            for r in sorted(below, key=lambda r: (-r["n"], r["chrom"], int(r["pos"]))):   # VARIANT_PON_V2\n',
        '            for r in sorted(noncoding_poly, key=lambda r: (-r["n"], r["chrom"], int(r["pos"]))):   # VARIANT_PON_V2B\n'
        '                fh.write("\\t".join(str(x) for x in [r["key"], r["gene"], r["n"], round(r["median"], 1), round(r["lo"], 1), round(r["hi"], 1), r["hgvsp"], r["csq"], "NONCODING_POLYMORPHISM"]) + "\\n")\n'
        '            for r in sorted(below, key=lambda r: (-r["n"], r["chrom"], int(r["pos"]))):   # VARIANT_PON_V2\n',
        "report")
    text = replace_once(
        text,
        '                   "## auto:VARIANT_PON_V2 rule: every consequence; same allele in >= %d/%d normals; UBIQUITOUS >= %.0f%% of normals at any VAF (caller-supported if low VAF); "\n',
        '                   "## auto:VARIANT_PON_V2 rule (V2b): coding alleles in >= %d/%d normals; non-coding alleles only through the low-VAF tiers; UBIQUITOUS >= %.0f%% of normals at any VAF (caller-supported if low VAF); "\n',
        "header note")
    return text, "patch"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--repo", default=".")
    args = ap.parse_args()
    os.chdir(args.repo)
    with open(TARGET) as f:
        text = f.read()
    try:
        new, status = patch(text)
    except PatchError as e:
        print("[error] %s\n[error] nothing written" % e); sys.exit(1)
    print("[%s] %s" % (status, TARGET))
    if not args.apply:
        print("[dry-run] re-run with --apply to write"); return
    if status == "patch":
        bak = "%s.bak_%s_%s" % (TARGET, TAG, STAMP)
        shutil.copy2(TARGET, bak); print("[backup] %s" % bak)
        with open(TARGET, "w") as f:
            f.write(new)
        os.chmod(TARGET, 0o755)
        print("[write] %s" % TARGET)
    print("[done] %s applied" % TAG)


if __name__ == "__main__":
    main()
