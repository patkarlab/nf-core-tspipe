#!/usr/bin/env python3
"""
patch_chrom_pages_v1.py -- wire CHROM_PAGES (MARKER CHROM_PAGES_V1).

Files (2), all-or-nothing:
  workflows/tspipe.nf       include; ch_purple_dir (HMF_PURPLE.out.dir or an empty
                            placeholder); CHROM_PAGES after EXON_PLOTS on the join of
                            consensus JSON + GATK allelic counts + DECoN filtered +
                            PURPLE dir; panel BED, base SNP catalog and BAF background
                            as values (empty when absent)
  conf/twist_apply.config   process CHROM_PAGES publishDir <outdir>/<sample>/cnv_consensus_multi
                            (pattern chrom_pages), like EXON_PLOTS

Requires EXON_PLOTS_V1, CNV_BLACKLIST_V1, HMF_PURPLE_V1. Dry run by default;
--apply writes .bak_chrom_pages_<ts> backups.
"""

import argparse
import datetime
import os
import re
import shutil
import sys

MARKER = "MARKER CHROM_PAGES_V1"
TAG = "CHROM_PAGES_V1"


def sub_once(text, pattern, repl, label, flags=re.M):
    rx = re.compile(pattern, flags)
    n = len(rx.findall(text))
    if n != 1:
        raise ValueError("anchor %s: expected 1 match, found %d (%s)" % ("not found" if n == 0 else "not unique", n, label))
    return rx.sub(repl, text, count=1), "[ok] %s" % label


CALL = '''
{i}// {m}: per-chromosome CNV pages in target space (depth, BAF, PURPLE, gene exon panels)
{i}def cp_panel_bed = "${{projectDir}}/assets/${{params.panel}}/panel.combined.filtered.bed"
{i}def cp_snp_base  = "${{projectDir}}/assets/${{params.panel}}/snp_sites.baf.base.bed"
{i}def cp_baf_bg    = "${{projectDir}}/assets/${{params.panel}}/baf_background.tsv"
{i}ch_cp_panel_bed = Channel.value(file(cp_panel_bed, checkIfExists: true))
{i}ch_cp_snp_base  = file(cp_snp_base).exists() ? Channel.value(file(cp_snp_base)) : Channel.value([])
{i}ch_cp_baf_bg    = file(cp_baf_bg).exists()   ? Channel.value(file(cp_baf_bg))   : Channel.value([])
{i}ch_chrom_pages_in = CNV_CONSENSUS_MULTI.out.json
{i}    .join( GATK_CNV_CALLING.out.allelic, by: 0 )
{i}    .join( ch_decon_filtered,            by: 0 )
{i}    .join( ch_purple_dir,                by: 0 )
{i}CHROM_PAGES( ch_chrom_pages_in, ch_cp_panel_bed, ch_cp_snp_base, ch_cp_baf_bg )'''

PROCESS = '''{i}// {m}: chromosome pages beside the consensus (GATK container: py3.6 + matplotlib)
{i}withName: 'CHROM_PAGES' {{
{i}    publishDir = [
{i}        path: {{ "${{params.outdir}}/${{meta.id}}/cnv_consensus_multi" }},
{i}        mode: 'copy',
{i}        pattern: 'chrom_pages'
{i}    ]
{i}}}
'''


def patch_tspipe(t):
    notes = []
    t, n = sub_once(t, r"^include \{ HMF_PURPLE\s*\} from '\.\./modules/local/hmf_purple'[^\n]*$",
                    lambda m: m.group(0) + "\ninclude { CHROM_PAGES         } from '../modules/local/chrom_pages'           // %s" % MARKER,
                    "include")
    notes.append(n)
    t, n = sub_once(t, r"^(?P<i>[ \t]*)ch_purple_summary = HMF_PURPLE\.out\.summary[ \t]*$",
                    lambda m: m.group(0) + "\n%sch_purple_dir     = HMF_PURPLE.out.dir   // %s" % (m.group("i"), TAG),
                    "ch_purple_dir (hmf on)")
    notes.append(n)
    t, n = sub_once(t, r"^(?P<i>[ \t]*)ch_purple_summary = ch_final_bam\.map \{ m, _b, _i -> \[ m, \[\] \] \}[ \t]*$",
                    lambda m: m.group(0) + "\n%sch_purple_dir     = ch_final_bam.map { m, _b, _i -> [ m, [] ] }   // %s" % (m.group("i"), TAG),
                    "ch_purple_dir (hmf off)")
    notes.append(n)
    t, n = sub_once(t, r"^(?P<i>[ \t]*)EXON_PLOTS\( ch_exon_plots_in, ch_focal_bed, ch_cnv_gene_blacklist \)[^\n]*$",
                    lambda m: m.group(0) + CALL.format(i=m.group("i"), m=TAG), "CHROM_PAGES call after EXON_PLOTS")
    notes.append(n)
    return t, notes


def patch_twist_apply(t):
    notes = []
    t, n = sub_once(t, r"^(?P<i>[ \t]*)withName: 'CNV_CONSENSUS_MULTI' \{[ \t]*$",
                    lambda m: PROCESS.format(i=m.group("i"), m=MARKER) + m.group(0), "process block")
    notes.append(n)
    return t, notes


FILES = [("workflows/tspipe.nf", patch_tspipe), ("conf/twist_apply.config", patch_twist_apply)]


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
            new_text, notes = fn(original)
        except ValueError as exc:
            print("   [error] %s" % exc); failed = True; continue
        for n in notes:
            print("   %s" % n)
        b0, b1 = original.count("{") - original.count("}"), new_text.count("{") - new_text.count("}")
        print("   [check] markers %d (expected 1); brace balance %d/%d" % (new_text.count(MARKER), b0, b1))
        if new_text.count(MARKER) != 1 or b0 != b1:
            print("   [error] verification failed"); failed = True; continue
        planned.append((path, original, new_text))
    if failed:
        print("\n[error] one or more files failed; nothing written"); sys.exit(1)
    if not planned:
        print("\n[skip] nothing to do"); sys.exit(0)
    if not args.apply:
        print("\n[dry-run] %d file(s) would change; re-run with --apply" % len(planned)); sys.exit(0)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    for path, original, new_text in planned:
        backup = "%s.bak_chrom_pages_%s" % (path, ts)
        shutil.copy2(path, backup)
        with open(path, "w") as fh:
            fh.write(new_text)
        print("[backup] %s" % os.path.relpath(backup, args.root))
        print("[patch]  wrote %s" % os.path.relpath(path, args.root))


if __name__ == "__main__":
    main()
