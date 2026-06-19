#!/usr/bin/env python3
"""Add a Franklin (Genoox) hg38 deep-link to the variant detail panel.

Mirrors the existing client-side GeneBe deep-link. Two anchored edits to
    bin/dashboard_builder/assets/js/variant-browser.js
  1. add a franklinUrl(chr, pos, ref, alt) helper next to genebeUrl(); and
  2. render an "Open in Franklin" button next to "Open in GeneBe" in
     renderDetail().

The link points at Franklin's variant page with the -hg38 reference suffix,
which resolves the variant in GRCh38 coordinates. No API token and no network
call are involved: the reviewer clicks through to Franklin's full interpretation.

Idempotent and anchor-based. Dry-run by default; pass --apply to write. A
timestamped backup (.bak_franklinlink_<UTC>) is written before any change.
Python 3.6-safe.

Run from the repository root:
    python3 patch_dashboard_franklin_link.py            # dry-run (shows a diff)
    python3 patch_dashboard_franklin_link.py --apply     # write the change
    python3 patch_dashboard_franklin_link.py --file <path-to-variant-browser.js> --apply
"""

import argparse
import datetime
import difflib
import os
import shutil
import sys

DEFAULT_REL = os.path.join("bin", "dashboard_builder", "assets", "js", "variant-browser.js")
TAG = "franklinlink"

# Each edit: a unique marker that proves it is already applied, the exact
# on-disk anchor block, and the replacement block. Anchors are matched verbatim
# and must occur exactly once.
EDITS = [
    {
        "name": "franklinUrl() helper",
        "marker": "function franklinUrl(",
        "anchor": (
            '  function genebeUrl(chr, pos, ref, alt) {\n'
            '    const c = String(chr || "").replace(/^chr/, "");\n'
            '    return "https://genebe.net/variant/hg38/chr" + c + "-" + pos + "-" + ref + "-" + alt;\n'
            '  }\n'
        ),
        "replacement": (
            '  function genebeUrl(chr, pos, ref, alt) {\n'
            '    const c = String(chr || "").replace(/^chr/, "");\n'
            '    return "https://genebe.net/variant/hg38/chr" + c + "-" + pos + "-" + ref + "-" + alt;\n'
            '  }\n'
            '\n'
            '  // Build an hg38 Franklin (Genoox) deep link. The Franklin variant page\n'
            '  // accepts a -hg38 reference suffix on the chr-pos-ref-alt slug, which\n'
            '  // resolves the variant in GRCh38 coordinates (verified against the live\n'
            '  // page). No API token or network call is involved; the reviewer clicks\n'
            '  // through to the full Franklin ACMG interpretation. Slug keeps "chr".\n'
            '  function franklinUrl(chr, pos, ref, alt) {\n'
            '    const c = String(chr || "").replace(/^chr/, "");\n'
            '    return "https://franklin.genoox.com/clinical-db/variant/snp/chr" + c + "-" + pos + "-" + ref + "-" + alt + "-hg38";\n'
            '  }\n'
        ),
    },
    {
        "name": '"Open in Franklin" button',
        "marker": "const flUrl = franklinUrl(",
        "anchor": (
            '      const gbUrl = genebeUrl(chrClean, r.Start, r.Ref, r.Alt);\n'
            '\n'
            '      let extButtons =\n'
            '        \'<a href="\' + escapeHtml(gbUrl) + \'" target="_blank" rel="noopener" class="btn btn-sm btn-outline-primary">\' +\n'
            '          "Open in GeneBe \\u2197</a>";\n'
        ),
        "replacement": (
            '      const gbUrl = genebeUrl(chrClean, r.Start, r.Ref, r.Alt);\n'
            '      const flUrl = franklinUrl(chrClean, r.Start, r.Ref, r.Alt);\n'
            '\n'
            '      let extButtons =\n'
            '        \'<a href="\' + escapeHtml(gbUrl) + \'" target="_blank" rel="noopener" class="btn btn-sm btn-outline-primary">\' +\n'
            '          "Open in GeneBe \\u2197</a>" +\n'
            '        \'<a href="\' + escapeHtml(flUrl) + \'" target="_blank" rel="noopener" class="btn btn-sm btn-outline-primary">\' +\n'
            '          "Open in Franklin \\u2197</a>";\n'
        ),
    },
]


def main():
    ap = argparse.ArgumentParser(description="Add a Franklin hg38 deep-link to the dashboard variant detail panel.")
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

    content = original
    changed_any = False

    for edit in EDITS:
        name = edit["name"]
        if edit["marker"] in content:
            print("[skip]  %s already present." % name)
            continue
        n = content.count(edit["anchor"])
        if n == 0:
            print("[error] anchor for '%s' not found. File may have changed; not writing." % name)
            return 3
        if n > 1:
            print("[error] anchor for '%s' found %d times (expected 1); not writing." % (name, n))
            return 3
        content = content.replace(edit["anchor"], edit["replacement"], 1)
        changed_any = True
        print("[patch] %s staged." % name)

    if not changed_any:
        print("[skip]  Nothing to do; both edits already present.")
        return 0

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
