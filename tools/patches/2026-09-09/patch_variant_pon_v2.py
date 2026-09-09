#!/usr/bin/env python3
"""VARIANT_PON_V2 -- tools/build_variant_pon_blacklist.py (N13 follow-up, 9 Sep 2026).

Why: two artefact families present in 8/8 run8 tumours and in 40-48/48 normals were invisible to
the cohort table and never blacklisted:
  - TERC region chr3:169765047 A>C (44/48 normals), 169765728 A>AT (48/48) and AT>A (44/48):
    non-coding consequences, skipped by the coding-only gate.
  - EGLN1 chr1:231421623 C>G (47/48) / C>T (46/48), 231421624 C>G (40/48): coding, but every
    normal call is single-caller (FreeBayes), so the "single-caller blips do not qualify" rule
    parked them as LOWVAF_SINGLE_CALLER.
Both are systematic, and a tumour where one of them picks up a second caller would PASS.

Changes (dry-run by default; --apply writes; .bak_VARIANT_PON_V2_<timestamp> backup):
  1. Every consequence is counted (the gate is removed). BLACKLIST is filter priority 0, so a
     blacklisted non-coding allele shows as BLACKLIST with its evidence on the Spike-in tab and
     the IGV table instead of an unexplained LOW_IMPACT.
  2. New tier UBIQUITOUS_SINGLE_CALLER: the same allele in >= --ubiquitous-single-frac (default
     0.75) of the normals at median VAF < --lowvaf-max with single-caller support. An allele in
     three quarters of the normals is not a blip. Hotspot residues stay exempt.
  3. The cohort table also lists every locus seen in 2..min_n-1 normals as BELOW_MIN_FRAC, so
     nothing recurrent is invisible again.
  4. Auto rows are tagged [auto:VARIANT_PON_V2]; V1 rows are replaced wholesale on rebuild.
"""
import argparse
import os
import shutil
import sys
import time

TAG = "VARIANT_PON_V2"
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
    text = replace_once(
        text,
        '"""tools/build_variant_pon_blacklist.py -- VARIANT_PON_V1 (N13)\n',
        '"""tools/build_variant_pon_blacklist.py -- VARIANT_PON_V2 (N13; V1 8 Sep, V2 9 Sep 2026)\n',
        "docstring title")
    text = replace_once(
        text,
        "Only coding / splice consequences are considered (intronic and UTR calls are\n"
        "LOW_IMPACT in the filter anyway, and the D13 spike-in regions are shown with\n"
        "their own filter value).\n",
        "Every consequence is counted (VARIANT_PON_V2). Non-coding alleles recurrent in the\n"
        "normals -- the TERC-region family in the spike-in regions, for one -- are blacklisted\n"
        "too, so they show as BLACKLIST with their evidence instead of an unexplained LOW_IMPACT.\n"
        "A fourth tier, UBIQUITOUS_SINGLE_CALLER, blacklists an allele present in\n"
        ">= --ubiquitous-single-frac of the normals at low VAF even when every normal call is\n"
        "single-caller (the EGLN1 chr1:231421623/624 FreeBayes family, 40-47/48 normals): a\n"
        "specific allele in three quarters of the cohort is not a blip. Loci seen in fewer than\n"
        "min-frac normals but in at least two are written to the cohort table as BELOW_MIN_FRAC.\n",
        "docstring gate paragraph")
    text = replace_once(
        text,
        'AUTO_TAG = "[auto:VARIANT_PON_V1]"\n',
        'AUTO_TAG = "[auto:VARIANT_PON_V2]"\n'
        'AUTO_TAG_ANY = "[auto:VARIANT_PON_V"   # V1 and V2 rows are replaced wholesale on rebuild\n',
        "auto tag")
    text = replace_once(
        text,
        '    ap.add_argument("--ubiquitous-frac", type=float, default=0.50, help="present in >= this fraction of normals -> blacklisted at any VAF")\n',
        '    ap.add_argument("--ubiquitous-frac", type=float, default=0.50, help="present in >= this fraction of normals -> blacklisted at any VAF")\n'
        '    ap.add_argument("--ubiquitous-single-frac", type=float, default=0.75,\n'
        '                    help="VARIANT_PON_V2: single-caller low-VAF allele in >= this fraction of normals -> UBIQUITOUS_SINGLE_CALLER")\n',
        "args")
    text = replace_once(
        text,
        '                csq = r.get("Consequence", "")\n'
        '                if not CODING_RE.search(csq):\n'
        '                    continue\n',
        '                csq = r.get("Consequence", "")   # VARIANT_PON_V2: every consequence is counted\n',
        "coding gate")
    text = replace_once(
        text,
        '    rows, mid, hot, low_weak = [], [], [], []\n'
        '    for key, e in loci.items():\n'
        '        k = len(e["vafs"])\n'
        '        if k < min_n:\n'
        '            continue\n'
        '        med = statistics.median(e["vafs"])\n'
        '        chrom, pos, ref, alt = key.split(":")\n'
        '        rec = {"key": key, "chrom": chrom, "pos": pos, "ref": ref, "alt": alt, "gene": e["gene"], "n": k,\n'
        '               "median": med, "lo": min(e["vafs"]), "hi": max(e["vafs"]), "hgvsp": e["hgvsp"], "csq": e["csq"]}\n'
        '        rec["n_supported"] = sum(1 for c in e["ncall"] if c >= a.min_callers)\n'
        '        if is_hotspot(hs, e["gene"], e["hgvsp"]):\n'
        '            hot.append(rec); continue\n',
        '    rows, mid, hot, low_weak, below = [], [], [], [], []\n'
        '    for key, e in loci.items():\n'
        '        k = len(e["vafs"])\n'
        '        if k < 2:\n'
        '            continue\n'
        '        med = statistics.median(e["vafs"])\n'
        '        chrom, pos, ref, alt = key.split(":")\n'
        '        rec = {"key": key, "chrom": chrom, "pos": pos, "ref": ref, "alt": alt, "gene": e["gene"], "n": k,\n'
        '               "median": med, "lo": min(e["vafs"]), "hi": max(e["vafs"]), "hgvsp": e["hgvsp"], "csq": e["csq"]}\n'
        '        rec["n_supported"] = sum(1 for c in e["ncall"] if c >= a.min_callers)\n'
        '        if k < min_n:\n'
        '            below.append(rec); continue   # VARIANT_PON_V2: reported, not blacklisted\n'
        '        if is_hotspot(hs, e["gene"], e["hgvsp"]):\n'
        '            hot.append(rec); continue\n',
        "classification head")
    text = replace_once(
        text,
        '        elif med < a.lowvaf_max:\n'
        '            if rec["n_supported"] < min_n:\n'
        '                low_weak.append(rec); continue   # only single-caller blips in the normals\n'
        '            rec["reason"] = "RECURRENT_IN_NORMALS_LOWVAF"\n',
        '        elif med < a.lowvaf_max:\n'
        '            if rec["n_supported"] < min_n:\n'
        '                if k >= a.ubiquitous_single_frac * n:\n'
        '                    # VARIANT_PON_V2: the same allele in >= 75% of normals is systematic even when\n'
        '                    # each normal call is single-caller (FreeBayes homopolymer / paralog families)\n'
        '                    rec["reason"] = "UBIQUITOUS_SINGLE_CALLER"\n'
        '                    rows.append(rec); continue\n'
        '                low_weak.append(rec); continue   # only single-caller blips in the normals\n'
        '            rec["reason"] = "RECURRENT_IN_NORMALS_LOWVAF"\n',
        "single-caller tier")
    text = replace_once(
        text,
        '    print("[ok] %d loci in >= %d/%d normals: %d ubiquitous (>= %.0f%% of normals), %d low-VAF artefacts (>= %d callers), "\n'
        '          "%d local polymorphisms, %d low-VAF single-caller-only (not blacklisted), %d mid-band (not blacklisted), %d hotspot-exempt"\n'
        '          % (len(rows) + len(mid) + len(hot) + len(low_weak), min_n, n, sum(1 for r in rows if r["reason"].startswith("UBIQ")), a.ubiquitous_frac * 100,\n'
        '             sum(1 for r in rows if r["reason"].startswith("RECURRENT")), a.min_callers,\n'
        '             sum(1 for r in rows if r["reason"].startswith("POPULATION")), len(low_weak), len(mid), len(hot)))\n',
        '    print("[ok] %d loci in >= %d/%d normals: %d ubiquitous (>= %.0f%% of normals), %d ubiquitous single-caller (>= %.0f%% of normals, V2), "\n'
        '          "%d low-VAF artefacts (>= %d callers), %d local polymorphisms, %d low-VAF single-caller-only (not blacklisted), "\n'
        '          "%d mid-band (not blacklisted), %d hotspot-exempt; %d loci in 2..%d normals reported as BELOW_MIN_FRAC"\n'
        '          % (len(rows) + len(mid) + len(hot) + len(low_weak), min_n, n,\n'
        '             sum(1 for r in rows if r["reason"] == "UBIQUITOUS_IN_NORMALS"), a.ubiquitous_frac * 100,\n'
        '             sum(1 for r in rows if r["reason"] == "UBIQUITOUS_SINGLE_CALLER"), a.ubiquitous_single_frac * 100,\n'
        '             sum(1 for r in rows if r["reason"].startswith("RECURRENT")), a.min_callers,\n'
        '             sum(1 for r in rows if r["reason"].startswith("POPULATION")), len(low_weak), len(mid), len(hot), len(below), min_n - 1))\n'
        '    half = [r for r in low_weak if r["n"] >= 0.5 * n]\n'
        '    if half:\n'
        '        print("[review] %d single-caller low-VAF alleles in >= 50%% but < %.0f%% of normals, NOT blacklisted (lower --ubiquitous-single-frac to include):"\n'
        '              % (len(half), a.ubiquitous_single_frac * 100))\n'
        '        for r in sorted(half, key=lambda r: -r["n"])[:20]:\n'
        '            print("     %-8s %-40s n=%2d median %5.1f%%  %s" % (r["gene"], (r["hgvsp"] or r["csq"])[:40], r["n"], r["median"], r["key"]))\n',
        "summary")
    text = replace_once(
        text,
        '            for r in hot:\n'
        '                fh.write("\\t".join(str(x) for x in [r["key"], r["gene"], r["n"], round(r["median"], 1), round(r["lo"], 1), round(r["hi"], 1), r["hgvsp"], r["csq"], "HOTSPOT_EXEMPT"]) + "\\n")\n',
        '            for r in hot:\n'
        '                fh.write("\\t".join(str(x) for x in [r["key"], r["gene"], r["n"], round(r["median"], 1), round(r["lo"], 1), round(r["hi"], 1), r["hgvsp"], r["csq"], "HOTSPOT_EXEMPT"]) + "\\n")\n'
        '            for r in sorted(below, key=lambda r: (-r["n"], r["chrom"], int(r["pos"]))):   # VARIANT_PON_V2\n'
        '                fh.write("\\t".join(str(x) for x in [r["key"], r["gene"], r["n"], round(r["median"], 1), round(r["lo"], 1), round(r["hi"], 1), r["hgvsp"], r["csq"], "BELOW_MIN_FRAC"]) + "\\n")\n',
        "report below")
    text = replace_once(
        text,
        '                if AUTO_TAG in line or line.startswith("## auto:VARIANT_PON_V1"):\n',
        '                if AUTO_TAG_ANY in line or line.startswith("## auto:VARIANT_PON_V"):   # VARIANT_PON_V2: replaces V1 rows too\n',
        "merge tag")
    text = replace_once(
        text,
        '    header_note = ["## auto:VARIANT_PON_V1 block below -- rebuilt %s from %d normals by tools/build_variant_pon_blacklist.py" % (today, n),\n'
        '                   "## auto:VARIANT_PON_V1 rule: same allele in >= %d/%d normals; UBIQUITOUS >= %.0f%% of normals at any VAF; LOWVAF median < %.0f%% with >= %d callers; POLYMORPHISM median >= %.0f%%; hotspot residues exempt"\n'
        '                   % (min_n, n, a.ubiquitous_frac * 100, a.lowvaf_max, a.min_callers, a.germline_min)]\n',
        '    header_note = ["## auto:VARIANT_PON_V2 block below -- rebuilt %s from %d normals by tools/build_variant_pon_blacklist.py" % (today, n),\n'
        '                   "## auto:VARIANT_PON_V2 rule: every consequence; same allele in >= %d/%d normals; UBIQUITOUS >= %.0f%% of normals at any VAF (caller-supported if low VAF); "\n'
        '                   "UBIQUITOUS_SINGLE_CALLER >= %.0f%% of normals at median < %.0f%% even single-caller; LOWVAF median < %.0f%% with >= %d callers; POLYMORPHISM median >= %.0f%%; hotspot residues exempt"\n'
        '                   % (min_n, n, a.ubiquitous_frac * 100, a.ubiquitous_single_frac * 100, a.lowvaf_max, a.lowvaf_max, a.min_callers, a.germline_min)]\n',
        "header note")
    return text, "patch"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--repo", default=".")
    args = ap.parse_args()
    os.chdir(args.repo)
    if not os.path.isfile(TARGET):
        print("[error] missing %s" % TARGET); sys.exit(2)
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
