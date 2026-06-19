#!/usr/bin/env python3
"""Surface full MobiDetails annotation in the dashboard (build-time, keyless).

MobiDetails' academic API tier returns a complete variant_data object with no
API key. This patch makes the existing audit-only MobiDetails integration pull
that full object, cache it whole, and render every field it returns in the
variant detail panel -- grouped by MobiDetails' own categories, empty/None
fields omitted, generic so any field MobiDetails adds later auto-appears. An
"Open in MobiDetails" link is included.

Ten anchored edits across three files (build.py already populates
ctx["mobidetails"] via filter_for_frontend, so it needs no change):

  bin/dashboard_builder/parsers/mobidetails.py
    1. MD_VARIANT_URL constant (keyless variant_data endpoint)
    2. _fetch_variant_data() helper
    3. store the full variant_data on each resolved hit
    4. filter_for_frontend() passes the data through to the frontend

  bin/dashboard_builder/templates/sample_report.html.j2
    5. mobidetailsAnnotations passthrough const
    6. pass mobidetailsAnnotations to the clinical variant browser
    7. pass an empty map on the filtered tab (parity with GeneBe/OncoKB)

  bin/dashboard_builder/assets/js/variant-browser.js
    8. accept config.mobidetailsAnnotations
    9. build + insert the MobiDetails block in renderDetail
   10. renderMobidetailsBlock() + helpers (generic full-object renderer)

Idempotent and anchor-based. Two-phase: every edit is validated first; if any
anchor is missing or ambiguous, nothing is written. Dry-run by default; pass
--apply to write. A timestamped backup (.bak_mobidetails_<UTC>) is written per
changed file. Python 3.6-safe.

Run from the repository root:
    python3 patch_dashboard_mobidetails.py            # dry-run (per-file diffs)
    python3 patch_dashboard_mobidetails.py --apply     # write
"""

import argparse
import datetime
import difflib
import os
import shutil
import sys

TAG = "mobidetails"

PARSER = os.path.join("bin", "dashboard_builder", "parsers", "mobidetails.py")
TPL = os.path.join("bin", "dashboard_builder", "templates", "sample_report.html.j2")
JS = os.path.join("bin", "dashboard_builder", "assets", "js", "variant-browser.js")

# ---------------------------------------------------------------------------
# parsers/mobidetails.py
# ---------------------------------------------------------------------------
P_CONST = {
    "name": "MD_VARIANT_URL constant",
    "marker": "MD_VARIANT_URL",
    "anchor": r'''MD_EXISTS_URL = "https://mobidetails.chu-montpellier.fr/api/variant/exists/{ghgvs}"
''',
    "replacement": r'''MD_EXISTS_URL = "https://mobidetails.chu-montpellier.fr/api/variant/exists/{ghgvs}"
# Full variant_data JSON for a resolved MD id. Keyless: the academic tier
# returns the complete annotation with no API key (the trailing slash is the
# empty api_key path segment). 'cli' = JSON without SPiP.
MD_VARIANT_URL = "https://mobidetails.chu-montpellier.fr/api/variant/{vid}/cli/"
''',
}

P_HELPER = {
    "name": "_fetch_variant_data() helper",
    "marker": "def _fetch_variant_data",
    "anchor": r'''def annotate(clinical_rows, sample_dir, sample):
    """Resolve clinical variants to MobiDetails record URLs.
''',
    "replacement": r'''def _fetch_variant_data(requests, vid, sample):
    """Fetch the full MobiDetails variant_data JSON for a resolved MD id.

    Keyless: the academic tier returns the complete annotation with no API key.
    Returns the parsed dict, or None on any failure (the caller still keeps the
    id/url so the link and a not-found state keep working).
    """
    if vid is None:
        return None
    try:
        resp = requests.get(
            MD_VARIANT_URL.format(vid=vid),
            timeout=TIMEOUT_S,
            headers={"Accept": "application/json"},
        )
    except requests.RequestException as exc:
        logging.warning("[%s] MobiDetails variant_data request failed for id %s: %s", sample, vid, exc)
        return None
    if resp.status_code != 200:
        logging.warning("[%s] MobiDetails variant_data HTTP %s for id %s", sample, resp.status_code, vid)
        return None
    try:
        out = resp.json()
    except ValueError:
        logging.warning("[%s] MobiDetails variant_data non-JSON for id %s", sample, vid)
        return None
    return out if isinstance(out, dict) else None


def annotate(clinical_rows, sample_dir, sample):
    """Resolve clinical variants to MobiDetails record URLs.
''',
}

P_HIT = {
    "name": "store full variant_data on each hit",
    "marker": 'entry["data"] = _fetch_variant_data',
    "anchor": r'''        if isinstance(data, dict) and "mobidetails_id" in data:
            cache[key] = {
                "mobidetails_id": data.get("mobidetails_id"),
                "url":            data.get("url"),
                "hgvs_g":         hgvs_g,
                "_fetched_at":    timestamp,
            }
            n_hit += 1
''',
    "replacement": r'''        if isinstance(data, dict) and "mobidetails_id" in data:
            vid = data.get("mobidetails_id")
            entry = {
                "mobidetails_id": vid,
                "url":            data.get("url"),
                "hgvs_g":         hgvs_g,
                "_fetched_at":    timestamp,
            }
            # Follow-up call: pull the full variant_data JSON (keyless) and store
            # it whole so the dashboard can render every field MD returns.
            entry["data"] = _fetch_variant_data(requests, vid, sample)
            time.sleep(SLEEP_BETWEEN_REQUESTS_S)
            cache[key] = entry
            n_hit += 1
''',
}

P_FILTER = {
    "name": "filter_for_frontend passes data through",
    "marker": 'ann.get("data")',
    "anchor": r'''        out[key] = {
            "url":            url,
            "mobidetails_id": ann.get("mobidetails_id"),
            "_fetched_at":    ann.get("_fetched_at"),
        }
''',
    "replacement": r'''        out[key] = {
            "url":            url,
            "mobidetails_id": ann.get("mobidetails_id"),
            "data":           ann.get("data"),
            "_fetched_at":    ann.get("_fetched_at"),
        }
''',
}

# ---------------------------------------------------------------------------
# templates/sample_report.html.j2
# ---------------------------------------------------------------------------
T_CONST = {
    "name": "mobidetailsAnnotations passthrough const",
    "marker": "const mobidetailsAnnotations",
    "anchor": r'''  // Optional GeneBe annotations, populated only when --annotate-genebe was used.
  const genebeAnnotations = {{ ctx.genebe | tojson }};
''',
    "replacement": r'''  // Optional GeneBe annotations, populated only when --annotate-genebe was used.
  const genebeAnnotations = {{ ctx.genebe | tojson }};

  // Optional MobiDetails annotations (full variant_data), only when --annotate-mobidetails was used.
  const mobidetailsAnnotations = {{ ctx.mobidetails | tojson }};
''',
}

T_CLINICAL = {
    "name": "pass mobidetailsAnnotations (clinical tab)",
    "marker": "mobidetailsAnnotations: mobidetailsAnnotations,",
    "anchor": r'''        genebeAnnotations: genebeAnnotations,
        oncokbAnnotations: oncokbAnnotations,
        cancervarAnnotations: cancervarAnnotations,
        enableReportSelect: true
''',
    "replacement": r'''        genebeAnnotations: genebeAnnotations,
        oncokbAnnotations: oncokbAnnotations,
        cancervarAnnotations: cancervarAnnotations,
        mobidetailsAnnotations: mobidetailsAnnotations,
        enableReportSelect: true
''',
}

T_FILTERED = {
    "name": "pass empty mobidetailsAnnotations (filtered tab)",
    "marker": "mobidetailsAnnotations: {},",
    "anchor": r'''          cancervarAnnotations: {},   // ditto for CancerVar
          enableReportSelect: false   // filtered tab is read-only for reporting
''',
    "replacement": r'''          cancervarAnnotations: {},   // ditto for CancerVar
          mobidetailsAnnotations: {}, // ditto for MobiDetails
          enableReportSelect: false   // filtered tab is read-only for reporting
''',
}

# ---------------------------------------------------------------------------
# assets/js/variant-browser.js
# ---------------------------------------------------------------------------
J_CONFIG = {
    "name": "accept config.mobidetailsAnnotations",
    "marker": "config.mobidetailsAnnotations",
    "anchor": r'''    const cancervarAnnotations = config.cancervarAnnotations || {};
    const enableReportSelect = !!config.enableReportSelect;
''',
    "replacement": r'''    const cancervarAnnotations = config.cancervarAnnotations || {};
    const mobidetailsAnnotations = config.mobidetailsAnnotations || {};
    const enableReportSelect = !!config.enableReportSelect;
''',
}

J_INSERT = {
    "name": "insert MobiDetails block in renderDetail",
    "marker": "mobidetailsBlock = renderMobidetailsBlock",
    "anchor": r'''      // OncoKB annotation block (only present when --annotate-oncokb was used at build time)
      let oncokbBlock = "";
      const oncoAnn = oncokbAnnotations[r._igvKey];
      if (oncoAnn) {
        oncokbBlock = renderOncokbBlock(oncoAnn);
      }

      return '<div class="vb-card-detail mt-3 pt-3 border-top">' +
               '<div class="row g-3">' + groups.join("") + "</div>" +
               genebeBlock +
               cancervarBlock +
               oncokbBlock +
''',
    "replacement": r'''      // OncoKB annotation block (only present when --annotate-oncokb was used at build time)
      let oncokbBlock = "";
      const oncoAnn = oncokbAnnotations[r._igvKey];
      if (oncoAnn) {
        oncokbBlock = renderOncokbBlock(oncoAnn);
      }

      // MobiDetails annotation block (only present when --annotate-mobidetails was used at build time)
      let mobidetailsBlock = "";
      const mdAnn = mobidetailsAnnotations[r._igvKey];
      if (mdAnn) {
        mobidetailsBlock = renderMobidetailsBlock(mdAnn);
      }

      return '<div class="vb-card-detail mt-3 pt-3 border-top">' +
               '<div class="row g-3">' + groups.join("") + "</div>" +
               genebeBlock +
               cancervarBlock +
               oncokbBlock +
               mobidetailsBlock +
''',
}

J_RENDER = {
    "name": "renderMobidetailsBlock() + helpers",
    "marker": "function renderMobidetailsBlock",
    "anchor": r'''    function renderGenebeBlock(ann) {
      const acmgPill = ann.acmg_classification
''',
    "replacement": r'''    // ---- MobiDetails: render the full variant_data object, every non-empty field ----
    function mdHumanizeKey(k) {
      return String(k)
        .replace(/_/g, " ")
        .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
        .replace(/^./, function (c) { return c.toUpperCase(); });
    }
    function mdIsEmpty(v) {
      if (v === null || v === undefined) return true;
      const s = String(v).trim();
      return s === "" || s === "None" || s === "." || s === "NA" ||
             s === "nan" || s === "Not performed" || s.indexOf("No match") === 0;
    }
    function mdFlatten(obj, prefix, out) {
      if (Array.isArray(obj)) {
        obj.forEach(function (item) { mdFlatten(item, prefix, out); });
      } else if (obj && typeof obj === "object") {
        Object.keys(obj).forEach(function (k) {
          const label = prefix ? prefix + " " + mdHumanizeKey(k) : mdHumanizeKey(k);
          mdFlatten(obj[k], label, out);
        });
      } else if (!mdIsEmpty(obj)) {
        out.push([prefix, obj]);
      }
    }
    // Friendlier headings for known groups; anything else falls back to a
    // humanised key, so fields MobiDetails adds later still render.
    const MD_GROUP_ORDER = [
      "gene", "nomenclatures", "VCF", "frequenciesDatabases", "overallPredictions",
      "missensePredictions", "splicingPredictions", "nonCodingPredictions",
      "miRNATargetSitesPredictions", "positions", "functionalStudies", "morfeedb",
      "sequences", "admin"
    ];
    const MD_GROUP_LABELS = {
      VCF: "VCF", frequenciesDatabases: "Frequencies & ClinVar",
      overallPredictions: "Overall predictions", missensePredictions: "Missense predictions",
      splicingPredictions: "Splicing predictions", nonCodingPredictions: "Non-coding predictions",
      miRNATargetSitesPredictions: "miRNA target sites", functionalStudies: "Functional studies",
      morfeedb: "MORFEE (uORF)", admin: "Record"
    };
    function renderMobidetailsBlock(annEntry) {
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
            'class="btn btn-sm btn-outline-primary mt-2">Open in MobiDetails \u2197</a>'
        : "";

      return '<div class="vb-md-block mt-3 pt-3 border-top">' +
               '<h6 class="text-uppercase text-muted small mb-2">MobiDetails (build-time)</h6>' +
               body + linkHtml +
             "</div>";
    }

    function renderGenebeBlock(ann) {
      const acmgPill = ann.acmg_classification
''',
}

TARGETS = [
    (PARSER, [P_CONST, P_HELPER, P_HIT, P_FILTER]),
    (TPL, [T_CONST, T_CLINICAL, T_FILTERED]),
    (JS, [J_CONFIG, J_INSERT, J_RENDER]),
]


def plan_file(path, edits):
    if not os.path.isfile(path):
        return None, ["[error] target not found: %s" % path], False, True
    with open(path, "r", encoding="utf-8") as fh:
        content = fh.read()
    statuses, changed, error = [], False, False
    for edit in edits:
        if edit["marker"] in content:
            statuses.append("[skip]  %s :: %s already present." % (path, edit["name"]))
            continue
        n = content.count(edit["anchor"])
        if n == 0:
            statuses.append("[error] %s :: anchor for '%s' not found." % (path, edit["name"]))
            error = True
            continue
        if n > 1:
            statuses.append("[error] %s :: anchor for '%s' found %d times (expected 1)." % (path, edit["name"], n))
            error = True
            continue
        content = content.replace(edit["anchor"], edit["replacement"], 1)
        changed = True
        statuses.append("[patch] %s :: %s staged." % (path, edit["name"]))
    return content, statuses, changed, error


def main():
    ap = argparse.ArgumentParser(description="Surface full MobiDetails annotation in the dashboard.")
    ap.add_argument("--root", default=None, help="Repository root (default: current working directory).")
    ap.add_argument("--apply", action="store_true", help="Write the changes (default is a dry-run preview).")
    args = ap.parse_args()

    root = args.root or os.getcwd()
    planned = []
    any_error = False
    any_change = False

    for rel, edits in TARGETS:
        path = os.path.join(root, rel)
        original = None
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as fh:
                original = fh.read()
        new_content, statuses, changed, error = plan_file(path, edits)
        for s in statuses:
            print(s)
        any_error = any_error or error
        any_change = any_change or changed
        planned.append((path, original, new_content, changed))

    if any_error:
        print("\n[abort] One or more anchors did not match. No files were written.")
        return 3
    if not any_change:
        print("\n[skip]  Nothing to do; all edits already present.")
        return 0

    if not args.apply:
        print("\n--- dry-run diffs (no files written) ---")
        for path, original, new_content, changed in planned:
            if not changed:
                continue
            diff = difflib.unified_diff(
                original.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=path + " (current)", tofile=path + " (patched)", n=2,
            )
            sys.stdout.writelines(diff)
        print("\n--- end diffs. Re-run with --apply to write. ---")
        return 0

    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    for path, original, new_content, changed in planned:
        if not changed:
            continue
        backup = "%s.bak_%s_%s" % (path, TAG, ts)
        shutil.copy2(path, backup)
        print("[backup] %s" % backup)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(new_content)
        print("[patch]  wrote %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
