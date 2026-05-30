#!/usr/bin/env python3

import argparse
import pandas as pd
from datetime import date

# -----------------------------
# argument parser
# -----------------------------
parser = argparse.ArgumentParser(
    description="Convert simple artefact list to blacklist format"
)

parser.add_argument(
    "-i", "--input",
    required=True,
    help="Input artefact TSV file"
)

parser.add_argument(
    "-o", "--output",
    required=True,
    help="Output blacklist TSV file"
)

parser.add_argument(
    "--gene",
    default=".",
    help="Default gene name (default: .)"
)

parser.add_argument(
    "--reason",
    default="ARTIFACT",
    help="Reason column value (default: ARTIFACT)"
)

parser.add_argument(
    "--evidence",
    default="Imported from artefact list",
    help="Evidence text"
)

args = parser.parse_args()

# -----------------------------
# constants
# -----------------------------
TODAY = str(date.today())

# -----------------------------
# read input
# -----------------------------
df = pd.read_csv(args.input, sep=r"\s+")

rows = []

# -----------------------------
# process variants
# -----------------------------
for _, r in df.iterrows():

    chrom = r["Chr"]
    pos = int(r["Start"])   # 1-based VCF POS
    ref = str(r["Ref"])
    alt = str(r["Alt"])

    # SNV
    is_snv = (len(ref) == 1 and len(alt) == 1)

    if is_snv:

        match_mode = "exact"

        # BED-style coordinates
        start0 = pos - 1
        end0 = pos

        pos_exact = pos
        ref_exact = ref
        alt_exact = alt

    else:

        match_mode = "region_indel"

        # indel window
        start0 = pos - 1
        end0 = pos + max(len(ref), len(alt)) - 1

        pos_exact = "."
        ref_exact = "."
        alt_exact = "."

    rows.append([
        chrom,
        start0,
        end0,
        match_mode,
        pos_exact,
        ref_exact,
        alt_exact,
        args.gene,
        args.reason,
        args.evidence,
        TODAY
    ])

# -----------------------------
# output dataframe
# -----------------------------
out = pd.DataFrame(rows, columns=[
    "#chrom",
    "start",
    "end",
    "match_mode",
    "pos_exact",
    "ref_exact",
    "alt_exact",
    "gene",
    "reason",
    "evidence",
    "date_added"
])

# -----------------------------
# write output
# -----------------------------
with open(args.output, "w") as f:

    f.write("## Leukemia panel SNV blacklist (hg38)\n")
    f.write("## Variants in this file are flagged FILTER=BLACKLIST.\n")
    f.write("##\n")

    out.to_csv(f, sep="\t", index=False)

print(f"Wrote blacklist file: {args.output}")
