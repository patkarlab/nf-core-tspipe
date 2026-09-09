#!/usr/bin/env python3
"""SEXCHECK_POLICY_V1 -- audit Q1/Q2, policy decided 9 Sep 2026: the run never stops on the sex
check; a failed check, an indeterminate inference, or a samplesheet/inference mismatch forces
the QC verdict to REVIEW so sample identity is confirmed before sign-out. The samplesheet sex
is kept on a mismatch (meta.sex is in every task hash; switching would re-execute the sample).

Run from the nf-core-tspipe repo root. Dry-run by default; --apply writes. All-or-nothing;
.bak_SEXCHECK_POLICY_V1_<timestamp> backups.

bin/sex_check.py                        (in the SEX_CHECK task hash -> 8 fast re-executions
                                         on resume; outputs identical for run8, downstream cached)
  - an exception writes status ERROR (was INDETERMINATE, indistinguishable from a data-driven
    indeterminate) with the traceback on stderr (.command.log); exit code stays 0.
bin/dashboard_builder/parsers/coverage.py (not hashed -> nocache re-render)
  - verdict(): ERROR -> REVIEW; MISMATCH (by status, so the depth-only case counts too) ->
    REVIEW; INDETERMINATE -> REVIEW; sheet-unknown stays a finding. Previously only a
    sheet-vs-heterozygosity mismatch reviewed; a crashed or indeterminate check passed.
subworkflows/local/preprocessing.nf     (workflow file, not hashed)
  - log.warn on status ERROR.
"""
import argparse
import os
import shutil
import sys
import time

TAG = "SEXCHECK_POLICY_V1"
STAMP = time.strftime("%Y%m%d_%H%M%S")


class PatchError(Exception):
    pass


def read(path):
    if not os.path.isfile(path):
        raise PatchError("missing file: %s" % path)
    with open(path) as f:
        return f.read()


def replace_once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise PatchError("%s: anchor found %d times (expected 1): %r" % (label, n, old[:80]))
    return text.replace(old, new)


def patch_sex_check(text):
    if TAG in text:
        return text, "skip"
    text = replace_once(
        text,
        "A MISMATCH between sheet and inference never overrides the sheet.\n",
        "A MISMATCH between sheet and inference never overrides the sheet.\n"
        "SEXCHECK_POLICY_V1: an exception inside run() writes status ERROR (flags\n"
        "ERROR:<message>, traceback on stderr) and still exits 0; the QC verdict\n"
        "turns ERROR, INDETERMINATE and MISMATCH into REVIEW. The run never stops\n"
        "on the sex check.\n",
        "sex_check docstring")
    text = replace_once(
        text,
        "import sys\n",
        "import sys\nimport traceback   # SEXCHECK_POLICY_V1\n",
        "sex_check import")
    text = replace_once(
        text,
        '        "resolved_sex": sheet, "status": "INDETERMINATE",\n',
        '        "resolved_sex": sheet, "status": "ERROR",   # SEXCHECK_POLICY_V1: distinct from a data-driven INDETERMINATE\n',
        "sex_check error_row status")
    text = replace_once(
        text,
        '    except Exception as exc:  # never fail the sample: emit an indeterminate row\n'
        '        error_row(args, exc)\n'
        '        sys.stderr.write("[sex_check] ERROR %s: %s (wrote indeterminate row)\\n" % (args.sample, exc))\n'
        '        rc = 0\n',
        '    except Exception as exc:  # SEXCHECK_POLICY_V1: never fail the sample; status ERROR forces QC REVIEW\n'
        '        error_row(args, exc)\n'
        '        traceback.print_exc(file=sys.stderr)\n'
        '        sys.stderr.write("[sex_check] ERROR %s: %s (wrote status=ERROR row; QC verdict will be REVIEW)\\n"\n'
        '                         % (args.sample, exc))\n'
        '        rc = 0\n',
        "sex_check except block")
    return text, "patch"


COVERAGE_OLD = '''        if sheet in ("male", "female") and het in ("male", "female") and sheet != het:
            review.append("Sex mismatch: samplesheet %s, chrX heterozygosity %s (possible sample swap)" % (sheet, het))
        elif sheet not in ("male", "female"):
            findings.append("Sex not given on the samplesheet; %s inferred from chrX heterozygosity" % (het or res or "unknown"))
'''
COVERAGE_NEW = '''        # SEXCHECK_POLICY_V1 (audit Q1/Q2, decision 9 Sep 2026): the run never stops on the sex
        # check; a failed check, an indeterminate inference or a sheet/inference mismatch forces
        # REVIEW so sample identity is confirmed before sign-out. MISMATCH is taken from the
        # status column so the depth-only (no het catalog) case counts too.
        inf = (sx.get("inferred_sex") or "").strip().lower()
        method = (sx.get("method") or "").strip()
        if status_sx == "ERROR" or flags.startswith("ERROR:"):
            review.append("Sex check failed to run (%s); sample identity not verified" % (flags or "no detail"))
        elif status_sx == "MISMATCH" or (sheet in ("male", "female") and inf in ("male", "female") and sheet != inf):
            review.append("Sex mismatch: samplesheet %s, data infers %s by %s (possible sample swap); samplesheet value kept"
                          % (sheet, inf or het or "unknown", method or "unknown method"))
        elif status_sx == "INDETERMINATE" or inf == "indeterminate":
            review.append("Sex could not be inferred from the data (%s); sample identity not verified"
                          % (flags or method or "insufficient sites"))
        elif sheet not in ("male", "female"):
            findings.append("Sex not given on the samplesheet; %s inferred from chrX heterozygosity" % (het or res or "unknown"))
'''


def patch_coverage(text):
    if TAG in text:
        return text, "skip"
    return replace_once(text, COVERAGE_OLD, COVERAGE_NEW, "coverage.py verdict sex block"), "patch"


def patch_preprocessing(text):
    if TAG in text:
        return text, "skip"
    return replace_once(
        text,
        "                    if( row.status == 'MISMATCH' )\n",
        "                    if( row.status == 'ERROR' )   // SEXCHECK_POLICY_V1\n"
        "                        log.warn \"[SEX_CHECK] ${meta.id}: sex check failed (${row.flags}); continuing with samplesheet sex '${row.resolved_sex}'; QC verdict will be REVIEW\"\n"
        "                    else if( row.status == 'MISMATCH' )\n",
        "preprocessing.nf ERROR log"), "patch"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    ap.add_argument("--repo", default=".", help="repo root (default: cwd)")
    args = ap.parse_args()
    os.chdir(args.repo)
    targets = [
        ("bin/sex_check.py", patch_sex_check),
        ("bin/dashboard_builder/parsers/coverage.py", patch_coverage),
        ("subworkflows/local/preprocessing.nf", patch_preprocessing),
    ]
    plan = []
    try:
        for path, fn in targets:
            new, status = fn(read(path))
            plan.append((path, new, status))
    except PatchError as e:
        print("[error] %s" % e)
        print("[error] nothing written")
        sys.exit(1)
    for path, _, status in plan:
        print("[%s] %s" % (status, path))
    if not args.apply:
        print("[dry-run] re-run with --apply to write")
        return
    for path, new, status in plan:
        if status == "skip":
            continue
        bak = "%s.bak_%s_%s" % (path, TAG, STAMP)
        shutil.copy2(path, bak)
        print("[backup] %s" % bak)
        with open(path, "w") as f:
            f.write(new)
        print("[write] %s" % path)
    print("[done] %s applied" % TAG)


if __name__ == "__main__":
    main()
