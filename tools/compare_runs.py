#!/usr/bin/env python3
"""
compare_runs.py -- compare two nf-core-tspipe outdirs file by file (FREEZE golden regression).

Walks both outdirs, pairs files by relative path, and reports: files present on one side only;
byte-identical files; files that differ, with a content-aware diff for text formats:
  .tsv/.csv/.txt/.bed/.json  -> differing line count, first differing lines (lines that carry a
                                path, date or run id are classed as "cosmetic" when they match after
                                masking those tokens)
  .vcf / .vcf.gz             -> header lines starting with ## are ignored (they carry commands and
                                dates); records compared as text
  .html/.zip/.png/.pdf/.bam  -> reported as differing or identical by md5 only
Exit status 0 when every non-cosmetic text file is identical, 1 otherwise.

Usage:
  python3 tools/compare_runs.py --a <outdir_host> --b <outdir_image> \
      --out docs/audit/<date>/run8_host_vs_image.md [--include-ext tsv,csv,txt,vcf,json,bed]
"""

import argparse
import gzip
import hashlib
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date

TEXT_EXT = {".tsv", ".csv", ".txt", ".bed", ".json", ".yml", ".yaml", ".md", ".log", ".summary"}
VCF_EXT = {".vcf"}
SKIP_DIRS = {"pipeline_info", "work", ".nextflow"}
COSMETIC_RE = re.compile(
    r"(/goast/[^\s\t'\"]+|/home/[^\s\t'\"]+|/opt/[^\s\t'\"]+|/tmp/[^\s\t'\"]+"
    r"|\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2})?(\.\d+)?|\d{2}-[A-Z][a-z]{2}-\d{4}|\b[0-9a-f]{2}/[0-9a-f]{6,}\b"
    r"|tspipe_run8(_img)?|session[ _=:]*[0-9a-f-]{36})"
)


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def kind_of(rel):
    base = rel.lower()
    if base.endswith(".vcf.gz") or base.endswith(".vcf"):
        return "vcf"
    ext = os.path.splitext(base)[1]
    if ext in TEXT_EXT:
        return "text"
    return "binary"


def read_lines(path, kind):
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    if kind == "vcf":
        lines = [l for l in lines if not l.startswith("##")]
    return lines


def walk(root):
    out = {}
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in fns:
            p = os.path.join(dp, fn)
            if os.path.islink(p):
                continue
            out[os.path.relpath(p, root)] = p
    return out


def diff_text(pa, pb, kind, max_examples=5):
    la = read_lines(pa, kind)
    lb = read_lines(pb, kind)
    sa, sb = set(la), set(lb)
    only_a = [l for l in la if l not in sb]
    only_b = [l for l in lb if l not in sa]
    masked_a = Counter(COSMETIC_RE.sub("<X>", l) for l in only_a)
    masked_b = Counter(COSMETIC_RE.sub("<X>", l) for l in only_b)
    # identical records after dropping ## headers (VCF) or gzip metadata count as cosmetic
    cosmetic = (not only_a and not only_b) or (masked_a == masked_b)
    return {
        "lines_a": len(la), "lines_b": len(lb), "only_a": len(only_a), "only_b": len(only_b),
        "cosmetic": bool(cosmetic),
        "examples": [("A", l[:160]) for l in only_a[:max_examples]] + [("B", l[:160]) for l in only_b[:max_examples]],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--a", required=True, help="reference outdir (host run)")
    ap.add_argument("--b", required=True, help="candidate outdir (image run)")
    ap.add_argument("--out", required=True, help="markdown report")
    ap.add_argument("--label-a", default="host")
    ap.add_argument("--label-b", default="image")
    args = ap.parse_args()

    fa, fb = walk(args.a), walk(args.b)
    only_a = sorted(set(fa) - set(fb))
    only_b = sorted(set(fb) - set(fa))
    common = sorted(set(fa) & set(fb))
    identical, differ = [], []
    for rel in common:
        if md5(fa[rel]) == md5(fb[rel]):
            identical.append(rel)
        else:
            differ.append(rel)

    details = {}
    real, cosmetic, binary = [], [], []
    for rel in differ:
        kind = kind_of(rel)
        if kind == "binary":
            binary.append(rel)
            continue
        try:
            d = diff_text(fa[rel], fb[rel], kind)
        except Exception as e:  # unreadable as text
            binary.append(rel)
            continue
        details[rel] = d
        (cosmetic if d["cosmetic"] else real).append(rel)

    by_dir = defaultdict(lambda: [0, 0, 0, 0])
    for rel in identical:
        by_dir[rel.split(os.sep)[0]][0] += 1
    for rel in real:
        by_dir[rel.split(os.sep)[0]][1] += 1
    for rel in cosmetic:
        by_dir[rel.split(os.sep)[0]][2] += 1
    for rel in binary:
        by_dir[rel.split(os.sep)[0]][3] += 1

    L = []
    A = L.append
    A("# Run comparison: %s (%s) vs %s (%s) -- %s" % (args.label_a, args.a, args.label_b, args.b, date.today().isoformat()))
    A("")
    A("Files: %d common, %d only in %s, %d only in %s. Common: %d identical (md5), %d differ "
      "(%d real text differences, %d cosmetic-only text differences, %d binary/other)." % (
          len(common), len(only_a), args.label_a, len(only_b), args.label_b, len(identical), len(differ),
          len(real), len(cosmetic), len(binary)))
    A("")
    A("Cosmetic = the differing lines match after masking paths, dates, run names, session ids and task hashes.")
    A("")
    A("| Top-level dir | identical | real diff | cosmetic diff | binary diff |")
    A("|---|---|---|---|---|")
    for d, (i, r, c, b) in sorted(by_dir.items()):
        A("| %s | %d | %d | %d | %d |" % (d, i, r, c, b))
    A("")
    if real:
        A("## Real text differences (%d)" % len(real))
        A("")
        for rel in real:
            d = details[rel]
            A("### %s" % rel)
            A("")
            A("lines %s=%d, %s=%d; only-in-%s %d, only-in-%s %d" % (args.label_a, d["lines_a"], args.label_b, d["lines_b"],
                                                                  args.label_a, d["only_a"], args.label_b, d["only_b"]))
            A("")
            for side, line in d["examples"]:
                A("- %s: `%s`" % (side, line.replace("|", "\\|")))
            A("")
    if cosmetic:
        A("## Cosmetic-only differences (%d)" % len(cosmetic))
        A("")
        for rel in cosmetic:
            d = details[rel]
            A("- %s (only-in-%s %d, only-in-%s %d; e.g. `%s`)" % (rel, args.label_a, d["only_a"], args.label_b, d["only_b"],
                                                                   (d["examples"][0][1] if d["examples"] else "").replace("|", "\\|")))
        A("")
    if binary:
        A("## Binary / other files that differ by md5 (%d)" % len(binary))
        A("")
        for rel in binary:
            A("- %s" % rel)
        A("")
    if only_a or only_b:
        A("## Present on one side only")
        A("")
        for rel in only_a:
            A("- only %s: %s" % (args.label_a, rel))
        for rel in only_b:
            A("- only %s: %s" % (args.label_b, rel))
        A("")
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("[ok] %s: %d identical, %d real, %d cosmetic, %d binary, %d/%d one-sided" % (
        args.out, len(identical), len(real), len(cosmetic), len(binary), len(only_a), len(only_b)))
    return 1 if real else 0


if __name__ == "__main__":
    sys.exit(main())
