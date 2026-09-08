#!/usr/bin/env python3
"""tools/patches/2026-09-08/patch_dash_spikein_links_v1.py -- MARKER SPIKEIN_V1c (D13b)

Spike-in tab: the "Calls inside spike-in regions" table is replaced by an
instance of the shared variant browser (window.initVariantBrowser, the same
widget that draws Clinical and All Filtered), fed the subset of
filteredVariants whose chr:pos:ref:alt lies inside a spike-in region. The
rows therefore get the same cards, Franklin / GeneBe links and IGV chips as
every other variant. igvLookup is passed (unlike All Filtered), so an IGV
chip resolves as soon as IGV_REPORTS renders the spike-in loci (D13b-2);
until then it shows "no IGV" like any row absent from the report.

SNP genotype rows gain a links column: dbSNP by rsID, and Franklin / GeneBe
built from the hg38 reference and the observed alt allele (or the curated
risk allele when the site is hom_ref and the risk allele is not the
reference).

Template only; re-render with -c /tmp/dash_nocache.config.

Usage:  python3 <this file> [--apply]
"""

import argparse
import shutil
import sys
import time
from pathlib import Path

MARKER = "SPIKEIN_V1c"
TAG = "spikein_v1c"
REPO = Path(__file__).resolve().parents[3]
TPL = "bin/dashboard_builder/templates/sample_report.html.j2"

# 1. region-calls table -> browser container (block replace: start line .. end line, inclusive)
BLOCK_START = "        {% if ctx.spikein.region_variants %}"
BLOCK_END = "          <div class=\"tspipe-empty\">No calls inside the spike-in regions in this sample.</div>"
BLOCK_NEW = (
    "        {# SPIKEIN_V1c (D13b): rendered by the shared variant browser, see body_scripts #}\n"
    "        {% if ctx.spikein.region_variants %}\n"
    "          <p class=\"text-muted small mb-1\">Same cards and link-outs as the Variants tabs; the region is the gene column (TERC, GATA2, MLH1 ...).</p>\n"
    "          <div id=\"spikein-browser\"></div>\n"
    "        {% else %}\n"
    "          <div class=\"tspipe-empty\">No calls inside the spike-in regions in this sample.</div>\n"
)
# the line after BLOCK_END in the V1 template is "        {% endif %}", which is kept.

# 2. SNP table header and links cell
SNP_TH_OLD = "<th>status</th><th>caller Filter</th></tr></thead>"
SNP_TH_NEW = "<th>status</th><th>caller Filter</th><th>links</th></tr></thead>"
SNP_TD_OLD = "                  <td class=\"small\">{% if s.filtered_row %}{{ s.filtered_row.Filter }} ({{ s.filtered_row.VAF_pct }}%){% else %}not called{% endif %}</td></tr>\n"
SNP_TD_NEW = (
    "                  <td class=\"small\">{% if s.filtered_row %}{{ s.filtered_row.Filter }} ({{ s.filtered_row.VAF_pct }}%){% else %}not called{% endif %}</td>\n"
    "                  {# SPIKEIN_V1c (D13b): link-outs #}\n"
    "                  {% set _c = s.chrom | replace('chr', '') %}\n"
    "                  {% set _ref = s.ref if (s.ref is defined and s.ref != '-') else '' %}\n"
    "                  {% set _alt = s.alt if (s.alt is defined and s.alt != '-') else (s.risk_allele if (s.risk_allele != '-' and s.risk_allele != _ref) else '') %}\n"
    "                  <td class=\"small text-nowrap\">\n"
    "                    {% if s.rsid and s.rsid != '-' %}<a href=\"https://www.ncbi.nlm.nih.gov/snp/{{ s.rsid }}\" target=\"_blank\" rel=\"noopener\">dbSNP</a>{% endif %}\n"
    "                    {% if _ref and _alt %}\n"
    "                      &middot; <a href=\"https://franklin.genoox.com/clinical-db/variant/snp/chr{{ _c }}-{{ s.pos }}-{{ _ref }}-{{ _alt }}-hg38\" target=\"_blank\" rel=\"noopener\">Franklin</a>\n"
    "                      &middot; <a href=\"https://genebe.net/variant/hg38/chr{{ _c }}-{{ s.pos }}-{{ _ref }}-{{ _alt }}\" target=\"_blank\" rel=\"noopener\">GeneBe</a>\n"
    "                    {% endif %}\n"
    "                  </td></tr>\n"
)

# 3. JS: replace the V1 DataTable init line with the browser instantiation
JS_OLD = "    if ($('#spikein-variants-table').length) { $('#spikein-variants-table').DataTable({ pageLength: 25, order: [] }); }   // SPIKEIN_V1\n"
JS_NEW = (
    "    // SPIKEIN_V1c (D13b): spike-in region calls through the shared variant browser, initialised on first show\n"
    "    (function () {\n"
    "      var el = document.getElementById(\"spikein-browser\");\n"
    "      if (!el || typeof initVariantBrowser !== \"function\") return;\n"
    "      var keys = new Set({{ (ctx.spikein.region_keys if ctx.spikein else []) | tojson }});\n"
    "      var inited = false;\n"
    "      function initSpikein() {\n"
    "        if (inited) return;\n"
    "        inited = true;\n"
    "        var rows = filteredVariants.filter(function (r) {\n"
    "          return keys.has((r.Chr || \"\") + \":\" + (r.Start || \"\") + \":\" + (r.Ref || \"\") + \":\" + (r.Alt || \"\"));\n"
    "        });\n"
    "        initVariantBrowser({\n"
    "          containerId: \"spikein-browser\",\n"
    "          variants: rows,\n"
    "          filterIds: [\"filter_status\", \"gene\", \"vaf_min\", \"callers_buttons\"],\n"
    "          igvLookup: igvLookup,\n"
    "          igvFrameId: \"igv-frame\",\n"
    "          igvTabSelector: '[data-bs-target=\"#tab-igv\"]',\n"
    "          genebeAnnotations: {},\n"
    "          oncokbAnnotations: {},\n"
    "          cancervarAnnotations: {},\n"
    "          mobidetailsAnnotations: {},\n"
    "          enableReportSelect: false\n"
    "        });\n"
    "      }\n"
    "      var btn = document.querySelector('[data-bs-target=\"#tab-spikein\"]');\n"
    "      if (btn) btn.addEventListener(\"shown.bs.tab\", initSpikein);\n"
    "      if (btn && btn.classList.contains(\"active\")) initSpikein();\n"
    "    })();\n"
)


def apply(text):
    lines = text.splitlines(keepends=True)
    # block replace
    starts = [i for i, l in enumerate(lines) if l.rstrip("\n") == BLOCK_START]
    if len(starts) != 1:
        raise RuntimeError("block start matched %d lines" % len(starts))
    s = starts[0]
    ends = [i for i in range(s, len(lines)) if lines[i].rstrip("\n") == BLOCK_END]
    if not ends:
        raise RuntimeError("block end not found after start")
    e = ends[0]
    lines[s:e + 1] = BLOCK_NEW.splitlines(keepends=True)
    text = "".join(lines)
    for old, new, what in ((SNP_TH_OLD, SNP_TH_NEW, "SNP thead"), (SNP_TD_OLD, SNP_TD_NEW, "SNP last cell"), (JS_OLD, JS_NEW, "JS init")):
        n = text.count(old)
        if n != 1:
            raise RuntimeError("%s anchor matched %d (need 1)" % (what, n))
        text = text.replace(old, new)
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--repo", default=str(REPO))
    args = ap.parse_args()
    p = Path(args.repo) / TPL
    src = p.read_text()
    if MARKER in src:
        print("[skip]   template already carries %s" % MARKER)
        return 0
    try:
        new = apply(src)
    except RuntimeError as exc:
        print("[error]  %s\n[error]  nothing written" % exc)
        return 1
    print("[patch]  %s: block replace + 3 edits" % TPL)
    if not args.apply:
        print("[dry]    re-run with --apply")
        return 0
    bak = p.with_name(p.name + ".bak_%s_%s" % (TAG, time.strftime("%Y%m%d_%H%M%S")))
    shutil.copy2(p, bak)
    p.write_text(new)
    print("[backup] %s\n[write]  %s\n[done]" % (bak.name, TPL))
    return 0


if __name__ == "__main__":
    sys.exit(main())
