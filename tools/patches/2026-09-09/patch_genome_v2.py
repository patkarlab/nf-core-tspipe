#!/usr/bin/env python3
"""GENOME_V2 -- one genome-wide figure instead of two.

Run from the repo root with plot_genome_overview.py next to this patcher. Dry-run by default;
--apply writes; .bak_GENOME_V2_<timestamp> backups.

bin/plot_genome_overview.py   replaced: genomic-coordinate figure with three tracks -- depth bins
                              with BAF_V2 arm medians, BAF coloured by the arm verdict (legend),
                              PURPLE total / minor-allele copy number. Same CLI, same output name
                              (chrom_pages/<sample>.genome.png), so the CHROM_PAGES module is unchanged;
                              the script is in bin/, so CHROM_PAGES re-executes on resume (~26 tasks).
templates/sample_report.html.j2
                              Genome-wide sub-tab text describes the three tracks; the BAF_V2B figure
                              card is removed from the BAF sub-tab (the detector PNG stays under
                              clinical/cnv/baf/ as a QC artefact, not displayed).
"""
import argparse
import os
import shutil
import sys
import time

TAG = "GENOME_V2"
STAMP = time.strftime("%Y%m%d_%H%M%S")
HERE = os.path.dirname(os.path.abspath(__file__))
TPL = "bin/dashboard_builder/templates/sample_report.html.j2"
SCRIPT = "bin/plot_genome_overview.py"


class PatchError(Exception):
    pass


def replace_once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise PatchError("%s: anchor found %d times (expected 1): %r" % (label, n, old[:80]))
    return text.replace(old, new)


def patch_template(text):
    if TAG in text:
        return text, "skip"
    text = replace_once(
        text,
        '          <p class="text-muted small mb-2">Per-bin log2 with one median line per chromosome arm (red below -0.25, green above +0.20), BAF (grey balanced, green deviated), PURPLE copy number. Arm medians are printed under the chromosome labels.</p>\n',
        '          {# GENOME_V2 #}\n'
        '          <p class="text-muted small mb-2">Three tracks on one genomic axis. Depth: denoised log2 copy ratio per bin with one median line per chromosome arm (red at or below -0.15, green at or above +0.15). BAF: every catalog site, heterozygous sites coloured by the arm\'s BAF verdict (red DEL, blue CNLOH, green GAIN, purple imbalance, grey balanced). PURPLE: total (blue) and minor-allele (orange) copy number per segment; copy-neutral LOH shows as the minor allele dropping to 0 while the total stays at 2. Centromeres shaded.</p>\n',
        "template genome text")
    text = replace_once(
        text,
        "          {% if ctx.cnv.baf_plot %}\n"
        "          <div class=\"row g-3\">\n"
        "            {{ macros.render_cnv_plot_card('baf_genome::1', 'Depth and BAF by arm (genome-wide)', ctx.cnv.baf_plot, 'col-12') }}\n"
        "          </div>\n"
        "          {% endif %}\n",
        "          {# GENOME_V2: the genome-wide figure lives on the Genome-wide sub-tab #}\n",
        "template BAF figure card")
    return text, "patch"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--repo", default=".")
    args = ap.parse_args()
    os.chdir(args.repo)
    src = os.path.join(HERE, "plot_genome_overview.py")
    if not os.path.isfile(src):
        print("[error] %s not found next to the patcher" % src); sys.exit(2)
    try:
        with open(TPL) as f:
            new_tpl, status = patch_template(f.read())
    except PatchError as e:
        print("[error] %s\n[error] nothing written" % e); sys.exit(1)
    with open(src) as f:
        newscript = f.read()
    cur = open(SCRIPT).read() if os.path.isfile(SCRIPT) else ""
    s_status = "skip" if cur == newscript else ("replace" if cur else "create")
    print("[%s] %s" % (status, TPL))
    print("[%s] %s" % (s_status, SCRIPT))
    if not args.apply:
        print("[dry-run] re-run with --apply to write"); return
    for path, content, st in ((TPL, new_tpl, status), (SCRIPT, newscript, s_status)):
        if st == "skip":
            continue
        if os.path.isfile(path):
            bak = "%s.bak_%s_%s" % (path, TAG, STAMP)
            shutil.copy2(path, bak); print("[backup] %s" % bak)
        with open(path, "w") as f:
            f.write(content)
        if path.endswith(".py"):
            os.chmod(path, 0o755)
        print("[write] %s" % path)
    print("[done] %s applied" % TAG)


if __name__ == "__main__":
    main()
