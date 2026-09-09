#!/usr/bin/env python3
"""DASH_LAYOUT_V1 -- dashboard layout fixes, CAVA on every card, MNV note (D1, D4, D5, D12, D17a, new).

Run from the nf-core-tspipe repo root. Dry-run by default; --apply writes. All edits are
computed first and written only if every anchor matches (all-or-nothing); each file gets a
.bak_DASH_LAYOUT_V1_<timestamp> backup. Touches bin/dashboard_builder only (not in any task
hash): verify with the nocache DASHBOARD/REPORT_BUNDLE re-render, no resume.

variant-browser.js
  - CAVA line on every compact card (clinical and filtered browsers): transcript, HGVSc,
    HGVSp (CSN on hover); "CAVA: no annotation" when CAVA produced nothing.
  - MNV badge on the compact card when MNV_Note is set; MNV_Note added to the detail view.
  - Reporting snapshot uses bestHGVSp/bestHGVSc (VariantValidator -> CAVA -> VEP), closing
    the D3b gap where the Reporting page still skipped CAVA.
  - Callers in the detail view rendered with a space after each comma so the list wraps.
dashboard.css
  - D1: sidebar pinned to the viewport (align-self: flex-start; it was stretched to the
    content height by the flex row, so position: sticky had nothing to stick within).
  - D5/D12: long HGVS strings, COSMIC lists and caller lists wrap inside their cell; the
    card body gets min-width: 0 so a flex child can shrink.
  - Reporting tables: fixed column layout so the page never widens; every cell wraps.
sample_report.html.j2
  - D4: the tier field is a textarea that grows with its text (was a 16-character input);
    Enter commits, newlines are collapsed so the copied TSV stays one row per variant.
  - D5: column widths on the Reporting table header; COSMIC cell wraps, full list as title.
build.py
  - BUILDER_VERSION 0.5.0-triage+exon -> 0.5.1-layout+cava; CHANGELOG_v051.md added.
"""
import argparse
import os
import shutil
import sys
import time

TAG = "DASH_LAYOUT_V1"
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
# variant-browser.js
# ---------------------------------------------------------------------------
def patch_js(text):
    if TAG in text:
        return text, "skip"
    # 1. MNV_Note in the detail view (Annotation group)
    text = replace_once(
        text,
        '      ["Canonical", "Canonical"],\n',
        '      ["Canonical", "Canonical"],\n'
        '      ["MNV_Note", "MNV note"],   // DASH_LAYOUT_V1 (D17a)\n',
        "js detail MNV_Note")
    # 2. compact card: MNV badge + CAVA line
    text = replace_once(
        text,
        '      // IGV chip on the compact view — visible without expanding the card.\n',
        '      // DASH_LAYOUT_V1 (D17a): MNV badge when MNV_MERGE re-joined or tagged this record.\n'
        '      let mnvBadge = "";\n'
        '      if (r.MNV_Note && r.MNV_Note !== "-1") {\n'
        '        mnvBadge = \'<span class="badge bg-info text-dark" title="\' + escapeHtml(r.MNV_Note) + \'">MNV</span>\';\n'
        '      }\n'
        '      // DASH_LAYOUT_V1: CAVA (MANE 1.5 RefSeq) shown on every card, not only when it differs.\n'
        '      const cavaTx = (r.CAVA_Transcript && r.CAVA_Transcript !== "-1") ? r.CAVA_Transcript : "";\n'
        '      const cavaC  = (r.CAVA_HGVSc && r.CAVA_HGVSc !== "-1") ? r.CAVA_HGVSc : "";\n'
        '      const cavaP  = (r.CAVA_HGVSp && r.CAVA_HGVSp !== "-1") ? r.CAVA_HGVSp : "";\n'
        '      let cavaLine;\n'
        '      if (cavaTx || cavaC || cavaP || cavaCsn) {\n'
        '        cavaLine = \'<span class="text-muted" title="CAVA 2.0.15, MANE 1.5 RefSeq catalog\' +\n'
        '                   (cavaCsn ? \'; CSN \' + escapeHtml(cavaCsn) : "") + \'">CAVA</span> \' +\n'
        '                   escapeHtml([cavaTx, cavaC, cavaP].filter(Boolean).join(" "));\n'
        '      } else {\n'
        '        cavaLine = \'<span class="text-muted">CAVA: no annotation</span>\';\n'
        '      }\n'
        '\n'
        '      // IGV chip on the compact view — visible without expanding the card.\n',
        "js compact card CAVA/MNV vars")
    text = replace_once(
        text,
        '              cavaBadges +   // CAVA_V1c\n',
        '              cavaBadges +   // CAVA_V1c\n'
        '              mnvBadge +     // DASH_LAYOUT_V1 (D17a)\n',
        "js compact badges")
    text = replace_once(
        text,
        '              escapeHtml(r.Ref || "") + "&gt;" + escapeHtml(r.Alt || "") +\n'
        '            "</div>" +\n'
        '          "</div>" +\n',
        '              escapeHtml(r.Ref || "") + "&gt;" + escapeHtml(r.Alt || "") +\n'
        '            "</div>" +\n'
        '            \'<div class="small font-monospace vb-cava-line">\' + cavaLine + "</div>" +   // DASH_LAYOUT_V1\n'
        '          "</div>" +\n',
        "js compact CAVA line")
    # 3. Reporting snapshot honours the D3b preference order
    text = replace_once(
        text,
        '              hgvsP:    row.VV_HGVSp || row.HGVSp || "",\n'
        '              hgvsC:    row.VV_HGVSc || row.HGVSc || "",\n',
        '              hgvsP:    bestHGVSp(row),   // DASH_LAYOUT_V1: VV -> CAVA -> VEP, as on the cards (D3b)\n'
        '              hgvsC:    bestHGVSc(row),\n',
        "js snapshot bestHGVS")
    # 4. detail view: callers wrap
    text = replace_once(
        text,
        '            \'">\' + emptyVal(v) + "</dd>"\n',
        '            \'">\' + (field === "Callers" ? emptyVal(v).replace(/,/g, ", ") : emptyVal(v)) + "</dd>"   // DASH_LAYOUT_V1 (D12)\n',
        "js detail callers")
    return text, "patch"


# ---------------------------------------------------------------------------
# dashboard.css
# ---------------------------------------------------------------------------
CSS_BLOCK = """
/* MARKER DASH_LAYOUT_V1 (D1): the sidebar is a flex child of the page row and was stretched to
   the full content height (align-items: stretch), so position: sticky had no room to move.
   Pin it to the viewport instead. */
.tspipe-sidebar {
  align-self: flex-start;
  height: 100vh;
  overflow-y: auto;
}

/* DASH_LAYOUT_V1 (D5, D12): long insertions, COSMIC lists and caller lists must wrap inside
   their cell instead of widening the page. A flex child defaults to min-width: auto, which
   stops it shrinking below its content width. */
.vb-card-compact > .flex-grow-1 { min-width: 0; }
.vb-card-compact .font-monospace,
.vb-card-detail dd { overflow-wrap: anywhere; word-break: break-word; }
.vb-cava-line { color: #495057; margin-top: 0.15rem; }

#reporting-table, #reporting-excluded-table { table-layout: fixed; width: 100%; }
#reporting-table td, #reporting-excluded-table td { overflow-wrap: anywhere; vertical-align: top; }
#reporting-table td.reporting-cosmic { overflow-wrap: anywhere; }   /* full list wraps; also in the tooltip */
.reporting-tier-input {            /* D4: grows with its text (see autosizeTier in the template) */
  resize: none;
  overflow: hidden;
  min-height: calc(1.5em + 0.5rem + 2px);
  line-height: 1.4;
}
"""


def patch_css(text):
    if TAG in text:
        return text, "skip"
    return replace_once(text, "\n.tspipe-main {\n", CSS_BLOCK + "\n.tspipe-main {\n", "css tspipe-main anchor"), "patch"


# ---------------------------------------------------------------------------
# sample_report.html.j2
# ---------------------------------------------------------------------------
THEAD_OLD = """                  <th scope="col" style="width:72px"></th>
                  <th scope="col">Gene</th>
                  <th scope="col">Genomic variant</th>
                  <th scope="col">Protein variant</th>
                  <th scope="col">Transcript Variant</th>
                  <th scope="col">Exon</th>
                  <th scope="col">COSMIC database reference</th>
                  <th scope="col">VAF (%)</th>
                  <th scope="col" style="width:160px">AMP/ASCO/CAP Tier (somatic)</th>
"""
THEAD_NEW = """                  {# DASH_LAYOUT_V1 (D4, D5): fixed column widths so the page never widens; every cell wraps #}
                  <th scope="col" style="width:72px"></th>
                  <th scope="col" style="width:90px">Gene</th>
                  <th scope="col" style="width:20%">Genomic variant</th>
                  <th scope="col" style="width:17%">Protein variant</th>
                  <th scope="col" style="width:17%">Transcript Variant</th>
                  <th scope="col" style="width:60px">Exon</th>
                  <th scope="col" style="width:16%">COSMIC database reference</th>
                  <th scope="col" style="width:64px">VAF (%)</th>
                  <th scope="col" style="width:170px">AMP/ASCO/CAP Tier (somatic)</th>
"""


def patch_template(text):
    if TAG in text:
        return text, "skip"
    text = replace_once(text, THEAD_OLD, THEAD_NEW, "template reporting thead")
    text = replace_once(
        text,
        """    // ACMG/AMP Tier inline edits -- persist on input
    tbody.addEventListener("input", function (ev) {
      const inp = ev.target.closest(".reporting-tier-input");
      if (!inp) return;
      const key = inp.getAttribute("data-vb-key");
      window.tspipeReporting.setTier(key, inp.value.trim());
    });
""",
        """    // ACMG/AMP Tier inline edits -- persist on input
    // DASH_LAYOUT_V1 (D4): the tier field is a textarea that grows with its text (wraps onto
    // further lines instead of scrolling out of view); Enter commits instead of inserting a
    // newline, and any newline is collapsed so the copied TSV stays one row per variant.
    function autosizeTier(el) {
      el.style.height = "auto";
      el.style.height = (el.scrollHeight + 2) + "px";
    }
    function autosizeAllTiers() {
      tbody.querySelectorAll(".reporting-tier-input").forEach(autosizeTier);
    }
    tbody.addEventListener("input", function (ev) {
      const inp = ev.target.closest(".reporting-tier-input");
      if (!inp) return;
      autosizeTier(inp);
      const key = inp.getAttribute("data-vb-key");
      window.tspipeReporting.setTier(key, inp.value.replace(/\\s+/g, " ").trim());
    });
    tbody.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter" && ev.target.closest(".reporting-tier-input")) {
        ev.preventDefault();
        ev.target.blur();
      }
    });
""",
        "template tier handler")
    text = replace_once(
        text,
        """      }).join("");
      tbody.innerHTML = html;
    }

    function renderExcluded(excluded) {""",
        """      }).join("");
      tbody.innerHTML = html;
      autosizeAllTiers();   // DASH_LAYOUT_V1 (D4)
    }

    function renderExcluded(excluded) {""",
        "template renderVariants autosize")
    text = replace_once(
        text,
        """                 '<td class="font-monospace small">' + escapeHtml(s.cosmic) + '</td>' +
                 '<td>' + escapeHtml(vaf) + '</td>' +
                 '<td><input type="text" class="form-control form-control-sm reporting-tier-input" ' +
                       'data-vb-key="' + escapeHtml(it.id) + '" ' +
                       'placeholder="-" value="' + tier + '" maxlength="16"></td>' +
""",
        """                 '<td class="font-monospace small reporting-cosmic" title="' + escapeHtml(s.cosmic) + '">' + escapeHtml(s.cosmic) + '</td>' +   // DASH_LAYOUT_V1 (D5)
                 '<td>' + escapeHtml(vaf) + '</td>' +
                 '<td><textarea rows="1" class="form-control form-control-sm reporting-tier-input" ' +   // DASH_LAYOUT_V1 (D4): grows with the text
                       'data-vb-key="' + escapeHtml(it.id) + '" ' +
                       'placeholder="-">' + tier + '</textarea></td>' +
""",
        "template reporting row")
    return text, "patch"


# ---------------------------------------------------------------------------
# build.py version + changelog
# ---------------------------------------------------------------------------
CHANGELOG = """# dashboard_builder v0.5.1 — layout fixes, CAVA on every card (DASH_LAYOUT_V1, 2026-09-09)

## What changed

- Every variant card (Clinical and All-filtered browsers) carries a CAVA line: MANE 1.5
  RefSeq transcript, CAVA HGVSc and HGVSp, with the CSN in the tooltip. Cards without a
  CAVA annotation say so. Previously CAVA was visible only in the expanded detail view,
  as the card nomenclature when VariantValidator had no result, and as the "CAVA differs"
  badge.
- MNV badge on the card and an "MNV note" row in the detail view when MNV_MERGE tagged the
  record (D17a).
- The Reporting snapshot now uses the same nomenclature preference as the cards
  (VariantValidator, then CAVA, then VEP); it previously skipped CAVA. Snapshots already
  stored in the browser keep their old strings until the variant is re-included.
- Left sidebar stays in view while scrolling (D1).
- Long insertions, COSMIC lists and caller lists wrap inside their cell instead of widening
  the page; Reporting tables use fixed column widths and every cell wraps (D5, D12).
- Tier field on the Reporting page grows with its text instead of clipping at 16 characters;
  Enter commits the value (D4).

## Verification

Nocache DASHBOARD/REPORT_BUNDLE re-render on run8; visual check on 26CGH60 and 26CGH1292.
"""


def patch_build(text):
    if TAG in text:
        return text, "skip"
    return replace_once(
        text,
        'BUILDER_VERSION = "0.5.0-triage+exon"\n',
        'BUILDER_VERSION = "0.5.1-layout+cava"   # DASH_LAYOUT_V1\n',
        "build.py version"), "patch"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    ap.add_argument("--repo", default=".", help="repo root (default: cwd)")
    args = ap.parse_args()
    os.chdir(args.repo)
    if not os.path.isdir(BUILDER):
        print("[error] %s not found under %s" % (BUILDER, os.getcwd()))
        sys.exit(2)

    targets = [
        (BUILDER + "/assets/js/variant-browser.js", patch_js),
        (BUILDER + "/assets/css/dashboard.css", patch_css),
        (BUILDER + "/templates/sample_report.html.j2", patch_template),
        (BUILDER + "/build.py", patch_build),
    ]
    plan = []
    try:
        for path, fn in targets:
            new, status = fn(read(path))
            plan.append((path, new, status))
        cl = BUILDER + "/CHANGELOG_v051.md"
        plan.append((cl, CHANGELOG, "skip" if os.path.isfile(cl) else "create"))
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
        if status != "create":
            bak = "%s.bak_%s_%s" % (path, TAG, STAMP)
            shutil.copy2(path, bak)
            print("[backup] %s" % bak)
        with open(path, "w") as f:
            f.write(new)
        print("[write] %s" % path)
    print("[done] %s applied" % TAG)


if __name__ == "__main__":
    main()
