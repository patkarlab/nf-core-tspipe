#!/usr/bin/env python3
"""
patch_hmf_purple_v1b.py -- driver panel enum columns and published tool logs
(MARKER HMF_PURPLE_V1b).
  bin/make_driver_gene_panel.py: templated rows get NONE in every
      reportGermline* column (enum DriverGeneGermlineReporting; an empty
      string crashed PURPLE 4.4); additionalReportedTranscripts stays empty
  modules/local/hmf_{amber,cobalt,purple}.nf: <id>.<tool>.log declared as an
      optional output so the publishDir pattern picks it up
"""
import argparse, datetime, os, re, shutil, sys

MARKER = "MARKER HMF_PURPLE_V1b"
EDITS = {
    "bin/make_driver_gene_panel.py": [
        (r'''            for col in header:
                if col\.startswith\("reportGermline"\) or col in \("additionalReportedTranscripts",\):
                    row\[col\] = "NONE" if col in \("reportGermlineVariant", "reportGermlineHotspot"\) else \("FALSE" if row\[col\] in \("TRUE", "FALSE"\) else ""\)
''',
         '''            for col in header:   # %s: germline reporting columns are enums; never empty
                if col.startswith("reportGermline"):
                    row[col] = "FALSE" if row[col] in ("TRUE", "FALSE") else "NONE"
                elif col == "additionalReportedTranscripts":
                    row[col] = ""
''' % MARKER, "templated germline columns"),
    ],
    "modules/local/hmf_amber.nf": [
        (r'^(?P<i>[ \t]*)tuple val\(meta\), path\("amber/\$\{meta\.id\}\.amber\.qc"\),(?P<s>[ \t]*)emit: qc[ \t]*$',
         lambda m: m.group(0) + "\n%stuple val(meta), path(\"${meta.id}.amber.log\"),%semit: log, optional: true   // %s" % (m.group("i"), " " * 14, MARKER), "amber log output"),
    ],
    "modules/local/hmf_cobalt.nf": [
        (r'^(?P<i>[ \t]*)tuple val\(meta\), path\("cobalt/\$\{meta\.id\}\.cobalt\.ratio\.tsv\.gz"\),(?P<s>[ \t]*)emit: ratio[ \t]*$',
         lambda m: m.group(0) + "\n%stuple val(meta), path(\"${meta.id}.cobalt.log\"),%semit: log, optional: true   // %s" % (m.group("i"), " " * 14, MARKER), "cobalt log output"),
    ],
    "modules/local/hmf_purple.nf": [
        (r'^(?P<i>[ \t]*)tuple val\(meta\), path\("\$\{meta\.id\}\.purple\.h_summary\.tsv"\),(?P<s>[ \t]*)emit: summary[ \t]*$',
         lambda m: m.group(0) + "\n%stuple val(meta), path(\"${meta.id}.purple.log\"),%semit: log, optional: true   // %s" % (m.group("i"), " " * 14, MARKER), "purple log output"),
    ],
}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--root", default="."); ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(); planned = []; failed = False
    for rel, edits in EDITS.items():
        p = os.path.join(a.root, rel); print("== %s" % rel)
        if not os.path.isfile(p):
            print("   [error] not found"); failed = True; continue
        t = open(p).read()
        if MARKER in t:
            print("   [skip] already applied"); continue
        for pat, rep, label in edits:
            rx = re.compile(pat, re.M); n = len(rx.findall(t))
            if n != 1:
                print("   [error] %s: %d matches" % (label, n)); failed = True; break
            t = rx.sub(rep, t, count=1); print("   [ok] %s" % label)
        else:
            if rel.endswith(".py"):
                try:
                    compile(t, p, "exec")
                except SyntaxError as exc:
                    print("   [error] does not compile: %s" % exc); failed = True; continue
            print("   [check] markers %d (expected 1)" % t.count(MARKER))
            if t.count(MARKER) != 1:
                failed = True; continue
            planned.append((p, t))
    if failed:
        print("[error] nothing written"); sys.exit(1)
    if not a.apply:
        print("[dry-run] %d file(s) would change" % len(planned)); sys.exit(0)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    for p, t in planned:
        shutil.copy2(p, "%s.bak_hmf_purple_v1b_%s" % (p, ts)); open(p, "w").write(t); print("[patch] wrote %s" % p)


if __name__ == "__main__":
    main()
