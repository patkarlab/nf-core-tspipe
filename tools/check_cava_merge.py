#!/usr/bin/env python3
"""
check_cava_merge.py  (CAVA_V1b, N3)

Read one or more annotated / filtered TSVs produced after CAVA_V1b and report:
  - how many rows carry a CAVA annotation
  - the CAVA_HGVSp_Match distribution (MATCH / DIFFER / NA)
  - how many rows carry an ALTANN (alignment-dependent indel)
  - the DIFFER rows, one line each, with VEP and CAVA HGVSp side by side
    (this table is the evidence for D3 / D6)

Usage:
    python3 tools/check_cava_merge.py results/run8/*/annotation/*.somaticseq.filtered.tsv
    python3 tools/check_cava_merge.py --clinical-only ...   (rows with Filter == PASS)
    python3 tools/check_cava_merge.py --out differ.tsv ...  (write the DIFFER table)
"""

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

NEEDED = ["CAVA_CSN", "CAVA_HGVSp", "CAVA_HGVSp_Match", "CAVA_AltAnn"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tsv", nargs="+")
    ap.add_argument("--clinical-only", action="store_true", help="restrict to Filter == PASS rows")
    ap.add_argument("--out", default=None, help="write the DIFFER rows as TSV")
    args = ap.parse_args()

    differ_rows = []
    grand = Counter()
    for path in args.tsv:
        path = Path(path)
        with open(path) as fh:
            reader = csv.DictReader(fh, delimiter="\t")
            missing = [c for c in NEEDED if c not in (reader.fieldnames or [])]
            if missing:
                print(f"{path.name}: missing {missing} -- produced before CAVA_V1b?")
                continue
            c = Counter()
            for row in reader:
                if args.clinical_only and row.get("Filter", "") != "PASS":
                    continue
                c["rows"] += 1
                has = row["CAVA_CSN"] not in ("", "-1")
                c["cava"] += has
                c[row["CAVA_HGVSp_Match"] or "NA"] += 1
                if row["CAVA_AltAnn"] not in ("", "-1"):
                    c["altann"] += 1
                if row["CAVA_HGVSp_Match"] == "DIFFER":
                    differ_rows.append({
                        "Sample": row.get("Sample", path.stem),
                        "Gene": row.get("Gene", ""),
                        "Chr": row.get("Chr", ""), "Start": row.get("Start", ""),
                        "Ref": row.get("Ref", ""), "Alt": row.get("Alt", ""),
                        "Filter": row.get("Filter", ""),
                        "Consequence": row.get("Consequence", ""),
                        "CAVA_Class": row.get("CAVA_Class", ""),
                        "VEP_HGVSc": row.get("HGVSc", ""), "CAVA_HGVSc": row.get("CAVA_HGVSc", ""),
                        "VEP_HGVSp": row.get("HGVSp", ""), "CAVA_HGVSp": row.get("CAVA_HGVSp", ""),
                        "VEP_transcript": row.get("MANE_SELECT", ""), "CAVA_Transcript": row.get("CAVA_Transcript", ""),
                        "CAVA_AltAnn": row.get("CAVA_AltAnn", ""),
                    })
            grand.update(c)
            print(f"{path.name}: {c['rows']} rows, {c['cava']} with CAVA, "
                  f"HGVSp MATCH {c['MATCH']} / DIFFER {c['DIFFER']} / NA {c['NA']}, ALTANN {c['altann']}")

    print(f"TOTAL: {grand['rows']} rows, {grand['cava']} with CAVA, "
          f"HGVSp MATCH {grand['MATCH']} / DIFFER {grand['DIFFER']} / NA {grand['NA']}, ALTANN {grand['altann']}")

    if differ_rows:
        print("\nDIFFER rows (VEP vs CAVA protein):")
        for r in differ_rows:
            print(f"  {r['Sample']:<24} {r['Gene']:<8} {r['Chr']}:{r['Start']} {r['Ref']}>{r['Alt']}  "
                  f"{r['Filter']:<14} VEP={r['VEP_HGVSp']}  CAVA={r['CAVA_HGVSp']}"
                  + (f"  ALT={r['CAVA_AltAnn']}" if r['CAVA_AltAnn'] not in ('', '-1') else ''))
        if args.out:
            with open(args.out, "w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(differ_rows[0].keys()), delimiter="\t")
                w.writeheader()
                w.writerows(differ_rows)
            print(f"\nwrote {len(differ_rows)} rows to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
