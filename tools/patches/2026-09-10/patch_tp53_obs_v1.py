#!/usr/bin/env python3
"""TP53_OBS_V1 -- TP53 / 17p observation block on the dashboard (handoff 2026-09-10 v2 section 1).

Patches (anchor-based, all-or-nothing, MARKER-guarded, dry-run unless --apply):
  bin/dashboard_builder/build.py                     import, ctx key, parse call, --tp53-rules, version 0.5.2-tp53
  bin/dashboard_builder/templates/sample_report.html.j2
                                                     card above the CNV sub-tabs; one-line mirror on the Reporting tab
  modules/local/dashboard.nf                         --tp53-rules assets/<panel>/tp53_interpretation_rules.tsv when present
Files delivered alongside (copied by hand, not by this script):
  bin/dashboard_builder/parsers/tp53.py
  assets/twist_myeloid/tp53_interpretation_rules.tsv

Run from the repo root:  python3 tools/patches/2026-09-10/patch_tp53_obs_v1.py [--apply]
"""
import argparse
import datetime as dt
import shutil
import sys
from pathlib import Path

MARKER = "TP53_OBS_V1"
TAG = "tp53_obs_v1"

# --------------------------------------------------------------------------------------
# template blocks
# --------------------------------------------------------------------------------------
CARD = r'''        {# MARKER TP53_OBS_V1: TP53 / 17p observation block -- observations only; the interpretation wording comes from assets/<panel>/tp53_interpretation_rules.tsv #}
        {% if ctx.tp53 %}
        {% set _t = ctx.tp53 %}
        <div class="card mb-3" id="tp53-observation-card">
          <div class="card-header py-2 d-flex justify-content-between align-items-center flex-wrap gap-2">
            <span class="fw-medium">TP53 / 17p observation</span>
            <span class="small text-muted">variant table &middot; CNV consensus &middot; BAF_V2 &middot; PURPLE &middot; PureCN, side by side; interpretation wording from <code>{{ _t.rules.name or 'no rule table' }}</code> ({{ _t.rules.n }} rule{{ '' if _t.rules.n == 1 else 's' }})</span>
          </div>
          <div class="card-body py-2">
            <div class="row g-3">
              <div class="col-lg-6">
                <h6 class="mb-1">TP53 variants in the clinical table <span class="badge {{ 'bg-warning text-dark' if _t.n_variants else 'bg-secondary' }}">{{ _t.n_variants }}</span></h6>
                {% if _t.variants %}
                <div class="table-responsive">
                <table class="table table-sm small mb-1">
                  <thead class="table-light"><tr><th>Variant</th><th>Transcript / exon</th><th>VAF %</th><th>Callers</th><th>Verdict</th><th>ClinVar</th><th>OncoVI</th></tr></thead>
                  <tbody>
                  {% for v in _t.variants %}
                  <tr>
                    <td><code>{{ v.hgvsc | e }}</code>{% if v.hgvsp %}<br><code>{{ v.hgvsp | e }}</code>{% endif %}<div class="text-muted">{{ v.key | e }}{% if v.hgvs_source %} &middot; {{ v.hgvs_source }}{% endif %}{% if v.variant_class %} &middot; {{ v.variant_class | e }}{% endif %}{% if v.mnv_note %} &middot; {{ v.mnv_note | e }}{% endif %}</div></td>
                    <td>{{ v.transcript | e }}{% if v.exon %}<br>exon {{ v.exon | e }}{% endif %}</td>
                    <td>{{ v.vaf_str }}{% if v.alt_count %}<div class="text-muted">{{ v.alt_count }}/{{ v.ref_count }}</div>{% endif %}</td>
                    <td>{{ v.n_callers }}<div class="text-muted" style="max-width:160px">{{ v.callers | e }}</div></td>
                    <td><span class="badge {{ 'bg-success' if v.verdict == 'PASS' else ('bg-warning text-dark' if v.verdict == 'LowQual' else 'bg-secondary') }}">{{ v.verdict or '?' }}</span></td>
                    <td>{{ v.clinvar | e }}</td>
                    <td>{{ v.oncovi | e }}{% if v.oncovi_score %} <span class="text-muted">({{ v.oncovi_score }})</span>{% endif %}</td>
                  </tr>
                  {% endfor %}
                  </tbody>
                </table>
                </div>
                {% if _t.n_variants > 1 %}<div class="small text-muted">More than one TP53 row is itself an observation.</div>{% endif %}
                {% else %}
                <div class="tspipe-empty">No reportable TP53 variant in the clinical table.</div>
                {% endif %}
              </div>
              <div class="col-lg-6">
                <h6 class="mb-1">17p allelic evidence at TP53</h6>
                <table class="table table-sm tspipe-kv-table mb-1"><tbody>
                  {% if _t.cnv %}
                  <tr><td class="label">Consensus (arms {{ _t.cnv.flags or '-' }})</td><td class="value">{{ _t.cnv.consensus_call }}{% if _t.cnv.tier and _t.cnv.tier != 'NA' %} &middot; {{ _t.cnv.tier }}{% endif %}{% if _t.cnv.cytoband %} &middot; {{ _t.cnv.cytoband }}{% endif %}</td></tr>
                  <tr><td class="label">Allelic state (BAF_V2 at the gene)</td><td class="value">{{ _t.cnv.allelic_state or '-' }}</td></tr>
                  <tr><td class="label">CNVkit (K)</td><td class="value">{{ _t.cnv.k_call or '-' }}{% if _t.cnv.k_cn %} &middot; cn {{ _t.cnv.k_cn }}{% endif %}{% if _t.cnv.k_log2 %} &middot; log2 {{ _t.cnv.k_log2 }}{% endif %}</td></tr>
                  <tr><td class="label">GATK (G)</td><td class="value">{{ _t.cnv.g_call or '-' }}{% if _t.cnv.g_seg_log2 %} &middot; log2 {{ _t.cnv.g_seg_log2 }}{% endif %}</td></tr>
                  {% endif %}
                  {% if _t.baf %}
                  <tr><td class="label">BAF_V2 17p arm (B)</td><td class="value">{{ _t.baf.verdict or '-' }}{% if _t.baf.f %} &middot; f {{ _t.baf.f }}{% endif %} &middot; {{ _t.baf.n_het or '?' }} het sites &middot; {{ _t.baf.confidence }} &middot; scope {{ _t.baf.scope or '?' }}{% if _t.baf.cr %} &middot; copy ratio {{ _t.baf.cr }}{% endif %}</td></tr>
                  {% else %}
                  <tr><td class="label">BAF_V2 17p arm (B)</td><td class="value">not available</td></tr>
                  {% endif %}
                  {% if _t.cnv %}
                  <tr><td class="label">PURPLE at TP53 (H)</td><td class="value">{{ _t.cnv.h_call or '-' }}{% if _t.cnv.h_cn_min %} &middot; total {{ _t.cnv.h_cn_min }}{% if _t.cnv.h_cn_max and _t.cnv.h_cn_max != _t.cnv.h_cn_min %}&ndash;{{ _t.cnv.h_cn_max }}{% endif %}{% endif %}{% if _t.cnv.h_macn_min %} &middot; minor {{ _t.cnv.h_macn_min }}{% endif %} &middot; LOH {{ _t.cnv.h_loh or '?' }}</td></tr>
                  <tr><td class="label">PureCN at TP53 (P)</td><td class="value">{{ _t.cnv.p_call or '-' }}{% if _t.cnv.p_C %} &middot; C {{ _t.cnv.p_C }}{% endif %} &middot; LOH {{ _t.cnv.p_loh or '?' }}</td></tr>
                  {% endif %}
                  <tr><td class="label">Purity</td><td class="value">{% if _t.purity.purple %}PURPLE {{ _t.purity.purple }} ({{ _t.purity.purple_status | e }}{% if _t.purity.purple_trusted != 'TRUE' %}, advisory{% endif %}){% endif %}{% if _t.purity.purecn %}{% if _t.purity.purple %} &middot; {% endif %}PureCN {{ _t.purity.purecn }}{% if _t.purity.purecn_comment %} ({{ _t.purity.purecn_comment | e }}){% endif %}{% endif %}{% if not _t.purity.purple and not _t.purity.purecn %}-{% endif %}</td></tr>
                </tbody></table>
              </div>
            </div>
            <div class="alert alert-light border py-2 mt-2 mb-1">
              <strong>Interpretation:</strong> {{ _t.interpretation.wording | e }}
              <span class="small text-muted">
                {% if _t.interpretation.source == 'rule' %}(rule at line {{ _t.interpretation.line }}: <code>{{ _t.interpretation.condition | e }}</code>){% else %}(no matching rule; wording is the reporting pathologist's){% endif %}
              </span>
              {% if _t.rules.errors %}<div class="small text-danger mt-1">Rule table problems: {{ _t.rules.errors | join('; ') | e }}</div>{% endif %}
            </div>
            <details class="small">
              <summary class="text-muted">Fields available to the rule table (this sample's values)</summary>
              <div class="mt-1" style="font-family: ui-monospace, SFMono-Regular, Menlo, monospace;">
                {% for k, v in _t.facts.items() %}{{ k }}={{ (v if v is not none else '') | e }}{% if not loop.last %} &nbsp; {% endif %}{% endfor %}
              </div>
            </details>
          </div>
        </div>
        {% endif %}

'''

MIRROR = r'''        {# MARKER TP53_OBS_V1: one-line mirror of the TP53 / 17p observation block (CNV tab) #}
        {% if ctx.tp53 %}
        <div class="alert alert-light border small mb-3" id="reporting-tp53-line">
          <strong>TP53 / 17p:</strong> {{ ctx.tp53.observations | join(' ') | e }}
          <strong>Interpretation:</strong> {{ ctx.tp53.interpretation.wording | e }}
        </div>
        {% endif %}

'''

# --------------------------------------------------------------------------------------
# edits: (path, [(anchor, replacement, description)])
# --------------------------------------------------------------------------------------
EDITS = {
    "bin/dashboard_builder/build.py": [
        ('from parsers import spikein as p_spikein   # SPIKEIN_V1\n',
         'from parsers import spikein as p_spikein   # SPIKEIN_V1\n'
         'from parsers import tp53 as p_tp53   # TP53_OBS_V1\n',
         "import"),
        ('BUILDER_VERSION = "0.5.1-layout+cava"   # DASH_LAYOUT_V1\n',
         'BUILDER_VERSION = "0.5.2-tp53"   # TP53_OBS_V1 (was 0.5.1-layout+cava, DASH_LAYOUT_V1)\n',
         "version"),
        ('        "cnv": None,\n',
         '        "cnv": None,\n'
         '        "tp53": None,   # TP53_OBS_V1\n',
         "ctx key"),
        ('        logging.warning("[%s] cnv v2 parse failed: %s", sample, exc)\n'
         '        ctx["cnv"] = {}\n',
         '        logging.warning("[%s] cnv v2 parse failed: %s", sample, exc)\n'
         '        ctx["cnv"] = {}\n'
         '    try:   # TP53_OBS_V1: TP53 variant(s) and 17p allelic evidence side by side; wording from the rule asset\n'
         '        ctx["tp53"] = p_tp53.parse(effective_dir, sample, clinical=ctx.get("clinical"))\n'
         '    except Exception as exc:  # noqa: BLE001\n'
         '        logging.warning("[%s] tp53 observation parse failed: %s", sample, exc)\n'
         '        ctx["tp53"] = None\n',
         "parse call"),
        ('             "SNP sites shown on the Spike-in tab. Optional."   # SPIKEIN_V1\n'
         '    )\n',
         '             "SNP sites shown on the Spike-in tab. Optional."   # SPIKEIN_V1\n'
         '    )\n'
         '    parser.add_argument(\n'
         '        "--tp53-rules", dest="tp53_rules", default=None,\n'
         '        help="tp53_interpretation_rules.tsv for the panel: condition -> wording table that "\n'
         '             "supplies the interpretation line of the TP53 / 17p observation block. "\n'
         '             "Optional; without it the line reads \'per reporting pathologist\'."   # TP53_OBS_V1\n'
         '    )\n',
         "argparse"),
        ('    p_spikein.ASSET_PATH = args.spikein_regions   # SPIKEIN_V1\n',
         '    p_spikein.ASSET_PATH = args.spikein_regions   # SPIKEIN_V1\n'
         '    p_tp53.RULES_PATH = args.tp53_rules   # TP53_OBS_V1\n',
         "rules path"),
    ],
    "bin/dashboard_builder/templates/sample_report.html.j2": [
        ('        {# DASH_CNV_TABS_V1: five sub-tabs; each source shown once #}\n',
         CARD + '        {# DASH_CNV_TABS_V1: five sub-tabs; each source shown once #}\n',
         "CNV-tab card"),
        ('        <div id="reporting-empty" class="tspipe-empty">\n',
         MIRROR + '        <div id="reporting-empty" class="tspipe-empty">\n',
         "Reporting mirror"),
    ],
    "modules/local/dashboard.nf": [
        ('        def spikein_arg   = spikein_asset.exists() ? "--spikein-regions ${spikein_asset}" : \'\'\n',
         '        def spikein_arg   = spikein_asset.exists() ? "--spikein-regions ${spikein_asset}" : \'\'\n'
         '        def tp53_rules    = file("${projectDir}/assets/${params.panel}/tp53_interpretation_rules.tsv")   // TP53_OBS_V1\n'
         '        def tp53_arg      = tp53_rules.exists() ? "--tp53-rules ${tp53_rules}" : \'\'\n',
         "asset lookup"),
        ('            ${spikein_arg} \\\\\n',
         '            ${spikein_arg} \\\\\n'
         '            ${tp53_arg} \\\\\n',
         "builder argument"),
    ],
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write the files (default: dry run)")
    ap.add_argument("--root", default=".", help="repo root (default: current directory)")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")

    planned = {}
    for rel, edits in EDITS.items():
        p = root / rel
        if not p.exists():
            print("[error] missing %s" % p)
            return 2
        text = p.read_text()
        if MARKER in text:
            print("[skip]  %s already carries %s" % (rel, MARKER))
            continue
        for anchor, repl, desc in edits:
            n = text.count(anchor)
            if n != 1:
                print("[error] %s: anchor for '%s' found %d times (need exactly 1)" % (rel, desc, n))
                return 2
            text = text.replace(anchor, repl, 1)
            print("[patch] %s: %s" % (rel, desc))
        planned[p] = text

    if not planned:
        print("nothing to do")
        return 0
    if not args.apply:
        print("dry run: %d file(s) would change; re-run with --apply" % len(planned))
        return 0
    for p, text in planned.items():
        bak = p.with_name(p.name + ".bak_%s_%s" % (TAG, stamp))
        shutil.copy2(p, bak)
        print("[backup] %s" % bak.relative_to(root))
        p.write_text(text)
        print("[write] %s (%d x %s)" % (p.relative_to(root), text.count(MARKER), MARKER))
    return 0


if __name__ == "__main__":
    sys.exit(main())
