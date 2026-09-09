#!/usr/bin/env python3
"""IGV_V2A -- dashboard-only half of the IGV block (D11, D12b, FLT3 display, COSMIC list format).

Run from the nf-core-tspipe repo root. Dry-run by default; --apply writes. All-or-nothing;
.bak_IGV_V2A_<timestamp> backups. Touches bin/dashboard_builder only (not in any task hash):
verify with the nocache DASHBOARD/REPORT_BUNDLE re-render, no resume.

templates/sample_report.html.j2
  - D11: each FLT3-ITD event card carries an "IGV ->" chip that jumps to the IGV-report row
    nearest the ITD position (within 300 bp; the FLT3 ensemble writes the ITD into the
    clinical set). "no IGV" when no row is within range.
  - Position (hg38) rendered as an integer (was the consensus mean, e.g. 28034088.0).
  - Domain falls back to the span derived from HGVSp when the tools left it empty.
parsers/flt3.py
  - domain_derived: 'p.585-610: JM-S -> beta1-sheet' from p.<start>_<end>dup, using the
    Rücker 2022 insertion-site regions (JM-B 572-578, JM-S 579-592, JM-Z 593-603,
    HR 604-609, beta1 610-615, NBL 616-623, beta2 624-630).
parsers/igv.py
  - D12b: the hash-router script injected into the IGV report also lets the Callers column
    wrap (', ' after each comma, white-space normal), so the variant table no longer
    scrolls sideways for a six-caller list.
assets/js/variant-browser.js
  - Reporting snapshot COSMIC list: 'COSV…, COSV…' instead of 'ID=COSV…;ID=COSV…'.
"""
import argparse
import os
import shutil
import sys
import time

TAG = "IGV_V2A"
STAMP = time.strftime("%Y%m%d_%H%M%S")
BUILDER = "bin/dashboard_builder"


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


# ---------------------------------------------------------------------------
# templates/sample_report.html.j2
# ---------------------------------------------------------------------------
TPL_HEADER_OLD = """                <strong>Event {{ loop.index }}</strong>
                &middot; status: <code>{{ r.status }}</code>
                &middot; {{ r.n_tools }} tools
"""
TPL_HEADER_NEW = """                <strong>Event {{ loop.index }}</strong>
                &middot; status: <code>{{ r.status }}</code>
                &middot; {{ r.n_tools }} tools
                {# IGV_V2A (D11): nearest IGV-report row to the ITD position, within 300 bp #}
                {% set ns = namespace(uid=none, best=301) %}
                {% for k, u in (ctx.igv.lookup if ctx.igv else {}).items() %}
                  {% set parts = k.split(':') %}
                  {% if parts[0] == 'chr13' and parts[1] and ((parts[1]|int) - (r.pos_hg38|int))|abs < ns.best %}
                    {% set ns.best = ((parts[1]|int) - (r.pos_hg38|int))|abs %}{% set ns.uid = u %}
                  {% endif %}
                {% endfor %}
                {% if ctx.files.igv_report and ns.uid is not none %}
                  <span class="vb-igv-chip vb-igv-chip-ok flt3-igv-chip ms-2" data-igv-uid="{{ ns.uid }}" title="Open the ITD locus in IGV">IGV &rarr;</span>
                {% elif ctx.files.igv_report %}
                  <span class="vb-igv-chip vb-igv-chip-missing ms-2" title="No variant row within 300 bp of the ITD in the IGV report">no IGV</span>
                {% endif %}
"""
TPL_POS_OLD = """                  <dt class="col-sm-3">Position (hg38)</dt>   <dd class="col-sm-9"><code>{{ r.pos_hg38 }}</code></dd>
"""
TPL_POS_NEW = """                  <dt class="col-sm-3">Position (hg38)</dt>   <dd class="col-sm-9"><code>chr13:{{ r.pos_hg38|int }}</code></dd>   {# IGV_V2A: integer, was the consensus mean #}
"""
TPL_DOMAIN_OLD = """                  <dt class="col-sm-3">Domain</dt>            <dd class="col-sm-9">{{ r.domain }}</dd>
"""
TPL_DOMAIN_NEW = """                  <dt class="col-sm-3">Domain</dt>            <dd class="col-sm-9">{{ r.domain or r.domain_derived or "—" }}</dd>   {# IGV_V2A: derived from HGVSp when the tools give none #}
"""
TPL_JS_ANCHOR = """    if (document.getElementById("clinical-browser")) {
      initVariantBrowser({
        containerId: "clinical-browser",
"""
TPL_JS_NEW = """    // IGV_V2A (D11): FLT3 tab chip -> IGV report row (same navigation as the card chips:
    // activate the IGV tab, then set the iframe src to "<report>#row_<uid>"; the router
    // injected into the report clicks the row).
    document.querySelectorAll(".flt3-igv-chip").forEach(function (chip) {
      chip.addEventListener("click", function () {
        const uid = chip.getAttribute("data-igv-uid");
        const frame = document.getElementById("igv-frame");
        if (uid === null || !frame) return;
        const trigger = document.querySelector('button[data-bs-target="#tab-igv"]');
        if (trigger && window.bootstrap && window.bootstrap.Tab) {
          window.bootstrap.Tab.getOrCreateInstance(trigger).show();
        }
        const baseSrc = frame.getAttribute("data-src") || (frame.src || "").replace(/#.*$/, "");
        if (!baseSrc) return;
        frame.src = baseSrc + "#row_" + uid;
        frame.removeAttribute("data-src");
      });
    });

""" + TPL_JS_ANCHOR


def patch_template(text):
    if TAG in text:
        return text, "skip"
    text = replace_once(text, TPL_HEADER_OLD, TPL_HEADER_NEW, "template FLT3 header")
    text = replace_once(text, TPL_POS_OLD, TPL_POS_NEW, "template FLT3 position")
    text = replace_once(text, TPL_DOMAIN_OLD, TPL_DOMAIN_NEW, "template FLT3 domain")
    text = replace_once(text, TPL_JS_ANCHOR, TPL_JS_NEW, "template FLT3 chip handler")
    return text, "patch"


# ---------------------------------------------------------------------------
# parsers/flt3.py
# ---------------------------------------------------------------------------
FLT3_OLD = """    df = df.fillna("")
    rows = df.to_dict(orient="records")
"""
FLT3_NEW = """    df = df.fillna("")
    rows = df.to_dict(orient="records")
    for r in rows:   # IGV_V2A: domain span from HGVSp when the tools left the field empty
        r["domain_derived"] = _domain_from_hgvsp(r.get("hgvsp", ""))
"""
FLT3_FUNC = '''

# IGV_V2A: FLT3 insertion-site regions (Rücker et al., Blood 2022), amino-acid coordinates on
# NP_004110. Residues above 630 fall in the rest of TKD1; below 572 is upstream of the JM domain.
_FLT3_REGIONS = [
    (572, 578, "JM-B"), (579, 592, "JM-S"), (593, 603, "JM-Z"), (604, 609, "HR"),
    (610, 615, "beta1-sheet"), (616, 623, "NBL"), (624, 630, "beta2-sheet"),
]


def _flt3_region(aa):
    for lo, hi, name in _FLT3_REGIONS:
        if lo <= aa <= hi:
            return name
    return "TKD1 (beyond beta2)" if aa > 630 else "upstream of JM"


def _domain_from_hgvsp(hgvsp):
    """'p.585_610dup' -> 'p.585-610: JM-S -> beta1-sheet'. Empty when HGVSp is not a
    residue-range duplication (the tools report other shapes for some events)."""
    import re
    m = re.search(r"p\\.(?:\\(?)(?:[A-Za-z]{0,3})(\\d+)_(?:[A-Za-z]{0,3})(\\d+)dup", str(hgvsp or ""))
    if not m:
        return ""
    a, b = int(m.group(1)), int(m.group(2))
    ra, rb = _flt3_region(a), _flt3_region(b)
    span = ra if ra == rb else "%s -> %s" % (ra, rb)
    return "p.%d-%d: %s" % (a, b, span)
'''


def patch_flt3(text):
    if TAG in text:
        return text, "skip"
    text = replace_once(text, FLT3_OLD, FLT3_NEW, "flt3 parser rows")
    text = replace_once(text, "\n\ndef parse(path):\n", FLT3_FUNC + "\n\ndef parse(path):\n", "flt3 parser helper")
    return text, "patch"


# ---------------------------------------------------------------------------
# parsers/igv.py -- router script addition
# ---------------------------------------------------------------------------
IGV_OLD = '''  window.addEventListener("hashchange", startPolling);
})();
</script>
"""
'''
IGV_NEW = '''  window.addEventListener("hashchange", startPolling);

  // IGV_V2A (D12b): let the Callers column wrap. igv-reports renders the caller list as one
  // comma-joined token with no break opportunity, so a six-caller list forces the whole
  // variant table to scroll sideways. Insert a space after each comma and allow wrapping.
  function fixCallers() {
    var headers = document.querySelectorAll("th");
    var idx = -1;
    for (var i = 0; i < headers.length; i++) {
      if ((headers[i].textContent || "").trim() === "Callers") { idx = i; break; }
    }
    if (idx < 0) return;
    var style = document.createElement("style");
    style.textContent = "td:nth-child(" + (idx + 1) + "), th:nth-child(" + (idx + 1) + ")" +
                        " { white-space: normal !important; max-width: 240px; overflow-wrap: anywhere; }";
    document.head.appendChild(style);
    var rows = document.querySelectorAll("tr[id^='row_']");
    for (var r = 0; r < rows.length; r++) {
      var cell = rows[r].children[idx];
      if (cell && cell.textContent.indexOf(",") !== -1 && cell.textContent.indexOf(", ") === -1) {
        cell.textContent = cell.textContent.replace(/,/g, ", ");
      }
    }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", fixCallers);
  } else {
    fixCallers();
  }
})();
</script>
"""
'''


def patch_igv_parser(text):
    if TAG in text:
        return text, "skip"
    return replace_once(text, IGV_OLD, IGV_NEW, "igv.py router"), "patch"


# ---------------------------------------------------------------------------
# variant-browser.js -- COSMIC list format
# ---------------------------------------------------------------------------
JS_OLD = '''      return String(existingVariation).split("&")
        .filter(function (s) { return /^COS[VMN]/.test(s); })
        .map(function (s) { return "ID=" + s; })
        .join(";");
'''
JS_NEW = '''      return String(existingVariation).split("&")
        .filter(function (s) { return /^COS[VMN]/.test(s); })
        .join(", ");   // IGV_V2A: plain 'COSV…, COSV…' (was 'ID=COSV…;ID=COSV…')
'''


def patch_js(text):
    if TAG in text:
        return text, "skip"
    return replace_once(text, JS_OLD, JS_NEW, "js extractCosmicIds"), "patch"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    ap.add_argument("--repo", default=".", help="repo root (default: cwd)")
    args = ap.parse_args()
    os.chdir(args.repo)
    targets = [
        (BUILDER + "/templates/sample_report.html.j2", patch_template),
        (BUILDER + "/parsers/flt3.py", patch_flt3),
        (BUILDER + "/parsers/igv.py", patch_igv_parser),
        (BUILDER + "/assets/js/variant-browser.js", patch_js),
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
