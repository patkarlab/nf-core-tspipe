#!/usr/bin/env python3
"""
patch_dashboard_cnv_v2a.py -- legacy CNV views removed; clinical/cnv/ shipped in
the bundle (MARKER DASH_CNV_V1a).

  templates/sample_report.html.j2   everything in the CNV tab from the legacy
                                    "Clinical CNV calls table" comment down to the
                                    tab's closing div is removed (tables, primary
                                    scatter, overview, combined, focused, per-gene,
                                    diagram PDF), and the "Legacy CNV views" divider
                                    of DASH_CNV_V1 goes with it
  tools/make_report_bundle.py       clinical/cnv/ copied as a subtree into the
                                    bundle staging beside cnvkit_plots/ and assets/
Dry run by default; --apply writes .bak_dash_cnv_v2a_<ts> backups.
"""
import argparse, datetime, os, re, shutil, sys

MARKER = "MARKER DASH_CNV_V1a"


def patch_template(t):
    start = t.find("        {# ---- Clinical CNV calls table ---- #}")
    igv = t.find('<div class="tab-pane fade" id="tab-igv"')
    if start < 0 or igv < 0 or igv < start:
        raise ValueError("legacy section anchors not found (start %d, igv %d)" % (start, igv))
    close = t.rfind("</div>", start, igv)          # the CNV tab-pane's closing div
    if close < 0:
        raise ValueError("closing div of the CNV tab not found")
    line_start = t.rfind("\n", start, close) + 1      # keep the closing div's own indentation
    removed = t[start:line_start]
    n_sections = removed.count("{# ----")
    t = t[:start] + "        {# legacy CNV views removed: %s #}\n" % MARKER + t[line_start:]
    t2, n_div = re.subn(r'\n[ \t]*<hr class="mt-4">\n[ \t]*<h5 class="mt-3 text-muted">Legacy CNV views</h5>\n', "\n", t)
    if n_div != 1:
        raise ValueError("DASH_CNV_V1 divider found %d times" % n_div)
    return t2, ["[ok] removed %d legacy sections (%d chars)" % (n_sections, len(removed)), "[ok] divider removed"]


def patch_bundler(t):
    rx = re.compile(r'^(?P<i>[ \t]*)shutil\.copytree\(cnvkit_plots, staging / "cnvkit_plots"\)[ \t]*$', re.M)
    if len(rx.findall(t)) != 1:
        raise ValueError("copytree(cnvkit_plots) anchor: %d matches" % len(rx.findall(t)))
    t = rx.sub(lambda m: m.group(0) + "\n%s# %s: v2 CNV tree (consensus, exon plots, chromosome pages, DECoN, PURPLE, sex check)\n"
                                       "%scnv_v2 = clinical / \"cnv\"\n%sif cnv_v2.is_dir():\n%s    shutil.copytree(cnv_v2, staging / \"cnv\")"
               % (m.group("i"), MARKER, m.group("i"), m.group("i"), m.group("i")), t, count=1)
    return t, ["[ok] clinical/cnv copied into the bundle staging"]


FILES = [("bin/dashboard_builder/templates/sample_report.html.j2", patch_template), ("tools/make_report_bundle.py", patch_bundler)]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--root", default="."); ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(); planned, failed = [], False
    for rel, fn in FILES:
        p = os.path.join(a.root, rel); print("== %s" % rel)
        if not os.path.isfile(p):
            print("   [error] not found"); failed = True; continue
        orig = open(p).read()
        if MARKER in orig:
            print("   [skip] already applied"); continue
        try:
            new, notes = fn(orig)
        except ValueError as exc:
            print("   [error] %s" % exc); failed = True; continue
        for n in notes:
            print("   %s" % n)
        if rel.endswith(".py"):
            try:
                compile(new, p, "exec")
            except SyntaxError as exc:
                print("   [error] does not compile: %s" % exc); failed = True; continue
        if rel.endswith(".j2"):
            try:
                import jinja2; jinja2.Environment().parse(new); print("   [check] jinja2 parse ok")
            except ImportError:
                print("   [check] jinja2 not importable here")
            except Exception as exc:  # noqa: BLE001
                print("   [error] template does not parse: %s" % exc); failed = True; continue
            # tab-pane balance: every tab-pane div still has its closing div
            print("   [check] tab-pane openings %d" % new.count('class="tab-pane'))
        print("   [check] markers %d (expected 1)" % new.count(MARKER))
        if new.count(MARKER) != 1:
            failed = True; continue
        planned.append((p, orig, new))
    if failed:
        print("[error] nothing written"); sys.exit(1)
    if not a.apply:
        print("[dry-run] %d file(s) would change" % len(planned)); sys.exit(0)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    for p, orig, new in planned:
        shutil.copy2(p, "%s.bak_dash_cnv_v2a_%s" % (p, ts)); open(p, "w").write(new); print("[patch] wrote %s" % p)


if __name__ == "__main__":
    main()
