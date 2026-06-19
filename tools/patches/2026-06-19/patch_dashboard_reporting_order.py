#!/usr/bin/env python3
"""Add up/down reordering of included variants in the Reporting tab.

The Reporting tab renders included variants in selection (insertion) order. This
patch adds a compact up/down control in the row-number cell so the reviewer can
arrange the reported variants in any order. The order is stored by rearranging
the selection array in localStorage, so it flows automatically into the TSV /
clipboard export and into the shared triage bundles -- no extra plumbing.

Scope (first pass): the included-variants list only. Excluded variants and CNV
report cards are unchanged.

Six anchored edits across three files:

  bin/dashboard_builder/assets/js/variant-browser.js
    1. add a move(kind, id, dir) method to the tspipeReporting store
    2. export move() in the store's public API

  bin/dashboard_builder/templates/sample_report.html.j2
    3. widen the reporting-table row-number column (32px -> 72px)
    4. render up/down buttons in each included-variant row (disabled at the ends)
    5. wire a click handler that calls store.move(); the existing onChange ->
       render hook repaints the table with refreshed numbers and disabled states

  bin/dashboard_builder/assets/css/dashboard.css
    6. compact styling for the .reporting-move-group buttons

Idempotent and anchor-based. Two-phase: every edit across all files is validated
first; if any anchor is missing or ambiguous, nothing is written. Dry-run by
default; pass --apply to write. A timestamped backup (.bak_reportorder_<UTC>) is
written per changed file. Python 3.6-safe.

Run from the repository root:
    python3 patch_dashboard_reporting_order.py            # dry-run (per-file diffs)
    python3 patch_dashboard_reporting_order.py --apply     # write
"""

import argparse
import datetime
import difflib
import os
import shutil
import sys

TAG = "reportorder"

JS = os.path.join("bin", "dashboard_builder", "assets", "js", "variant-browser.js")
TPL = os.path.join("bin", "dashboard_builder", "templates", "sample_report.html.j2")
CSS = os.path.join("bin", "dashboard_builder", "assets", "css", "dashboard.css")

# ---------------------------------------------------------------------------
# variant-browser.js
# ---------------------------------------------------------------------------
JS_EDIT_MOVE = {
    "name": "store.move() method",
    "marker": "function move(kind, id, dir)",
    "anchor": r'''      if (decision !== "exclude") setExcludeReason(id, "");
      save(items);
    }
''',
    "replacement": r'''      if (decision !== "exclude") setExcludeReason(id, "");
      save(items);
    }

    // Reorder an item within its display group (same kind and same decision).
    // dir = -1 moves it one position earlier, +1 one later. Items of other
    // kinds or other decisions are skipped, so reordering the included
    // variants never disturbs excluded variants or CNV selections. The new
    // order persists in the selection array, so the TSV export and shared
    // triage bundles follow it automatically.
    function move(kind, id, dir) {
      if (dir !== 1 && dir !== -1) return;
      const items = load();
      const ti = items.findIndex(function (it) { return it.kind === kind && it.id === id; });
      if (ti < 0) return;
      const decision = items[ti].decision || "include";
      const group = [];
      for (let i = 0; i < items.length; i++) {
        if (items[i].kind === kind && (items[i].decision || "include") === decision) group.push(i);
      }
      const p = group.indexOf(ti);
      const q = p + dir;
      if (q < 0 || q >= group.length) return;   // already at an end
      const a = group[p], b = group[q];
      const tmp = items[a];
      items[a] = items[b];
      items[b] = tmp;
      save(items);                              // fires onChange -> render
    }
''',
}

JS_EDIT_EXPORT = {
    "name": "store.move() export",
    "marker": "move: move,",
    "anchor": r'''      getDecision: getDecision,
      setDecision: setDecision,
      getExcludeReason: getExcludeReason,
''',
    "replacement": r'''      getDecision: getDecision,
      setDecision: setDecision,
      move: move,
      getExcludeReason: getExcludeReason,
''',
}

# ---------------------------------------------------------------------------
# sample_report.html.j2
# ---------------------------------------------------------------------------
TPL_EDIT_HEADER = {
    "name": "reporting-table row-number column width",
    "marker": r'''            <table class="table table-sm table-hover align-middle" id="reporting-table">
              <thead class="table-light">
                <tr>
                  <th scope="col" style="width:72px"></th>
''',
    "anchor": r'''            <table class="table table-sm table-hover align-middle" id="reporting-table">
              <thead class="table-light">
                <tr>
                  <th scope="col" style="width:32px"></th>
''',
    "replacement": r'''            <table class="table table-sm table-hover align-middle" id="reporting-table">
              <thead class="table-light">
                <tr>
                  <th scope="col" style="width:72px"></th>
''',
}

TPL_EDIT_ROWBTNS = {
    "name": "up/down buttons in included-variant rows",
    "marker": "reporting-move-up",
    "anchor": r'''      const html = variants.map(function (it, idx) {
        const s = it.snapshot || {};
        const tier = escapeHtml(window.tspipeReporting.getTier(it.id) || "");
        const vaf = s.vaf ? Number(s.vaf).toFixed(1) : "";
        return '<tr data-vb-key="' + escapeHtml(it.id) + '">' +
                 '<td class="text-muted small">' + (idx + 1) + '</td>' +
''',
    "replacement": r'''      const html = variants.map(function (it, idx) {
        const s = it.snapshot || {};
        const tier = escapeHtml(window.tspipeReporting.getTier(it.id) || "");
        const vaf = s.vaf ? Number(s.vaf).toFixed(1) : "";
        const upDisabled = idx === 0 ? " disabled" : "";
        const downDisabled = idx === variants.length - 1 ? " disabled" : "";
        return '<tr data-vb-key="' + escapeHtml(it.id) + '">' +
                 '<td class="text-muted small">' +
                   '<div class="d-flex align-items-center gap-1">' +
                     '<span>' + (idx + 1) + '</span>' +
                     '<div class="btn-group-vertical reporting-move-group" role="group" aria-label="Reorder variant">' +
                       '<button type="button" class="btn btn-outline-secondary reporting-move-up" data-vb-key="' + escapeHtml(it.id) + '" title="Move up"' + upDisabled + '>\u25B2</button>' +
                       '<button type="button" class="btn btn-outline-secondary reporting-move-down" data-vb-key="' + escapeHtml(it.id) + '" title="Move down"' + downDisabled + '>\u25BC</button>' +
                     '</div>' +
                   '</div>' +
                 '</td>' +
''',
}

TPL_EDIT_HANDLER = {
    "name": "row reorder click handler",
    "marker": 'tspipeReporting.move("variant"',
    "anchor": r'''    // ACMG/AMP Tier inline edits -- persist on input
    tbody.addEventListener("input", function (ev) {
      const inp = ev.target.closest(".reporting-tier-input");
      if (!inp) return;
      const key = inp.getAttribute("data-vb-key");
      window.tspipeReporting.setTier(key, inp.value.trim());
    });
''',
    "replacement": r'''    // ACMG/AMP Tier inline edits -- persist on input
    tbody.addEventListener("input", function (ev) {
      const inp = ev.target.closest(".reporting-tier-input");
      if (!inp) return;
      const key = inp.getAttribute("data-vb-key");
      window.tspipeReporting.setTier(key, inp.value.trim());
    });

    // Up/down reorder of included variants. Mutating the store fires the
    // onChange -> render hook, which repaints the table with refreshed row
    // numbers and disabled states. The order persists for the TSV export and
    // for shared triage bundles. Disabled buttons do not emit click events.
    tbody.addEventListener("click", function (ev) {
      const up = ev.target.closest(".reporting-move-up");
      const down = ev.target.closest(".reporting-move-down");
      if (!up && !down) return;
      const key = (up || down).getAttribute("data-vb-key");
      window.tspipeReporting.move("variant", key, up ? -1 : 1);
    });
''',
}

# ---------------------------------------------------------------------------
# dashboard.css
# ---------------------------------------------------------------------------
CSS_EDIT = {
    "name": "reporting-move-group styles",
    "marker": ".reporting-move-group",
    "anchor": r'''.vb-ext-links .btn { font-size: 0.85rem; }
''',
    "replacement": r'''.vb-ext-links .btn { font-size: 0.85rem; }

/* Reporting tab: compact up/down reorder control in the row-number cell. */
.reporting-move-group { gap: 1px; }
.reporting-move-group .btn {
  padding: 0 0.3rem;
  font-size: 0.6rem;
  line-height: 1.25;
  border-radius: 0.2rem;
}
.reporting-move-group .btn:disabled { opacity: 0.35; }
''',
}

TARGETS = [
    (JS, [JS_EDIT_MOVE, JS_EDIT_EXPORT]),
    (TPL, [TPL_EDIT_HEADER, TPL_EDIT_ROWBTNS, TPL_EDIT_HANDLER]),
    (CSS, [CSS_EDIT]),
]


def plan_file(path, edits):
    """Return (new_content, statuses, changed, error). Does not write."""
    if not os.path.isfile(path):
        return None, ["[error] target not found: %s" % path], False, True
    with open(path, "r", encoding="utf-8") as fh:
        content = fh.read()
    statuses = []
    changed = False
    error = False
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
    ap = argparse.ArgumentParser(description="Add up/down reordering of included variants in the Reporting tab.")
    ap.add_argument("--root", default=None, help="Repository root (default: current working directory).")
    ap.add_argument("--apply", action="store_true", help="Write the changes (default is a dry-run preview).")
    args = ap.parse_args()

    root = args.root or os.getcwd()

    planned = []     # (path, original, new_content, changed)
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
        if error:
            any_error = True
        if changed:
            any_change = True
        planned.append((path, original, new_content, changed))

    if any_error:
        print("\n[abort] One or more anchors did not match. No files were written.")
        print("        Re-pull the repo or check whether these files were edited since this patch was built.")
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
                fromfile=path + " (current)",
                tofile=path + " (patched)",
                n=2,
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
