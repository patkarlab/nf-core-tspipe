#!/usr/bin/env python3
"""
patch_cnv_parser_annotated_table.py

Surface the CNV annotated table in the per-sample report. Part 1 of 3 (parser).

The annotated table (clinical/cnv_consensus/<sample>_cnv_annotated.tsv, delivered
by the earlier CNV fix) carries cytoband, ClinGen HI/TS dosage scores, gene role,
heme significance, and CDKN2A/2B + 9p/9q rescue comments that the tiered clinical
table does not. This makes the dashboard CNV parser read it into an
`annotated_table` entry (same shape as `clinical_table`) so the template can
render it as a second table in the CNV subtab.

Two anchored edits to bin/dashboard_builder/parsers/cnv.py:
  1. parse <sample>_cnv_annotated.tsv after the clinical table
  2. add "annotated_table" to the return dict

Apply together with the build.py and sample_report.html.j2 patches.

Conventions: dry-run by default; --apply writes; backup .bak_cnvannottab_<ts>;
idempotent via MARKER; status [skip]/[backup]/[patch]/[error].
"""

import argparse
import datetime
import os
import sys

TARGET = "/goast/hemat_data/nf-core-tspipe/bin/dashboard_builder/parsers/cnv.py"
MARKER = "annotated_table"

OLD_PARSE = r'''        except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError):
            clinical_table = None

    # ---- Genome-wide scatter PNG / diagram PDF ----
'''

NEW_PARSE = r'''        except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError):
            clinical_table = None

    # ---- Per-gene annotated CNV table (cytoband, ClinGen, gene role, heme) ----
    # Richer per-gene annotation from cnv_annotate.py: cytoband, ClinGen HI/TS
    # dosage scores, gene role, heme significance, and CDKN2A/2B + 9p/9q rescue
    # comments. Delivered alongside the tiered clinical table; rendered as a
    # second table in the CNV tab.
    annotated_path = sample_dir / "cnv_consensus" / f"{sample}_cnv_annotated.tsv"
    annotated_table = None
    if annotated_path.exists():
        try:
            adf = pd.read_csv(
                annotated_path, sep="\t", dtype=str,
                keep_default_na=False, na_values=[""],
            ).fillna("")
            annotated_table = {
                "columns": list(adf.columns),
                "rows":    adf.to_dict(orient="records"),
                "n":       len(adf),
            }
        except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError):
            annotated_table = None

    # ---- Genome-wide scatter PNG / diagram PDF ----
'''

OLD_RET = r'''    return {
        "clinical_table":     clinical_table,
        "scatter_png":        scatter_png,
'''

NEW_RET = r'''    return {
        "clinical_table":     clinical_table,
        "annotated_table":    annotated_table,
        "scatter_png":        scatter_png,
'''


def status(tag, msg):
    sys.stdout.write("[%s] %s\n" % (tag, msg))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="Write changes. Default is dry-run.")
    ap.add_argument("--file", default=TARGET, help="Target file (default: %s)" % TARGET)
    args = ap.parse_args()

    path = args.file
    if not os.path.isfile(path):
        status("error", "target not found: %s" % path)
        return 1

    with open(path, "r") as f:
        src = f.read()

    if MARKER in src:
        status("skip", "MARKER already present; file looks patched. No changes.")
        return 0

    problems = []
    if OLD_PARSE not in src:
        problems.append("clinical-table/scatter anchor not found (Edit 1)")
    if OLD_RET not in src:
        problems.append("return-dict head anchor not found (Edit 2)")
    if problems:
        for p in problems:
            status("error", p)
        status("error", "no changes made; anchors must match the live file exactly")
        return 2

    patched = src.replace(OLD_PARSE, NEW_PARSE, 1).replace(OLD_RET, NEW_RET, 1)

    if patched == src or MARKER not in patched:
        status("error", "patch did not land as expected; aborting")
        return 3

    if not args.apply:
        status("patch", "DRY-RUN ok. would apply 2 edits:")
        status("patch", "  1. parse <sample>_cnv_annotated.tsv into annotated_table")
        status("patch", "  2. add annotated_table to the parse() return dict")
        status("patch", "re-run with --apply to write.")
        return 0

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = "%s.bak_cnvannottab_%s" % (path, ts)
    with open(backup, "w") as f:
        f.write(src)
    status("backup", backup)
    with open(path, "w") as f:
        f.write(patched)
    status("patch", "added annotated_table parsing in %s" % path)
    status("patch", "verify: grep -n 'annotated_table\\|_cnv_annotated.tsv' %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
