#!/usr/bin/env python3
"""tools/build_variant_pon_blacklist.py -- VARIANT_PON_V2 (N13; V1 8 Sep, V2 9 Sep 2026)

Build automatic SNV/indel blacklist rows from the panel-of-normals cohort and
merge them into the 11-column blacklist read by VARIANT_FILTER
(references/blacklist_file.tsv; matcher bin/apply_blacklist.py).

Two tiers, both requiring the same allele (chr:pos:ref:alt) in at least
--min-frac of the normals:
  RECURRENT_IN_NORMALS_LOWVAF     median VAF < --lowvaf-max   (systematic artefact:
                                  pseudogene mis-mapping, homopolymer slippage)
  POPULATION_POLYMORPHISM_LOCAL   median VAF >= --germline-min (a germline polymorphism
                                  of the local population that gnomAD does not carry)
Loci with a median VAF between the two bands are reported but not blacklisted.
Hotspot residues (myeloid_hotspots.tsv, Gene + residue) are never blacklisted; anything
the rules would have caught there is printed for a human look (CHIP in normals is
real biology).

Every consequence is counted (VARIANT_PON_V2), but a non-coding allele is blacklisted
only through the low-VAF artefact tiers (VARIANT_PON_V2B): the TERC-region family in
the spike-in regions shows as BLACKLIST with its evidence instead of an unexplained
LOW_IMPACT, while the CNV backbone's common SNPs and other non-coding alleles recurrent
at germline VAF are written to the cohort table as NONCODING_POLYMORPHISM, not blacklisted.
A fourth tier, UBIQUITOUS_SINGLE_CALLER, blacklists an allele present in
>= --ubiquitous-single-frac of the normals at low VAF even when every normal call is
single-caller (the EGLN1 chr1:231421623/624 FreeBayes family, 40-47/48 normals): a
specific allele in three quarters of the cohort is not a blip. Loci seen in fewer than
min-frac normals but in at least two are written to the cohort table as BELOW_MIN_FRAC.

Rows written by this tool carry reason strings ending in ' [auto:VARIANT_PON_V1]'
and are replaced wholesale on every rebuild; curated rows are never touched.

Usage:
  tools/build_variant_pon_blacklist.py \\
      --normals-dir /goast/hemat_data/pon_twist/realign_v4 \\
      --normals-dir /goast/hemat_data/pon_twist/realign_v4_female \\
      --hotspots assets/myeloid_hotspots.tsv \\
      --blacklist references/blacklist_file.tsv \\
      [--min-frac 0.10] [--lowvaf-max 20] [--germline-min 35] [--report /tmp/pon_variants.tsv]
Pure stdlib.
"""

import argparse
import csv
import glob
import os
import re
import statistics
import sys
import time

AUTO_TAG = "[auto:VARIANT_PON_V2]"
AUTO_TAG_ANY = "[auto:VARIANT_PON_V"   # V1 and V2 rows are replaced wholesale on rebuild
CODING_RE = re.compile(r"missense|stop_gained|stop_lost|start_lost|frameshift|inframe|protein_altering|"
                       r"synonymous|splice_acceptor|splice_donor|coding_sequence|incomplete_terminal")
RESIDUE_RE = re.compile(r"p\.(?:[A-Z][a-z]{2}|[A-Z])(\d+)")


def read_hotspots(path):
    """Gene -> set of residue numbers (or ranges) from myeloid_hotspots.tsv."""
    hs = {}
    if not path or not os.path.isfile(path):
        return hs
    with open(path) as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            g = (r.get("Gene") or "").strip()
            h = (r.get("Hotspot") or "").strip()
            m = re.match(r"^[A-Z]?(\d+)(?:-(\d+))?", h)
            if not g or not m:
                continue
            lo = int(m.group(1)); hi = int(m.group(2) or lo)
            hs.setdefault(g, []).append((lo, hi))
    return hs


def is_hotspot(hs, gene, hgvsp):
    if gene not in hs:
        return False
    m = RESIDUE_RE.search(str(hgvsp or ""))
    if not m:
        return False
    n = int(m.group(1))
    return any(lo <= n <= hi for lo, hi in hs[gene])


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--normals-dir", action="append", required=True)
    ap.add_argument("--hotspots", default=None)
    ap.add_argument("--blacklist", required=True, help="references/blacklist_file.tsv (updated in place)")
    ap.add_argument("--min-frac", type=float, default=0.10)
    ap.add_argument("--lowvaf-max", type=float, default=25.0, help="percent")
    ap.add_argument("--germline-min", type=float, default=35.0, help="percent")
    ap.add_argument("--min-callers", type=int, default=2, help="LOWVAF tier: the normals' calls must have >= this many callers in >= min-frac of normals")
    ap.add_argument("--ubiquitous-frac", type=float, default=0.50, help="present in >= this fraction of normals -> blacklisted at any VAF")
    ap.add_argument("--ubiquitous-single-frac", type=float, default=0.75,
                    help="VARIANT_PON_V2: single-caller low-VAF allele in >= this fraction of normals -> UBIQUITOUS_SINGLE_CALLER")
    ap.add_argument("--report", default=None, help="write the full per-locus cohort table here")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    files = []
    for d in a.normals_dir:
        files += glob.glob(os.path.join(d, "*", "clinical", "*.somaticseq.filtered.tsv"))
    files = sorted(set(files))
    if not files:
        sys.exit("no *.somaticseq.filtered.tsv under the normals directories")
    n = len(files)
    print("[ok] %d normal tables" % n)

    loci = {}   # key -> {"vafs": [], "gene", "csq", "hgvsp", "hgvsc"}
    for f in files:
        seen = set()
        with open(f) as fh:
            for r in csv.DictReader(fh, delimiter="\t"):
                if r.get("VariantCaller_Count", "-1") == "-1":
                    continue   # annotation orphans
                csq = r.get("Consequence", "")   # VARIANT_PON_V2: every consequence is counted
                key = "%s:%s:%s:%s" % (r["Chr"], r["Start"], r["Ref"], r["Alt"])
                if key in seen:
                    continue
                seen.add(key)
                try:
                    vaf = float(r.get("VAF_pct", "nan"))
                except ValueError:
                    continue
                if vaf != vaf:
                    continue
                try:
                    ncall = int(r.get("VariantCaller_Count", "0"))
                except ValueError:
                    ncall = 0
                e = loci.setdefault(key, {"vafs": [], "ncall": [], "gene": r.get("Gene", ""), "csq": csq,
                                          "hgvsp": r.get("HGVSp", ""), "hgvsc": r.get("HGVSc", "")})
                e["vafs"].append(vaf)
                e["ncall"].append(ncall)

    hs = read_hotspots(a.hotspots)
    min_n = max(2, int(round(a.min_frac * n + 0.4999)))
    rows, mid, hot, low_weak, below, noncoding_poly = [], [], [], [], [], []
    for key, e in loci.items():
        k = len(e["vafs"])
        if k < 2:
            continue
        med = statistics.median(e["vafs"])
        chrom, pos, ref, alt = key.split(":")
        rec = {"key": key, "chrom": chrom, "pos": pos, "ref": ref, "alt": alt, "gene": e["gene"], "n": k,
               "median": med, "lo": min(e["vafs"]), "hi": max(e["vafs"]), "hgvsp": e["hgvsp"], "csq": e["csq"]}
        rec["n_supported"] = sum(1 for c in e["ncall"] if c >= a.min_callers)
        rec["coding"] = bool(CODING_RE.search(e["csq"]))   # VARIANT_PON_V2B
        if k < min_n:
            below.append(rec); continue   # VARIANT_PON_V2: reported, not blacklisted
        if is_hotspot(hs, e["gene"], e["hgvsp"]):
            hot.append(rec); continue
        if not rec["coding"] and med >= a.lowvaf_max:
            noncoding_poly.append(rec); continue   # VARIANT_PON_V2B: germline-VAF non-coding recurrence, not an artefact
        if k >= a.ubiquitous_frac * n and (med >= a.lowvaf_max or rec["n_supported"] >= min_n):
            # present in most normals: cannot be somatic at any VAF (reference-minor allele,
            # paralog/pseudogene mis-mapping, repeat polymorphism); low-VAF ubiquity still needs
            # caller-supported calls, single-caller blips do not qualify
            rec["reason"] = "UBIQUITOUS_IN_NORMALS"
        elif med < a.lowvaf_max:
            if rec["n_supported"] < min_n:
                if k >= a.ubiquitous_single_frac * n:
                    # VARIANT_PON_V2: the same allele in >= 75% of normals is systematic even when
                    # each normal call is single-caller (FreeBayes homopolymer / paralog families)
                    rec["reason"] = "UBIQUITOUS_SINGLE_CALLER"
                    rows.append(rec); continue
                low_weak.append(rec); continue   # only single-caller blips in the normals
            rec["reason"] = "RECURRENT_IN_NORMALS_LOWVAF"
        elif med >= a.germline_min:
            rec["reason"] = "POPULATION_POLYMORPHISM_LOCAL"
        else:
            mid.append(rec); continue
        rows.append(rec)
    rows.sort(key=lambda r: (r["reason"], r["chrom"], int(r["pos"])))

    today = time.strftime("%Y-%m-%d")
    out_lines = []
    for r in rows:
        ev = "%d/%d normals, VAF median %.1f%% (%.1f-%.1f); %s %s" % (
            r["n"], n, r["median"], r["lo"], r["hi"], r["hgvsp"] or r["csq"].split("&")[0], AUTO_TAG)
        out_lines.append("\t".join([r["chrom"], r["pos"], r["pos"], "exact", r["pos"], r["ref"], r["alt"],
                                    r["gene"], r["reason"], ev, today]))

    print("[ok] %d loci in >= %d/%d normals: %d ubiquitous (>= %.0f%% of normals), %d ubiquitous single-caller (>= %.0f%% of normals, V2), "
          "%d low-VAF artefacts (>= %d callers), %d local polymorphisms, %d low-VAF single-caller-only (not blacklisted), "
          "%d mid-band (not blacklisted), %d hotspot-exempt; %d loci in 2..%d normals reported as BELOW_MIN_FRAC; "
          "%d non-coding germline-VAF recurrences reported as NONCODING_POLYMORPHISM (V2b, not blacklisted)"
          % (len(rows) + len(mid) + len(hot) + len(low_weak), min_n, n,
             sum(1 for r in rows if r["reason"] == "UBIQUITOUS_IN_NORMALS"), a.ubiquitous_frac * 100,
             sum(1 for r in rows if r["reason"] == "UBIQUITOUS_SINGLE_CALLER"), a.ubiquitous_single_frac * 100,
             sum(1 for r in rows if r["reason"].startswith("RECURRENT")), a.min_callers,
             sum(1 for r in rows if r["reason"].startswith("POPULATION")), len(low_weak), len(mid), len(hot), len(below), min_n - 1,
             len(noncoding_poly)))
    half = [r for r in low_weak if r["n"] >= 0.5 * n]
    if half:
        print("[review] %d single-caller low-VAF alleles in >= 50%% but < %.0f%% of normals, NOT blacklisted (lower --ubiquitous-single-frac to include):"
              % (len(half), a.ubiquitous_single_frac * 100))
        for r in sorted(half, key=lambda r: -r["n"])[:20]:
            print("     %-8s %-40s n=%2d median %5.1f%%  %s" % (r["gene"], (r["hgvsp"] or r["csq"])[:40], r["n"], r["median"], r["key"]))
    for r in rows[:60]:
        print("     %-30s %-8s %-40s n=%2d median %5.1f%%  %s" % (r["reason"], r["gene"], r["hgvsp"][:40], r["n"], r["median"], r["key"]))
    if len(rows) > 60:
        print("     ... %d more" % (len(rows) - 60))
    if hot:
        print("[review] hotspot residues recurrent in normals (NOT blacklisted):")
        for r in hot:
            print("     %-8s %-40s n=%2d median %5.1f%%  %s" % (r["gene"], r["hgvsp"][:40], r["n"], r["median"], r["key"]))
    if mid:
        print("[info] %d loci with median VAF between %.0f%% and %.0f%% (not blacklisted); first 10:" % (len(mid), a.lowvaf_max, a.germline_min))
        for r in mid[:10]:
            print("     %-8s %-40s n=%2d median %5.1f%%  %s" % (r["gene"], r["hgvsp"][:40], r["n"], r["median"], r["key"]))

    if a.report:
        with open(a.report, "w") as fh:
            fh.write("key\tgene\tn_normals\tmedian_vaf\tmin_vaf\tmax_vaf\thgvsp\tconsequence\tdisposition\n")
            for r in rows:
                fh.write("\t".join(str(x) for x in [r["key"], r["gene"], r["n"], round(r["median"], 1), round(r["lo"], 1), round(r["hi"], 1), r["hgvsp"], r["csq"], r["reason"]]) + "\n")
            for r in mid:
                fh.write("\t".join(str(x) for x in [r["key"], r["gene"], r["n"], round(r["median"], 1), round(r["lo"], 1), round(r["hi"], 1), r["hgvsp"], r["csq"], "MID_BAND"]) + "\n")
            for r in low_weak:
                fh.write("\t".join(str(x) for x in [r["key"], r["gene"], r["n"], round(r["median"], 1), round(r["lo"], 1), round(r["hi"], 1), r["hgvsp"], r["csq"], "LOWVAF_SINGLE_CALLER"]) + "\n")
            for r in hot:
                fh.write("\t".join(str(x) for x in [r["key"], r["gene"], r["n"], round(r["median"], 1), round(r["lo"], 1), round(r["hi"], 1), r["hgvsp"], r["csq"], "HOTSPOT_EXEMPT"]) + "\n")
            for r in sorted(noncoding_poly, key=lambda r: (-r["n"], r["chrom"], int(r["pos"]))):   # VARIANT_PON_V2B
                fh.write("\t".join(str(x) for x in [r["key"], r["gene"], r["n"], round(r["median"], 1), round(r["lo"], 1), round(r["hi"], 1), r["hgvsp"], r["csq"], "NONCODING_POLYMORPHISM"]) + "\n")
            for r in sorted(below, key=lambda r: (-r["n"], r["chrom"], int(r["pos"]))):   # VARIANT_PON_V2
                fh.write("\t".join(str(x) for x in [r["key"], r["gene"], r["n"], round(r["median"], 1), round(r["lo"], 1), round(r["hi"], 1), r["hgvsp"], r["csq"], "BELOW_MIN_FRAC"]) + "\n")
        print("[ok] cohort table -> %s" % a.report)

    # merge into the blacklist: keep every non-auto line, replace the auto block
    kept = []
    if os.path.isfile(a.blacklist):
        with open(a.blacklist) as fh:
            for line in fh:
                if AUTO_TAG_ANY in line or line.startswith("## auto:VARIANT_PON_V"):   # VARIANT_PON_V2: replaces V1 rows too
                    continue
                kept.append(line.rstrip("\n"))
    header_note = ["## auto:VARIANT_PON_V2 block below -- rebuilt %s from %d normals by tools/build_variant_pon_blacklist.py" % (today, n),
                   "## auto:VARIANT_PON_V2 rule (V2b): coding alleles in >= %d/%d normals; non-coding alleles only through the low-VAF tiers; UBIQUITOUS >= %.0f%% of normals at any VAF (caller-supported if low VAF); "
                   "UBIQUITOUS_SINGLE_CALLER >= %.0f%% of normals at median < %.0f%% even single-caller; LOWVAF median < %.0f%% with >= %d callers; POLYMORPHISM median >= %.0f%%; hotspot residues exempt"
                   % (min_n, n, a.ubiquitous_frac * 100, a.ubiquitous_single_frac * 100, a.lowvaf_max, a.lowvaf_max, a.min_callers, a.germline_min)]
    new_text = "\n".join(kept).rstrip("\n") + "\n" + "\n".join(header_note) + "\n" + "\n".join(out_lines) + "\n"
    if a.dry_run:
        print("[dry-run] would write %d curated + %d auto rows to %s" % (sum(1 for l in kept if l and not l.startswith("#")), len(out_lines), a.blacklist))
        return 0
    if os.path.isfile(a.blacklist):
        bak = a.blacklist + ".bak_variant_pon_%s" % time.strftime("%Y%m%d_%H%M%S")
        os.replace(a.blacklist, bak)
        print("[ok] previous blacklist -> %s" % bak)
    with open(a.blacklist, "w") as fh:
        fh.write(new_text)
    print("[ok] wrote %s: %d curated lines kept, %d auto rows" % (a.blacklist, sum(1 for l in kept if l and not l.startswith("#")), len(out_lines)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
