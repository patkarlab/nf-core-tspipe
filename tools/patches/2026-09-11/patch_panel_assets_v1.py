#!/usr/bin/env python3
"""
patch_panel_assets_v1.py -- PANEL_ASSETS_V1 (post-v1.0.0 portability fixes)

Two defects found when Vishram reviewed the clinical-23 configuration on 2026-09-11. Both are of
the same kind as the VarScan threshold found by the golden regression: something that determines
what is analysed, living outside the shared, version-controlled configuration.

1. The MYOPOOL panel BEDs are referenced from `${params.pipeline_root}/bedfiles/`, which resolves
   to the legacy targeted-seq-pipeline tree on gandalf and to the superseded June clone on
   clinical-23. A panel definition for a clinical assay must be in the repository, not in an
   unversioned directory that can be moved or deleted. Both files are byte-identical on the two
   hosts (verified 2026-09-11), so adopting them changes nothing except where they are read from.
   This patch copies them into assets/myeloid/, makes them the default in nextflow.config, and
   removes the per-site overrides.

2. The hmftools resource paths in conf/twist_apply.config are hardcoded to gandalf locations. A
   panel overlay is loaded after the site profile, so a second site cannot override them from its
   profile and must pass a params file instead -- which works, but fails obscurely at AMBER if the
   operator forgets it. This patch introduces params.hmf_root, defaulted to the gandalf location,
   so a site profile sets one value and the five paths follow.

Effect on task hashes: MYOPOOL runs re-execute (the BED path changes, though its content does
not); Twist runs are unaffected unless a site changes hmf_root. Anchor-based, dry-run by default,
--apply writes .bak_panelassets_<stamp> copies.

Usage, from the repository root:
    python3 tools/patches/2026-09-11/patch_panel_assets_v1.py \
        --bed-src /goast/hemat_data/targeted-seq-pipeline/bedfiles
    python3 tools/patches/2026-09-11/patch_panel_assets_v1.py --bed-src <dir> --apply
"""

import argparse
import hashlib
import os
import re
import shutil
import sys
import time

MARKER = "MARKER PANEL_ASSETS_V1"
STAMP = time.strftime("%Y%m%d_%H%M%S")
BEDS = {
    "MYOPOOL_240125_UBTF_hg38.bed": "13474f961b958109ec307281964e3e1b",
    "MYOPOOL_240125_UBTF_Exonwise_hg38.bed": "95fe5d6e6dbdac2af6e5ea21412f0cdd",
}
ASSET_DIR = "assets/myeloid"
SITE_CONFIGS = ["conf/gandalf.config", "conf/clinical23.config", "conf/site_template.config"]
HMF_KEYS = ["hmf_resources", "hmf_loci", "hmf_gc_profile", "hmf_ensembl_dir", "hmf_hotspots"]
HMF_ROOT_DEFAULT = "/goast/hemat_data/references/hmftools/hmf_pipeline_resources.38_v3.0.0--8"


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def write(p, s, apply_):
    if not apply_:
        return
    if os.path.exists(p):
        shutil.copy2(p, p + ".bak_panelassets_" + STAMP)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(s)


def patch_nextflow_config(apply_):
    """Point the panel BED defaults at the repository assets."""
    p = "nextflow.config"
    if MARKER in read(p):
        return "nextflow.config: already patched, unchanged"
    lines = read(p).split("\n")
    changed = []
    for key, fname in (("bed", "MYOPOOL_240125_UBTF_hg38.bed"),
                       ("exonwise_bed", "MYOPOOL_240125_UBTF_Exonwise_hg38.bed")):
        idx = [i for i, l in enumerate(lines)
               if re.match(r"^\s*%s\s*=\s*null" % key, l)]
        if not idx:
            raise SystemExit("[error] nextflow.config: no `%s = null` line to replace "
                             "(already patched, or the file has changed)" % key)
        i = idx[0]
        indent = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
        lines[i] = ('%s%-18s = "${projectDir}/%s/%s"   // %s: panel definition lives in the '
                    'repository, not a site path' % (indent, key, ASSET_DIR, fname, MARKER))
        changed.append(key)
    write(p, "\n".join(lines), apply_)
    return "nextflow.config: defaults set for %s" % ", ".join(changed)


def patch_site_config(path, apply_):
    """Remove per-site MYOPOOL BED overrides; the repository default now applies."""
    if not os.path.exists(path):
        return "%s: absent, skipped" % path
    lines = read(path).split("\n")
    keep, removed = [], []
    for l in lines:
        if re.match(r"^\s*(bed|exonwise_bed)\s*=.*MYOPOOL", l):
            removed.append(l.strip().split("=")[0].strip())
            continue
        keep.append(l)
    if not removed:
        return "%s: no MYOPOOL override found, unchanged" % path
    # leave a note where the block was, so the omission is deliberate and visible
    for i, l in enumerate(keep):
        if re.match(r"^\s*pindel_bed\s*=", l):
            indent = l[:len(l) - len(l.lstrip())]
            keep.insert(i, "%s// %s: panel BEDs come from assets/myeloid/ in the repository." % (indent, MARKER))
            break
    write(path, "\n".join(keep), apply_)
    return "%s: removed %s" % (path, ", ".join(removed))


def patch_twist_apply(apply_):
    """Introduce params.hmf_root and derive the five hmftools paths from it."""
    p = "conf/twist_apply.config"
    text = read(p)
    if "hmf_root" in text:
        return "%s: hmf_root already present, unchanged" % p
    lines = text.split("\n")
    idx = {}
    for k in HMF_KEYS:
        m = [i for i, l in enumerate(lines) if re.match(r"^\s*%s\s*=" % k, l)]
        if len(m) != 1:
            raise SystemExit("[error] %s: expected one `%s =` line, found %d" % (p, k, len(m)))
        idx[k] = m[0]
    first = min(idx.values())
    indent = lines[first][:len(lines[first]) - len(lines[first].lstrip())]
    suffix = {
        "hmf_resources": "",
        "hmf_loci": "/dna/copy_number/AmberGermlineSites.38.tsv.gz",
        "hmf_gc_profile": "/dna/copy_number/GC_profile.1000bp.38.cnp",
        "hmf_ensembl_dir": "/common/ensembl_data",
        "hmf_hotspots": "/dna/variants/KnownHotspots.somatic.38.vcf.gz",
    }
    for k, i in idx.items():
        lines[i] = '%s%-17s = "${params.hmf_root}%s"' % (indent, k, suffix[k])
    header = [
        "%s// %s: the hmftools resource bundle is site data. A panel overlay is loaded after the" % (indent, MARKER),
        "%s// site profile, so a site cannot override these five paths from its own profile --" % indent,
        "%s// it sets hmf_root instead, and the paths below follow. The default is the location" % indent,
        "%s// on the development host." % indent,
        "%s// A panel overlay loads AFTER the site profile, so this default must not clobber a" % indent,
        "%s// value the site already set -- hence the containsKey guard." % indent,
        "%s%-17s = params.containsKey('hmf_root') ? params.hmf_root : '%s'" % (indent, "hmf_root", HMF_ROOT_DEFAULT),
    ]
    lines[first:first] = header
    write(p, "\n".join(lines), apply_)
    return "%s: hmf_root introduced, %d paths derived from it" % (p, len(HMF_KEYS))


def patch_clinical23_hmf_root(apply_):
    """Set hmf_root in the clinical-23 profile so its params file no longer needs the hmf paths."""
    p = "conf/clinical23.config"
    if not os.path.exists(p):
        return "%s: absent, skipped" % p
    text = read(p)
    if re.search(r"^\s*hmf_root\s*=", text, re.M):
        return "%s: hmf_root already set, unchanged" % p
    m = re.search(r"^(\s*)hmf_resources\s*=\s*(.+)$", text, re.M)
    if not m:
        return "%s: no hmf_resources line; set hmf_root by hand" % p
    indent, value = m.group(1), m.group(2).rstrip()
    new = ('%s// %s: one value now drives every hmftools path (see conf/twist_apply.config).\n'
           '%shmf_root          = %s' % (indent, MARKER, indent, value))
    text = text.replace(m.group(0), new)
    dropped = []
    keep = []
    for l in text.split("\n"):
        if re.match(r"^\s*(hmf_loci|hmf_gc_profile|hmf_ensembl_dir|hmf_hotspots|hmf_resources)\s*=", l):
            dropped.append(l.strip().split("=")[0].strip())
            continue
        keep.append(l)
    write(p, "\n".join(keep), apply_)
    return "%s: hmf_root set; dropped %s (now derived)" % (p, ", ".join(dropped) or "nothing")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".")
    ap.add_argument("--bed-src", required=True, help="directory holding the two MYOPOOL BED files")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    os.chdir(args.repo)

    print("== 1. panel BEDs")
    os.makedirs(ASSET_DIR, exist_ok=True) if args.apply else None
    for fname, expect in BEDS.items():
        src = os.path.join(args.bed_src, fname)
        dst = os.path.join(ASSET_DIR, fname)
        if not os.path.isfile(src):
            raise SystemExit("[error] not found: %s" % src)
        got = md5(src)
        if got != expect:
            raise SystemExit("[error] %s md5 %s, expected %s -- do not adopt a BED that differs "
                             "from the validated one" % (src, got, expect))
        if os.path.exists(dst):
            print("   [skip] %s already in %s (md5 %s)" % (fname, ASSET_DIR, md5(dst)))
        elif args.apply:
            shutil.copy2(src, dst)
            print("   [copy] %s -> %s (md5 %s)" % (fname, dst, md5(dst)))
        else:
            print("   [plan] copy %s -> %s (md5 %s verified)" % (fname, dst, got))

    print("== 2. configuration")
    for msg in [patch_nextflow_config(args.apply)] + \
               [patch_site_config(c, args.apply) for c in SITE_CONFIGS] + \
               [patch_twist_apply(args.apply), patch_clinical23_hmf_root(args.apply)]:
        print("   " + msg)

    if not args.apply:
        print("\n[dry-run] nothing written; re-run with --apply")
        return 0
    print("\n[applied] backups carry the suffix .bak_panelassets_%s" % STAMP)
    print("Next: confirm both profiles resolve the panel BEDs to assets/myeloid and the hmftools")
    print("paths to the intended root, then run the stub DAG on each host before committing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
