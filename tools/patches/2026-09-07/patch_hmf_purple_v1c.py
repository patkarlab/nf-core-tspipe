#!/usr/bin/env python3
"""
patch_hmf_purple_v1c.py -- PURPLE 4.4 QC file (MARKER HMF_PURPLE_V1c).
  bin/purple_gene_table.py: --qc is <id>.purple.qc, key<TAB>value lines
      (QCStatus, Method, ...); status comes from QCStatus there, method from
      Method; the purity file's 'status' column (fit method in 4.4) is the fallback
  modules/local/hmf_purple.nf: --qc purple/${meta.id}.purple.qc
"""
import argparse, datetime, os, re, shutil, sys

MARKER = "MARKER HMF_PURPLE_V1c"
EDITS = {
    "bin/purple_gene_table.py": [
        (r'''def read_one_row\(path\):
    with open\(path\) as fh:
        rows = list\(csv\.DictReader\(fh, delimiter="\\t"\)\)
    return rows\[0\] if rows else \{\}
''', '''def read_one_row(path):
    with open(path) as fh:
        rows = list(csv.DictReader(fh, delimiter="\\t"))
    return rows[0] if rows else {}


def read_key_value(path):
    """%s: <id>.purple.qc is key<TAB>value per line (QCStatus, Method, ...)."""
    out = {}
    with open(path) as fh:
        for line in fh:
            p = line.rstrip("\\n").split("\\t")
            if len(p) >= 2:
                out[p[0].strip()] = p[1].strip()
    return out
''' % MARKER, "read_key_value helper"),
        (r'''        qc = read_one_row\(args\.qc\) if args\.qc else \{\}
''', '''        qc = read_key_value(args.qc) if args.qc and os.path.isfile(args.qc) else {}
''', "qc parsed as key-value"),
        (r'''    status = pur\.get\("status"\) or qc\.get\("QCStatus"\) or "UNKNOWN"
    method = qc\.get\("Method", pur\.get\("fitMethod", "NA"\)\)
''', '''    status = qc.get("QCStatus") or pur.get("status") or "UNKNOWN"
    method = qc.get("Method") or pur.get("fitMethod") or pur.get("status") or "NA"
''', "status from QCStatus"),
        (r'^import argparse\nimport csv\nimport sys\n', 'import argparse\nimport csv\nimport os\nimport sys\n', "os import"),
    ],
    "modules/local/hmf_purple.nf": [
        (r'--qc purple/\$\{meta\.id\}\.purple\.purity\.qc', '--qc purple/${meta.id}.purple.qc', "qc path"),
        (r"^( \* modules/local/hmf_purple\.nf  \(HMF_PURPLE_V1; MARKER HMF_PURPLE_V1a: PURPLE 4\.4 option names)\)", r"\1; %s: .purple.qc)" % MARKER, "header"),
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
            t = rx.sub(rep if callable(rep) else (lambda m, r=rep: r), t, count=1); print("   [ok] %s" % label)
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
        shutil.copy2(p, "%s.bak_hmf_purple_v1c_%s" % (p, ts)); open(p, "w").write(t); print("[patch] wrote %s" % p)


if __name__ == "__main__":
    main()
