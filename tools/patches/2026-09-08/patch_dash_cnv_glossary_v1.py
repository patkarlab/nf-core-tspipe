#!/usr/bin/env python3
"""tools/patches/<date>/patch_dash_cnv_glossary_v1.py -- MARKER DASH_GLOSS_V1

Adds a collapsed "Column key" (<details>) between the consensus-table
description and the DASH_TIER_V1 button group in
bin/dashboard_builder/templates/sample_report.html.j2, so a reader who is not
the pipeline author can decode k_call / g_seg_log2 / loo_fp_any / clingen_hi
and the rest. Closed by default; the table does not move.

bin/ is not hashed: re-render with `-c /tmp/dash_nocache.config`.

Usage:  python3 <this file>            # dry run
        python3 <this file> --apply
Guard:  MARKER DASH_GLOSS_V1; single exact anchor; backup <file>.bak_dash_gloss_v1_<stamp>.
"""

import argparse
import sys
import time
from pathlib import Path

MARKER = "DASH_GLOSS_V1"
TAG = "dash_gloss_v1"
REPO = Path(__file__).resolve().parents[3]
TARGET = "bin/dashboard_builder/templates/sample_report.html.j2"

ANCHOR = (
    "            REVIEW: arms disagree. Blacklisted genes are excluded.\n"
    "          </p>\n"
    "          {# DASH_TIER_V1: tier filter; first button is the default view #}\n"
)

ROWS = [
    ("gene, cytoband, chrom, start, end",
     "gene symbol, UCSC cytoband (hg38), and the span of the gene's targets"),
    ("consensus_call",
     "GAIN, LOSS, CNLOH, NEUTRAL, DISCORDANT (arms disagree) or BLACKLISTED"),
    ("tier",
     "TIER_1: a depth arm (K or G) and an independent arm (B, P, E, H) agree and the LOO false-positive rate is acceptable; "
     "TIER_2: both depth arms agree (LOO ok) or two independent arms agree; TIER_3: a single arm; REVIEW: arms contradict"),
    ("flags", "letters of the arms that voted: K G B P E H"),
    ("k_call, k_cn, k_log2",
     "K = CNVkit (read depth vs the sex-matched panel of normals): call, integer copy number, segment log2 ratio"),
    ("g_call, g_seg_log2",
     "G = GATK ModelSegments (read depth, same PoN): call, segment log2 ratio"),
    ("b_call",
     "B = B-allele frequency / cnLOH (17p region in the current version): LOSS, CNLOH or NEUTRAL"),
    ("p_call, p_C",
     "P = PureCN: call and absolute copy number; advisory only when the purity fit is flagged"),
    ("e_call, e_bf",
     "E = DECoN (exon-level, multi-exon deletions): call and Bayes factor"),
    ("h_call, h_cn_min, h_cn_max, h_loh",
     "H = PURPLE (hmftools, purity/ploidy adjusted): call, minimum and maximum copy number over the gene, LOH flag; "
     "advisory on low purity"),
    ("loo_fp_any",
     "fraction of panel-of-normals samples in which this gene was called non-neutral in leave-one-out; "
     "must be below 0.10 for TIER_1 or TIER_2"),
    ("driver_role", "hmftools DriverGenePanel: ONCO (oncogene) or TSG (tumour suppressor)"),
    ("clingen_hi, clingen_ts",
     "ClinGen dosage-sensitivity scores for haploinsufficiency / triplosensitivity: "
     "3 sufficient evidence, 2 emerging, 1 little, 0 none, 30 autosomal-recessive phenotype, "
     "40 dosage sensitivity unlikely; NA when the gene is not curated"),
]

def block():
    lines = [
        "          {# DASH_GLOSS_V1: column key, collapsed by default #}\n",
        "          <details class=\"small text-muted mb-2\">\n",
        "            <summary>Column key</summary>\n",
        "            <table class=\"table table-sm table-borderless mb-0\" style=\"max-width: 1100px;\">\n",
        "              <tbody>\n",
    ]
    for k, v in ROWS:
        lines.append("                <tr><td class=\"text-nowrap\"><code>%s</code></td><td>%s</td></tr>\n" % (k, v))
    lines += [
        "              </tbody>\n",
        "            </table>\n",
        "          </details>\n",
    ]
    return "".join(lines)


NEW = (
    "            REVIEW: arms disagree. Blacklisted genes are excluded.\n"
    "          </p>\n"
    + block() +
    "          {# DASH_TIER_V1: tier filter; first button is the default view #}\n"
)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    args = ap.parse_args()

    p = REPO / TARGET
    if not p.exists():
        print("ABORT: %s not found" % TARGET)
        sys.exit(1)
    text = p.read_text()
    if MARKER in text:
        print("SKIP  %s: %s already present" % (TARGET, MARKER))
        return
    n = text.count(ANCHOR)
    if n != 1:
        print("ABORT -- nothing written: anchor matched %d times (need 1)" % n)
        sys.exit(1)
    new_text = text.replace(ANCHOR, NEW, 1)
    print("PLAN  %s: +%d lines, marker %s" % (TARGET, new_text.count("\n") - text.count("\n"), MARKER))
    if not args.apply:
        print("dry run; re-run with --apply")
        return
    stamp = time.strftime("%Y%m%d_%H%M%S")
    bak = p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp))
    bak.write_text(text)
    p.write_text(new_text)
    print("WROTE %s (backup %s)" % (TARGET, bak.name))
    print("done")


if __name__ == "__main__":
    main()
