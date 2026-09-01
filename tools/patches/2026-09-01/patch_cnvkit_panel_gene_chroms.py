#!/usr/bin/env python3
"""Optional per-panel gene-chromosome map for CNVkit per-chromosome
scatters (marker PGC_ARG_V1).

bin/cnvkit_wrapper.py hardcodes PANEL_GENE_CHROMS for the myeloid panel;
its own comment anticipates a --panel-gene-chroms override. This patch
adds it, fully backward-compatible:

  - new optional argument --panel-gene-chroms <tsv>
    (lines: chrom<TAB>comma,separated,genes; '#' comments ignored).
    Absent -> the built-in myeloid map, byte-identical behaviour for the
    legacy panels.
  - loader with loud validation.
  - Step 7 resolves the map from the argument when given.
  - modules/local/cnvkit.nf gains an ext.args hook appended to the
    wrapper command (empty by default). conf/twist_apply.config populates
    it for twist runs only.

Idempotent, anchor-based, dry-run by default. Run from the repo root:
    python tools/patches/2026-09-01/patch_cnvkit_panel_gene_chroms.py           # dry-run
    python tools/patches/2026-09-01/patch_cnvkit_panel_gene_chroms.py --apply
"""

import argparse
import os
import shutil
import sys
from datetime import datetime

MARKER = "PGC_ARG_V1"

WRAPPER = "bin/cnvkit_wrapper.py"
MODULE = "modules/local/cnvkit.nf"

LOADER_LINES = [
    "",
    "",
    "def load_panel_gene_chroms(path):",
    "    \"\"\"Load a per-panel chrom -> gene-list map (" + MARKER + ").",
    "",
    "    Format: one line per chromosome page, chrom<TAB>comma,separated,genes.",
    "    Full-line '#' comments and blank lines are ignored. Genes label the",
    "    output filename and log line only; the scatter itself is",
    "    chromosome-wide (cnvkit.py scatter -c <chrom>).",
    "    \"\"\"",
    "    mapping = {}",
    "    with open(path) as fh:",
    "        for lineno, line in enumerate(fh, 1):",
    "            line = line.strip()",
    "            if not line or line.startswith(\"#\"):",
    "                continue",
    "            parts = line.split(\"\\t\")",
    "            if len(parts) != 2:",
    "                log.error(\"panel-gene-chroms line %d: expected \"",
    "                          \"chrom<TAB>genes, got %d fields\", lineno, len(parts))",
    "                sys.exit(1)",
    "            genes = [g.strip() for g in parts[1].split(\",\") if g.strip()]",
    "            if not genes:",
    "                log.error(\"panel-gene-chroms line %d: empty gene list\", lineno)",
    "                sys.exit(1)",
    "            mapping[parts[0]] = genes",
    "    if not mapping:",
    "        log.error(\"panel-gene-chroms: no entries in %s\", path)",
    "        sys.exit(1)",
    "    return mapping",
]

ARG_LINES = [
    "    ap.add_argument(\"--panel-gene-chroms\", default=None,",
    "                    help=\"TSV (chrom<TAB>comma,genes) overriding the \"",
    "                         \"built-in myeloid PANEL_GENE_CHROMS map for \"",
    "                         \"per-chromosome scatters (" + MARKER + ")\")",
]

RESOLVE_LINES = [
    "    if args.panel_gene_chroms:",
    "        panel_gene_chroms = load_panel_gene_chroms(args.panel_gene_chroms)",
    "        log.info(\"  Panel gene-chrom map: %s (%d chromosomes)\",",
    "                 args.panel_gene_chroms, len(panel_gene_chroms))",
    "    else:",
    "        panel_gene_chroms = PANEL_GENE_CHROMS",
]

EDITS = {
    WRAPPER: [
        {
            "kind": "insert_before",
            "anchor": ["    return ap.parse_args()"],
            "payload": ARG_LINES,
        },
        {
            "kind": "insert_after",
            "anchor": ["    return ap.parse_args()"],
            "payload": LOADER_LINES,
        },
        {
            "kind": "insert_after",
            "anchor": ["    log.info(\"Step 7: Per-chromosome scatter plots for panel genes\")"],
            "payload": RESOLVE_LINES,
        },
        {
            "kind": "replace_block",
            "anchor": ["    for chrom, genes in PANEL_GENE_CHROMS.items():"],
            "payload": ["    for chrom, genes in panel_gene_chroms.items():"],
        },
    ],
    MODULE: [
        {
            "kind": "insert_before",
            "anchor": [" * PoN selection logic:"],
            "payload": [
                " * " + MARKER + ": task.ext.args is appended to the wrapper command",
                " * (empty by default). Per-panel configs use it to pass",
                " * --panel-gene-chroms; legacy panels are unaffected.",
                " *",
            ],
        },
        {
            "kind": "replace_block",
            "anchor": ["            --loo-summary ${loo_summary}"],
            "payload": ["            --loo-summary ${loo_summary} ${task.ext.args ?: ''}"],
        },
    ],
}


def find_block(lines, anchor):
    hits = []
    n = len(anchor)
    for i in range(len(lines) - n + 1):
        if all(lines[i + k].rstrip("\n") == anchor[k] for k in range(n)):
            hits.append(i)
    return hits


def apply_edits(lines, ops, path):
    for op in ops:
        hits = find_block(lines, op["anchor"])
        if len(hits) != 1:
            print("[error] {0}: anchor found {1} times (need exactly 1):".format(
                path, len(hits)))
            print("        {0}".format(op["anchor"][0]))
            sys.exit(1)
        i = hits[0]
        n = len(op["anchor"])
        payload = [p + "\n" for p in op["payload"]]
        if op["kind"] == "replace_block":
            lines[i:i + n] = payload
        elif op["kind"] == "insert_after":
            lines[i + n:i + n] = payload
        elif op["kind"] == "insert_before":
            lines[i:i] = payload
        else:
            print("[error] unknown edit kind: {0}".format(op["kind"]))
            sys.exit(1)
    return lines


def main():
    ap = argparse.ArgumentParser(description="panel-gene-chroms override patch")
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry-run)")
    args = ap.parse_args()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    for path, ops in EDITS.items():
        if not os.path.isfile(path):
            print("[error] target not found: {0} (run from the repo root)".format(path))
            sys.exit(1)
        with open(path) as fh:
            text = fh.read()
        if MARKER in text:
            print("[skip] {0}: marker {1} already present".format(path, MARKER))
            continue

        lines = text.splitlines(True)
        for op in ops:
            hits = find_block(lines, op["anchor"])
            if len(hits) != 1:
                print("[error] {0}: anchor found {1} times (need exactly 1):".format(
                    path, len(hits)))
                print("        {0}".format(op["anchor"][0]))
                sys.exit(1)
        print("[plan] {0}: {1} edits, all anchors unique".format(path, len(ops)))

        if not args.apply:
            continue

        backup = "{0}.bak_pgc_arg_{1}".format(path, ts)
        shutil.copy2(path, backup)
        print("[backup] {0}".format(backup))

        lines = apply_edits(lines, ops, path)
        with open(path, "w") as fh:
            fh.write("".join(lines))

        with open(path) as fh:
            verify = fh.read()
        n_marker = verify.count(MARKER)
        if path == WRAPPER:
            import py_compile
            try:
                py_compile.compile(path, doraise=True)
            except py_compile.PyCompileError as exc:
                print("[error] {0}: does not compile after patch: {1}; "
                      "restore from {2}".format(path, exc, backup))
                sys.exit(1)
            ok = n_marker >= 2 and "panel_gene_chroms.items()" in verify
        else:
            ok = n_marker >= 1 and "task.ext.args" in verify
        if not ok:
            print("[error] {0}: post-write verification failed (marker={1}); "
                  "restore from {2}".format(path, n_marker, backup))
            sys.exit(1)
        print("[patch] {0}: panel-gene-chroms override applied (marker x{1})".format(
            path, n_marker))

    if not args.apply:
        print("[dry-run] no changes written; re-run with --apply")


if __name__ == "__main__":
    main()
