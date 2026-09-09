#!/usr/bin/env python3
"""DASH_CNV_TABS_V1 -- CNV tab restructured into sub-tabs; BAF table shows called arms only.

Run from the repo root with baf_cnloh_detect_v2.py next to this patcher. Dry-run by default;
--apply writes. .bak_DASH_CNV_TABS_V1_<timestamp> backups.

templates/sample_report.html.j2 (CNV pane)
  Sub-tabs: Consensus CNV calls | BAF | Genome-wide | reconCNV | Chromosome pages (24).
  - Consensus keeps the intro, column key, tier filter and table; the DECoN exon-level table sits
    under it in a fold (it is arm E's evidence).
  - BAF: called arms only (LOW ones marked ?), a fold with all arms, then the two-track figure.
  - Genome-wide: the arm-median overview. reconCNV: the Bokeh view. Chromosome pages: the 24
    per-chromosome pills, with the exon-level figures underneath.
  - DataTables inside sub-tabs / folds get columns.adjust() when shown.
bin/baf_cnloh_detect.py
  Reinstalled from baf_cnloh_detect_v2.py (two-track figure, chromosome labels on the bottom
  axis, legend). Costs a CNV_BAF_CNLOH re-execution on resume (~40 tasks including the render).
"""
import argparse
import os
import shutil
import sys
import time

TAG = "DASH_CNV_TABS_V1"
STAMP = time.strftime("%Y%m%d_%H%M%S")
HERE = os.path.dirname(os.path.abspath(__file__))
TPL = "bin/dashboard_builder/templates/sample_report.html.j2"


class PatchError(Exception):
    pass


def between(text, start_anchor, end_anchor, label, include_end=False):
    s = text.find(start_anchor)
    if s < 0:
        raise PatchError("%s: start anchor not found: %r" % (label, start_anchor[:60]))
    e = text.find(end_anchor, s)
    if e < 0:
        raise PatchError("%s: end anchor not found: %r" % (label, end_anchor[:60]))
    if include_end:
        e += len(end_anchor)
    return s, e


def patch_template(text):
    if TAG in text:
        return text, "skip"
    # --- slice the existing blocks (content is reused verbatim) ---
    pane_s = text.find('        {% if ctx.cnv.consensus_table and ctx.cnv.consensus_table.rows %}\n          <h5 class="mt-2">Consensus CNV calls')
    pane_e = text.find('        {# legacy CNV views removed: MARKER DASH_CNV_V1a #}')
    if pane_s < 0 or pane_e < 0 or pane_e < pane_s:
        raise PatchError("CNV pane boundaries not found")
    region = text[pane_s:pane_e]

    cs, ce = between(region, '          <h5 class="mt-2">Consensus CNV calls',
                     "          {{ macros.render_datatable('cnv-consensus-table', ctx.cnv.consensus_table.columns, ctx.cnv.consensus_table.rows) }}\n",
                     "consensus core", include_end=True)
    consensus_core = region[cs:ce]

    ds, de = between(region, '        {% if ctx.cnv.decon_table and ctx.cnv.decon_table.rows %}\n',
                     "          {{ macros.render_datatable('cnv-decon-table', ctx.cnv.decon_table.columns, ctx.cnv.decon_table.rows) }}\n        {% endif %}\n",
                     "decon block", include_end=True)
    decon_block = region[ds:de]

    gs, ge = between(region, '        {% if ctx.cnv.genome_overview %}\n', '        {% endif %}\n', "genome block", include_end=True)
    genome_block = region[gs:ge]
    rs, re_ = between(region, '        {% if ctx.cnv.reconcnv %}\n', '        {% endif %}\n', "reconcnv block", include_end=True)
    recon_block = region[rs:re_]
    hs, he = between(region, '        {% if ctx.cnv.chrom_pages %}\n', '          </div>\n        {% endif %}\n', "chrom pages block", include_end=True)
    chrom_block = region[hs:he]
    xs, xe = between(region, '        {% if ctx.cnv.exon_plots %}\n', '          </div>\n        {% endif %}\n', "exon plots block", include_end=True)
    exon_block = region[xs:xe]

    new_region = '''        {# DASH_CNV_TABS_V1: five sub-tabs; each source shown once #}
        <ul class="nav nav-tabs mb-3" id="cnv-subtabs" role="tablist">
          <li class="nav-item" role="presentation"><button class="nav-link active" data-bs-toggle="tab" data-bs-target="#cnv-sub-consensus" type="button" role="tab">Consensus CNV calls</button></li>
          <li class="nav-item" role="presentation"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#cnv-sub-baf" type="button" role="tab">BAF by arm{% if ctx.cnv.baf_calls %} <span class="badge bg-warning text-dark">{{ ctx.cnv.baf_calls|length }}</span>{% endif %}</button></li>
          <li class="nav-item" role="presentation"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#cnv-sub-genome" type="button" role="tab">Genome-wide</button></li>
          <li class="nav-item" role="presentation"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#cnv-sub-reconcnv" type="button" role="tab">reconCNV</button></li>
          <li class="nav-item" role="presentation"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#cnv-sub-chrom" type="button" role="tab">Chromosome pages{% if ctx.cnv.chrom_pages %} ({{ ctx.cnv.chrom_pages|length }}){% endif %}</button></li>
        </ul>
        <div class="tab-content" id="cnv-subpanes">

          {# ---- Consensus ---- #}
          <div class="tab-pane fade show active" id="cnv-sub-consensus" role="tabpanel">
        {% if ctx.cnv.consensus_table and ctx.cnv.consensus_table.rows %}
''' + consensus_core + '''        {% elif ctx.cnv.consensus_tiers is defined %}
          <div class="tspipe-empty">No non-neutral consensus CNV calls.</div>
        {% endif %}
        {% if ctx.cnv.decon_table and ctx.cnv.decon_table.rows %}
          <details class="mt-4">
            <summary class="h6">DECoN exon-level calls <span class="badge bg-secondary">{{ ctx.cnv.decon_table.rows|length }}</span> <span class="text-muted small">(arm E evidence)</span></summary>
''' + decon_block.replace('          <h5 class="mt-4">DECoN exon-level calls</h5>\n', '').replace(
        '        {% if ctx.cnv.decon_table and ctx.cnv.decon_table.rows %}\n', '').replace(
        "          {{ macros.render_datatable('cnv-decon-table', ctx.cnv.decon_table.columns, ctx.cnv.decon_table.rows) }}\n        {% endif %}\n",
        "          {{ macros.render_datatable('cnv-decon-table', ctx.cnv.decon_table.columns, ctx.cnv.decon_table.rows) }}\n") + '''          </details>
        {% endif %}
          </div>

          {# ---- BAF by arm (BAF_V2 / BAF_V2B) ---- #}
          <div class="tab-pane fade" id="cnv-sub-baf" role="tabpanel">
        {% if ctx.cnv.baf_arms %}
          {% set _baf_called = ctx.cnv.baf_arms | rejectattr('verdict', 'in', ['NEUTRAL', 'INDETERMINATE', '']) | list %}
          <h5 class="mt-2">BAF by chromosome arm
            {% if ctx.cnv.baf_calls %}<span class="badge bg-warning text-dark ms-1">{{ ctx.cnv.baf_calls|length }} arm(s) with a call</span>
            {% else %}<span class="badge bg-success ms-1">all arms balanced</span>{% endif %}
          </h5>
          <p class="text-muted small mb-2">Mirrored B-allele deviation over the sample's heterozygous catalog sites (CNV backbone plus the 17p windows), per arm; the noise floor is the sample's own balanced arms. DEL / GAIN use the arm's denoised copy ratio; CNLOH is a shift at neutral copy number; INDETERMINATE means too few heterozygous sites (acrocentric p arms, chrX in males). A call marked ? is LOW confidence (fewer than 20 heterozygous sites or a deviation under 1.5 x the noise floor) and casts no vote in the consensus.</p>
          {% if _baf_called %}
          <div class="table-responsive" style="max-width: 900px;">
            <table class="table table-sm small mb-2">
              <thead class="table-light"><tr><th>Arm</th><th>Het sites</th><th>Clonal fraction</th><th>Copy ratio (log2)</th><th>Verdict</th><th>Confidence</th><th>Scope</th></tr></thead>
              <tbody>
              {% for a in _baf_called %}
                <tr class="{% if a.confidence == 'HIGH' %}table-warning{% else %}table-light{% endif %}">
                  <td><strong>{{ a.arm }}</strong></td><td>{{ a.n_het }}</td><td>{{ a.f }}</td><td>{{ a.cr }}</td>
                  <td><strong>{{ a.verdict }}{% if a.confidence == 'LOW' %}?{% endif %}</strong></td><td>{{ a.confidence }}</td><td>{{ a.scope }}</td>
                </tr>
              {% endfor %}
              </tbody>
            </table>
          </div>
          {% else %}
          <div class="tspipe-empty mb-2">No arm with an allelic imbalance.</div>
          {% endif %}
          <details class="small mb-3">
            <summary class="text-muted">Show all {{ ctx.cnv.baf_arms|length }} arms</summary>
            <div class="table-responsive mt-2" style="max-width: 900px;">
              <table class="table table-sm table-striped small mb-0">
                <thead class="table-light"><tr><th>Arm</th><th>Het sites</th><th>Clonal fraction</th><th>Copy ratio (log2)</th><th>Verdict</th><th>Confidence</th><th>Scope</th></tr></thead>
                <tbody>
                {% for a in ctx.cnv.baf_arms %}
                  <tr{% if a.verdict in ('DEL','CNLOH','GAIN','IMBALANCE') and a.confidence == 'HIGH' %} class="table-warning"{% endif %}>
                    <td>{{ a.arm }}</td><td>{{ a.n_het }}</td><td>{{ a.f }}</td><td>{{ a.cr }}</td>
                    <td>{{ a.verdict }}{% if a.confidence == 'LOW' %}?{% endif %}</td><td>{{ a.confidence }}</td><td>{{ a.scope }}</td>
                  </tr>
                {% endfor %}
                </tbody>
              </table>
            </div>
          </details>
          {% if ctx.cnv.baf_plot %}
          <div class="row g-3">
            {{ macros.render_cnv_plot_card('baf_genome::1', 'Depth and BAF by arm (genome-wide)', ctx.cnv.baf_plot, 'col-12') }}
          </div>
          {% endif %}
        {% else %}
          <div class="tspipe-empty">BAF per-arm summary not available for this sample.</div>
        {% endif %}
          </div>

          {# ---- Genome-wide ---- #}
          <div class="tab-pane fade" id="cnv-sub-genome" role="tabpanel">
''' + genome_block.replace('          <h5 class="mt-4">Genome-wide</h5>\n', '          <h5 class="mt-2">Genome-wide overview (arm medians)</h5>\n') + '''        {% if not ctx.cnv.genome_overview %}<div class="tspipe-empty">Genome overview not available.</div>{% endif %}
          </div>

          {# ---- reconCNV ---- #}
          <div class="tab-pane fade" id="cnv-sub-reconcnv" role="tabpanel">
''' + recon_block.replace('          <h5 class="mt-4">reconCNV (interactive)</h5>\n', '          <h5 class="mt-2">reconCNV (interactive)</h5>\n') + '''        {% if not ctx.cnv.reconcnv %}<div class="tspipe-empty">reconCNV view not available.</div>{% endif %}
          </div>

          {# ---- Chromosome pages + exon figures ---- #}
          <div class="tab-pane fade" id="cnv-sub-chrom" role="tabpanel">
''' + chrom_block.replace('          <h5 class="mt-4">Chromosome pages ({{ ctx.cnv.chrom_pages|length }})</h5>\n', '          <h5 class="mt-2">Chromosome pages ({{ ctx.cnv.chrom_pages|length }})</h5>\n') + exon_block + '''          </div>
        </div>

        <script>
          // DASH_CNV_TABS_V1: DataTables laid out while hidden need a column adjust once visible
          document.addEventListener("DOMContentLoaded", function () {
            function adjust() { if (window.jQuery && jQuery.fn.dataTable) { jQuery.fn.dataTable.tables({ visible: true, api: true }).columns.adjust(); } }
            document.querySelectorAll('#cnv-subtabs button[data-bs-toggle="tab"]').forEach(function (b) { b.addEventListener("shown.bs.tab", adjust); });
            document.querySelectorAll("#tab-cnv details").forEach(function (d) { d.addEventListener("toggle", adjust); });
          });
        </script>

'''
    return text[:pane_s] + new_region + text[pane_e:], "patch"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--repo", default=".")
    args = ap.parse_args()
    os.chdir(args.repo)
    det_src = os.path.join(HERE, "baf_cnloh_detect_v2.py")
    if not os.path.isfile(det_src):
        print("[error] %s not found next to the patcher" % det_src); sys.exit(2)
    try:
        with open(TPL) as f:
            new_tpl, status = patch_template(f.read())
    except PatchError as e:
        print("[error] %s\n[error] nothing written" % e); sys.exit(1)
    det = "bin/baf_cnloh_detect.py"
    with open(det) as f:
        cur = f.read()
    with open(det_src) as f:
        newdet = f.read()
    det_status = "skip" if cur == newdet else "replace"
    print("[%s] %s" % (status, TPL))
    print("[%s] %s" % (det_status, det))
    if not args.apply:
        print("[dry-run] re-run with --apply to write"); return
    for path, content, st in ((TPL, new_tpl, status), (det, newdet, det_status)):
        if st == "skip":
            continue
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
