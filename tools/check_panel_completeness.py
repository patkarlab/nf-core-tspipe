#!/usr/bin/env python3
"""
check_panel_completeness.py

Release gate. Asserts that the variant-calling interval list contains the
entire manufactured capture space, and that named clinical hotspots are
inside it.

Why this exists
---------------
Until 12 Sep 2026 params.bed pointed at panel.combined.filtered.bed, a
derived asset built from only two of the five Main probe categories. IDH1
exon 4, IDH2 exon 4 and BRAF exon 15 were sequenced at 900-1700x and never
examined by any caller, in every case reported on the assay. Nothing in
verify_install.sh could detect it: every file existed and every checksum
matched. The file was intact and wrong.

A checksum proves a file is the one you expected. It does not prove the
file is correct. This gate checks the property that matters -- no probe
region is missing from the callable space.

Exit status
-----------
0 = PASS, 1 = FAIL (or the inputs could not be read).

Usage
-----
    python3 check_panel_completeness.py --assets assets/twist_myeloid
    python3 check_panel_completeness.py --assets <dir> --calling-bed <path>
"""

import argparse
import os
import sys

MAIN_BED = "probes_ok_ACTREC_Myeloid_TE-99430185_hg38_Main_260602213057.bed"
BACKBONE_BED = "probes_ok_ACTREC_Myeloid_TE-99430185_CNV_Backbone_Spikein_260603122240.bed"
BACKBONE_GENOMIC = "backbone.hg38.bed"

# Codon spans, hg38, 1-based inclusive. Verified against run9.
NAMED = [
    ("IDH1 R132", "chr2", 208248387, 208248389),
    ("IDH2 R140", "chr15", 90088701, 90088703),
    ("IDH2 R172", "chr15", 90088605, 90088607),
    ("BRAF V600", "chr7", 140753335, 140753337),
    ("NPM1 W288", "chr5", 171410539, 171410545),
    ("FLT3 D835", "chr13", 28018503, 28018507),
    ("JAK2 V617", "chr9", 5073768, 5073772),
    ("KIT D816", "chr4", 54733153, 54733157),
    ("TP53 R248", "chr17", 7674219, 7674223),
    ("SRSF2 P95", "chr17", 76736875, 76736879),
]


def read_bed(path):
    rows = []
    with open(path) as fh:
        for line in fh:
            if not line.strip() or line.startswith(("#", "track", "browser")):
                continue
            f = line.rstrip("\n").split("\t")
            if len(f) < 3:
                continue
            try:
                s, e = int(f[1]), int(f[2])
            except ValueError:
                continue
            if e > s:
                rows.append((f[0], s, e, f[3] if len(f) > 3 else "."))
    return rows


def decode_range(contig):
    """Probe-space rows encode the locus as ..._range=chr_start_end."""
    if "range=" not in contig:
        return None
    parts = contig.split("range=")[-1].rsplit("_", 2)
    if len(parts) != 3:
        return None
    try:
        return (parts[0], int(parts[1]) - 1, int(parts[2]))
    except ValueError:
        return None


def is_primary(c):
    if "_" in c or c.startswith("HLA"):
        return False
    b = c[3:] if c.startswith("chr") else c
    return b in [str(i) for i in range(1, 23)] + ["X", "Y", "M", "MT"]


def merge(rows):
    by = {}
    for c, s, e, _ in rows:
        by.setdefault(c, []).append((s, e))
    out = {}
    for c, iv in by.items():
        iv.sort()
        acc, cs, ce = [], iv[0][0], iv[0][1]
        for s, e in iv[1:]:
            if s <= ce:
                ce = max(ce, e)
            else:
                acc.append((cs, ce))
                cs, ce = s, e
        acc.append((cs, ce))
        out[c] = acc
    return out


def contained(merged, c, lo, hi):
    """Is the 1-based inclusive span lo..hi inside one merged interval?"""
    for s, e in merged.get(c, []):
        if lo > s and hi <= e:
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", required=True)
    ap.add_argument("--calling-bed", default=None,
                    help="default: <assets>/panel.calling.bed")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    def find(base):
        for dirpath, _d, files in os.walk(args.assets):
            if base in files:
                return os.path.join(dirpath, base)
        return None

    call_p = args.calling_bed or os.path.join(args.assets, "panel.calling.bed")
    main_p = find(MAIN_BED)
    back_p = find(BACKBONE_BED)
    bbg_p = find(BACKBONE_GENOMIC)

    fails = []
    for label, p in (("calling BED", call_p), ("Main probe BED", main_p),
                     ("backbone probe BED", back_p)):
        if not p or not os.path.exists(p):
            print("FAIL  %s not found" % label)
            fails.append(label)
    if fails:
        return 1

    merged = merge(read_bed(call_p))

    probes, undecodable = [], 0
    for c, s, e, n in read_bed(main_p) + read_bed(back_p):
        if is_primary(c):
            probes.append((c, s, e, n))
            continue
        d = decode_range(c)
        if d and is_primary(d[0]):
            probes.append((d[0], d[1], d[2], n))
        else:
            undecodable += 1
    if bbg_p:
        probes += [r for r in read_bed(bbg_p) if is_primary(r[0])]

    if not args.quiet:
        print("      calling BED : %s" % call_p)
        print("      probe intervals checked : %d" % len(probes))
        if undecodable:
            print("      probe rows neither genomic nor decodable : %d"
                  % undecodable)

    missing = [p for p in probes if not contained(merged, p[0], p[1] + 1, p[2])]
    if missing:
        print("FAIL  %d of %d probe intervals are NOT in the calling BED"
              % (len(missing), len(probes)))
        seen = set()
        for c, s, e, n in missing:
            key = n.split(",")[0]
            if key in seen:
                continue
            seen.add(key)
            print("        %s  %s:%d-%d" % (key, c, s, e))
            if len(seen) >= 15:
                print("        ... and more")
                break
        fails.append("containment")
    else:
        print("OK    all %d probe intervals are inside the calling BED"
              % len(probes))

    bad = [n for n, c, lo, hi in NAMED if not contained(merged, c, lo, hi)]
    if bad:
        print("FAIL  named hotspots absent from the calling BED: %s"
              % ", ".join(bad))
        fails.append("hotspots")
    else:
        print("OK    all %d named clinical hotspots are callable" % len(NAMED))

    if fails:
        print()
        print("PANEL COMPLETENESS CHECK FAILED.")
        print("Do not release. A calling BED that omits probe regions makes")
        print("those regions permanently invisible: they sequence normally,")
        print("coverage QC reports them as covered, and no variant is ever")
        print("called there.")
        return 1

    print("PANEL COMPLETENESS CHECK PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
