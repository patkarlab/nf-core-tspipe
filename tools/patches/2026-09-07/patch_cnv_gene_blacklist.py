#!/usr/bin/env python3
"""
patch_cnv_gene_blacklist.py -- panel CNV gene blacklist (MARKER CNV_BLACKLIST_V1).

Genes listed in assets/<panel>/cnv_gene_blacklist.tsv (column 'gene') get
consensus_call BLACKLISTED, tier NA, support 0 in CNV_CONSENSUS_MULTI; the
per-arm columns stay for audit. EXON_PLOTS ignores them as plot triggers.
The file is optional: panels without it behave as before.

Files (5), all-or-nothing:
  bin/cnv_consensus_multi.py           --gene-blacklist; BLACKLISTED handling
  modules/local/cnv_consensus_multi.nf path gene_blacklist input (empty list when absent)
  bin/plot_exon_ratio_batch.py         --gene-blacklist; BLACKLISTED not a trigger
  modules/local/exon_plots.nf          path gene_blacklist input
  workflows/tspipe.nf                  ch_cnv_gene_blacklist value; passed to both

Dry run by default; --apply writes .bak_cnv_blacklist_<ts> backups.
"""

import argparse
import datetime
import os
import re
import shutil
import sys

MARKER = "MARKER CNV_BLACKLIST_V1"
TAG = "CNV_BLACKLIST_V1"


def sub_once(text, pattern, repl, label, flags=re.M):
    rx = re.compile(pattern, flags)
    n = len(rx.findall(text))
    if n != 1:
        raise ValueError("anchor %s: expected 1 match, found %d (%s)" % ("not found" if n == 0 else "not unique", n, label))
    return rx.sub(repl, text, count=1), "[ok] %s" % label


READ_BLACKLIST = '''def read_gene_blacklist(path):
    """%s: gene symbols from a TSV with a 'gene' column (or first column); empty if no file."""
    genes = set()
    if not path or not os.path.isfile(path):
        return genes
    with open(path) as fh:
        header = None
        for line in fh:
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.rstrip("\\n").split("\\t")
            if header is None:
                header = parts
                if "gene" in header:
                    continue
                genes.add(parts[0].strip())
                continue
            idx = header.index("gene") if "gene" in header else 0
            if len(parts) > idx and parts[idx].strip():
                genes.add(parts[idx].strip())
    return genes


''' % TAG


def patch_consensus_py(t):
    notes = []
    t, n = sub_once(t, r'^def main\(\):\n', lambda m: READ_BLACKLIST + m.group(0), "read_gene_blacklist helper")
    notes.append(n)
    t, n = sub_once(t, r'^    ap\.add_argument\("--sex", default="unknown",\n[^\n]*\n',
                    lambda m: m.group(0) + '    ap.add_argument("--gene-blacklist", default=None,\n'
                    '                    help="TSV of genes never called (consensus BLACKLISTED); optional (%s)")\n' % TAG,
                    "argparse --gene-blacklist")
    notes.append(n)
    t, n = sub_once(t, r'^    # ---- LOO per-gene fp rate\n',
                    lambda m: "    # ---- %s: panel gene blacklist\n    blacklist = read_gene_blacklist(args.gene_blacklist)\n    if blacklist:\n        print(\"[ok] gene blacklist: {0} gene(s)\".format(len(blacklist)))\n\n" % MARKER + m.group(0),
                    "load blacklist")
    notes.append(n)
    t, n = sub_once(t, r'^        if tier in \("TIER_1", "TIER_2"\):\n            n_consensus \+= 1\n',
                    lambda m: "        if g[\"gene\"] in blacklist:   # %s: arms kept for audit, no call\n            consensus, tier = \"BLACKLISTED\", \"NA\"\n            arms, flags = {}, \"\"\n" % TAG + m.group(0),
                    "BLACKLISTED consensus")
    notes.append(n)
    return t, notes


def patch_consensus_nf(t):
    notes = []
    t, n = sub_once(t, r"^(?P<i>[ \t]*)path loo_summary_female, stageAs: 'female_stratum/\*'[^\n]*$",
                    lambda m: m.group(0) + "\n%spath gene_blacklist   // %s (empty list when the panel has none)" % (m.group("i"), MARKER),
                    "cnv_consensus_multi.nf: input")
    notes.append(n)
    t, n = sub_once(t, r'^(?P<i>[ \t]*)def decon_arg = decon_genes \? "--decon-genes \$\{decon_genes\}" : \'\'[^\n]*$',
                    lambda m: m.group(0) + "\n%sdef blacklist_arg = gene_blacklist ? \"--gene-blacklist ${gene_blacklist}\" : ''   // %s" % (m.group("i"), TAG),
                    "cnv_consensus_multi.nf: blacklist_arg")
    notes.append(n)
    t, n = sub_once(t, r'^(?P<i>[ \t]*)\$\{decon_arg\} \\\\[ \t]*$',
                    lambda m: m.group(0) + "\n%s${blacklist_arg} \\\\" % m.group("i"), "cnv_consensus_multi.nf: script arg")
    notes.append(n)
    return t, notes


def patch_batch_py(t):
    notes = []
    t, n = sub_once(t, r'^    ap\.add_argument\("--min-bf", type=float, default=5\.0,[^\n]*\n',
                    lambda m: m.group(0) + '    ap.add_argument("--gene-blacklist", default=None,\n'
                    '                    help="TSV of blacklisted genes: never a plot trigger (%s)")\n' % TAG,
                    "batch: argparse")
    notes.append(n)
    t, n = sub_once(t, r'^    focal = read_focal_chroms\(args\.focal_bed\)\n',
                    lambda m: m.group(0) + "    # %s\n    blacklist = set()\n    if args.gene_blacklist and os.path.isfile(args.gene_blacklist):\n        with open(args.gene_blacklist) as fh:\n            rows = [l.rstrip(\"\\n\").split(\"\\t\") for l in fh if l.strip() and not l.startswith(\"#\")]\n        if rows:\n            idx = rows[0].index(\"gene\") if \"gene\" in rows[0] else 0\n            blacklist = set(r[idx] for r in (rows[1:] if \"gene\" in rows[0] else rows) if len(r) > idx)\n" % MARKER,
                    "batch: load blacklist")
    notes.append(n)
    t, n = sub_once(t, r'^        nn = \[g for _, g, call, _ in rows if call not in \("NEUTRAL", "NA", ""\)\]\n',
                    '        nn = [g for _, g, call, _ in rows if call not in ("NEUTRAL", "NA", "", "BLACKLISTED") and g not in blacklist]\n',
                    "batch: consensus trigger")
    notes.append(n)
    t, n = sub_once(t, r'^        if c\["bf"\] >= args\.min_bf:\n',
                    '        if c["bf"] >= args.min_bf and c["gene"] not in blacklist:\n', "batch: DECoN trigger")
    notes.append(n)
    return t, notes


def patch_exon_plots_nf(t):
    notes = []
    t, n = sub_once(t, r'^(?P<i>[ \t]*)path focal_bed[ \t]*$',
                    lambda m: m.group(0) + "\n%spath gene_blacklist   // %s" % (m.group("i"), MARKER), "exon_plots.nf: input")
    notes.append(n)
    t, n = sub_once(t, r"^(?P<i>[ \t]*)def focal_arg = focal_bed      \? \"--focal-bed \$\{focal_bed\}\"  : ''[ \t]*$",
                    lambda m: m.group(0) + "\n%sdef blacklist_arg = gene_blacklist ? \"--gene-blacklist ${gene_blacklist}\" : ''   // %s" % (m.group("i"), TAG),
                    "exon_plots.nf: blacklist_arg")
    notes.append(n)
    t, n = sub_once(t, r'^(?P<i>[ \t]*)\$\{decon_arg\} \$\{focal_arg\} \\\\[ \t]*$',
                    lambda m: "%s${decon_arg} ${focal_arg} ${blacklist_arg} \\\\" % m.group("i"), "exon_plots.nf: script arg")
    notes.append(n)
    return t, notes


def patch_tspipe(t):
    notes = []
    t, n = sub_once(t, r'^(?P<i>[ \t]*)CNV_CONSENSUS_MULTI\( ch_consensus_in, ch_cnv_loo_summary, ch_cnv_loo_summary_female \)[^\n]*$',
                    lambda m: "%s// %s: optional panel gene blacklist (consensus BLACKLISTED; no plot trigger)\n"
                              "%sdef gene_blacklist_path = \"${projectDir}/assets/${params.panel}/cnv_gene_blacklist.tsv\"\n"
                              "%sch_cnv_gene_blacklist = file(gene_blacklist_path).exists() ? Channel.value(file(gene_blacklist_path)) : Channel.value([])\n"
                              "%sCNV_CONSENSUS_MULTI( ch_consensus_in, ch_cnv_loo_summary, ch_cnv_loo_summary_female, ch_cnv_gene_blacklist )   // SEXSTRAT_V1 %s"
                              % (m.group("i"), MARKER, m.group("i"), m.group("i"), m.group("i"), TAG),
                    "tspipe.nf: consensus call")
    notes.append(n)
    t, n = sub_once(t, r'^(?P<i>[ \t]*)EXON_PLOTS\( ch_exon_plots_in, ch_focal_bed \)[ \t]*$',
                    lambda m: "%sEXON_PLOTS( ch_exon_plots_in, ch_focal_bed, ch_cnv_gene_blacklist )   // %s" % (m.group("i"), TAG),
                    "tspipe.nf: EXON_PLOTS call")
    notes.append(n)
    return t, notes


FILES = [
    ("bin/cnv_consensus_multi.py",           patch_consensus_py),
    ("modules/local/cnv_consensus_multi.nf", patch_consensus_nf),
    ("bin/plot_exon_ratio_batch.py",         patch_batch_py),
    ("modules/local/exon_plots.nf",          patch_exon_plots_nf),
    ("workflows/tspipe.nf",                  patch_tspipe),
]


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
        backup = "%s.bak_cnv_blacklist_%s" % (path, ts)
        shutil.copy2(path, backup)
        with open(path, "w") as fh:
            fh.write(new_text)
        print("[backup] %s" % os.path.relpath(backup, args.root))
        print("[patch]  wrote %s" % os.path.relpath(path, args.root))


if __name__ == "__main__":
    main()
