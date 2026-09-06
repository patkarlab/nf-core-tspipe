#!/usr/bin/env python3
"""
patch_preprocessing_sex_check.py -- wire SEX_CHECK into PREPROCESSING.

MARKER SEX_CHECK_V1. Idempotent, anchor-based. Dry run by default; --apply
writes with a timestamped backup (.bak_sex_check_<timestamp>).

Edits to subworkflows/local/preprocessing.nf:
  1. include SEX_CHECK after the PARSE_EXON_COVERAGE include
  2. helper function withResolvedSex() before 'workflow PREPROCESSING {'
  3. SEX_CHECK call + ch_sex_by_id after the PARSE_EXON_COVERAGE call
  4. every emit rewritten through withResolvedSex(), plus a sex_check emit

meta.sex is rewritten only when the sheet value is not male/female, so for
sheets with a known sex meta is unchanged and -resume caches are intact.

Usage:
    python3 tools/patches/2026-09-06/patch_preprocessing_sex_check.py            # dry run
    python3 tools/patches/2026-09-06/patch_preprocessing_sex_check.py --apply
"""

import argparse
import datetime
import os
import re
import shutil
import sys

MARKER = "MARKER SEX_CHECK_V1"
EXPECTED_MARKERS = 4
TARGET_DEFAULT = "subworkflows/local/preprocessing.nf"

INCLUDE_ANCHOR = re.compile(
    r"^include \{ PARSE_EXON_COVERAGE\s*\} from '\.\./\.\./modules/local/parse_exon_coverage'[ \t]*$",
    re.M)
INCLUDE_LINE = "include { SEX_CHECK              } from '../../modules/local/sex_check'   // %s" % MARKER

WORKFLOW_ANCHOR = re.compile(r"^workflow PREPROCESSING \{[ \t]*$", re.M)
HELPER = '''// %s: rewrite meta.sex on a [meta, ...] channel from the per-sample
// resolved sex keyed on meta.id. Samplesheet male/female always wins; 'unknown'
// takes the inference; a sample with no SEX_CHECK row keeps its meta. The key
// set of meta is unchanged, so task hashes only move when the value moves.
def withResolvedSex(ch, sex_by_id) {
    ch.map { it -> [ it[0].id, it ] }
      .join(sex_by_id, remainder: true)
      .filter { id, tup, sex -> tup != null }
      .map { id, tup, sex ->
          def meta     = tup[0]
          def resolved = (meta.sex in ['male', 'female']) ? meta.sex : (sex ?: meta.sex)
          [ meta + [sex: resolved] ] + tup.drop(1)
      }
}

''' % MARKER

CALL_ANCHOR = re.compile(
    r"^(?P<indent>[ \t]+)PARSE_EXON_COVERAGE\(MOSDEPTH\.out\.regions_thresholds, exonwise_bed_ch\)[ \t]*$",
    re.M)
CALL_BLOCK = '''
{i}// {m}: sex from the mosdepth regions (X/A ratio); one row per sample.
{i}// resolved_sex = sheet value if male/female, else the inference.
{i}SEX_CHECK(MOSDEPTH.out.regions_thresholds)
{i}ch_sex_by_id = SEX_CHECK.out.tsv
{i}    .splitCsv(header: true, sep: '\\t', elem: 1)
{i}    .map {{ meta, row ->
{i}        if( row.status == 'MISMATCH' )
{i}            log.warn "[SEX_CHECK] ${{meta.id}}: samplesheet sex=${{row.sheet_sex}} but data infers ${{row.inferred_sex}} (X/A=${{row.x_auto_ratio}}); keeping the samplesheet value"
{i}        else if( row.sheet_sex == 'unknown' )
{i}            log.info "[SEX_CHECK] ${{meta.id}}: samplesheet sex unknown; using inferred ${{row.resolved_sex}} (X/A=${{row.x_auto_ratio}}, status=${{row.status}})"
{i}        [ meta.id, row.resolved_sex ]
{i}    }}
'''

EMIT_BLOCK = re.compile(r"^(?P<indent>[ \t]+)emit:[ \t]*\n(?P<body>.*?)(?P<close>^\}[ \t]*$)", re.M | re.S)
EMIT_LINE = re.compile(r"^(?P<indent>[ \t]+)(?P<name>\w+)[ \t]*=[ \t]*(?P<expr>\S.*?)[ \t]*$")


def patch(text):
    if MARKER in text:
        return None, "[skip] %s already present (%d occurrences)" % (MARKER, text.count(MARKER))

    # 1. include
    m = INCLUDE_ANCHOR.search(text)
    if not m:
        return None, "[error] include anchor for PARSE_EXON_COVERAGE not found"
    text = text[:m.end()] + "\n" + INCLUDE_LINE + text[m.end():]

    # 2. helper before workflow
    m = WORKFLOW_ANCHOR.search(text)
    if not m:
        return None, "[error] 'workflow PREPROCESSING {' anchor not found"
    text = text[:m.start()] + HELPER + text[m.start():]

    # 3. call block after PARSE_EXON_COVERAGE call
    m = CALL_ANCHOR.search(text)
    if not m:
        return None, "[error] PARSE_EXON_COVERAGE(...) call anchor not found"
    text = text[:m.end()] + CALL_BLOCK.format(i=m.group("indent"), m=MARKER) + text[m.end():]

    # 4. emit block
    m = EMIT_BLOCK.search(text)
    if not m:
        return None, "[error] emit block not found"
    indent = m.group("indent")
    body_lines = m.group("body").splitlines()
    emits = []
    for line in body_lines:
        if not line.strip():
            continue
        lm = EMIT_LINE.match(line)
        if not lm:
            return None, "[error] unparsed emit line: %r" % line
        emits.append((lm.group("name"), lm.group("expr")))
    if not emits:
        return None, "[error] emit block is empty"
    names = [n for n, _ in emits]
    if "sex_check" in names:
        return None, "[error] emit 'sex_check' already exists without marker; inspect by hand"

    inner = indent + "    "
    width = max(len(n) for n in names + ["sex_check"])
    main_lines = [indent + "    // %s: resolved meta.sex on every emit so downstream joins stay consistent" % MARKER]
    for name, expr in emits:
        main_lines.append("%sch_sexed_%s = withResolvedSex(%s, ch_sex_by_id)" % (inner, name, expr))
    main_lines.append("%sch_sexed_sex_check = withResolvedSex(SEX_CHECK.out.tsv, ch_sex_by_id)" % inner)
    emit_lines = [indent + "emit:"]
    for name in names + ["sex_check"]:
        emit_lines.append("%s%-*s = ch_sexed_%s" % (inner, width, name, name))

    new_block = "\n".join(main_lines) + "\n\n" + "\n".join(emit_lines) + "\n" + m.group("close")
    text = text[:m.start()] + new_block + text[m.end():]
    return text, "[patch] 4 edits applied"


def brace_balance(text):
    return text.count("{") - text.count("}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default=TARGET_DEFAULT)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    if not os.path.isfile(args.target):
        print("[error] target not found: %s" % args.target)
        sys.exit(1)
    original = open(args.target).read()
    before_balance = brace_balance(original)

    new_text, msg = patch(original)
    print(msg)
    if new_text is None:
        sys.exit(0 if msg.startswith("[skip]") else 1)

    n_markers = new_text.count(MARKER)
    after_balance = brace_balance(new_text)
    print("[check] markers: %d (expected %d); brace balance before/after: %d/%d"
          % (n_markers, EXPECTED_MARKERS, before_balance, after_balance))
    if n_markers != EXPECTED_MARKERS or after_balance != before_balance:
        print("[error] verification failed; nothing written")
        sys.exit(1)

    if not args.apply:
        print("[dry-run] no changes written; re-run with --apply")
        print("---- diff preview (new lines only) ----")
        old_set = set(original.splitlines())
        for line in new_text.splitlines():
            if line not in old_set:
                print("+ " + line)
        sys.exit(0)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = "%s.bak_sex_check_%s" % (args.target, ts)
    shutil.copy2(args.target, backup)
    print("[backup] %s" % backup)
    with open(args.target, "w") as fh:
        fh.write(new_text)
    print("[patch] wrote %s" % args.target)


if __name__ == "__main__":
    main()
