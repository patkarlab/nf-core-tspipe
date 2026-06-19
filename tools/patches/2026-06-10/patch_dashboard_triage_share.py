#!/usr/bin/env python3
"""
patch_dashboard_triage_share.py

Problem: dashboard triage decisions (include/exclude, exclude reasons, AMP/ASCO/CAP
tier, CNV captions) are stored in browser localStorage, which is per-machine. A
resident's edits on their computer never appear on anyone else's.

Fix (per-reviewer file export/import, no server):
  - JS (variant-browser.js): add exportAll() and importAll() INSIDE the
    tspipeReporting module, where the four KEY_PREFIX constants are in scope, so
    the bundle reads/writes the exact same keys the rest of the module uses.
  - Template (sample_report.html.j2): add "Save my decisions" and "Load
    decisions" buttons on the Reporting tab, plus handlers that download a
    <sample>.triage.<reviewer>.json and import one back. Reviewer name is
    prompted once and remembered. Import refuses a file whose sample id does not
    match the current report (clinical safety guard). Imported decisions are an
    editable starting point: edit, then save under your own name.

file:// cannot write to disk, so "Save" is a browser download (drop it on the
shared drive yourself) and "Load" is an explicit file picker. No auto-discovery.

Conventions: dry-run default; --apply writes; .bak_<tag>_<timestamp> per file;
idempotent via MARKER; status [skip]/[backup]/[patch]/[error]. Touches two files.
"""

import argparse
import datetime
import os
import sys

JS = "/goast/hemat_data/nf-core-tspipe/bin/dashboard_builder/assets/js/variant-browser.js"
TPL = "/goast/hemat_data/nf-core-tspipe/bin/dashboard_builder/templates/sample_report.html.j2"
MARKER = "triage-share export/import"

# ---------------------------------------------------------------------------
# JS edit: insert exportAll/importAll before the module's `return {` public API.
# Anchor on the exact return-object opening seen in the file.
# ---------------------------------------------------------------------------
JS_ANCHOR = "    return {\n      setSample: setSample,\n"

JS_BLOCK = '''    // [%s]
    // Gather every stored key for this sample across all four namespaces and
    // bundle them for export. Reads localStorage directly so nothing is missed.
    function exportAll(reviewer) {
      if (!sampleKey || !HAS_STORAGE) return null;
      var bundle = {
        schema: 1,
        sample: sampleKey,
        reviewer: reviewer || "",
        savedAt: new Date().toISOString(),
        selection: load(),
        excludeReasons: {},
        tiers: {},
        cnvCaptions: {}
      };
      var prefixes = [
        [EXCLUDE_REASON_KEY_PREFIX, bundle.excludeReasons],
        [TIER_KEY_PREFIX, bundle.tiers],
        [CNV_CAPTION_KEY_PREFIX, bundle.cnvCaptions]
      ];
      try {
        for (var i = 0; i < window.localStorage.length; i++) {
          var k = window.localStorage.key(i);
          for (var p = 0; p < prefixes.length; p++) {
            var pre = prefixes[p][0] + sampleKey + ":";
            if (k.indexOf(pre) === 0) {
              var id = k.slice(pre.length);
              prefixes[p][1][id] = window.localStorage.getItem(k);
            }
          }
        }
      } catch (e) { /* storage iteration failed; return what we have */ }
      return bundle;
    }

    // Restore a bundle into localStorage for the CURRENT sample. Refuses a
    // bundle whose sample id does not match (clinical safety). Uses the existing
    // setters so listeners fire and the Reporting table repaints. Imported state
    // is an editable starting point; the reviewer saves under their own name.
    function importAll(bundle) {
      if (!sampleKey || !HAS_STORAGE) return { ok: false, reason: "no-storage" };
      if (!bundle || typeof bundle !== "object") return { ok: false, reason: "bad-file" };
      if (bundle.sample && bundle.sample !== sampleKey) {
        return { ok: false, reason: "sample-mismatch", got: bundle.sample, want: sampleKey };
      }
      try {
        save(Array.isArray(bundle.selection) ? bundle.selection : []);
        var er = bundle.excludeReasons || {};
        Object.keys(er).forEach(function (id) { setExcludeReason(id, er[id]); });
        var ti = bundle.tiers || {};
        Object.keys(ti).forEach(function (id) { setTier(id, ti[id]); });
        var cc = bundle.cnvCaptions || {};
        Object.keys(cc).forEach(function (id) { setCnvCaption(id, cc[id]); });
      } catch (e) {
        return { ok: false, reason: "write-failed" };
      }
      return { ok: true, reviewer: bundle.reviewer || "", savedAt: bundle.savedAt || "" };
    }

''' % MARKER

JS_API_ADD = ("      setSample: setSample,\n"
              "      exportAll: exportAll,        // [%s]\n"
              "      importAll: importAll,        // [%s]\n" % (MARKER, MARKER))
JS_API_ANCHOR = "      setSample: setSample,\n"

# ---------------------------------------------------------------------------
# Template edit: add the two buttons + handlers. Anchor on the setSample call,
# which sits inside the report's <script> and runs after tspipeReporting exists.
# We append a self-contained IIFE that injects the toolbar into the Reporting
# tab pane and wires the handlers.
# ---------------------------------------------------------------------------
TPL_ANCHOR = "    if (window.tspipeReporting) {\n      window.tspipeReporting.setSample({{ ctx.sample | tojson }});\n"

TPL_BLOCK = '''    if (window.tspipeReporting) {
      window.tspipeReporting.setSample({{ ctx.sample | tojson }});

      /* [%s] Per-reviewer decision sharing across machines.
         Save downloads <sample>.triage.<reviewer>.json; Load imports one back.
         Decisions live in localStorage (per-machine), so this is how a
         resident's triage reaches another computer: save, drop on the shared
         drive, the next person loads it. Imported state is editable; saving
         always writes under the loader's own name. */
      (function () {
        var SAMPLE = {{ ctx.sample | tojson }};
        var NAME_KEY = "tspipe_reviewer_name";

        function reviewerName(forcePrompt) {
          var n = "";
          try { n = window.localStorage.getItem(NAME_KEY) || ""; } catch (e) {}
          if (!n || forcePrompt) {
            n = window.prompt("Your name (used to label your decisions file):", n || "");
            if (n) { try { window.localStorage.setItem(NAME_KEY, n); } catch (e) {} }
          }
          return n || "";
        }

        function safe(s) { return String(s || "").replace(/[^A-Za-z0-9._-]+/g, "_"); }

        function doSave() {
          var name = reviewerName(false);
          if (!name) return;
          var bundle = window.tspipeReporting.exportAll(name);
          if (!bundle) { alert("Nothing to save yet, or storage is unavailable."); return; }
          var blob = new Blob([JSON.stringify(bundle, null, 2)], { type: "application/json" });
          var url = URL.createObjectURL(blob);
          var a = document.createElement("a");
          a.href = url;
          a.download = safe(SAMPLE) + ".triage." + safe(name) + ".json";
          document.body.appendChild(a); a.click();
          document.body.removeChild(a); URL.revokeObjectURL(url);
          setBanner("Saved decisions as " + a.download + " - move it to the shared drive.");
        }

        function doLoad(file) {
          var reader = new FileReader();
          reader.onload = function () {
            var bundle;
            try { bundle = JSON.parse(reader.result); }
            catch (e) { alert("Could not read that file (not valid JSON)."); return; }
            var res = window.tspipeReporting.importAll(bundle);
            if (!res.ok) {
              if (res.reason === "sample-mismatch") {
                alert("That file is for sample '" + res.got + "', but this report is '" +
                      res.want + "'. Not loaded.");
              } else {
                alert("Could not load that file (" + res.reason + ").");
              }
              return;
            }
            setBanner("Loaded decisions from " + (res.reviewer || "unknown") +
                      (res.savedAt ? " (saved " + res.savedAt.slice(0, 10) + ")" : "") +
                      " - your edits will save under your own name.");
            /* repaint the Reporting table if a renderer hook exists */
            if (typeof window.tspipeRenderReporting === "function") {
              try { window.tspipeRenderReporting(); } catch (e) {}
            } else {
              window.tspipeReporting.onChange && window.tspipeReporting.load();
            }
          };
          reader.readAsText(file);
        }

        var bannerEl = null;
        function setBanner(msg) {
          if (!bannerEl) return;
          bannerEl.textContent = msg;
          bannerEl.style.display = msg ? "" : "none";
        }

        function mount() {
          var pane = document.getElementById("tab-reporting") ||
                     document.querySelector('[id*="reporting"]');
          if (!pane) return;
          var bar = document.createElement("div");
          bar.className = "d-flex align-items-center gap-2 mb-2 flex-wrap";
          var save = document.createElement("button");
          save.type = "button";
          save.className = "btn btn-sm btn-outline-primary";
          save.textContent = "Save my decisions";
          save.addEventListener("click", doSave);
          var load = document.createElement("button");
          load.type = "button";
          load.className = "btn btn-sm btn-outline-secondary";
          load.textContent = "Load decisions";
          var picker = document.createElement("input");
          picker.type = "file"; picker.accept = ".json"; picker.style.display = "none";
          picker.addEventListener("change", function () {
            if (picker.files && picker.files[0]) doLoad(picker.files[0]);
            picker.value = "";
          });
          load.addEventListener("click", function () { picker.click(); });
          var changeName = document.createElement("button");
          changeName.type = "button";
          changeName.className = "btn btn-sm btn-link text-muted p-0 ms-1";
          changeName.textContent = "(change name)";
          changeName.addEventListener("click", function () { reviewerName(true); });
          bannerEl = document.createElement("div");
          bannerEl.className = "text-muted small w-100";
          bannerEl.style.display = "none";
          bar.appendChild(save); bar.appendChild(load);
          bar.appendChild(picker); bar.appendChild(changeName);
          bar.appendChild(bannerEl);
          pane.insertBefore(bar, pane.firstChild);
        }

        if (document.readyState === "loading") {
          document.addEventListener("DOMContentLoaded", mount);
        } else {
          mount();
        }
      })();
''' % MARKER


def status(tag, msg):
    sys.stdout.write("[%s] %s\n" % (tag, msg))


def patch_file(path, edits, apply):
    """edits: list of (old, new). Returns (changed, problems)."""
    if not os.path.isfile(path):
        return False, ["not found: %s" % path]
    with open(path) as f:
        src = f.read()
    if MARKER in src:
        status("skip", "%s already patched (MARKER present)" % os.path.basename(path))
        return False, []
    problems = []
    for old, _new in edits:
        if old not in src:
            problems.append("anchor not found in %s: %r" % (os.path.basename(path), old[:60]))
    if problems:
        return False, problems
    patched = src
    for old, new in edits:
        patched = patched.replace(old, new, 1)
    if patched == src:
        return False, ["no change produced in %s" % os.path.basename(path)]
    if not apply:
        status("patch", "DRY-RUN ok: %s would be edited (%d insertion(s))"
               % (os.path.basename(path), len(edits)))
        return True, []
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = "%s.bak_triageshare_%s" % (path, ts)
    with open(backup, "w") as f:
        f.write(src)
    status("backup", backup)
    with open(path, "w") as f:
        f.write(patched)
    status("patch", "applied to %s" % os.path.basename(path))
    return True, []


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="Write changes (default: dry-run).")
    ap.add_argument("--js", default=JS)
    ap.add_argument("--tpl", default=TPL)
    args = ap.parse_args()

    # JS: two edits - insert the block before the return-object, and add the two
    # API properties. Order matters: insert block first (its anchor is the full
    # return-object head), then extend the API list (anchor is the first line).
    js_edits = [
        (JS_ANCHOR, JS_BLOCK + JS_ANCHOR),
        (JS_API_ANCHOR, JS_API_ADD),
    ]
    tpl_edits = [
        (TPL_ANCHOR, TPL_BLOCK),
    ]

    rc = 0
    for path, edits in [(args.js, js_edits), (args.tpl, tpl_edits)]:
        changed, problems = patch_file(path, edits, args.apply)
        for p in problems:
            status("error", p)
        if problems:
            rc = 2
    if rc == 0 and args.apply:
        status("patch", "done. Hard-refresh a sample report and check the Reporting tab.")
    elif rc == 0:
        status("patch", "re-run with --apply to write both files.")
    else:
        status("error", "anchors did not match; NO files changed. Paste current bytes to re-sync.")
    return rc


if __name__ == "__main__":
    sys.exit(main())
