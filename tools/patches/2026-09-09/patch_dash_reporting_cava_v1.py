#!/usr/bin/env python3
"""DASH_REPORTING_CAVA_V1 -- CAVA on the Reporting tab, and live-row fallbacks so stored
selections pick up new fields without being re-included.

Run from the nf-core-tspipe repo root. Dry-run by default; --apply writes. All-or-nothing;
.bak_DASH_REPORTING_CAVA_V1_<timestamp> backups. Template only (bin/dashboard_builder, not in
any task hash): nocache DASHBOARD/REPORT_BUNDLE re-render, no resume.

templates/sample_report.html.j2
  - New column "CAVA (MANE RefSeq)" after "Transcript Variant": CAVA transcript:HGVSc on one
    line, HGVSp on the next; "alt alignment" note with the alternative alignment on hover;
    "differs from VEP" badge when CAVA_HGVSp_Match is DIFFER; em dash when CAVA has nothing.
  - Values are read from the live clinical row (embedded in the page, matched by
    chr:pos:ref:alt), falling back to the stored snapshot. The COSMIC cell does the same, so
    selections stored before IGV_V2A now show 'COSV…, COSV…' without being re-included.
  - Copy-as-TSV gains three columns: CAVA transcript variant, CAVA protein variant,
    CAVA alternative alignment.
  - Column widths rebalanced for the extra column.
"""
import argparse
import os
import shutil
import sys
import time

TAG = "DASH_REPORTING_CAVA_V1"
STAMP = time.strftime("%Y%m%d_%H%M%S")
TPL = "bin/dashboard_builder/templates/sample_report.html.j2"


class PatchError(Exception):
    pass


def read(path):
    if not os.path.isfile(path):
        raise PatchError("missing file: %s" % path)
    with open(path) as f:
        return f.read()


def replace_once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise PatchError("%s: anchor found %d times (expected 1): %r" % (label, n, old[:80]))
    return text.replace(old, new)


THEAD_OLD = """                  <th scope="col" style="width:90px">Gene</th>
                  <th scope="col" style="width:20%">Genomic variant</th>
                  <th scope="col" style="width:17%">Protein variant</th>
                  <th scope="col" style="width:17%">Transcript Variant</th>
                  <th scope="col" style="width:60px">Exon</th>
                  <th scope="col" style="width:16%">COSMIC database reference</th>
"""
THEAD_NEW = """                  <th scope="col" style="width:90px">Gene</th>
                  <th scope="col" style="width:17%">Genomic variant</th>
                  <th scope="col" style="width:14%">Protein variant</th>
                  <th scope="col" style="width:14%">Transcript Variant</th>
                  <th scope="col" style="width:17%">CAVA (MANE RefSeq)</th>   {# DASH_REPORTING_CAVA_V1 #}
                  <th scope="col" style="width:60px">Exon</th>
                  <th scope="col" style="width:13%">COSMIC database reference</th>
"""

COLS_OLD = """    const VARIANT_COLUMNS = [
      "Gene", "Genomic variant", "Protein variant", "Transcript Variant", "Exon",
      "COSMIC database reference", "Variant allele frequency (%)",
      "AMP/ASCO/CAP Tier (somatic)"
    ];
"""
COLS_NEW = """    const VARIANT_COLUMNS = [
      "Gene", "Genomic variant", "Protein variant", "Transcript Variant",
      "CAVA transcript variant", "CAVA protein variant", "CAVA alternative alignment",   // DASH_REPORTING_CAVA_V1
      "Exon",
      "COSMIC database reference", "Variant allele frequency (%)",
      "AMP/ASCO/CAP Tier (somatic)"
    ];

    // DASH_REPORTING_CAVA_V1: the live clinical row for a stored selection (matched on
    // chr:pos:ref:alt), so fields added after the selection was stored still render.
    const liveRows = {};
    (typeof clinicalVariants !== "undefined" ? clinicalVariants : []).forEach(function (r) {
      liveRows[(r.Chr || "") + ":" + (r.Start || "") + ":" + (r.Ref || "") + ":" + (r.Alt || "")] = r;
    });
    function isSet(v) { return v !== undefined && v !== null && v !== "" && v !== "-1"; }
    function cavaOf(it) {
      const r = liveRows[it.id] || {};
      const s = it.snapshot || {};
      const tx = isSet(r.CAVA_Transcript) ? r.CAVA_Transcript : (s.cavaTx || "");
      const c  = isSet(r.CAVA_HGVSc) ? r.CAVA_HGVSc : (s.cavaC || "");
      const p  = isSet(r.CAVA_HGVSp) ? r.CAVA_HGVSp : (s.cavaP || "");
      const alt = isSet(r.CAVA_AltAnn) ? r.CAVA_AltAnn : (s.cavaAlt || "");
      const differs = (r.CAVA_HGVSp_Match || s.cavaMatch || "") === "DIFFER";
      return { tx: tx, c: c, p: p, alt: alt, differs: differs,
               cText: c ? ((tx && c.indexOf(":") === -1) ? tx + ":" + c : c) : "" };
    }
    function cosmicOf(it) {
      const r = liveRows[it.id];
      const s = it.snapshot || {};
      if (r && isSet(r.Existing_variation)) return window.tspipeReporting.extractCosmicIds(r.Existing_variation);
      return String(s.cosmic || "").replace(/ID=/g, "").replace(/;/g, ", ");
    }
"""

TSV_OLD = """    function variantRowToTsv(it) {
      const tier = window.tspipeReporting.getTier(it.id) || "";
      const s = it.snapshot || {};
      const vaf = s.vaf ? Number(s.vaf).toFixed(1) : "";
      return [s.gene || "", s.hgvsG || "", s.hgvsP || "", s.hgvsC || "", s.exon || "",
              s.cosmic || "", vaf, tier].join("\\t");
    }
"""
TSV_NEW = """    function variantRowToTsv(it) {
      const tier = window.tspipeReporting.getTier(it.id) || "";
      const s = it.snapshot || {};
      const vaf = s.vaf ? Number(s.vaf).toFixed(1) : "";
      const cv = cavaOf(it);   // DASH_REPORTING_CAVA_V1
      return [s.gene || "", s.hgvsG || "", s.hgvsP || "", s.hgvsC || "",
              cv.cText, cv.p, cv.alt, s.exon || "",
              cosmicOf(it), vaf, tier].join("\\t");
    }
"""

ROW_OLD = """                 '<td class="font-monospace small">' + escapeHtml(s.hgvsC) + '</td>' +
                 '<td>' + escapeHtml(s.exon || "") + '</td>' +
                 '<td class="font-monospace small reporting-cosmic" title="' + escapeHtml(s.cosmic) + '">' + escapeHtml(s.cosmic) + '</td>' +   // DASH_LAYOUT_V1 (D5)
"""
ROW_NEW = """                 '<td class="font-monospace small">' + escapeHtml(s.hgvsC) + '</td>' +
                 '<td class="font-monospace small">' + cavaCell(it) + '</td>' +   // DASH_REPORTING_CAVA_V1
                 '<td>' + escapeHtml(s.exon || "") + '</td>' +
                 '<td class="font-monospace small reporting-cosmic" title="' + escapeHtml(cosmicOf(it)) + '">' + escapeHtml(cosmicOf(it)) + '</td>' +   // DASH_LAYOUT_V1 (D5); live row since DASH_REPORTING_CAVA_V1
"""

RENDER_ANCHOR = """    function renderVariants(variants) {
      if (variants.length === 0) {
"""
RENDER_NEW = """    // DASH_REPORTING_CAVA_V1: CAVA cell -- transcript:c. on one line, p. on the next, alt alignment
    // and the differs-from-VEP flag as small notes.
    function cavaCell(it) {
      const cv = cavaOf(it);
      if (!cv.cText && !cv.p) return '<span class="text-muted">\\u2014</span>';
      let html = escapeHtml(cv.cText);
      if (cv.p) html += (html ? "<br>" : "") + escapeHtml(cv.p);
      if (cv.alt) html += '<br><span class="badge bg-light text-dark border" title="Alternative alignment: ' + escapeHtml(cv.alt) + '">alt alignment</span>';
      if (cv.differs) html += ' <span class="badge bg-warning text-dark" title="CAVA protein call differs from VEP">differs from VEP</span>';
      return html;
    }

""" + RENDER_ANCHOR

SNAP_OLD = """              exon:     row.EXON_REPORT || row.EXON || "",
              cosmic:   window.tspipeReporting.extractCosmicIds(row.Existing_variation),
"""
SNAP_NEW = """              exon:     row.EXON_REPORT || row.EXON || "",
              cosmic:   window.tspipeReporting.extractCosmicIds(row.Existing_variation),
              cavaTx:   (row.CAVA_Transcript && row.CAVA_Transcript !== "-1") ? row.CAVA_Transcript : "",   // DASH_REPORTING_CAVA_V1
              cavaC:    (row.CAVA_HGVSc && row.CAVA_HGVSc !== "-1") ? row.CAVA_HGVSc : "",
              cavaP:    (row.CAVA_HGVSp && row.CAVA_HGVSp !== "-1") ? row.CAVA_HGVSp : "",
              cavaAlt:  (row.CAVA_AltAnn && row.CAVA_AltAnn !== "-1") ? row.CAVA_AltAnn : "",
              cavaMatch: row.CAVA_HGVSp_Match || "",
"""


def patch_template(text):
    if TAG in text:
        return text, "skip"
    text = replace_once(text, THEAD_OLD, THEAD_NEW, "thead")
    text = replace_once(text, COLS_OLD, COLS_NEW, "VARIANT_COLUMNS")
    text = replace_once(text, TSV_OLD, TSV_NEW, "variantRowToTsv")
    text = replace_once(text, ROW_OLD, ROW_NEW, "renderVariants cells")
    text = replace_once(text, RENDER_ANCHOR, RENDER_NEW, "cavaCell helper")
    return text, "patch"


def patch_js(text):
    if TAG in text:
        return text, "skip"
    return replace_once(text, SNAP_OLD, SNAP_NEW, "snapshot CAVA fields"), "patch"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    ap.add_argument("--repo", default=".", help="repo root (default: cwd)")
    args = ap.parse_args()
    os.chdir(args.repo)
    targets = [
        (TPL, patch_template),
        ("bin/dashboard_builder/assets/js/variant-browser.js", patch_js),
    ]
    plan = []
    try:
        for path, fn in targets:
            new, status = fn(read(path))
            plan.append((path, new, status))
    except PatchError as e:
        print("[error] %s" % e)
        print("[error] nothing written")
        sys.exit(1)
    for path, _, status in plan:
        print("[%s] %s" % (status, path))
    if not args.apply:
        print("[dry-run] re-run with --apply to write")
        return
    for path, new, status in plan:
        if status == "skip":
            continue
        bak = "%s.bak_%s_%s" % (path, TAG, STAMP)
        shutil.copy2(path, bak)
        print("[backup] %s" % bak)
        with open(path, "w") as f:
            f.write(new)
        print("[write] %s" % path)
    print("[done] %s applied" % TAG)


if __name__ == "__main__":
    main()
