#!/usr/bin/env python3
"""Change the Callers filter thresholds in the variant browser to Any / >1 / >2 / >3.

The clinical variant browser's "Callers" button-group filter (on
VariantCaller_Count) currently offers Any / >2 / >3 / >4. This patch makes it
Any / >1 / >2 / >3: it adds the >1 threshold (exclude single-caller calls) and
drops >4. "Any" stays as the unfiltered default.

Single anchored edit to
    bin/dashboard_builder/assets/js/variant-browser.js

The ALT count filter (which uses >10 / >15 / >20) is unaffected; the anchor is
the callers-specific option block, which is unique.

Idempotent and anchor-based. Dry-run by default; pass --apply to write. A
timestamped backup (.bak_callersgt1_<UTC>) is written before any change.
Python 3.6-safe.

Run from the repository root:
    python3 patch_dashboard_callers_gt1.py            # dry-run (shows a diff)
    python3 patch_dashboard_callers_gt1.py --apply     # write
"""

import argparse
import datetime
import difflib
import os
import shutil
import sys

DEFAULT_REL = os.path.join("bin", "dashboard_builder", "assets", "js", "variant-browser.js")
TAG = "callersgt1"

EDIT = {
    "name": "Callers filter thresholds (Any/>1/>2/>3)",
    "marker": 'id: "gt1", label: ">1"',
    "anchor": r'''        { id: "any", label: "Any", test: function () { return true; } },
        { id: "gt2", label: ">2",  test: function (v) { return v !== null && v > 2; } },
        { id: "gt3", label: ">3",  test: function (v) { return v !== null && v > 3; } },
        { id: "gt4", label: ">4",  test: function (v) { return v !== null && v > 4; } },
''',
    "replacement": r'''        { id: "any", label: "Any", test: function () { return true; } },
        { id: "gt1", label: ">1",  test: function (v) { return v !== null && v > 1; } },
        { id: "gt2", label: ">2",  test: function (v) { return v !== null && v > 2; } },
        { id: "gt3", label: ">3",  test: function (v) { return v !== null && v > 3; } },
''',
}


def main():
    ap = argparse.ArgumentParser(description="Change the Callers filter thresholds to Any/>1/>2/>3.")
    ap.add_argument("--file", default=None, help="Path to variant-browser.js (default: %s relative to CWD)" % DEFAULT_REL)
    ap.add_argument("--apply", action="store_true", help="Write the change (default is a dry-run preview).")
    args = ap.parse_args()

    target = args.file or os.path.join(os.getcwd(), DEFAULT_REL)
    if not os.path.isfile(target):
        print("[error] target not found: %s" % target)
        print("        Run this from the repository root, or pass --file <path>.")
        return 2

    with open(target, "r", encoding="utf-8") as fh:
        original = fh.read()

    if EDIT["marker"] in original:
        print("[skip]  %s already present." % EDIT["name"])
        return 0

    n = original.count(EDIT["anchor"])
    if n == 0:
        print("[error] anchor for '%s' not found. File may have changed; not writing." % EDIT["name"])
        return 3
    if n > 1:
        print("[error] anchor for '%s' found %d times (expected 1); not writing." % (EDIT["name"], n))
        return 3

    content = original.replace(EDIT["anchor"], EDIT["replacement"], 1)
    print("[patch] %s staged." % EDIT["name"])

    if not args.apply:
        print("\n--- dry-run diff (no files written) ---")
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            content.splitlines(keepends=True),
            fromfile=target + " (current)",
            tofile=target + " (patched)",
            n=2,
        )
        sys.stdout.writelines(diff)
        print("\n--- end diff. Re-run with --apply to write. ---")
        return 0

    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup = "%s.bak_%s_%s" % (target, TAG, ts)
    shutil.copy2(target, backup)
    print("[backup] %s" % backup)
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(content)
    print("[patch]  wrote %s" % target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
