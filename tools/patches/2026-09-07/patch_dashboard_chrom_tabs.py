#!/usr/bin/env python3
"""patch_dashboard_chrom_tabs.py -- chromosome pages as sub-tabs (MARKER DASH_CNV_V1b):
one pill per chromosome, one page shown at a time; the report-selection card is unchanged."""
import argparse, datetime, re, shutil, sys

MARKER = "MARKER DASH_CNV_V1b"
TARGET = "bin/dashboard_builder/templates/sample_report.html.j2"
OLD = re.compile(r'''^(?P<i>[ \t]*)<div class="row g-3">\n[ \t]*\{% for item in ctx\.cnv\.chrom_pages %\}\n[ \t]*\{\{ macros\.render_cnv_plot_card\('chrom_page::' ~ item\.chrom, item\.chrom ~ ' \(' ~ item\.n_targets ~ ' targets, ' ~ item\.n_baf_sites ~ ' BAF sites\)', item\.path, 'col-12'\) \}\}\n[ \t]*\{% endfor %\}\n[ \t]*</div>[ \t]*$''', re.M)
NEW = '''{i}{{# {m}: one sub-tab per chromosome #}}
{i}<ul class="nav nav-pills flex-wrap mb-2" id="cnv-chrom-tabs" role="tablist">
{i}  {{% for item in ctx.cnv.chrom_pages %}}
{i}    <li class="nav-item" role="presentation">
{i}      <button class="nav-link py-0 px-2 small{{% if loop.first %}} active{{% endif %}}" data-bs-toggle="pill" data-bs-target="#cnv-chrom-{{{{ item.chrom }}}}" type="button" role="tab">{{{{ item.chrom | replace('chr', '') }}}}</button>
{i}    </li>
{i}  {{% endfor %}}
{i}</ul>
{i}<div class="tab-content" id="cnv-chrom-panes">
{i}  {{% for item in ctx.cnv.chrom_pages %}}
{i}    <div class="tab-pane fade{{% if loop.first %}} show active{{% endif %}}" id="cnv-chrom-{{{{ item.chrom }}}}" role="tabpanel">
{i}      <div class="row g-3">
{i}        {{{{ macros.render_cnv_plot_card('chrom_page::' ~ item.chrom, item.chrom ~ ' (' ~ item.n_targets ~ ' targets, ' ~ item.n_baf_sites ~ ' BAF sites)', item.path, 'col-12') }}}}
{i}      </div>
{i}    </div>
{i}  {{% endfor %}}
{i}</div>'''


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--target", default=TARGET); ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(); t = open(a.target).read()
    if MARKER in t:
        print("[skip] already applied"); sys.exit(0)
    n = len(OLD.findall(t))
    if n != 1:
        print("[error] chromosome pages gallery block: %d matches; nothing written" % n); sys.exit(1)
    m = OLD.search(t)
    t2 = t[:m.start()] + NEW.format(i=m.group("i"), m=MARKER) + t[m.end():]
    try:
        import jinja2; jinja2.Environment().parse(t2); print("[check] jinja2 parse ok")
    except ImportError:
        print("[check] jinja2 not importable here")
    except Exception as exc:  # noqa: BLE001
        print("[error] template does not parse: %s" % exc); sys.exit(1)
    print("[ok] chromosome pages -> sub-tabs; markers %d" % t2.count(MARKER))
    if not a.apply:
        print("[dry-run]"); sys.exit(0)
    b = "%s.bak_dash_chrom_tabs_%s" % (a.target, datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(a.target, b); open(a.target, "w").write(t2); print("[patch] wrote %s" % a.target)


if __name__ == "__main__":
    main()
