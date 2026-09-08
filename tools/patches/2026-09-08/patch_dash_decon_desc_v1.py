#!/usr/bin/env python3
"""tools/patches/<date>/patch_dash_decon_desc_v1.py -- MARKER DASH_DECON_V1

Replaces the one-line DECoN table description in
bin/dashboard_builder/templates/sample_report.html.j2 with a short explanation
of the Bayes factor, the reads ratio and the decision/reportable columns, plus
a collapsed column key in the same style as DASH_GLOSS_V1.

bin/ is not hashed: re-render with `-c /tmp/dash_nocache.config`.

Usage:  python3 <this file>            # dry run
        python3 <this file> --apply
Guard:  MARKER DASH_DECON_V1; single exact anchor; backup <file>.bak_dash_decon_v1_<stamp>.
"""

import argparse
import sys
import time
from pathlib import Path

MARKER = "DASH_DECON_V1"
TAG = "dash_decon_v1"
REPO = Path(__file__).resolve().parents[3]
TARGET = "bin/dashboard_builder/templates/sample_report.html.j2"

OLD = (
    "          <p class=\"text-muted small mb-2\">Reportable calls and multi-exon calls at BF &ge; 5 "
    "(sub-threshold ones carry decision BELOW_BF).</p>\n"
)

ROWS = [
    ("Gene, CNV.type, N.exons", "gene, deletion or duplication, number of consecutive exons in the call"),
    ("Chromosome, Start, End", "span of the called exons (hg38)"),
    ("BF",
     "Bayes factor, log10 scale: the evidence for a copy-number change over no change, from the sample's exon "
     "read depth against the sex-matched pool of normals. BF 5 is roughly 100,000:1; larger is stronger. "
     "Calls with BF &ge; 5 are listed; a call enters the consensus as arm E only at BF &ge; 8 for multi-exon "
     "deletions and BF &ge; 12 for single-exon calls"),
    ("Reads.ratio",
     "observed / expected read depth over the called exons: about 0.5 for a heterozygous deletion, about 0 for "
     "a homozygous deletion, about 1.5 for a single-copy gain"),
    ("decision",
     "how the call was classified: PASS, BELOW_BF (BF under the reporting threshold), or a flag naming why it is "
     "not reportable"),
    ("reportable", "TRUE when the call meets the BF threshold and carries no disqualifying flag"),
    ("exon_flags",
     "per-exon caveats such as PROBE_VARIANT (a variant under a probe can mimic a deletion), "
     "RECURRENT_IN_NORMALS or LOW_POWER"),
]


def block():
    lines = [
        "          {# DASH_DECON_V1: BF explanation and column key #}\n",
        "          <p class=\"text-muted small mb-2\">\n",
        "            Exon-level calls from DECoN, listed at Bayes factor (BF) &ge; 5; sub-threshold calls carry\n",
        "            decision BELOW_BF. BF is on a log10 scale, so BF 5 is about 100,000:1 evidence for a copy-number\n",
        "            change over none. Only calls at BF &ge; 8 (multi-exon deletions) or BF &ge; 12 (single exon)\n",
        "            vote as arm E in the consensus table above. Reads.ratio near 0.5 indicates a heterozygous\n",
        "            deletion, near 0 a homozygous deletion, near 1.5 a single-copy gain.\n",
        "          </p>\n",
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
    n = text.count(OLD)
    if n != 1:
        print("ABORT -- nothing written: anchor matched %d times (need 1)" % n)
        sys.exit(1)
    new_text = text.replace(OLD, block(), 1)
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
