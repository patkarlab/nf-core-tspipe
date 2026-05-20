#!/usr/bin/env python3
"""
Collapse the segment-level panel BED into an exon-level BED by
grouping rows that share the same (chrom, normalized exon_label) and
emitting one entry per exon spanning min(start) to max(end).

Usage:
    collapse_to_exonwise.py \
        --bed   MYOPOOL_240125_UBTF_hg38.bed \
        --out   MYOPOOL_240125_UBTF_Exonwise_hg38.bed \
        --audit collapse_audit.tsv

Outputs:
  * --out:   BED4 sorted by chrom, start. Column 4 is the normalized
             exon label (gene_Ex_id).
  * --audit: TSV with one row per output exon, listing source row count,
             classification breakdown, total span, and total covered
             length (sum of source-segment widths, useful as a sanity
             check against the span).
  * Also writes intron-only probes to a sidecar BED if any exist.
"""

import argparse
import re
import sys
from collections import defaultdict, Counter
from pathlib import Path


EXON_ID = r"(?:\d+[A-Za-z]?|[35]'UTR|intr_\d+_part)"
GENE_EXON_TOKEN = (
    r"(?P<gene>[A-Za-z][A-Za-z0-9]*)"
    r"_(?:Ex|EX)_?(?P<exon>" + EXON_ID + r")"
    r"(?:_NM_\d+)?"
)
RE_GENE_EXON_TOKEN = re.compile(GENE_EXON_TOKEN)
RE_GENE_EXON_FULL  = re.compile(r"^" + GENE_EXON_TOKEN + r"$")
RE_PREFIXED_SINGLE = re.compile(
    r"^(?:\d+_)+" + GENE_EXON_TOKEN + r"_(?P<tile>\d+)$"
)
RE_INTRON_ONLY = re.compile(
    r"^(?P<gene>[A-Za-z][A-Za-z0-9]*)_Intron_\d+-\d+$"
)


RE_LETTER_SUFFIX = re.compile(r"^(\d+)[A-Za-z]$")


def maybe_merge_isoform(exon_label, merge_isoforms):
    """If --merge-isoforms is set, collapse Ex_4A/Ex_4B/Ex_4C to Ex_4.

    Only acts on numeric exon ids with a trailing single letter. UTR
    designators (5'UTR, 3'UTR) and intron designators (intr_N_part)
    are left unchanged.
    """
    if not merge_isoforms:
        return exon_label
    gene, eid = exon_label.split("_Ex_", 1)
    m = RE_LETTER_SUFFIX.match(eid)
    if m:
        return f"{gene}_Ex_{m.group(1)}"
    return exon_label


def normalize(label_field):
    fields = label_field.split(";")
    if len(fields) >= 3:
        for tok in reversed(fields):
            m = RE_GENE_EXON_FULL.match(tok)
            if m:
                gene, exon = m.group("gene"), m.group("exon")
                klass = "simple_3field" if len(fields) == 3 else "intron_or_outlier"
                return gene, f"{gene}_Ex_{exon}", klass
        m = RE_INTRON_ONLY.match(fields[-1])
        if m:
            return m.group("gene"), fields[-1], "intron_only"
        return None, None, "unparsed"
    raw = fields[0].strip()
    if raw.startswith('"') and raw.endswith('"'):
        raw = raw[1:-1]
    if "," in raw:
        toks = RE_GENE_EXON_TOKEN.findall(raw)
        if toks:
            return toks[0][0], f"{toks[0][0]}_Ex_{toks[0][1]}", "multi_exon"
        return None, None, "unparsed"
    m = RE_PREFIXED_SINGLE.match(raw)
    if m:
        gene, exon = m.group("gene"), m.group("exon")
        return gene, f"{gene}_Ex_{exon}", "prefixed_single"
    return None, None, "unparsed"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bed", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--audit", type=Path, required=True)
    ap.add_argument("--introns-out", type=Path, default=None,
                    help="Optional sidecar BED for intron-only probes.")
    ap.add_argument("--merge-isoforms", action="store_true",
                    help="Collapse letter-suffix isoform exons "
                         "(Ex_4A, Ex_4B, Ex_4C) into the base exon (Ex_4). "
                         "Matches legacy hg19 Exonwise BED convention.")
    args = ap.parse_args()

    # exon_key -> dict with chrom, start, end, source rows
    exons = defaultdict(lambda: {
        "chrom": None,
        "start": None,
        "end": None,
        "n_rows": 0,
        "classifications": Counter(),
        "covered_bp": 0,
        "source_isoforms": set(),
    })
    intron_rows = []
    unparsed_rows = []

    with args.bed.open() as fh:
        for line_no, line in enumerate(fh, 1):
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 4:
                continue
            chrom, start, end, label = parts[0], int(parts[1]), int(parts[2]), parts[3]

            gene, exon_label, klass = normalize(label)

            if klass == "unparsed":
                unparsed_rows.append((line_no, line))
                continue
            if klass == "intron_only":
                intron_rows.append((chrom, start, end, exon_label))
                continue

            original_exon_label = exon_label
            exon_label = maybe_merge_isoform(exon_label, args.merge_isoforms)

            key = (chrom, exon_label)
            ex = exons[key]
            ex["chrom"] = chrom
            ex["start"] = start if ex["start"] is None else min(ex["start"], start)
            ex["end"]   = end   if ex["end"]   is None else max(ex["end"],   end)
            ex["n_rows"] += 1
            ex["classifications"][klass] += 1
            ex["covered_bp"] += (end - start)
            ex["source_isoforms"].add(original_exon_label)

    if unparsed_rows:
        print(f"WARNING: {len(unparsed_rows)} unparsed rows (see stderr).",
              file=sys.stderr)
        for ln, raw in unparsed_rows[:10]:
            print(f"  line {ln}: {raw}", file=sys.stderr)

    rows = []
    for (chrom, label), info in exons.items():
        rows.append((chrom, info["start"], info["end"], label, info))

    def chrom_sort_key(chrom):
        c = chrom.replace("chr", "")
        try:
            return (0, int(c))
        except ValueError:
            return (1, c)

    rows.sort(key=lambda r: (chrom_sort_key(r[0]), r[1], r[2]))

    with args.out.open("w") as out:
        for chrom, start, end, label, _info in rows:
            out.write(f"{chrom}\t{start}\t{end}\t{label}\n")

    with args.audit.open("w") as aud:
        aud.write("chrom\tstart\tend\texon_label\tgene\tn_source_rows\t"
                  "span_bp\tsource_covered_bp\tclassifications\t"
                  "source_isoforms\n")
        for chrom, start, end, label, info in rows:
            gene = label.split("_Ex_", 1)[0]
            klass = ",".join(f"{k}:{v}" for k, v in info["classifications"].most_common())
            isoforms = ",".join(sorted(info["source_isoforms"]))
            aud.write(f"{chrom}\t{start}\t{end}\t{label}\t{gene}\t"
                      f"{info['n_rows']}\t{end - start}\t{info['covered_bp']}\t"
                      f"{klass}\t{isoforms}\n")

    if args.introns_out and intron_rows:
        intron_rows.sort(key=lambda r: (chrom_sort_key(r[0]), r[1], r[2]))
        with args.introns_out.open("w") as fh:
            for chrom, s, e, lab in intron_rows:
                fh.write(f"{chrom}\t{s}\t{e}\t{lab}\n")

    n_exons = len(rows)
    n_genes = len({lbl.split("_Ex_", 1)[0] for _c, _s, _e, lbl, _i in rows})
    print(f"Wrote {n_exons} exon rows ({n_genes} genes) to {args.out}")
    print(f"Audit:   {args.audit}")
    if args.introns_out:
        print(f"Introns: {args.introns_out} ({len(intron_rows)} rows)")
    if unparsed_rows:
        print(f"WARNING: {len(unparsed_rows)} unparsed rows - "
              f"check stderr and decide handling.")


if __name__ == "__main__":
    main()
