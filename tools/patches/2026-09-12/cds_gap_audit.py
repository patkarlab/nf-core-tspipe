#!/usr/bin/env python3
"""
cds_gap_audit.py

Question
--------
82 intervals of targets.exonwise.bed are not fully covered by the Twist
capture space (14,128 bases). Almost all are terminal exons, whose bulk is
3'UTR, so the shortfall is expected for a coding-focused design and is not a
defect. This separates the two cases: for each uncovered stretch, how many of
its bases fall inside a coding sequence.

Only CDS gaps are worth raising with Twist.

Method
------
Uncovered stretches = targets.exonwise.bed minus the merged calling BED.
CDS intervals are built from ANNOVAR's hg38_refGene.txt, taking the union of
CDS across all NM_ transcripts of each gene. The union is deliberately
conservative: a base coding in any RefSeq transcript counts as coding, so the
result over-reports rather than under-reports.

Usage
-----
    python3 cds_gap_audit.py \
        --assets /goast/hemat_data/nf-core-tspipe/assets/twist_myeloid \
        [--refgene <path to hg38_refGene.txt>] \
        [--out /tmp/cds_gaps.tsv]
"""

import argparse
import os
import sys

REFGENE_CANDIDATES = [
    "/goast/hemat_data/targeted-seq-pipeline/software/annovar/humandb/"
    "hg38_refGene.txt",
    os.path.expanduser("~/programs/annovar/humandb/hg38_refGene.txt"),
]


def log(tag, msg):
    print("[%s] %s" % (tag, msg))


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


def merge(rows):
    by = {}
    for c, s, e, _n in rows:
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


def subtract(chrom, start, end, merged):
    """Return the sub-intervals of [start,end) not covered by merged."""
    gaps, cur = [], start
    for s, e in merged.get(chrom, []):
        if e <= cur:
            continue
        if s >= end:
            break
        if s > cur:
            gaps.append((cur, min(s, end)))
        cur = max(cur, e)
        if cur >= end:
            break
    if cur < end:
        gaps.append((cur, end))
    return gaps


def overlap(a_s, a_e, intervals):
    """Bases of [a_s,a_e) covered by a sorted list of intervals."""
    n = 0
    for s, e in intervals:
        if e <= a_s:
            continue
        if s >= a_e:
            break
        n += min(a_e, e) - max(a_s, s)
    return n


def load_cds(refgene):
    """gene -> chrom -> sorted CDS intervals, union over NM_ transcripts."""
    raw = {}
    with open(refgene) as fh:
        for line in fh:
            f = line.rstrip("\n").split("\t")
            if len(f) < 16:
                continue
            name, chrom = f[1], f[2]
            if not name.startswith("NM_"):
                continue
            if "_" in chrom[3:]:          # skip alt/random contigs
                continue
            try:
                cds_s, cds_e = int(f[6]), int(f[7])
            except ValueError:
                continue
            if cds_e <= cds_s:            # non-coding transcript
                continue
            gene = f[12]
            starts = [int(x) for x in f[9].rstrip(",").split(",") if x]
            ends = [int(x) for x in f[10].rstrip(",").split(",") if x]
            for s, e in zip(starts, ends):
                a, b = max(s, cds_s), min(e, cds_e)
                if b > a:
                    raw.setdefault(gene, {}).setdefault(chrom, []).append((a, b))

    cds = {}
    for gene, chroms in raw.items():
        cds[gene] = {}
        for chrom, iv in chroms.items():
            iv.sort()
            acc, cs, ce = [], iv[0][0], iv[0][1]
            for s, e in iv[1:]:
                if s <= ce:
                    ce = max(ce, e)
                else:
                    acc.append((cs, ce))
                    cs, ce = s, e
            acc.append((cs, ce))
            cds[gene][chrom] = acc
    return cds


def gene_of(name):
    g = name.split(",")[0]
    for sep in ("_exon", "_Ex_", "_intron", "_Intron", "_5UTR", "_3UTR"):
        if sep in g:
            g = g.split(sep)[0]
            break
    return g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", required=True)
    ap.add_argument("--refgene")
    ap.add_argument("--calling-bed", default="panel.calling.bed")
    ap.add_argument("--exonwise-bed", default="targets.exonwise.bed")
    ap.add_argument("--out", default="/tmp/cds_gaps.tsv")
    args = ap.parse_args()

    call_p = os.path.join(args.assets, args.calling_bed)
    exon_p = os.path.join(args.assets, args.exonwise_bed)
    for p in (call_p, exon_p):
        if not os.path.exists(p):
            log("error", "missing: %s" % p)
            return 1

    refgene = args.refgene
    if not refgene:
        for c in REFGENE_CANDIDATES:
            if os.path.exists(c):
                refgene = c
                break
    if not refgene or not os.path.exists(refgene):
        log("error", "hg38_refGene.txt not found; pass --refgene")
        return 1
    log("info", "refGene: %s" % refgene)

    merged = merge(read_bed(call_p))
    exons = read_bed(exon_p)
    cds = load_cds(refgene)
    log("info", "genes with CDS in refGene: %d" % len(cds))

    rows, no_cds = [], set()
    for chrom, s, e, name in exons:
        gaps = subtract(chrom, s, e, merged)
        if not gaps:
            continue
        gene = gene_of(name)
        gcds = cds.get(gene, {}).get(chrom)
        if gcds is None:
            no_cds.add(gene)
            gcds = []
        for gs, ge in gaps:
            rows.append((gene, name, chrom, gs, ge, ge - gs,
                         overlap(gs, ge, gcds)))

    tot = sum(r[5] for r in rows)
    cds_tot = sum(r[6] for r in rows)
    log("info", "uncovered stretches: %d  bases: %d" % (len(rows), tot))
    log("info", "of which inside a coding sequence: %d bases (%.1f%%)"
        % (cds_tot, 100.0 * cds_tot / tot if tot else 0))

    if no_cds:
        log("info", "no NM_ CDS found for: %s"
            % ", ".join(sorted(no_cds)[:15]))

    with open(args.out, "w") as fh:
        fh.write("gene\ttarget\tchrom\tstart\tend\tbases\tcds_bases\n")
        for r in sorted(rows, key=lambda x: (-x[6], -x[5])):
            fh.write("%s\t%s\t%s\t%d\t%d\t%d\t%d\n" % r)
    log("info", "written: %s" % args.out)

    hits = [r for r in rows if r[6] > 0]
    print()
    if not hits:
        print("No coding sequence is uncovered. Every shortfall against")
        print("targets.exonwise.bed is UTR, which is expected for a")
        print("coding-focused capture design. Nothing to raise with Twist.")
        return 0

    per_gene = {}
    for r in hits:
        per_gene[r[0]] = per_gene.get(r[0], 0) + r[6]
    print("CODING BASES NOT COVERED BY ANY PROBE")
    print("%-14s %-24s %-26s %8s" % ("gene", "target", "interval", "cds_bp"))
    for r in sorted(hits, key=lambda x: -x[6])[:40]:
        print("%-14s %-24s %-26s %8d"
              % (r[0], r[1][:24], "%s:%d-%d" % (r[2], r[3], r[4]), r[6]))
    if len(hits) > 40:
        print("... and %d more rows" % (len(hits) - 40))
    print()
    print("Per gene, coding bases uncovered:")
    for g in sorted(per_gene, key=lambda k: -per_gene[k]):
        print("   %-14s %d bp" % (g, per_gene[g]))
    print()
    print("These are the genuine design gaps and the only coverage material")
    print("for the Twist letter. Everything else is UTR.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
