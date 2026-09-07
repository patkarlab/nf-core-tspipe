#!/usr/bin/env python3
"""
patch_organize_cnv_v1.py -- v2 CNV outputs into clinical/cnv/ (MARKER ORG_CNV_V1).
Handoff item 12, ORGANIZE_OUTPUT routing.

Files (3), all-or-nothing:
  bin/organize_output.py           eleven optional args; hardlinks into clinical/cnv/
                                   {consensus,exon_plots,chrom_pages,decon,purple,sex_check}/;
                                   absent or empty inputs are skipped with a log line
  modules/local/organize_output.nf tuple gains the eleven paths; args passed when present
  workflows/tspipe.nf              ch_organize gains the joins (placeholders exist for
                                   DECoN and PURPLE when those arms are off)

The dashboard sees only clinical/, so this is what makes the consensus tables,
exon plots, chromosome pages, DECoN tables, PURPLE summaries and the sex check
visible to it and to report.zip. Dry run by default; --apply writes .bak_org_cnv_<ts>.
"""

import argparse
import datetime
import os
import re
import shutil
import sys

MARKER = "MARKER ORG_CNV_V1"
TAG = "ORG_CNV_V1"


def sub_once(text, pattern, repl, label, flags=re.M):
    rx = re.compile(pattern, flags)
    n = len(rx.findall(text))
    if n != 1:
        raise ValueError("anchor %s: expected 1 match, found %d (%s)" % ("not found" if n == 0 else "not unique", n, label))
    return rx.sub(repl, text, count=1), "[ok] %s" % label


NEW_ARGS = [
    ("cnv-consensus-genes",    "CMX consensus per-gene table"),
    ("cnv-consensus-segments", "CMX consensus segment intersection"),
    ("cnv-consensus-json",     "CMX consensus JSON (tracks for figures)"),
    ("exon-plots-dir",         "EXON_PLOTS directory (per-chromosome exon figures + index)"),
    ("chrom-pages-dir",        "CHROM_PAGES directory (per-chromosome pages + index)"),
    ("decon-filtered",         "DECoN filtered calls"),
    ("decon-genes",            "DECoN per-gene table (arm E contract)"),
    ("purple-summary",         "PURPLE arm H summary"),
    ("purple-genes",           "PURPLE arm H gene table"),
    ("purple-dir",             "PURPLE output directory"),
    ("sex-check",              "SEX_CHECK table"),
]

PY_ARGS = "".join('    parser.add_argument("--%s", default=None, help="%s (optional; %s)")\n' % (a, h, TAG) for a, h in NEW_ARGS)

PY_BLOCK = '''    # --- CNV v2 (%s): consensus, exon plots, chromosome pages, DECoN, PURPLE, sex check ---
    logger.info("--- CNV v2 ---")
    cnv2 = out / "cnv"

    def present(p):
        return bool(p) and Path(p).exists() and not is_sentinel(Path(p))

    for src, sub, desc in (
            (args.cnv_consensus_genes,    "consensus", "CMX consensus per-gene table"),
            (args.cnv_consensus_segments, "consensus", "CMX consensus segments"),
            (args.cnv_consensus_json,     "consensus", "CMX consensus JSON"),
            (args.decon_filtered,         "decon",     "DECoN filtered calls"),
            (args.decon_genes,            "decon",     "DECoN per-gene table"),
            (args.purple_summary,         "purple",    "PURPLE arm H summary"),
            (args.purple_genes,           "purple",    "PURPLE arm H gene table"),
            (args.sex_check,              "sex_check", "SEX_CHECK table")):
        if present(src):
            hardlink(src, cnv2 / sub / Path(src).name, desc)
        else:
            logger.info("skip (absent): %%s", desc)
    for src, sub, desc in (
            (args.exon_plots_dir,  "exon_plots",  "exon figures"),
            (args.chrom_pages_dir, "chrom_pages", "chromosome pages"),
            (args.purple_dir,      "purple",      "PURPLE outputs")):
        if src and Path(src).is_dir():
            hardlink_dir(Path(src), cnv2 / sub, "CNV v2 " + desc)
        else:
            logger.info("skip (absent): %%s", desc)

''' % MARKER


def patch_py(t):
    notes = []
    t, n = sub_once(t, r'^    parser\.add_argument\("--cnvkit-plots-dir", required=True\)\n',
                    lambda m: m.group(0) + PY_ARGS, "argparse: eleven optional args")
    notes.append(n)
    t, n = sub_once(t, r'^    # --- Summary ---\n', lambda m: PY_BLOCK + m.group(0), "routing block before the summary")
    notes.append(n)
    return t, notes


NF_INPUTS = '''              path(cnvkit_plots_dir),
              path(cnv_consensus_genes), path(cnv_consensus_segments), path(cnv_consensus_json),   // %s
              path(exon_plots_dir), path(chrom_pages_dir),
              path(decon_filtered), path(decon_genes),
              path(purple_summary), path(purple_genes), path(purple_dir),
              path(sex_check)''' % MARKER


def patch_nf(t):
    notes = []
    t, n = sub_once(t, r'^(?P<i>[ \t]*)path\(cnvkit_plots_dir\)[ \t]*$', lambda m: NF_INPUTS, "input tuple gains eleven paths")
    notes.append(n)
    opts = [("cnv_consensus_genes", "cnv-consensus-genes"), ("cnv_consensus_segments", "cnv-consensus-segments"),
            ("cnv_consensus_json", "cnv-consensus-json"), ("exon_plots_dir", "exon-plots-dir"), ("chrom_pages_dir", "chrom-pages-dir"),
            ("decon_filtered", "decon-filtered"), ("decon_genes", "decon-genes"), ("purple_summary", "purple-summary"),
            ("purple_genes", "purple-genes"), ("purple_dir", "purple-dir"), ("sex_check", "sex-check")]
    defs = "\n".join("        def %s_arg = %s ? \"--%s ${%s}\" : ''" % (v, v, a, v) for v, a in opts)
    t, n = sub_once(t, r'^(?P<i>[ \t]*)script:[ \t]*\n', lambda m: m.group(0) + "        // %s: optional v2 CNV args\n%s\n" % (TAG, defs), "script: optional arg definitions")
    notes.append(n)
    rx = re.compile(r'^(?P<i>[ \t]*)--cnvkit-plots-dir[ \t]+\$\{cnvkit_plots_dir\}(?P<tail>[ \t]*\\\\)?[ \t]*$', re.M)
    m_all = rx.findall(t)
    if len(m_all) != 1:
        raise ValueError("anchor --cnvkit-plots-dir line: %d matches" % len(m_all))
    m = rx.search(t)
    ind = m.group("i")
    extra = " \\\\\n".join("%s${%s_arg}" % (ind, v) for v, _ in opts)
    if m.group("tail"):
        repl = "%s--cnvkit-plots-dir    ${cnvkit_plots_dir} \\\\\n%s \\\\" % (ind, extra)
    else:
        repl = "%s--cnvkit-plots-dir    ${cnvkit_plots_dir} \\\\\n%s" % (ind, extra)
    t = t[:m.start()] + repl + t[m.end():]
    notes.append("[ok] script: args appended after --cnvkit-plots-dir")
    return t, notes


TSPIPE_JOINS = '''{i}.join(CNV_CALLING.out.plots_dir)                                     // + cnvkit_plots_dir
{i}.join(CNV_CONSENSUS_MULTI.out.g)                                     // + cnv_consensus_genes ({m})
{i}.join(CNV_CONSENSUS_MULTI.out.s)                                     // + cnv_consensus_segments
{i}.join(CNV_CONSENSUS_MULTI.out.j)                                     // + cnv_consensus_json
{i}.join(EXON_PLOTS.out.dir)                                            // + exon_plots_dir
{i}.join(CHROM_PAGES.out.dir)                                           // + chrom_pages_dir
{i}.join(ch_decon_filtered)                                             // + decon_filtered (placeholder when off)
{i}.join(ch_decon_genes)                                                // + decon_genes
{i}.join(ch_purple_summary)                                             // + purple_summary (placeholder when off)
{i}.join(ch_purple_genes)                                               // + purple_genes
{i}.join(ch_purple_dir)                                                 // + purple_dir
{i}.join(PREPROCESSING.out.sex_check)                                   // + sex_check'''


def patch_tspipe(t):
    notes = []
    t, n = sub_once(t, r'^(?P<i>[ \t]*)\.join\(CNV_CALLING\.out\.plots_dir\)[ \t]*// \+ cnvkit_plots_dir[ \t]*$',
                    lambda m: TSPIPE_JOINS.format(i=m.group("i"), m=MARKER), "ch_organize joins")
    notes.append(n)
    return t, notes


FILES = [("bin/organize_output.py", patch_py), ("modules/local/organize_output.nf", patch_nf), ("workflows/tspipe.nf", patch_tspipe)]


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
        if rel.endswith(".py"):
            try:
                compile(new_text, path, "exec")
            except SyntaxError as exc:
                print("   [error] does not compile: %s" % exc); failed = True; continue
        if rel.endswith(".nf"):
            blocks = new_text.split('"""')
            bad = [l for b in blocks[1::2] for l in b.splitlines() if re.search(r'\S\s+//', l)]
            if bad:
                print("   [error] '//' inside a script block: %s" % bad[0].strip()); failed = True; continue
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
        backup = "%s.bak_org_cnv_%s" % (path, ts)
        shutil.copy2(path, backup)
        with open(path, "w") as fh:
            fh.write(new_text)
        print("[backup] %s" % os.path.relpath(backup, args.root))
        print("[patch]  wrote %s" % os.path.relpath(path, args.root))


if __name__ == "__main__":
    main()
