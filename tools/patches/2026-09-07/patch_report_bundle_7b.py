#!/usr/bin/env python3
"""
patch_report_bundle_7b.py -- REPORT_BUNDLE after CNV_RETIRE_7B.

tools/make_report_bundle.py still required and copied clinical/cnvkit_plots/,
which ORGANIZE_OUTPUT no longer produces (first resume after 6b7778c failed
REPORT_BUNDLE for all eight samples). The required tree is now clinical/cnv/.
modules/local/report_bundle.nf: version string 0.2 -> 0.3.

Dry run by default; --apply writes; .bak_bundle_7b_<ts> backups; idempotent.
"""
import argparse, os, re, sys, time

MARKER = "CNV_RETIRE_7B"
TAG = "bundle_7b"

EDITS = {
    "tools/make_report_bundle.py": [
        ("docstring layout in",
         """    <outdir>/<S>/clinical/cnvkit_plots/           (full subtree)
""",
         """    <outdir>/<S>/clinical/cnv/                    (full subtree; CNV_RETIRE_7B)
"""),
        ("docstring layout out",
         """    <S>/cnvkit_plots/...        (full subtree, copied in)
""",
         """    <S>/cnv/...                 (full subtree, copied in)
"""),
        ("required check",
         """    cnvkit_plots = clinical / "cnvkit_plots"
    if not cnvkit_plots.is_dir():
        raise RuntimeError(
            f"sample {sample}: cnvkit_plots/ directory missing: "
            f"{cnvkit_plots}"
        )
""",
         """    # CNV_RETIRE_7B: clinical/cnv/ (consensus, exon plots, chromosome pages, DECoN,
    # PURPLE, sex check, reconCNV) is the CNV deliverable; cnvkit_plots/ is gone.
    cnv_v2 = clinical / "cnv"
    if not cnv_v2.is_dir():
        raise RuntimeError(
            f"sample {sample}: cnv/ directory missing: "
            f"{cnv_v2}"
        )
"""),
        ("copy block",
         """        # Copy cnvkit_plots and assets as whole subtrees
        shutil.copytree(cnvkit_plots, staging / "cnvkit_plots")
        # MARKER DASH_CNV_V1a: v2 CNV tree (consensus, exon plots, chromosome pages, DECoN, PURPLE, sex check)
        cnv_v2 = clinical / "cnv"
        if cnv_v2.is_dir():
            shutil.copytree(cnv_v2, staging / "cnv")
        shutil.copytree(assets, staging / "assets")
""",
         """        # Copy the CNV tree and assets as whole subtrees
        # MARKER DASH_CNV_V1a: v2 CNV tree (consensus, exon plots, chromosome pages, DECoN, PURPLE, sex check)
        shutil.copytree(cnv_v2, staging / "cnv")
        shutil.copytree(assets, staging / "assets")
"""),
    ],
    "modules/local/report_bundle.nf": [
        ("version string",
         """            make_report_bundle: '0.2'
""",
         """            make_report_bundle: '0.3'   // CNV_RETIRE_7B
"""),
    ],
}


def flex_pattern(anchor):
    lines = anchor.rstrip("\n").split("\n")
    out = []
    for ln in lines:
        body = re.escape(ln.lstrip(" \t"))
        body = re.sub(r"(\\ )+", r"[ \\t]+", body)
        out.append(r"[ \t]*" + body)
    pat = r"\n".join(out)
    if anchor.endswith("\n"):
        pat += r"\n"
    return re.compile(pat)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.getcwd())
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    actions, errors = [], 0
    for rel, edits in EDITS.items():
        path = os.path.join(a.repo, rel)
        if not os.path.exists(path):
            print("[error] %s: missing" % rel); errors += 1; continue
        cur = open(path).read()
        if MARKER in cur:
            print("[skip] %s already carries %s" % (rel, MARKER)); continue
        new, ok = cur, True
        for label, old, rep in edits:
            hits = list(flex_pattern(old).finditer(new))
            if len(hits) != 1:
                print("[error] %s: anchor '%s' matched %d times" % (rel, label, len(hits))); ok = False; continue
            new = new[:hits[0].start()] + rep + new[hits[0].end():]
        if not ok:
            errors += 1; continue
        if new.count("{") - new.count("}") != cur.count("{") - cur.count("}"):
            print("[error] %s: brace balance changed" % rel); errors += 1; continue
        actions.append((rel, new))
    if errors:
        print("[error] %d problem(s); nothing written" % errors); sys.exit(1)
    if not actions:
        print("[ok] nothing to do"); return
    for rel, _ in actions:
        print("[plan] %s" % rel)
    if not a.apply:
        print("[dry-run] re-run with --apply"); return
    ts = time.strftime("%Y%m%d_%H%M%S")
    for rel, new in actions:
        path = os.path.join(a.repo, rel)
        bak = "%s.bak_%s_%s" % (path, TAG, ts)
        open(bak, "w").write(open(path).read()); os.chmod(bak, os.stat(path).st_mode)
        print("[backup] %s" % bak)
        open(path, "w").write(new)
        print("[patch] %s: %s x%d" % (rel, MARKER, new.count(MARKER)))


if __name__ == "__main__":
    main()
