#!/usr/bin/env python3
"""
patch_exon_plots_v1.py -- wire EXON_PLOTS (MARKER EXON_PLOTS_V1).

Files (2), all-or-nothing:
  conf/twist_apply.config   params exon_plot_min_bf (5); process EXON_PLOTS
                            publishDir <outdir>/<sample>/cnv_consensus_multi/exon_plots
  workflows/tspipe.nf       include; ch_decon_filtered (DECON.out.filtered, or an
                            empty placeholder) beside ch_decon_genes; EXON_PLOTS
                            call after CNV_CONSENSUS_MULTI with the focal-CNV BED
                            as a value (empty when the panel has none)

Requires DECON_V1/V1a and PUBLISH_CLINICAL_V2. Dry run by default; --apply
writes with .bak_exon_plots_<ts> backups.
"""

import argparse
import datetime
import os
import re
import shutil
import sys

MARKER = "MARKER EXON_PLOTS_V1"
TAG = "EXON_PLOTS_V1"


def sub_once(text, pattern, repl, label, flags=re.M):
    rx = re.compile(pattern, flags)
    n = len(rx.findall(text))
    if n != 1:
        raise ValueError("anchor %s: expected 1 match, found %d (%s)" % ("not found" if n == 0 else "not unique", n, label))
    return rx.sub(repl, text, count=1), "[ok] %s" % label


PARAMS = '''
{i}// {m}: exon-level figures; DECoN calls at or above this BF are drawn
{i}exon_plot_min_bf   = 5'''

PROCESS = '''{i}// {m}: exon-level figures beside the consensus (GATK container: py3.6 + matplotlib)
{i}withName: 'EXON_PLOTS' {{
{i}    publishDir = [
{i}        path: {{ "${{params.outdir}}/${{meta.id}}/cnv_consensus_multi" }},
{i}        mode: 'copy',
{i}        pattern: 'exon_plots'
{i}    ]
{i}}}
'''

CALL = '''
{i}// {m}: per-chromosome exon figures from the consensus bins (+ DECoN brackets)
{i}def focal_bed = "${{projectDir}}/assets/${{params.panel}}/targets.focal_cnv.bed"
{i}ch_focal_bed = file(focal_bed).exists() ? Channel.value(file(focal_bed)) : Channel.value([])
{i}ch_exon_plots_in = CNV_CONSENSUS_MULTI.out.json
{i}    .join( CNV_CONSENSUS_MULTI.out.genes, by: 0 )
{i}    .join( ch_decon_filtered,             by: 0 )
{i}EXON_PLOTS( ch_exon_plots_in, ch_focal_bed )'''


def patch_twist_apply(t):
    notes = []
    t, n = sub_once(t, r'^(?P<i>[ \t]*)decon_bf[ \t]*=[ \t]*12[ \t]*$',
                    lambda m: m.group(0) + PARAMS.format(i=m.group("i"), m=MARKER), "twist_apply.config: exon_plot_min_bf")
    notes.append(n)
    t, n = sub_once(t, r"^(?P<i>[ \t]*)withName: 'CNV_CONSENSUS_MULTI' \{[ \t]*$",
                    lambda m: PROCESS.format(i=m.group("i"), m=TAG) + m.group(0), "twist_apply.config: EXON_PLOTS process block")
    notes.append(n)
    return t, notes, 1


def patch_tspipe(t):
    notes = []
    t, n = sub_once(t, r"^include \{ DECON\s*\} from '\.\./modules/local/decon'[^\n]*$",
                    lambda m: m.group(0) + "\ninclude { EXON_PLOTS          } from '../modules/local/exon_plots'            // %s" % MARKER,
                    "tspipe.nf: include")
    notes.append(n)
    t, n = sub_once(t, r"^(?P<i>[ \t]*)ch_decon_genes = DECON\.out\.genes[ \t]*$",
                    lambda m: m.group(0) + "\n%sch_decon_filtered = DECON.out.filtered   // %s" % (m.group("i"), TAG),
                    "tspipe.nf: ch_decon_filtered (DECON on)")
    notes.append(n)
    t, n = sub_once(t, r"^(?P<i>[ \t]*)ch_decon_genes = ch_final_bam\.map \{ m, _b, _i -> \[ m, \[\] \] \}[ \t]*$",
                    lambda m: m.group(0) + "\n%sch_decon_filtered = ch_final_bam.map { m, _b, _i -> [ m, [] ] }   // %s" % (m.group("i"), TAG),
                    "tspipe.nf: ch_decon_filtered (DECON off)")
    notes.append(n)
    t, n = sub_once(t, r"^(?P<i>[ \t]*)CNV_CONSENSUS_MULTI\( ch_consensus_in, ch_cnv_loo_summary, ch_cnv_loo_summary_female \)[^\n]*$",
                    lambda m: m.group(0) + CALL.format(i=m.group("i"), m=TAG), "tspipe.nf: EXON_PLOTS call")
    notes.append(n)
    return t, notes, 1


FILES = [("conf/twist_apply.config", patch_twist_apply), ("workflows/tspipe.nf", patch_tspipe)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    planned, failed = [], False
    for rel, fn in FILES:
        path = os.path.join(args.root, rel)
        print("== %s" % rel)
        if not os.path.isfile(path):
            print("   [error] file not found"); failed = True; continue
        original = open(path).read()
        if MARKER in original:
            print("   [skip] %s already present" % MARKER); continue
        try:
            new_text, notes, expected = fn(original)
        except ValueError as exc:
            print("   [error] %s" % exc); failed = True; continue
        for n in notes:
            print("   %s" % n)
        b0, b1 = original.count("{") - original.count("}"), new_text.count("{") - new_text.count("}")
        print("   [check] markers %d (expected %d); brace balance %d/%d" % (new_text.count(MARKER), expected, b0, b1))
        if new_text.count(MARKER) != expected or b0 != b1:
            print("   [error] verification failed"); failed = True; continue
        planned.append((path, original, new_text))
    if failed:
        print("\n[error] one or more files failed; nothing written"); sys.exit(1)
    if not planned:
        print("\n[skip] nothing to do"); sys.exit(0)
    if not args.apply:
        print("\n[dry-run] %d file(s) would change; re-run with --apply" % len(planned))
        for path, original, new_text in planned:
            old_set = set(original.splitlines())
            print("## %s" % os.path.relpath(path, args.root))
            for line in new_text.splitlines():
                if line not in old_set:
                    print("+ " + line)
        sys.exit(0)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    for path, original, new_text in planned:
        backup = "%s.bak_exon_plots_%s" % (path, ts)
        shutil.copy2(path, backup)
        with open(path, "w") as fh:
            fh.write(new_text)
        print("[backup] %s" % os.path.relpath(backup, args.root))
        print("[patch]  wrote %s" % os.path.relpath(path, args.root))


if __name__ == "__main__":
    main()
