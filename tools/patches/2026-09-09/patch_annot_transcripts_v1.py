#!/usr/bin/env python3
"""ANNOT_TRANSCRIPTS_V1 -- every transcript consequence VEP emitted, carried through to the
dashboard as a collapsible "All transcripts" block in the variant detail view. Also carries
Q7 (VEP determinism) and the gene "-1" display fix, so one annotation-path resume covers all.

Run from the nf-core-tspipe repo root. Dry-run by default; --apply writes. All-or-nothing;
.bak_ANNOT_TRANSCRIPTS_V1_<timestamp> backups.

bin/annotate.py   (in the VEP_ANNOTATE task hash -> annotation-path resume, ~60 tasks)
  - new last column VEP_Transcripts: 'Feature|BIOTYPE|Consequence|HGVSc|HGVSp|flags' per
    transcript block, ';'-joined, flags a '+'-joined subset of REPORTED / MANE:<RefSeq> /
    CANONICAL / PICK. Regulatory and motif features skipped. '-1' when there is none.
    Appended after CAVA_HGVSp_Match so existing column positions are unchanged.
  - Q7: run_vep() sets PERL_HASH_SEED=0 and PERL_PERTURB_KEYS=0 so equal-rank consequence
    terms come out in a fixed order and two runs of the same input are byte-identical.
bin/dashboard_builder/assets/js/variant-browser.js   (not hashed -> nocache re-render)
  - detail view: collapsible "All transcripts (VEP, Ensembl)" table, reported row first and
    highlighted, MANE RefSeq and canonical badges, HGVS shown without the accession prefix.
  - compact card: a gene of "-1" renders as an em dash instead of "-1".

Verification: check_annovar_fatal.py C-path is no longer byte-identical by design (new column);
use compare_annotated.py against the previous task: only VEP_Transcripts should be new, and
Consequence differences (Q7 tie order) must be zero across two consecutive runs.
"""
import argparse
import os
import shutil
import sys
import time

TAG = "ANNOT_TRANSCRIPTS_V1"
STAMP = time.strftime("%Y%m%d_%H%M%S")


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
# bin/annotate.py
# ---------------------------------------------------------------------------
ALL_TX_FUNC = '''

def _all_transcripts(blocks, picked):
    """ANNOT_TRANSCRIPTS_V1: every transcript consequence VEP emitted for the variant.

    Returns 'Feature|BIOTYPE|Consequence|HGVSc|HGVSp|flags' entries joined by ';'.
    flags is a '+'-joined subset of REPORTED (the block the clinical columns were
    taken from), MANE:<RefSeq accession>, CANONICAL and PICK. Regulatory and motif
    features are skipped. Field separators inside values are replaced so the
    string stays parseable. Empty when no transcript block exists.
    """
    out = []
    for b in blocks:
        if str(b.get("Feature_type", "Transcript")) != "Transcript":
            continue
        flags = []
        if b is picked:
            flags.append("REPORTED")
        mane = str(b.get("MANE_SELECT", "")).strip()
        if mane:
            flags.append("MANE:" + mane)
        if str(b.get("CANONICAL", "")).strip() == "YES":
            flags.append("CANONICAL")
        if str(b.get("PICK", "")).strip() == "1":
            flags.append("PICK")
        vals = [str(b.get(k, "")).replace("|", "/").replace(";", ",")
                for k in ("Feature", "BIOTYPE", "Consequence", "HGVSc", "HGVSp")]
        out.append("|".join(vals) + "|" + "+".join(flags))
    return ";".join(out)
'''


def patch_annotate(text):
    if TAG in text:
        return text, "skip"
    # column
    text = replace_once(
        text,
        '    "CAVA_SO", "CAVA_Impact", "CAVA_AltAnn", "CAVA_HGVSp_Match",\n',
        '    "CAVA_SO", "CAVA_Impact", "CAVA_AltAnn", "CAVA_HGVSp_Match",\n'
        '    # ANNOT_TRANSCRIPTS_V1: every transcript block VEP emitted (see _all_transcripts).\n'
        '    # Appended last so existing column positions are unchanged.\n'
        '    "VEP_Transcripts",\n',
        "annotate COLUMNS")
    # helper before _pick_csq
    text = replace_once(
        text,
        "\n\ndef _pick_csq(csq_blocks, csq_fields):\n",
        ALL_TX_FUNC + "\n\ndef _pick_csq(csq_blocks, csq_fields):\n",
        "annotate helper")
    # build after pick
    text = replace_once(
        text,
        "                    if blocks:\n"
        "                        csq_data = _pick_csq(blocks, csq_fields)\n",
        "                    if blocks:\n"
        "                        csq_data = _pick_csq(blocks, csq_fields)\n"
        "                        csq_data[\"__all_transcripts\"] = _all_transcripts(blocks, csq_data)   # ANNOT_TRANSCRIPTS_V1\n",
        "annotate parse")
    # output row
    text = replace_once(
        text,
        '            "MNV_Note": _clean(vcf.get("mnv_note", "")),   # MNV_MERGE_V1 (N2)\n',
        '            "MNV_Note": _clean(vcf.get("mnv_note", "")),   # MNV_MERGE_V1 (N2)\n'
        '            "VEP_Transcripts": _clean(vep.get("__all_transcripts", "")),   # ANNOT_TRANSCRIPTS_V1\n',
        "annotate row")
    # Q7 determinism
    text = replace_once(
        text,
        '    for _v in ("PERL5LIB", "PERL_LOCAL_LIB_ROOT", "PERL_MM_OPT", "PERL_MB_OPT"):\n'
        '        vep_env.pop(_v, None)\n',
        '    for _v in ("PERL5LIB", "PERL_LOCAL_LIB_ROOT", "PERL_MM_OPT", "PERL_MB_OPT"):\n'
        '        vep_env.pop(_v, None)\n'
        '    # Q7 (memo 16): VEP orders equal-rank consequence terms by Perl hash iteration, which\n'
        '    # is randomised per process; fix the seed so two runs of one input are byte-identical.\n'
        '    vep_env["PERL_HASH_SEED"] = "0"\n'
        '    vep_env["PERL_PERTURB_KEYS"] = "0"\n',
        "annotate Q7")
    return text, "patch"


# ---------------------------------------------------------------------------
# variant-browser.js
# ---------------------------------------------------------------------------
JS_TX_BLOCK = '''      // ANNOT_TRANSCRIPTS_V1: every transcript VEP annotated for this variant, collapsed by
      // default; the reported (MANE-first) block leads and is highlighted.
      let txBlock = "";
      if (r.VEP_Transcripts && r.VEP_Transcripts !== "-1") {
        const txEntries = String(r.VEP_Transcripts).split(";").map(function (e) {
          const p = e.split("|");
          return { feature: p[0] || "", biotype: p[1] || "", csq: p[2] || "",
                   c: p[3] || "", p: p[4] || "", flags: (p[5] || "").split("+").filter(Boolean) };
        });
        txEntries.sort(function (a, b) {
          return (b.flags.indexOf("REPORTED") !== -1 ? 1 : 0) - (a.flags.indexOf("REPORTED") !== -1 ? 1 : 0);
        });
        const txRows = txEntries.map(function (t) {
          const isRep = t.flags.indexOf("REPORTED") !== -1;
          const mane = t.flags.filter(function (f) { return f.indexOf("MANE:") === 0; })
                              .map(function (f) { return f.slice(5); })[0] || "";
          const acc = (t.c.indexOf(":") !== -1) ? t.c.split(":")[0] : t.feature;   // versioned accession when HGVSc has it
          const flagHtml =
            (isRep ? '<span class="badge bg-primary">reported</span> ' : "") +
            (mane ? '<span class="badge bg-light text-dark border">MANE ' + escapeHtml(mane) + "</span> " : "") +
            (t.flags.indexOf("CANONICAL") !== -1 ? '<span class="badge bg-light text-dark border">canonical</span>' : "");
          return "<tr" + (isRep ? ' class="table-primary"' : "") + ">" +
                 '<td class="font-monospace">' + escapeHtml(acc) + "</td>" +
                 "<td>" + escapeHtml(t.biotype.replace(/_/g, " ")) + "</td>" +
                 "<td>" + escapeHtml(t.csq.replace(/&/g, ", ")) + "</td>" +
                 '<td class="font-monospace">' + escapeHtml(t.c.replace(/^[^:]+:/, "")) + "</td>" +
                 '<td class="font-monospace">' + escapeHtml(t.p.replace(/^[^:]+:/, "")) + "</td>" +
                 "<td>" + flagHtml + "</td></tr>";
        }).join("");
        txBlock =
          '<details class="vb-transcripts mt-3">' +
            '<summary class="text-uppercase text-muted small">All transcripts (VEP, Ensembl): ' + txEntries.length + "</summary>" +
            '<div class="table-responsive mt-2"><table class="table table-sm small mb-0">' +
              "<thead><tr><th>Transcript</th><th>Biotype</th><th>Consequence</th><th>HGVSc</th><th>HGVSp</th><th></th></tr></thead>" +
              "<tbody>" + txRows + "</tbody></table></div>" +
          "</details>";
      }

'''


def patch_js(text):
    if TAG in text:
        return text, "skip"
    text = replace_once(
        text,
        "      // External-link buttons (always visible)\n",
        JS_TX_BLOCK + "      // External-link buttons (always visible)\n",
        "js transcripts block")
    text = replace_once(
        text,
        "      return '<div class=\"vb-card-detail mt-3 pt-3 border-top\">' +\n"
        "               '<div class=\"row g-3\">' + groups.join(\"\") + \"</div>\" +\n",
        "      return '<div class=\"vb-card-detail mt-3 pt-3 border-top\">' +\n"
        "               '<div class=\"row g-3\">' + groups.join(\"\") + \"</div>\" +\n"
        "               txBlock +   // ANNOT_TRANSCRIPTS_V1\n",
        "js detail return")
    text = replace_once(
        text,
        "      const hgvsp = bestHGVSp(r);\n",
        "      const hgvsp = bestHGVSp(r);\n"
        "      const geneLabel = (r.Gene && r.Gene !== \"-1\") ? r.Gene : \"\\u2014\";   // ANNOT_TRANSCRIPTS_V1: no '-1' as a gene name\n",
        "js gene label var")
    text = replace_once(
        text,
        "'<span class=\"vb-gene\">' + escapeHtml(r.Gene || \"?\") + \"</span>\" +\n",
        "'<span class=\"vb-gene\">' + escapeHtml(geneLabel) + \"</span>\" +   // ANNOT_TRANSCRIPTS_V1\n",
        "js gene label use")
    return text, "patch"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    ap.add_argument("--repo", default=".", help="repo root (default: cwd)")
    args = ap.parse_args()
    os.chdir(args.repo)
    targets = [
        ("bin/annotate.py", patch_annotate),
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
        if path.endswith(".py"):
            os.chmod(path, 0o755)
        print("[write] %s" % path)
    print("[done] %s applied" % TAG)


if __name__ == "__main__":
    main()
