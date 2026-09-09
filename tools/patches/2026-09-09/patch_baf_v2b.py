#!/usr/bin/env python3
"""BAF_V2B -- deliver the BAF_V2 outputs to the clinical/ tree and the dashboard.

CNV_BAF_CNLOH publishes to <outdir>/<sample>/cnv_baf/, outside clinical/, so neither the report
bundle nor the dashboard could see the per-arm summary or the two-track figure. This patch routes
both through ORGANIZE_OUTPUT into clinical/cnv/baf/ and shows the figure on the CNV tab.

workflows/tspipe.nf            NO_FILE_baf_plot.png sentinel; ch_baf_plot (optional, driver join);
                               ORGANIZE join gains baf_summary and baf_plot.
modules/local/organize_output.nf   tuple gains path(baf_summary), path(baf_plot); --baf-summary/--baf-plot.
bin/organize_output.py         both hardlinked into clinical/cnv/baf/ (plot skipped when sentinel).
bin/dashboard_builder/parsers/cnv_v2.py   baf_plot relative path; arm table falls back to the
                               consensus JSON's baf_arms when the summary file is absent.
templates/sample_report.html.j2   figure card under the arm table.
assets/NO_FILE_baf_plot.png    created (empty sentinel; add to git).

Resume cost: ORGANIZE_OUTPUT (8) + DASHBOARD + REPORT_BUNDLE. Dry-run by default; --apply writes.
"""
import argparse
import os
import shutil
import sys
import time

TAG = "BAF_V2B"
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


def patch_wf(text):
    if TAG in text:
        return text, "skip"
    text = replace_once(
        text,
        '    def no_u2af1_rescue = file("${projectDir}/assets/NO_FILE_u2af1_rescue.tsv",        checkIfExists: true)\n',
        '    def no_u2af1_rescue = file("${projectDir}/assets/NO_FILE_u2af1_rescue.tsv",        checkIfExists: true)\n'
        '    def no_baf_plot     = file("${projectDir}/assets/NO_FILE_baf_plot.png",              checkIfExists: true)   // BAF_V2B\n',
        "wf sentinel")
    text = replace_once(
        text,
        "    ch_u2af1_rescue = ch_meta_driver\n"
        "        .join(VARIANT_CALLING.out.u2af1_tsv,    remainder: true)\n"
        "        .map { meta, f -> [meta, f ?: no_u2af1_rescue] }\n",
        "    ch_u2af1_rescue = ch_meta_driver\n"
        "        .join(VARIANT_CALLING.out.u2af1_tsv,    remainder: true)\n"
        "        .map { meta, f -> [meta, f ?: no_u2af1_rescue] }\n"
        "\n"
        "    // BAF_V2B: the two-track figure is an optional output of CNV_BAF_CNLOH\n"
        "    ch_baf_plot = ch_meta_driver\n"
        "        .join(GATK_CNV_CALLING.out.baf_plot,    remainder: true)\n"
        "        .map { meta, f -> [meta, f ?: no_baf_plot] }\n",
        "wf ch_baf_plot")
    text = replace_once(
        text,
        "        .join(PREPROCESSING.out.spikein)                                     // + spikein (SPIKEIN_V1)\n",
        "        .join(PREPROCESSING.out.spikein)                                     // + spikein (SPIKEIN_V1)\n"
        "        .join(GATK_CNV_CALLING.out.baf_summary)                              // + baf_summary (BAF_V2B)\n"
        "        .join(ch_baf_plot)                                                   // + baf_plot (sentinel when absent)\n",
        "wf organize join")
    return text, "patch"


def patch_module(text):
    if TAG in text:
        return text, "skip"
    text = replace_once(
        text,
        "              path(spikein)   // MARKER SPIKEIN_V1: SPIKEIN_SITES genotype table\n",
        "              path(spikein),   // MARKER SPIKEIN_V1: SPIKEIN_SITES genotype table\n"
        "              path(baf_summary), path(baf_plot)   // BAF_V2B: per-arm BAF summary + two-track figure (sentinel when absent)\n",
        "module tuple")
    text = replace_once(
        text,
        "        def spikein_arg = spikein ? \"--spikein-snps ${spikein}\" : ''   // SPIKEIN_V1\n",
        "        def spikein_arg = spikein ? \"--spikein-snps ${spikein}\" : ''   // SPIKEIN_V1\n"
        "        def baf_args = \"--baf-summary ${baf_summary} --baf-plot ${baf_plot}\"   // BAF_V2B\n",
        "module args")
    text = replace_once(
        text,
        "            ${spikein_arg}\n",
        "            ${spikein_arg} \\\\\n"
        "            ${baf_args}\n",
        "module script")
    return text, "patch"


def patch_py(text):
    if TAG in text:
        return text, "skip"
    text = replace_once(
        text,
        '    parser.add_argument("--spikein-snps", default=None, help="SPIKEIN_SITES genotype table (optional; SPIKEIN_V1)")\n',
        '    parser.add_argument("--spikein-snps", default=None, help="SPIKEIN_SITES genotype table (optional; SPIKEIN_V1)")\n'
        '    parser.add_argument("--baf-summary", default=None, help="BAF_V2 per-arm summary (optional; BAF_V2B)")\n'
        '    parser.add_argument("--baf-plot", default=None, help="BAF_V2 two-track figure (optional; BAF_V2B)")\n',
        "py args")
    text = replace_once(
        text,
        '            (args.sex_check,              "sex_check", "SEX_CHECK table")):\n',
        '            (args.sex_check,              "sex_check", "SEX_CHECK table"),\n'
        '            (args.baf_summary,            "baf",       "BAF per-arm summary (BAF_V2B)"),\n'
        '            (args.baf_plot,               "baf",       "BAF two-track figure (BAF_V2B)")):\n',
        "py links")
    return text, "patch"


PARSER_OLD = '''    # ---- BAF by arm (BAF_V2) ----
    for cand in (v2 / ("%s.baf.summary.tsv" % sample), v2 / "baf" / ("%s.baf.summary.tsv" % sample)):
        if cand.exists():
            rows = _read_tsv(cand)
            if rows:
                out["baf_arms"] = [{"arm": r.get("arm", ""), "n_het": r.get("n_het", ""), "f": r.get("f_estimate", ""),
                                    "cr": r.get("cr_median_log2", ""), "verdict": r.get("verdict", ""),
                                    "confidence": r.get("confidence", ""), "scope": r.get("scope", "")} for r in rows]
                out["baf_calls"] = [r for r in out["baf_arms"] if r["verdict"] not in ("NEUTRAL", "INDETERMINATE", "") and r["confidence"] == "HIGH"]
            break
'''
PARSER_NEW = '''    # ---- BAF by arm (BAF_V2; BAF_V2B: clinical/cnv/baf/, consensus-JSON fallback, figure) ----
    baf_rows = None
    for cand in (v2 / "baf" / ("%s.baf.summary.tsv" % sample), v2 / ("%s.baf.summary.tsv" % sample)):
        if cand.exists():
            baf_rows = _read_tsv(cand)
            break
    if baf_rows is None:
        cj = v2 / "consensus" / ("%s.cnv_consensus4.json" % sample)
        if cj.exists():
            try:
                import json
                with open(cj) as fh:
                    baf_rows = json.load(fh).get("baf_arms") or None
            except (OSError, ValueError):
                baf_rows = None
    if baf_rows:
        out["baf_arms"] = [{"arm": r.get("arm", ""), "n_het": r.get("n_het", ""), "f": r.get("f_estimate", ""),
                            "cr": r.get("cr_median_log2", ""), "verdict": r.get("verdict", ""),
                            "confidence": r.get("confidence", ""), "scope": r.get("scope", "")} for r in baf_rows]
        out["baf_calls"] = [r for r in out["baf_arms"] if r["verdict"] not in ("NEUTRAL", "INDETERMINATE", "") and r["confidence"] == "HIGH"]
    bp = v2 / "baf" / ("%s.baf.png" % sample)
    if bp.exists():
        out["baf_plot"] = _rel(bp, sample_dir)
'''

TPL_OLD = '''              </tbody>
            </table>
          </div>
          {% endif %}
'''
TPL_NEW = '''              </tbody>
            </table>
          </div>
          {% if ctx.cnv.baf_plot %}   {# BAF_V2B: two-track figure #}
          <div class="row g-3 mt-1">
            {{ macros.render_cnv_plot_card('baf_genome::1', 'Depth and BAF by arm (genome-wide)', ctx.cnv.baf_plot, 'col-12') }}
          </div>
          {% endif %}
          {% endif %}
'''


def patch_parser(text):
    if TAG in text:
        return text, "skip"
    return replace_once(text, PARSER_OLD, PARSER_NEW, "parser BAF block"), "patch"


def patch_template(text):
    if TAG in text:
        return text, "skip"
    # anchor the closing of the BAF_V2 arm table (unique because of the preceding BAF_V2 comment)
    start = text.find("{# BAF_V2: per-arm allelic state #}")
    if start < 0:
        raise PatchError("template: BAF_V2 arm table not found")
    idx = text.find(TPL_OLD, start)
    if idx < 0:
        raise PatchError("template: arm-table closing anchor not found")
    return text[:idx] + TPL_NEW + text[idx + len(TPL_OLD):] + "", "patch"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--repo", default=".")
    args = ap.parse_args()
    os.chdir(args.repo)
    targets = [
        ("workflows/tspipe.nf", patch_wf),
        ("modules/local/organize_output.nf", patch_module),
        ("bin/organize_output.py", patch_py),
        ("bin/dashboard_builder/parsers/cnv_v2.py", patch_parser),
        ("bin/dashboard_builder/templates/sample_report.html.j2", patch_template),
    ]
    plan = []
    try:
        for path, fn in targets:
            new, status = fn(read(path))
            plan.append((path, new, status))
    except PatchError as e:
        print("[error] %s\n[error] nothing written" % e); sys.exit(1)
    sentinel = "assets/NO_FILE_baf_plot.png"
    plan.append((sentinel, "", "skip" if os.path.isfile(sentinel) else "create"))
    for path, _, status in plan:
        print("[%s] %s" % (status, path))
    if not args.apply:
        print("[dry-run] re-run with --apply to write"); return
    for path, new, status in plan:
        if status == "skip":
            continue
        if status == "create":
            open(path, "w").close(); print("[write] %s (empty sentinel)" % path); continue
        bak = "%s.bak_%s_%s" % (path, TAG, STAMP)
        shutil.copy2(path, bak); print("[backup] %s" % bak)
        with open(path, "w") as f:
            f.write(new)
        print("[write] %s" % path)
    print("[done] %s applied" % TAG)


if __name__ == "__main__":
    main()
