#!/usr/bin/env python3
"""
patch_dashboard_default_annotators.py

Make the two standard clinical-report annotators -- GeneBe and MobiDetails --
default-ON, in both layers where the default lives, so a rebuild or a pipeline
run never silently drops them. OncoKB and CancerVar stay opt-in.

Background
----------
Until now every annotator was opt-in everywhere:
  - build.py: --annotate-genebe / --annotate-mobidetails were store_true,
    default False, so forgetting the flag on a manual rebuild produced an empty
    annotation block (the GeneBe block went blank while its coordinate-derived
    link persisted).
  - the pipeline: dashboard.nf gated GeneBe on params.genebe_enabled (default
    false) and never passed --annotate-mobidetails at all, so an end-to-end run
    produced no MobiDetails annotation.

What this changes (three files)
-------------------------------
1. bin/dashboard_builder/build.py
   - --annotate-genebe and --annotate-mobidetails now default ON, each paired
     with an explicit --no-annotate-* opt-out (Python 3.6-safe paired flags).
   - The two function signatures (collect_sample_context, build) flip their
     annotate_genebe / annotate_mobidetails defaults to True for consistency
     with programmatic callers.
   - The stale MobiDetails help text (which said MD adds no UI links) is
     corrected to describe the curated annotation block.

2. nextflow.config
   - genebe_enabled flips false -> true (GeneBe works anonymously, rate-limited,
     so this is safe without credentials; creds still raise the limits).
   - a new mobidetails_enabled = true param is added (MobiDetails had no param).

3. modules/local/dashboard.nf
   - The build.py invocation inverts its gating: instead of passing
     --annotate-genebe when enabled, it passes --no-annotate-genebe when
     DISABLED (so build.py's new default-on is respected and the param still
     controls behaviour). A matching --no-annotate-mobidetails opt-out line is
     added.

Net behaviour: both a manual build.py rebuild and a full pipeline run annotate
GeneBe + MobiDetails by default. Disable per-run with --no-annotate-genebe /
--no-annotate-mobidetails (manual) or genebe_enabled=false /
mobidetails_enabled=false (pipeline).

Idempotent, anchor-based, two-phase (validate every file before writing any).
Dry-run by default; pass --apply to write. Timestamped .bak_<tag>_<UTC> backups.
Python 3.6-safe.
"""

import argparse
import datetime
import os
import sys

REPO_DEFAULT = "/goast/hemat_data/nf-core-tspipe"
TAG = "defaultann"

# Two literal backslashes, built without escaping ambiguity, for the shell
# line-continuation that the Nextflow heredoc requires on the inserted line.
BS2 = chr(92) + chr(92)

BUILD_PY = "bin/dashboard_builder/build.py"
NF_CONFIG = "nextflow.config"
DASH_NF = "modules/local/dashboard.nf"

# ----------------------------------------------------------------------------
# build.py edits
# ----------------------------------------------------------------------------
BUILD_EDITS = [
    # signature: collect_sample_context
    (
        'def collect_sample_context(sample_dir, build_time, subdir="",\n'
        '                           annotate_genebe=False, genebe_user=None, genebe_key=None,\n'
        '                           annotate_mobidetails=False,',
        'def collect_sample_context(sample_dir, build_time, subdir="",\n'
        '                           annotate_genebe=True, genebe_user=None, genebe_key=None,\n'
        '                           annotate_mobidetails=True,',
    ),
    # signature: build
    (
        'def build(run_dir, subdir="",\n'
        '          annotate_genebe=False, genebe_user=None, genebe_key=None,\n'
        '          annotate_mobidetails=False,',
        'def build(run_dir, subdir="",\n'
        '          annotate_genebe=True, genebe_user=None, genebe_key=None,\n'
        '          annotate_mobidetails=True,',
    ),
    # argparse: --annotate-genebe -> default on + --no-annotate-genebe
    (
        '    parser.add_argument(\n'
        '        "--annotate-genebe", action="store_true",\n'
        '        help="Annotate clinical variants via the GeneBe REST API at build time (network required)."\n'
        '    )',
        '    parser.add_argument(\n'
        '        "--annotate-genebe", dest="annotate_genebe", action="store_true", default=True,\n'
        '        help="Annotate clinical variants via the GeneBe REST API at build time "\n'
        '             "(network required). On by default; works anonymously (rate-limited) "\n'
        '             "or with --genebe-user/--genebe-key. Use --no-annotate-genebe to disable."\n'
        '    )\n'
        '    parser.add_argument(\n'
        '        "--no-annotate-genebe", dest="annotate_genebe", action="store_false",\n'
        '        help="Disable the default GeneBe annotation for this run."\n'
        '    )',
    ),
    # argparse: --annotate-mobidetails -> default on + --no-annotate-mobidetails
    # (also corrects the stale help text)
    (
        '    parser.add_argument(\n'
        '        "--annotate-mobidetails", action="store_true",\n'
        '        help="Resolve clinical variants to MobiDetails record IDs at build time "\n'
        '             "via the /api/variant/exists endpoint (network required, no API key). "\n'
        '             "Writes <sample>_mobidetails_cache.json with which variants are known "\n'
        '             "to MD. Note: this does NOT add UI links -- MD has no reliable "\n'
        '             "anonymous deep link, so the cache is for audit purposes only. "\n'
        '             "The user-facing path is the Copy VV_HGVS dropdown."\n'
        '    )',
        '    parser.add_argument(\n'
        '        "--annotate-mobidetails", dest="annotate_mobidetails", action="store_true", default=True,\n'
        '        help="Annotate clinical variants via the MobiDetails API at build time "\n'
        '             "(network required, keyless academic API). Fetches the full variant "\n'
        '             "record and renders a curated clinical block (ClinVar, gnomAD v4, "\n'
        '             "REVEL, AlphaMissense, CADD, SpliceAI, MPA, etc.) in each variant\'s "\n'
        '             "detail panel, caching to <sample>_mobidetails_cache.json. On by "\n'
        '             "default; use --no-annotate-mobidetails to disable."\n'
        '    )\n'
        '    parser.add_argument(\n'
        '        "--no-annotate-mobidetails", dest="annotate_mobidetails", action="store_false",\n'
        '        help="Disable the default MobiDetails annotation for this run."\n'
        '    )',
    ),
]

# ----------------------------------------------------------------------------
# nextflow.config edits
# ----------------------------------------------------------------------------
NF_EDITS = [
    (
        '    // ---- Dashboard GeneBe annotation (opt-in) ------------------------\n'
        '    // GeneBe (https://genebe.net) adds ACMG classification, ClinVar\n'
        '    // status, and gnomAD frequencies to the dashboard\'s Variants tab.\n'
        '    // Defaults below keep the feature disabled. To enable, set\n'
        '    // genebe_enabled = true and provide the credentials via the\n'
        '    // credentials.config file loaded at the bottom of this file (NOT\n'
        '    // here, so the key never lands in version control).\n'
        '    genebe_enabled = false\n'
        '    genebe_user    = null\n'
        '    genebe_key     = null',
        '    // ---- Dashboard GeneBe annotation (default on) --------------------\n'
        '    // GeneBe (https://genebe.net) adds ACMG classification, ClinVar\n'
        '    // status, and gnomAD frequencies to the dashboard\'s Variants tab.\n'
        '    // On by default. GeneBe works anonymously (rate-limited); for higher\n'
        '    // limits, set genebe_user / genebe_key via the credentials.config\n'
        '    // file loaded at the bottom of this file (NOT here, so the key never\n'
        '    // lands in version control). To disable, set genebe_enabled = false.\n'
        '    genebe_enabled = true\n'
        '    genebe_user    = null\n'
        '    genebe_key     = null\n'
        '\n'
        '    // ---- Dashboard MobiDetails annotation (default on) ---------------\n'
        '    // MobiDetails (https://mobidetails.chu-montpellier.fr) adds a curated\n'
        '    // clinical annotation block (ClinVar, gnomAD v4, REVEL, AlphaMissense,\n'
        '    // CADD, SpliceAI, MPA, etc.) to each variant\'s detail panel. Keyless\n'
        '    // academic API; no credentials required. To disable, set\n'
        '    // mobidetails_enabled = false.\n'
        '    mobidetails_enabled = true',
    ),
]

# ----------------------------------------------------------------------------
# dashboard.nf edits (surgical; backslashes via BS2 to avoid escaping issues)
# ----------------------------------------------------------------------------
DASH_EDITS = [
    # invert GeneBe gating: opt-out when disabled, so build.py default-on is respected
    (
        'params.genebe_enabled ? "--annotate-genebe" : ""',
        'params.genebe_enabled ? "" : "--no-annotate-genebe"',
    ),
    # add a MobiDetails opt-out line just before the OncoKB line
    (
        '            ${ params.oncokb_enabled ? "--annotate-oncokb"',
        '            ${ params.mobidetails_enabled ? "" : "--no-annotate-mobidetails" } ' + BS2 + '\n'
        '            ${ params.oncokb_enabled ? "--annotate-oncokb"',
    ),
]

FILES = [
    (BUILD_PY, BUILD_EDITS, "--no-annotate-genebe"),
    (NF_CONFIG, NF_EDITS, "mobidetails_enabled"),
    (DASH_NF, DASH_EDITS, "--no-annotate-mobidetails"),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=REPO_DEFAULT,
                    help="repo root (default: %s)" % REPO_DEFAULT)
    ap.add_argument("--apply", action="store_true",
                    help="write changes (default: dry-run)")
    args = ap.parse_args()

    planned = []   # (path, new_src) for files needing a write
    errors = []

    # ---- Phase 1: validate every file; write nothing yet --------------------
    for rel, edits, marker in FILES:
        path = os.path.join(args.repo, rel)
        if not os.path.isfile(path):
            errors.append("%s :: file not found" % rel)
            continue
        with open(path, "r", encoding="utf-8") as fh:
            src = fh.read()
        if marker in src:
            print("[skip] %s :: already patched (marker '%s' present)." % (rel, marker))
            continue
        new_src = src
        ok = True
        for old, new in edits:
            count = new_src.count(old)
            if count == 0:
                errors.append("%s :: anchor not found:\n        %s" % (rel, old.splitlines()[0]))
                ok = False
                break
            if count > 1:
                errors.append("%s :: anchor matched %d times (expected 1):\n        %s"
                              % (rel, count, old.splitlines()[0]))
                ok = False
                break
            new_src = new_src.replace(old, new)
        if ok and new_src != src:
            planned.append((path, new_src, rel))

    if errors:
        print("[error] aborting -- no files written. Issues:")
        for e in errors:
            print("  - %s" % e)
        return 3

    if not planned:
        print("[done] nothing to do (all target files already patched).")
        return 0

    if not args.apply:
        for path, new_src, rel in planned:
            print("[dry-run] %s :: would apply edits (net %+d bytes)."
                  % (rel, len(new_src) - os.path.getsize(path)))
        print("[dry-run] re-run with --apply to write.")
        return 0

    # ---- Phase 2: write with backups ---------------------------------------
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    for path, new_src, rel in planned:
        with open(path, "r", encoding="utf-8") as fh:
            original = fh.read()
        bak = "%s.bak_%s_%s" % (path, TAG, ts)
        with open(bak, "w", encoding="utf-8") as fh:
            fh.write(original)
        print("[backup] %s" % bak)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(new_src)
        print("[patch]  wrote %s" % rel)

    print("[done]   GeneBe + MobiDetails are now default-on (build.py + pipeline).")
    print("         Manual rebuilds no longer need --annotate-genebe/-mobidetails;")
    print("         disable per-run with --no-annotate-genebe / --no-annotate-mobidetails,")
    print("         or in the pipeline via genebe_enabled / mobidetails_enabled.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
