#!/usr/bin/env python3
"""
CAVA_V1b (N3 stage 2a): merge CAVA annotations into the annotated TSV.

Patches:
  bin/annotate.py
    - new optional argument --cava-vcf
    - parse_cava_vcf(): reads CAVA_* INFO tags from the CAVA output VCF, keyed on
      the record's own chr:pos:ref:alt (CAVA returns the input record unchanged,
      so the key matches the VCF/VEP key directly; no A18-style mismatch)
    - per-variant transcript selection when the catalog carries more than one
      transcript for a gene (MANE 1.5: GATA2, CUX1, NF1): the transcript matching
      VEP's MANE_SELECT / Feature wins, else the first
    - nine new columns appended AFTER MNV_Note so existing column indexes are
      unchanged: CAVA_CSN, CAVA_HGVSc, CAVA_HGVSp, CAVA_Transcript, CAVA_Class,
      CAVA_SO, CAVA_Impact, CAVA_AltAnn, CAVA_HGVSp_Match
    - CAVA_HGVSp_Match: MATCH / DIFFER / NA after normalising both spellings
      (protein accession stripped, parentheses stripped, %3D decoded). DIFFER
      rows are the D3/D6 evidence.
  modules/local/vep_annotate.nf
    - input tuple gains path(cava_vcf); script passes --cava-vcf

Usage:
    python3 tools/patches/2026-09-08/apply_cava_v1b_annotate.py          # dry run
    python3 tools/patches/2026-09-08/apply_cava_v1b_annotate.py --apply

Idempotent: a file already carrying the CAVA_V1b marker is left untouched.
Backups: <file>.bak_cava_v1b_<timestamp>.
"""

import argparse
import shutil
import sys
import time
from pathlib import Path

TAG = "cava_v1b"
MARKER = "CAVA_V1b"


def patch_annotate(text: str) -> str:
    if MARKER in text:
        print("  bin/annotate.py already patched")
        return text

    # 1. columns ------------------------------------------------------------
    old = '''    "MNV_Note",   # MNV_MERGE_V1 (N2): "MNV of <positions> (<evidence>)" or "component of <chrom:pos:ref:alt>"
]
'''
    new = '''    "MNV_Note",   # MNV_MERGE_V1 (N2): "MNV of <positions> (<evidence>)" or "component of <chrom:pos:ref:alt>"
    # CAVA_V1b (N3): CAVA 2.0.15 on the MANE 1.5 RefSeq catalog. Appended after MNV_Note so
    # existing column positions are unchanged. '-1' when CAVA produced no annotation.
    "CAVA_CSN", "CAVA_HGVSc", "CAVA_HGVSp", "CAVA_Transcript", "CAVA_Class",
    "CAVA_SO", "CAVA_Impact", "CAVA_AltAnn", "CAVA_HGVSp_Match",
]
'''
    assert text.count(old) == 1, "anchor 1 (COLUMNS) not found exactly once"
    text = text.replace(old, new)

    # 2. argument -------------------------------------------------------------
    old = '''    ap.add_argument("--vep-fork", type=int, default=4,
                    help="VEP parallel forks (default: 4). The Nextflow "
                         "module passes task.cpus here.")
    return ap.parse_args()
'''
    new = '''    ap.add_argument("--vep-fork", type=int, default=4,
                    help="VEP parallel forks (default: 4). The Nextflow "
                         "module passes task.cpus here.")
    ap.add_argument("--cava-vcf", default=None,   # CAVA_V1b (N3)
                    help="CAVA-annotated copy of the same input VCF (output of the "
                         "CAVA module). Optional; CAVA_* columns are -1 without it.")
    return ap.parse_args()
'''
    assert text.count(old) == 1, "anchor 2 (parse_args) not found exactly once"
    text = text.replace(old, new)

    # 3. parser + helpers, inserted before _cosmic_id ---------------------------
    old = '''def _cosmic_id(annovar_val, existing_variation):
'''
    new = r'''# CAVA_V1b (N3) ------------------------------------------------------------------
# CAVA (2.0.15, config @prefix=TRUE) writes one INFO tag per annotation, all named
# CAVA_<name>. Within one record, values for multiple transcripts are joined with
# ':' (multiple ALT alleles with ',', not applicable: the consensus VCF is
# one-ALT-per-record). The HGVS tags contain ':' inside each value
# (NC_000017.11(NM_000546.6):c.524G>A), so those are re-split by pattern.
import urllib.parse as _urlparse_cava

_CAVA_TAGS = ("CAVA_TRANSCRIPT", "CAVA_GENE", "CAVA_CSN", "CAVA_CLASS", "CAVA_SO",
              "CAVA_IMPACT", "CAVA_ALTANN", "CAVA_HGVSc", "CAVA_HGVSp", "CAVA_HGVSg")
_CAVA_HGVS_RE = {
    # one match per transcript; the accession/transcript part never contains ':'
    "CAVA_HGVSc": re.compile(r"[A-Za-z]{2}_[0-9]+\.[0-9]+\([^)]*\):c\.[^:]+"),
    "CAVA_HGVSp": re.compile(r"[A-Za-z]{2}_[0-9]+\.[0-9]+:p\.[^:]+"),
    "CAVA_HGVSg": re.compile(r"[A-Za-z]{2}_[0-9]+\.[0-9]+:g\.[^:]+"),
}


def _cava_split(tag, value, n_transcripts):
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


def _strip_version(acc):
    return str(acc or "").split(".")[0].strip()


def parse_cava_vcf(cava_vcf):
    """Parse the CAVA output VCF -> dict keyed by chr:pos:ref:alt.

    Each value is a dict with one entry per transcript:
        {"transcripts": ["NM_000546.6", ...], "per_tx": [{tag: value, ...}, ...]}
    Records with no CAVA_TRANSCRIPT (CAVA could not annotate them, e.g. a
    reference-mismatched allele, which CAVA passes through with an error line)
    are stored with an empty transcript list so the merge can count them.
    """
    variants = {}
    if not cava_vcf:
        return variants
    if not os.path.isfile(cava_vcf):
        log.warning("CAVA VCF not found: %s", cava_vcf)
        return variants
    n_unannotated = 0
    with open(cava_vcf) as f:
        for line in f:
            if line.startswith("#"):
                continue
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 8:
                continue
            chrom, pos, ref, alt, info = cols[0], cols[1], cols[3], cols[4], cols[7]
            key = "{0}:{1}:{2}:{3}".format(chrom, pos, ref, alt)
            tx_raw = _get_info_value(info, "CAVA_TRANSCRIPT")
            transcripts = [t for t in tx_raw.split(":") if t and t != "."] if tx_raw else []
            n = len(transcripts)
            if n == 0:
                n_unannotated += 1
                variants[key] = {"transcripts": [], "per_tx": []}
                continue
            per_tx = [{} for _ in range(n)]
            for tag in _CAVA_TAGS:
                vals = _cava_split(tag, _get_info_value(info, tag), n)
                for i in range(n):
                    per_tx[i][tag] = vals[i]
            variants[key] = {"transcripts": transcripts, "per_tx": per_tx}
    log.info("Parsed %d variants from CAVA VCF (%d without a CAVA annotation)",
             len(variants), n_unannotated)
    return variants


def _cava_pick(entry, vep):
    """Choose the per-transcript CAVA block that matches the VEP transcript.

    Preference: VEP MANE_SELECT accession, then VEP Feature, both compared
    without version; otherwise the first transcript in CAVA's order.
    """
    txs = entry.get("transcripts") or []
    if not txs:
        return None
    wanted = [_strip_version(vep.get("MANE_SELECT", "")), _strip_version(vep.get("Feature", ""))]
    wanted = [w for w in wanted if w]
    for w in wanted:
        for i, t in enumerate(txs):
            if _strip_version(t) == w:
                return entry["per_tx"][i]
    return entry["per_tx"][0]


def _normalize_hgvsp_for_match(val):
    """'NP_000537.3:p.(Arg175His)' / 'NP_000537.3:p.Arg175His' / 'p.Arg175%3D' -> 'Arg175His' / 'Arg175='."""
    s = _urlparse_cava.unquote(str(val or "")).strip()
    if s in ("", "-1", "."):
        return ""
    if ":" in s:
        s = s.rsplit(":", 1)[1]
    if s.startswith("p."):
        s = s[2:]
    s = s.replace("(", "").replace(")", "")
    return s


def _cava_hgvsp_match(vep_hgvsp, cava_hgvsp):
    a = _normalize_hgvsp_for_match(vep_hgvsp)
    b = _normalize_hgvsp_for_match(cava_hgvsp)
    if not a or not b:
        return "NA"
    if a == b:
        return "MATCH"
    # CAVA writes p.? for unpredictable protein effects; VEP leaves HGVSp empty
    # for those, so a populated VEP string against p.? is a genuine difference.
    return "DIFFER"


def _cava_columns(entry, vep):
    """The nine CAVA_* output columns for one merged row ('-1' when absent)."""
    blk = _cava_pick(entry, vep) if entry else None
    if not blk:
        return {
            "CAVA_CSN": "-1", "CAVA_HGVSc": "-1", "CAVA_HGVSp": "-1", "CAVA_Transcript": "-1",
            "CAVA_Class": "-1", "CAVA_SO": "-1", "CAVA_Impact": "-1", "CAVA_AltAnn": "-1",
            "CAVA_HGVSp_Match": "NA",
        }
    cava_hgvsp = _clean(blk.get("CAVA_HGVSp", ""))
    return {
        "CAVA_CSN": _clean(blk.get("CAVA_CSN", "")),
        "CAVA_HGVSc": _clean(blk.get("CAVA_HGVSc", "")),
        "CAVA_HGVSp": cava_hgvsp,
        "CAVA_Transcript": _clean(blk.get("CAVA_TRANSCRIPT", "")),
        "CAVA_Class": _clean(blk.get("CAVA_CLASS", "")),
        "CAVA_SO": _clean(blk.get("CAVA_SO", "")),
        "CAVA_Impact": _clean(blk.get("CAVA_IMPACT", "")),
        "CAVA_AltAnn": _clean(blk.get("CAVA_ALTANN", "")),
        "CAVA_HGVSp_Match": _cava_hgvsp_match(vep.get("HGVSp", ""), cava_hgvsp),
    }
# end CAVA_V1b -----------------------------------------------------------------


def _cosmic_id(annovar_val, existing_variation):
'''
    assert text.count(old) == 1, "anchor 3 (_cosmic_id) not found exactly once"
    text = text.replace(old, new)

    # 4. merge signature + diagnostics ----------------------------------------
    old = '''def merge_annotations(vcf_fields, vep_variants, annovar_variants,
                      output_tsv, sample):
'''
    new = '''def merge_annotations(vcf_fields, vep_variants, annovar_variants,
                      output_tsv, sample, cava_variants=None):   # CAVA_V1b (N3)
'''
    assert text.count(old) == 1, "anchor 4 (merge signature) not found exactly once"
    text = text.replace(old, new)

    old = '''    log.info("Merging annotations: %d VCF, %d VEP, %d ANNOVAR, %d total unique",
             len(vcf_fields), len(vep_variants), len(annovar_variants),
             len(all_keys))
'''
    new = '''    log.info("Merging annotations: %d VCF, %d VEP, %d ANNOVAR, %d total unique",
             len(vcf_fields), len(vep_variants), len(annovar_variants),
             len(all_keys))
    # CAVA_V1b (N3): CAVA rows are the input records echoed back, so every key should match.
    cava_variants = cava_variants or {}
    if cava_variants:
        _cava_annotated = sum(1 for v in cava_variants.values() if v.get("transcripts"))
        log.info("CAVA merge: %d records, %d annotated, %d matched a VCF record",
                 len(cava_variants), _cava_annotated, len(set(cava_variants) & _vcf_keys))
    _cava_match_counts = {"MATCH": 0, "DIFFER": 0, "NA": 0}
'''
    assert text.count(old) == 1, "anchor 4b (merge log) not found exactly once"
    text = text.replace(old, new)

    # 5. row assembly -----------------------------------------------------------
    old = '''            "MNV_Note": _clean(vcf.get("mnv_note", "")),   # MNV_MERGE_V1 (N2)
        }
        rows.append(row)
'''
    new = '''            "MNV_Note": _clean(vcf.get("mnv_note", "")),   # MNV_MERGE_V1 (N2)
        }
        row.update(_cava_columns(cava_variants.get(key), vep))   # CAVA_V1b (N3)
        _cava_match_counts[row["CAVA_HGVSp_Match"]] = _cava_match_counts.get(row["CAVA_HGVSp_Match"], 0) + 1
        rows.append(row)
'''
    assert text.count(old) == 1, "anchor 5 (row assembly) not found exactly once"
    text = text.replace(old, new)

    old = '''    log.info("Wrote %d variants to %s", len(rows), output_tsv)
    return len(rows)
'''
    new = '''    if cava_variants:   # CAVA_V1b (N3)
        log.info("CAVA vs VEP HGVSp: %d MATCH, %d DIFFER, %d NA",
                 _cava_match_counts.get("MATCH", 0), _cava_match_counts.get("DIFFER", 0),
                 _cava_match_counts.get("NA", 0))
    log.info("Wrote %d variants to %s", len(rows), output_tsv)
    return len(rows)
'''
    assert text.count(old) == 1, "anchor 5b (merge return) not found exactly once"
    text = text.replace(old, new)

    # 6. main -------------------------------------------------------------------
    old = '''    log.info("VEP forks:      %d", args.vep_fork)
'''
    new = '''    log.info("VEP forks:      %d", args.vep_fork)
    log.info("CAVA VCF:       %s", args.cava_vcf or "(none)")   # CAVA_V1b (N3)
'''
    assert text.count(old) == 1, "anchor 6 (main log) not found exactly once"
    text = text.replace(old, new)

    old = '''    vep_variants, _ = parse_vep_csq(vep_vcf)
    annovar_variants = parse_annovar_txt(annovar_txt)
    n = merge_annotations(vcf_fields, vep_variants, annovar_variants,
                          output_tsv, sample)
'''
    new = '''    vep_variants, _ = parse_vep_csq(vep_vcf)
    annovar_variants = parse_annovar_txt(annovar_txt)
    cava_variants = parse_cava_vcf(args.cava_vcf)   # CAVA_V1b (N3): empty dict when not given
    n = merge_annotations(vcf_fields, vep_variants, annovar_variants,
                          output_tsv, sample, cava_variants=cava_variants)
'''
    assert text.count(old) == 1, "anchor 6b (main merge call) not found exactly once"
    text = text.replace(old, new)
    return text


def patch_module(text: str) -> str:
    if MARKER in text:
        print("  modules/local/vep_annotate.nf already patched")
        return text

    old = '''    input:
        tuple val(meta), path(vcf)
        tuple path(fasta), path(fai), path(dict)
'''
    new = '''    input:
        tuple val(meta), path(vcf), path(cava_vcf)   // CAVA_V1b (N3): CAVA-annotated copy of vcf
        tuple path(fasta), path(fai), path(dict)
'''
    assert text.count(old) == 1, "module anchor 1 (input) not found exactly once"
    text = text.replace(old, new)

    old = '''        # annotate.py ANNOVAR_KEY_V1: ANNOVAR rows keyed on the VCF record; A19 COSMIC_ID from VEP Existing_variation (bash comment; busts the task cache)
        annotate.py \\\\
            --somaticseq-vcf ${vcf} \\\\
'''
    new = '''        # annotate.py ANNOVAR_KEY_V1: ANNOVAR rows keyed on the VCF record; A19 COSMIC_ID from VEP Existing_variation (bash comment; busts the task cache)
        # CAVA_V1b (N3): --cava-vcf merges CAVA_* columns
        annotate.py \\\\
            --somaticseq-vcf ${vcf} \\\\
            --cava-vcf ${cava_vcf} \\\\
'''
    assert text.count(old) == 1, "module anchor 2 (script) not found exactly once"
    text = text.replace(old, new)

    old = ''' * Inputs:
 *   vcf       -- SomaticSeq consensus VCF
'''
    new = ''' * Inputs:
 *   vcf       -- SomaticSeq consensus VCF
 *   cava_vcf  -- the same VCF annotated by the CAVA module (CAVA_V1b, N3)
'''
    assert text.count(old) == 1, "module anchor 3 (header) not found exactly once"
    text = text.replace(old, new)
    return text


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--root", default=".", help="repository root (default: cwd)")
    args = ap.parse_args()
    root = Path(args.root)
    targets = [
        (root / "bin/annotate.py", patch_annotate),
        (root / "modules/local/vep_annotate.nf", patch_module),
    ]
    ts = time.strftime("%Y%m%d_%H%M%S")
    for path, fn in targets:
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
