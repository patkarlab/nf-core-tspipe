#!/usr/bin/env python3
"""RUN_BUNDLE_V1 -- one shareable zip per run (Nikhil, 2026-09-10).

Patches workflows/tspipe.nf (anchor-based, MARKER-guarded, dry-run unless --apply):
  * include RUN_BUNDLE after REPORT_BUNDLE
  * call RUN_BUNDLE(DASHBOARD.out.clinical_dirs, DASHBOARD.out.assets, DASHBOARD.out.cohort_html)
    after the REPORT_BUNDLE call (runs beside it; consumes DASHBOARD outputs directly)
  * header comment
Files delivered alongside (copied by hand): modules/local/run_bundle.nf, tools/make_run_bundle.py.
A new process changes no existing task hash: a plain resume executes one RUN_BUNDLE task and
publishes <outdir>/<outdir basename>_reports.zip.

Run from the repo root:  python3 tools/patches/2026-09-10/patch_run_bundle_v1.py [--apply]
"""
import argparse
import datetime as dt
import shutil
import sys
from pathlib import Path

MARKER = "RUN_BUNDLE_V1"
TAG = "run_bundle_v1"

EDITS = {
    "workflows/tspipe.nf": [
        (" *                   -> IGV_REPORTS -> ORGANIZE_OUTPUT -> DASHBOARD -> REPORT_BUNDLE\n",
         " *                   -> IGV_REPORTS -> ORGANIZE_OUTPUT -> DASHBOARD -> REPORT_BUNDLE + RUN_BUNDLE\n",
         "header"),
        ("include { REPORT_BUNDLE       } from '../modules/local/report_bundle'\n",
         "include { REPORT_BUNDLE       } from '../modules/local/report_bundle'\n"
         "include { RUN_BUNDLE          } from '../modules/local/run_bundle'   // RUN_BUNDLE_V1\n",
         "include"),
        ("    REPORT_BUNDLE(\n"
         "        DASHBOARD.out.clinical_dirs,\n"
         "        DASHBOARD.out.assets,\n"
         "    )\n"
         "}\n",
         "    REPORT_BUNDLE(\n"
         "        DASHBOARD.out.clinical_dirs,\n"
         "        DASHBOARD.out.assets,\n"
         "    )\n"
         "\n"
         "    // ----- 10. RUN_BUNDLE: one zip for the whole run (RUN_BUNDLE_V1) -\n"
         "    // <outdir>/<run>_reports.zip: cohort index, assets once, one folder\n"
         "    // per sample. Reads DASHBOARD outputs directly, beside REPORT_BUNDLE.\n"
         "    RUN_BUNDLE(\n"
         "        DASHBOARD.out.clinical_dirs,\n"
         "        DASHBOARD.out.assets,\n"
         "        DASHBOARD.out.cohort_html,\n"
         "    )\n"
         "}\n",
         "call"),
    ],
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    for rel in ("modules/local/run_bundle.nf", "tools/make_run_bundle.py"):
        if not (root / rel).exists():
            print("[error] %s missing - copy it from the bundle first" % rel)
            return 2
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    planned = {}
    for rel, edits in EDITS.items():
        p = root / rel
        text = p.read_text()
        if MARKER in text:
            print("[skip]  %s already carries %s" % (rel, MARKER))
            continue
        for anchor, repl, desc in edits:
            n = text.count(anchor)
            if n != 1:
                print("[error] %s: anchor for '%s' found %d times" % (rel, desc, n))
                return 2
            text = text.replace(anchor, repl, 1)
            print("[patch] %s: %s" % (rel, desc))
        planned[p] = text
    if not planned:
        print("nothing to do")
        return 0
    if not args.apply:
        print("dry run: %d file(s) would change; re-run with --apply" % len(planned))
        return 0
    for p, text in planned.items():
        bak = p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp))
        shutil.copy2(p, bak)
        print("[backup] %s" % bak.relative_to(root))
        p.write_text(text)
        print("[write] %s (%d x %s)" % (p.relative_to(root), text.count(MARKER), MARKER))
    return 0


if __name__ == "__main__":
    sys.exit(main())
