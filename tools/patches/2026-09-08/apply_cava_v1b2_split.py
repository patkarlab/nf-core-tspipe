#!/usr/bin/env python3
"""
CAVA_V1b2 (N3): multi-transcript HGVS split fix.

Run8 showed that when the MANE 1.5 catalog carries several transcripts for a gene
(GNAS, KRAS, CDKN2A, PRPF40B, ...) and some of them have no protein-level value,
CAVA writes a '.' placeholder in the ':'-joined list, e.g.

    CAVA_HGVSp=NP_000507.1:p.(Ile131=):.:NP_536350.2:p.(Ile774=)

The V1b regex-based splitter only matched populated items, so the item count
disagreed with the transcript count and the whole string was kept, which made
the row show as DIFFER against VEP. This replaces the splitter with a tokenizer:
an accession token (NP_/NM_/NC_...) starts an item and takes the following
token; a bare '.' is an item of its own.

Also bumps the cache-bust comment in modules/local/vep_annotate.nf so the
VEP_ANNOTATE tasks re-run on -resume (Nextflow does not hash bin/ contents).

Usage:
    python3 tools/patches/2026-09-08/apply_cava_v1b2_split.py --apply
"""

import argparse
import shutil
import sys
import time
from pathlib import Path

TAG = "cava_v1b2"
MARKER = "CAVA_V1b2"


def patch_annotate(text):
    if MARKER in text:
        print("  already patched")
        return text
    old = '''def _cava_split(tag, value, n_transcripts):
    """Split one CAVA tag value into a per-transcript list of length n_transcripts."""
    value = _urlparse_cava.unquote(value or "")
    if n_transcripts <= 1:
        return [value]
    if tag in _CAVA_HGVS_RE:
        parts = _CAVA_HGVS_RE[tag].findall(value)
        if len(parts) == n_transcripts:
            return parts
        return [value] * n_transcripts       # unexpected shape: keep whole string
    parts = value.split(":")
    if len(parts) == n_transcripts:
        return parts
    return [value] * n_transcripts
'''
    new = '''_CAVA_ACC_RE = re.compile(r"^[A-Za-z]{2}_[0-9]+\\.[0-9]+(\\([^)]*\\))?$")   # CAVA_V1b2: NP_1.1 / NC_1.1(NM_2.2)


def _cava_split_hgvs(value):
    """CAVA_V1b2: tokenise a ':'-joined multi-transcript HGVS value.

    Items are either '<accession>:<description>' (two tokens) or '.' (one token,
    a transcript with no value at this level), so a plain split on ':' cannot be
    used. An accession token opens an item and consumes the next token.
    """
    tokens = value.split(":")
    items, i = [], 0
    while i < len(tokens):
        tok = tokens[i]
        if _CAVA_ACC_RE.match(tok) and i + 1 < len(tokens):
            items.append(tok + ":" + tokens[i + 1])
            i += 2
        else:
            items.append(tok)
            i += 1
    return items


def _cava_split(tag, value, n_transcripts):
    """Split one CAVA tag value into a per-transcript list of length n_transcripts."""
    value = _urlparse_cava.unquote(value or "")
    if n_transcripts <= 1:
        return [value]
    if tag in _CAVA_HGVS_RE:
        parts = _cava_split_hgvs(value)   # CAVA_V1b2
        if len(parts) == n_transcripts:
            return parts
        return [value] * n_transcripts       # unexpected shape: keep whole string
    parts = value.split(":")
    if len(parts) == n_transcripts:
        return parts
    return [value] * n_transcripts
'''
    assert text.count(old) == 1, "anchor (_cava_split) not found exactly once"
    return text.replace(old, new)


def patch_module(text):
    if MARKER in text:
        print("  already patched")
        return text
    old = "        # CAVA_V1b (N3): --cava-vcf merges CAVA_* columns\n"
    new = "        # CAVA_V1b (N3): --cava-vcf merges CAVA_* columns; CAVA_V1b2 multi-transcript split fix (bash comment; busts the task cache)\n"
    assert text.count(old) == 1, "anchor (module comment) not found exactly once"
    return text.replace(old, new)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    root = Path(args.root)
    ts = time.strftime("%Y%m%d_%H%M%S")
    for path, fn in [(root / "bin/annotate.py", patch_annotate),
                     (root / "modules/local/vep_annotate.nf", patch_module)]:
        print(path)
        text = path.read_text()
        new = fn(text)
        if new == text:
            continue
        if args.apply:
            backup = path.with_name(path.name + f".bak_{TAG}_{ts}")
            shutil.copy2(path, backup)
            path.write_text(new)
            print(f"  patched (backup {backup.name})")
        else:
            print("  would patch (dry run; use --apply)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
