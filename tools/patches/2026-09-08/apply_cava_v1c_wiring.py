#!/usr/bin/env python3
"""
CAVA_V1c (N3 stage 2b): wire CAVA into the pipeline and surface it on the dashboard.

Patches:
  nextflow.config
    - params.cava_catalog  = assets/cava/mane-1.5-grch38-refseq
    - params.cava_config   = assets/cava/cava_config.template.txt
  conf/modules.config
    - withName: 'CAVA' publishDir -> <outdir>/<sample>/annotation, pattern *.cava.vcf
  subworkflows/local/annotation.nf
    - include CAVA; run it on the post-MNV VCF in parallel with nothing else
      (it is the first step), then VEP_ANNOTATE takes [meta, vcf, cava_vcf]
  bin/dashboard_builder/assets/js/variant-browser.js
    - detail group "CAVA (MANE 1.5 RefSeq)" with the CAVA_* fields
    - compact card: CSN shown when VEP has no protein string; badges
      "CAVA differs" (CAVA_HGVSp_Match == DIFFER) and "alt alignment"
      (CAVA_AltAnn present)

Requires CAVA_V1b (apply_cava_v1b_annotate.py) already applied and
modules/local/cava.nf present.

Usage:
    python3 tools/patches/2026-09-08/apply_cava_v1c_wiring.py          # dry run
    python3 tools/patches/2026-09-08/apply_cava_v1c_wiring.py --apply
"""

import argparse
import shutil
import sys
import time
from pathlib import Path

TAG = "cava_v1c"
MARKER = "CAVA_V1c"


def _replace_once(text, old, new, what):
    assert text.count(old) == 1, f"anchor not found exactly once: {what}"
    return text.replace(old, new)


def patch_nextflow_config(text):
    if MARKER in text:
        print("  already patched")
        return text
    old = '''    vep_cache          = null
    annovar_script     = null   // path to ANNOVAR's table_annovar.pl
    annovar_db         = null
'''
    new = '''    vep_cache          = null
    annovar_script     = null   // path to ANNOVAR's table_annovar.pl
    annovar_db         = null
    // CAVA_V1c (N3): CAVA 2.0.15 transcript catalog + config template (assets, tracked in git)
    cava_catalog       = "${projectDir}/assets/cava/mane-1.5-grch38-refseq"
    cava_config        = "${projectDir}/assets/cava/cava_config.template.txt"
'''
    return _replace_once(text, old, new, "nextflow.config annotation params")


def patch_modules_config(text):
    if MARKER in text:
        print("  already patched")
        return text
    old = '''    withName: 'VARIANT_FILTER' {
        publishDir = [
            path: { "${params.outdir}/${meta.id}/annotation" },
            mode: params.publish_dir_mode,
            pattern: '*.{tsv,clinical.tsv,filtered.tsv}'
        ]
    }
'''
    new = old + '''
    // CAVA_V1c (N3): CAVA-annotated VCF alongside the annotation outputs
    withName: 'CAVA' {
        publishDir = [
            path: { "${params.outdir}/${meta.id}/annotation" },
            mode: params.publish_dir_mode,
            pattern: '*.cava.vcf'
        ]
    }
'''
    return _replace_once(text, old, new, "modules.config VARIANT_FILTER block")


def patch_annotation_nf(text):
    if MARKER in text:
        print("  already patched")
        return text
    old = '''include { VEP_ANNOTATE        } from '../../modules/local/vep_annotate'
'''
    new = '''include { CAVA                } from '../../modules/local/cava'           // CAVA_V1c (N3)
include { VEP_ANNOTATE        } from '../../modules/local/vep_annotate'
'''
    text = _replace_once(text, old, new, "annotation.nf include")
    old = '''    main:
        VEP_ANNOTATE(somaticseq_vcf_ch, reference_ch)
'''
    new = '''    main:
        // CAVA_V1c (N3): CAVA (CSN / HGVS / ALTANN on MANE 1.5 RefSeq) runs on the same
        // post-MNV VCF; VEP_ANNOTATE merges its tags into the CAVA_* columns.
        ch_cava_catalog = Channel.value(file(params.cava_catalog, checkIfExists: true))
        ch_cava_config  = Channel.value(file(params.cava_config,  checkIfExists: true))
        CAVA(somaticseq_vcf_ch, reference_ch, ch_cava_catalog, ch_cava_config)

        VEP_ANNOTATE(somaticseq_vcf_ch.join(CAVA.out.vcf, by: 0), reference_ch)
'''
    return _replace_once(text, old, new, "annotation.nf VEP_ANNOTATE call")


def patch_variant_browser(text):
    if MARKER in text:
        print("  already patched")
        return text
    # 1. detail group after "Annotation"
    old = '''      ["MANE_SELECT", "MANE Select"],
      ["Canonical", "Canonical"],
    ]],
    ["VariantValidator", [
'''
    new = '''      ["MANE_SELECT", "MANE Select"],
      ["Canonical", "Canonical"],
    ]],
    // CAVA_V1c (N3): CAVA 2.0.15 on the MANE 1.5 RefSeq catalog
    ["CAVA (MANE 1.5 RefSeq)", [
      ["CAVA_CSN", "CSN"],
      ["CAVA_HGVSc", "CAVA HGVSc"],
      ["CAVA_HGVSp", "CAVA HGVSp"],
      ["CAVA_Transcript", "CAVA transcript"],
      ["CAVA_Class", "CAVA class"],
      ["CAVA_SO", "CAVA SO"],
      ["CAVA_AltAnn", "Alternative alignment"],
      ["CAVA_HGVSp_Match", "Protein agrees with VEP"],
    ]],
    ["VariantValidator", [
'''
    text = _replace_once(text, old, new, "variant-browser DETAIL_GROUPS")

    # 2. monospace for the CAVA HGVS fields in the detail view
    old = '''              (field === "HGVSc" || field === "HGVSg" || field === "VV_HGVSc" || field === "VV_HGVSg" ||
               field === "HGVSp" || field === "VV_HGVSp" ? ' font-monospace' : '') +
'''
    new = '''              (field === "HGVSc" || field === "HGVSg" || field === "VV_HGVSc" || field === "VV_HGVSg" ||
               field === "HGVSp" || field === "VV_HGVSp" ||
               field === "CAVA_CSN" || field === "CAVA_HGVSc" || field === "CAVA_HGVSp" || field === "CAVA_AltAnn"   // CAVA_V1c
               ? ' font-monospace' : '') +
'''
    text = _replace_once(text, old, new, "variant-browser renderDetail monospace")

    # 3. compact card: CSN fallback + badges
    old = '''      const filterLabel = (r.Filter && r.Filter !== "PASS")
        ? ' <span class="badge bg-light text-dark border ms-1">' + escapeHtml(r.Filter) + "</span>"
        : "";
'''
    new = '''      const filterLabel = (r.Filter && r.Filter !== "PASS")
        ? ' <span class="badge bg-light text-dark border ms-1">' + escapeHtml(r.Filter) + "</span>"
        : "";

      // CAVA_V1c (N3): CSN when VEP gives no protein string (complex / delins calls);
      // badges when CAVA's protein call differs from VEP or an alternative alignment exists.
      const cavaCsn = (r.CAVA_CSN && r.CAVA_CSN !== "-1") ? r.CAVA_CSN : "";
      let cavaBadges = "";
      if (r.CAVA_HGVSp_Match === "DIFFER") {
        cavaBadges += '<span class="badge bg-warning text-dark" title="CAVA: ' +
                      escapeHtml(r.CAVA_HGVSp || "") + '">CAVA differs</span>';
      }
      if (r.CAVA_AltAnn && r.CAVA_AltAnn !== "-1") {
        cavaBadges += '<span class="badge bg-light text-dark border" title="Alternative alignment: ' +
                      escapeHtml(r.CAVA_AltAnn) + '">alt alignment</span>';
      }
'''
    text = _replace_once(text, old, new, "variant-browser renderCard filterLabel")

    old = '''              (r.IMPACT ? '<span class="badge bg-light text-dark border">' + escapeHtml(r.IMPACT) + "</span>" : "") +
              igvChip +
            "</div>" +
            '<div class="small font-monospace text-muted mt-1">' +
              escapeHtml(hgvsp || (r.HGVSc || "")) +
'''
    new = '''              (r.IMPACT ? '<span class="badge bg-light text-dark border">' + escapeHtml(r.IMPACT) + "</span>" : "") +
              cavaBadges +   // CAVA_V1c
              igvChip +
            "</div>" +
            '<div class="small font-monospace text-muted mt-1">' +
              escapeHtml(hgvsp || cavaCsn || (r.HGVSc || "")) +   // CAVA_V1c: CSN fallback
'''
    text = _replace_once(text, old, new, "variant-browser renderCard compact line")
    return text


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    root = Path(args.root)
    if not (root / "modules/local/cava.nf").exists():
        sys.exit("modules/local/cava.nf missing: extract the stage-2a bundle first")
    if "CAVA_V1b" not in (root / "bin/annotate.py").read_text():
        sys.exit("bin/annotate.py lacks CAVA_V1b: run apply_cava_v1b_annotate.py --apply first")
    targets = [
        (root / "nextflow.config", patch_nextflow_config),
        (root / "conf/modules.config", patch_modules_config),
        (root / "subworkflows/local/annotation.nf", patch_annotation_nf),
        (root / "bin/dashboard_builder/assets/js/variant-browser.js", patch_variant_browser),
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
