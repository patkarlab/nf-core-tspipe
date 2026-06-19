#!/usr/bin/env python3
"""
patch_dashboard_mobidetails_curate.py

Replace the full-dump MobiDetails renderer with a curated view.

The current renderMobidetailsBlock() prints every non-empty field MobiDetails
returns (~110 rows). This patch swaps it for a curated set, in the same compact
style as the GeneBe block, while keeping every raw field one click away behind a
collapsed "Show all MobiDetails fields" toggle.

Curated set (empty / "not found" values are dropped automatically via the
existing mdIsEmpty helper, so each variant shows only the fields it actually has):
  - ClinVar significance (+ review status)
  - gnomAD v4 exome AF
  - gnomAD v4 genome AF
  - dbSNP rsID
  - REVEL (score + call)
  - AlphaMissense (score + call)
  - CADD (Phred)
  - SpliceAI (max of the four delta scores)
  - MPA (impact + score)
  - Gene role (oncogene / tumor suppressor)
  - ClinGen criteria (gene.clingenCriteriaSpec)
  - Variant location (exon/intron + number)

Scope: single file -- bin/dashboard_builder/assets/js/variant-browser.js.
The generic helpers (mdHumanizeKey/mdIsEmpty/mdFlatten/MD_GROUP_ORDER/
MD_GROUP_LABELS) are left untouched and reused for the full-dump toggle.
No parser change and no MobiDetails cache rebuild are required; the full
variant_data object is already cached, so a plain build.py re-run is enough.

Idempotent, anchor-based. Dry-run by default; pass --apply to write.
A timestamped .bak_<tag>_<UTC> backup is taken before writing.
Python 3.6-safe.
"""

import argparse
import datetime
import os
import sys

REPO_DEFAULT = "/goast/hemat_data/nf-core-tspipe"
REL = "bin/dashboard_builder/assets/js/variant-browser.js"
TAG = "mdcurate"
MARKER = "function mdCuratedRows"

# --- exact current renderMobidetailsBlock() function (anchor) -----------------
OLD = """    function renderMobidetailsBlock(annEntry) {
      const data = annEntry && annEntry.data;
      const vid = (annEntry && annEntry.mobidetails_id) || (data && data.variantId);
      const link = (annEntry && annEntry.url) ||
        (vid ? "https://mobidetails.chu-montpellier.fr/api/variant/" + vid + "/browser/" : "");

      let body;
      if (data && typeof data === "object") {
        const seen = {};
        const order = MD_GROUP_ORDER.concat(
          Object.keys(data).filter(function (k) { return MD_GROUP_ORDER.indexOf(k) === -1; })
        );
        const cols = [];
        order.forEach(function (g) {
          if (seen[g]) return;
          seen[g] = true;
          if (g === "variantId") return;            // surfaced via the link
          if (!(g in data)) return;
          const pairs = [];
          mdFlatten(data[g], "", pairs);
          if (pairs.length === 0) return;           // skip empty groups
          const rows = pairs.map(function (p) {
            return '<dt class="col-sm-6 text-muted fw-normal small">' + escapeHtml(p[0]) + "</dt>" +
                   '<dd class="col-sm-6 small mb-1">' + escapeHtml(String(p[1])) + "</dd>";
          }).join("");
          cols.push(
            '<div class="col-md-6">' +
              '<h6 class="text-uppercase text-muted small mt-3 mb-2">' +
                escapeHtml(MD_GROUP_LABELS[g] || mdHumanizeKey(g)) + "</h6>" +
              '<dl class="row mb-0">' + rows + "</dl>" +
            "</div>"
          );
        });
        body = '<div class="row g-3">' + cols.join("") + "</div>";
      } else {
        body = '<p class="text-muted small mb-0">Resolved in MobiDetails; full annotation not retrieved.</p>';
      }

      const linkHtml = link
        ? '<a href="' + escapeHtml(link) + '" target="_blank" rel="noopener" ' +
            'class="btn btn-sm btn-outline-primary mt-2">Open in MobiDetails \\u2197</a>'
        : "";

      return '<div class="vb-md-block mt-3 pt-3 border-top">' +
               '<h6 class="text-uppercase text-muted small mb-2">MobiDetails (build-time)</h6>' +
               body + linkHtml +
             "</div>";
    }"""

# --- replacement: curated view + factored full-dump helper -------------------
NEW = """    // Coerce MobiDetails booleans, which arrive as real bools or "True"/"False".
    function mdTruthy(v) {
      return v === true || v === "True" || v === "true" || v === 1 || v === "1";
    }
    // "0.107 (Benign)" when both are present; just the score otherwise.
    function mdScorePred(score, pred) {
      if (mdIsEmpty(score)) return "";
      return !mdIsEmpty(pred) ? String(score) + " (" + String(pred) + ")" : String(score);
    }
    // Largest of the four SpliceAI delta scores, e.g. "0.03 (max \\u0394)".
    function mdSpliceaiMax(sp) {
      if (!sp || typeof sp !== "object") return "";
      const vals = ["spliceai_DS_AG", "spliceai_DS_AL", "spliceai_DS_DG", "spliceai_DS_DL"]
        .map(function (k) { return parseFloat(sp[k]); })
        .filter(function (x) { return !isNaN(x); });
      if (vals.length === 0) return "";
      return Math.max.apply(null, vals).toFixed(2) + " (max \\u0394)";
    }
    function mdGeneRole(g) {
      if (!g) return "";
      const roles = [];
      if (mdTruthy(g.isOncogene)) roles.push("oncogene");
      if (mdTruthy(g.isTumorSuppressor)) roles.push("tumor suppressor");
      return roles.join(", ");
    }
    function mdVariantLocation(p) {
      if (!p) return "";
      // Prefer "exon 13" (segment type + number); fall back to the coarse location.
      if (!mdIsEmpty(p.segmentStartType) && !mdIsEmpty(p.segmentStartNumber)) {
        return String(p.segmentStartType) + " " + String(p.segmentStartNumber);
      }
      return mdIsEmpty(p.variantLocation) ? "" : String(p.variantLocation);
    }
    // Curated field set. Empty / "not found" values drop out via mdIsEmpty, so a
    // given variant shows only the fields it actually carries.
    function mdCuratedRows(data) {
      const f = data.frequenciesDatabases || {};
      const m = data.missensePredictions || {};
      const o = data.overallPredictions || {};
      const sp = data.splicingPredictions || {};
      const g = data.gene || {};
      const p = data.positions || {};
      const clinvar = mdIsEmpty(f.clinvarClinsig) ? "" :
        (!mdIsEmpty(f.clinvarClinRevStat)
          ? String(f.clinvarClinsig) + " (" + String(f.clinvarClinRevStat) + ")"
          : String(f.clinvarClinsig));
      const candidates = [
        ["ClinVar", clinvar],
        ["gnomAD v4 exome", mdIsEmpty(f.gnomADv4Exome) ? "" : String(f.gnomADv4Exome)],
        ["gnomAD v4 genome", mdIsEmpty(f.gnomADv4Genome) ? "" : String(f.gnomADv4Genome)],
        ["dbSNP", mdIsEmpty(f.dbSNPrsid) ? "" : String(f.dbSNPrsid)],
        ["REVEL", mdScorePred(m.revelScore, m.revelPred)],
        ["AlphaMissense", mdScorePred(m.amScore, m.amPred)],
        ["CADD (Phred)", mdIsEmpty(o.caddPhred) ? "" : String(o.caddPhred)],
        ["SpliceAI", mdSpliceaiMax(sp)],
        ["MPA", mdScorePred(o.mpaImpact, o.mpaScore)],
        ["Gene role", mdGeneRole(g)],
        ["ClinGen criteria", mdIsEmpty(g.clingenCriteriaSpec) ? "" : String(g.clingenCriteriaSpec)],
        ["Variant location", mdVariantLocation(p)]
      ];
      return candidates.filter(function (r) { return r[1] !== ""; });
    }
    // Full, every-field dump -- kept behind a collapsed toggle.
    function mdRenderAllGroups(data) {
      const seen = {};
      const order = MD_GROUP_ORDER.concat(
        Object.keys(data).filter(function (k) { return MD_GROUP_ORDER.indexOf(k) === -1; })
      );
      const cols = [];
      order.forEach(function (g) {
        if (seen[g]) return;
        seen[g] = true;
        if (g === "variantId") return;            // surfaced via the link
        if (!(g in data)) return;
        const pairs = [];
        mdFlatten(data[g], "", pairs);
        if (pairs.length === 0) return;           // skip empty groups
        const rows = pairs.map(function (p) {
          return '<dt class="col-sm-6 text-muted fw-normal small">' + escapeHtml(p[0]) + "</dt>" +
                 '<dd class="col-sm-6 small mb-1">' + escapeHtml(String(p[1])) + "</dd>";
        }).join("");
        cols.push(
          '<div class="col-md-6">' +
            '<h6 class="text-uppercase text-muted small mt-3 mb-2">' +
              escapeHtml(MD_GROUP_LABELS[g] || mdHumanizeKey(g)) + "</h6>" +
            '<dl class="row mb-0">' + rows + "</dl>" +
          "</div>"
        );
      });
      return '<div class="row g-3">' + cols.join("") + "</div>";
    }
    function renderMobidetailsBlock(annEntry) {
      const data = annEntry && annEntry.data;
      const vid = (annEntry && annEntry.mobidetails_id) || (data && data.variantId);
      const link = (annEntry && annEntry.url) ||
        (vid ? "https://mobidetails.chu-montpellier.fr/api/variant/" + vid + "/browser/" : "");

      let body;
      if (data && typeof data === "object") {
        const rows = mdCuratedRows(data);
        if (rows.length) {
          const dl = rows.map(function (r) {
            return '<dt class="col-sm-5 text-muted fw-normal small">' + escapeHtml(r[0]) + "</dt>" +
                   '<dd class="col-sm-7 small mb-1">' + escapeHtml(r[1]) + "</dd>";
          }).join("");
          body = '<dl class="row mb-0">' + dl + "</dl>";
        } else {
          body = '<p class="text-muted small mb-0">Resolved in MobiDetails; no curated fields populated.</p>';
        }
        // Every raw field, collapsed by default.
        body += '<details class="vb-md-all mt-2">' +
                  '<summary class="small text-muted" style="cursor:pointer;">Show all MobiDetails fields</summary>' +
                  '<div class="mt-2">' + mdRenderAllGroups(data) + "</div>" +
                "</details>";
      } else {
        body = '<p class="text-muted small mb-0">Resolved in MobiDetails; full annotation not retrieved.</p>';
      }

      const linkHtml = link
        ? '<a href="' + escapeHtml(link) + '" target="_blank" rel="noopener" ' +
            'class="btn btn-sm btn-outline-primary mt-2">Open in MobiDetails \\u2197</a>'
        : "";

      return '<div class="vb-md-block mt-3 pt-3 border-top">' +
               '<h6 class="text-uppercase text-muted small mb-2">MobiDetails (build-time)</h6>' +
               body + linkHtml +
             "</div>";
    }"""


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=REPO_DEFAULT,
                    help="repo root (default: %s)" % REPO_DEFAULT)
    ap.add_argument("--apply", action="store_true",
                    help="write changes (default: dry-run)")
    args = ap.parse_args()

    path = os.path.join(args.repo, REL)
    if not os.path.isfile(path):
        print("[error] not found: %s" % path)
        return 2

    with open(path, "r", encoding="utf-8") as fh:
        src = fh.read()

    if MARKER in src:
        print("[skip] %s :: curated MobiDetails view already present (marker found)." % REL)
        return 0

    if OLD not in src:
        print("[error] %s :: anchor renderMobidetailsBlock() not found verbatim." % REL)
        print("        The MobiDetails patch must be applied first, and the function")
        print("        must be unmodified. No changes written.")
        return 3

    if src.count(OLD) != 1:
        print("[error] %s :: anchor matched %d times; expected exactly 1. Aborting."
              % (REL, src.count(OLD)))
        return 4

    new_src = src.replace(OLD, NEW)

    if not args.apply:
        print("[dry-run] %s :: would replace full-dump renderMobidetailsBlock() with"
              " curated view + collapsible full dump." % REL)
        print("[dry-run] net change: +%d bytes. Re-run with --apply to write."
              % (len(new_src) - len(src)))
        return 0

    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    bak = "%s.bak_%s_%s" % (path, TAG, ts)
    with open(bak, "w", encoding="utf-8") as fh:
        fh.write(src)
    print("[backup] %s" % bak)

    with open(path, "w", encoding="utf-8") as fh:
        fh.write(new_src)
    print("[patch]  wrote %s" % path)
    print("[done]   curated MobiDetails view applied. Re-run build.py against the")
    print("         published run dir (no --annotate-mobidetails needed; cache reused).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
