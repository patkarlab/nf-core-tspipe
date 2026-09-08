#!/usr/bin/env python3
"""
DASH_HGVS_PREF_V1 (D3b): variant-card nomenclature preference VV -> CAVA -> VEP.

VEP writes ENST/ENSP accessions on every HGVSc/HGVSp because it annotates from
the Ensembl cache, even when the block is the MANE Select transcript. That is
the "Ensembl-style description" the fellow reported (D3). VariantValidator
gives the RefSeq form for the clinical set only; CAVA (CAVA_V1b) now gives it
on MANE 1.5 RefSeq for every row. The card's best-HGVS helpers therefore
prefer, in order: VV_HGVS* (validated) -> CAVA_HGVS* -> HGVS* (VEP).

Patches:
  bin/dashboard_builder/assets/js/variant-browser.js   bestHGVSp / bestHGVSc
  bin/dashboard_builder/parsers/variants.py            best_hgvsp

Usage:
    python3 tools/patches/2026-09-08/apply_dash_hgvs_pref_v1.py --apply
Then the nocache dashboard re-render used for D13b.
"""

import argparse
import shutil
import sys
import time
from pathlib import Path

TAG = "dash_hgvs_pref_v1"
MARKER = "DASH_HGVS_PREF_V1"


def patch_js(text):
    if MARKER in text:
        print("  already patched")
        return text
    old = '''  function bestHGVSp(row) {
    const vv = row.VV_HGVSp;
    if (vv && vv !== "-1") return vv;
    const hg = row.HGVSp;
    if (hg && hg !== "-1") return hg;
    return "";
  }

  function bestHGVSc(row) {
    const vv = row.VV_HGVSc;
    if (vv && vv !== "-1") return vv;
    const hg = row.HGVSc;
    if (hg && hg !== "-1") return hg;
    return "";
  }
'''
    new = '''  // DASH_HGVS_PREF_V1 (D3b): VariantValidator -> CAVA (MANE 1.5 RefSeq) -> VEP (Ensembl accessions)
  function bestHGVSp(row) {
    const vv = row.VV_HGVSp;
    if (vv && vv !== "-1") return vv;
    const cv = row.CAVA_HGVSp;
    if (cv && cv !== "-1") return cv;
    const hg = row.HGVSp;
    if (hg && hg !== "-1") return hg;
    return "";
  }

  function bestHGVSc(row) {
    const vv = row.VV_HGVSc;
    if (vv && vv !== "-1") return vv;
    const cv = row.CAVA_HGVSc;
    if (cv && cv !== "-1") return cv;
    const hg = row.HGVSc;
    if (hg && hg !== "-1") return hg;
    return "";
  }
'''
    assert text.count(old) == 1, "anchor (bestHGVSp/bestHGVSc) not found exactly once"
    return text.replace(old, new)


def patch_py(text):
    if MARKER in text:
        print("  already patched")
        return text
    old = '''def best_hgvsp(row):
    """Prefer VV_HGVSp (VariantValidator) over HGVSp when available."""
    vv = row.get("VV_HGVSp", "")
    hg = row.get("HGVSp", "")
    if vv and vv != "-1":
        return vv
    if hg and hg != "-1":
        return hg
    return ""
'''
    new = '''def best_hgvsp(row):
    """DASH_HGVS_PREF_V1 (D3b): VariantValidator -> CAVA (MANE 1.5 RefSeq) -> VEP."""
    for col in ("VV_HGVSp", "CAVA_HGVSp", "HGVSp"):
        v = row.get(col, "")
        if v and v != "-1":
            return v
    return ""
'''
    assert text.count(old) == 1, "anchor (best_hgvsp) not found exactly once"
    return text.replace(old, new)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    root = Path(args.root)
    ts = time.strftime("%Y%m%d_%H%M%S")
    for path, fn in [(root / "bin/dashboard_builder/assets/js/variant-browser.js", patch_js),
                     (root / "bin/dashboard_builder/parsers/variants.py", patch_py)]:
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
