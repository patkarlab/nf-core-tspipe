#!/usr/bin/env python3
"""tools/build_variant_pon_blacklist.py -- VARIANT_PON_V1 (N13)

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

Only coding / splice consequences are considered (intronic and UTR calls are
LOW_IMPACT in the filter anyway, and the D13 spike-in regions are shown with
their own filter value).

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

AUTO_TAG = "[auto:VARIANT_PON_V1]"
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
                csq = r.get("Consequence", "")
                if not CODING_RE.search(csq):
                    continue
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
    rows, mid, hot, low_weak = [], [], [], []
    for key, e in loci.items():
        k = len(e["vafs"])
        if k < min_n:
            continue
        med = statistics.median(e["vafs"])
        chrom, pos, ref, alt = key.split(":")
        rec = {"key": key, "chrom": chrom, "pos": pos, "ref": ref, "alt": alt, "gene": e["gene"], "n": k,
               "median": med, "lo": min(e["vafs"]), "hi": max(e["vafs"]), "hgvsp": e["hgvsp"], "csq": e["csq"]}
        rec["n_supported"] = sum(1 for c in e["ncall"] if c >= a.min_callers)
        if is_hotspot(hs, e["gene"], e["hgvsp"]):
            hot.append(rec); continue
        if k >= a.ubiquitous_frac * n and (med >= a.lowvaf_max or rec["n_supported"] >= min_n):
            # present in most normals: cannot be somatic at any VAF (reference-minor allele,
            # paralog/pseudogene mis-mapping, repeat polymorphism); low-VAF ubiquity still needs
            # caller-supported calls, single-caller blips do not qualify
            rec["reason"] = "UBIQUITOUS_IN_NORMALS"
        elif med < a.lowvaf_max:
            if rec["n_supported"] < min_n:
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

    print("[ok] %d loci in >= %d/%d normals: %d ubiquitous (>= %.0f%% of normals), %d low-VAF artefacts (>= %d callers), "
          "%d local polymorphisms, %d low-VAF single-caller-only (not blacklisted), %d mid-band (not blacklisted), %d hotspot-exempt"
          % (len(rows) + len(mid) + len(hot) + len(low_weak), min_n, n, sum(1 for r in rows if r["reason"].startswith("UBIQ")), a.ubiquitous_frac * 100,
             sum(1 for r in rows if r["reason"].startswith("RECURRENT")), a.min_callers,
             sum(1 for r in rows if r["reason"].startswith("POPULATION")), len(low_weak), len(mid), len(hot)))
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
        print("[ok] cohort table -> %s" % a.report)

    # merge into the blacklist: keep every non-auto line, replace the auto block
    kept = []
    if os.path.isfile(a.blacklist):
        with open(a.blacklist) as fh:
            for line in fh:
                if AUTO_TAG in line or line.startswith("## auto:VARIANT_PON_V1"):
                    continue
                kept.append(line.rstrip("\n"))
    header_note = ["## auto:VARIANT_PON_V1 block below -- rebuilt %s from %d normals by tools/build_variant_pon_blacklist.py" % (today, n),
                   "## auto:VARIANT_PON_V1 rule: same allele in >= %d/%d normals; UBIQUITOUS >= %.0f%% of normals at any VAF; LOWVAF median < %.0f%% with >= %d callers; POLYMORPHISM median >= %.0f%%; hotspot residues exempt"
                   % (min_n, n, a.ubiquitous_frac * 100, a.lowvaf_max, a.min_callers, a.germline_min)]
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
