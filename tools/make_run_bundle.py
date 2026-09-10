#!/usr/bin/env python3
"""
make_run_bundle.py  (RUN_BUNDLE_V1)

Build ONE shareable zip for a whole TSPIPE run (batch), complementing the per-sample
bundles made by tools/make_report_bundle.py.

    <outdir>/<name>_reports.zip   unpacks to   <name>_reports/
        cohort_index.html                 (links rewritten to <S>/<S>_report.html)
        assets/                           (shared CSS/JS, once)
        <S>/<S>_report.html               (../../assets/ -> ../assets/ ; ../../cohort_index.html -> ../cohort_index.html)
        <S>/<S>_dashboard.html            (byte copy)
        <S>/<S>_fastp.html                (byte copy)
        <S>/<S>_igv_report.html           (byte copy)
        <S>/cnv/...                       (full subtree: consensus, chromosome pages incl. 17p, PURPLE, ...)

Not included: BAM/BAI, raw TSV/VCF, caches - as in the per-sample bundles.

Inputs are read from the published outdir (same as the per-sample bundler):
    <outdir>/cohort_index.html
    <outdir>/assets/
    <outdir>/<S>/clinical/<S>_{report,dashboard,fastp,igv_report}.html
    <outdir>/<S>/clinical/cnv/

Usage:
    make_run_bundle.py --outdir <outdir> [--name <run>] [--samples S1 S2 ...] [--out <zip>] [--force]
Standard library only.
"""
import argparse
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

REPORT_ASSET_RE = re.compile(r"""((?:href|src))=(["'])\.\./\.\./assets/""", re.IGNORECASE)
REPORT_COHORT_RE = re.compile(r"""((?:href))=(["'])\.\./\.\./cohort_index\.html""", re.IGNORECASE)
LEFTOVER_RE = re.compile(r"""(?:href|src)=["']\.\./\.\./""", re.IGNORECASE)
# cohort index: href="./<S>/<anything>/<S>_report.html"  ->  href="./<S>/<S>_report.html"
INDEX_LINK_RE = re.compile(r"""(href=["'])\./([^/"']+)/(?:[^"']*?/)?\2_report\.html(["'])""", re.IGNORECASE)


def fmt_bytes(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return "%.1f %s" % (n, unit) if unit != "B" else "%d B" % n
        n /= 1024.0
    return "%d B" % n


def find_samples(outdir):
    out = []
    for d in sorted(p for p in outdir.iterdir() if p.is_dir()):
        if (d / "clinical" / ("%s_report.html" % d.name)).is_file():
            out.append(d)
    return out


def stage_sample(sample_dir, staging, stats):
    sample = sample_dir.name
    clinical = sample_dir / "clinical"
    need = [clinical / ("%s_%s.html" % (sample, k)) for k in ("report", "dashboard", "fastp", "igv_report")]
    missing = [str(f) for f in need if not f.is_file()]
    if missing:
        raise RuntimeError("%s: missing %s" % (sample, ", ".join(missing)))
    cnv = clinical / "cnv"
    if not cnv.is_dir():
        raise RuntimeError("%s: cnv/ directory missing" % sample)
    dst = staging / sample
    dst.mkdir()
    for f in need[1:]:
        shutil.copy2(f, dst / f.name)
    shutil.copytree(cnv, dst / "cnv")
    text = need[0].read_text(encoding="utf-8")
    text, n_assets = REPORT_ASSET_RE.subn(r"\1=\2../assets/", text)
    text, n_cohort = REPORT_COHORT_RE.subn(r"\1=\2../cohort_index.html", text)
    left = len(LEFTOVER_RE.findall(text))
    if left:
        stats["warnings"].append("%s: %d '../../' reference(s) left in the report" % (sample, left))
    (dst / need[0].name).write_text(text, encoding="utf-8")
    stats["samples"][sample] = {"assets_rewritten": n_assets, "cohort_links_rewritten": n_cohort}


def stage_index(outdir, staging, samples, stats):
    src = outdir / "cohort_index.html"
    if not src.is_file():
        stats["warnings"].append("cohort_index.html not found in the outdir; bundle has no index")
        return
    text = src.read_text(encoding="utf-8")
    text, n = INDEX_LINK_RE.subn(r"\1./\2/\2_report.html\3", text)
    stats["index_links_rewritten"] = n
    for s in samples:
        if ("./%s/%s_report.html" % (s, s)) not in text:
            stats["warnings"].append("cohort index has no link to %s" % s)
    (staging / "cohort_index.html").write_text(text, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--outdir", type=Path, required=True)
    ap.add_argument("--name", default=None, help="bundle name (default: outdir basename)")
    ap.add_argument("--samples", nargs="+", default=None, help="subset of samples (default: all found)")
    ap.add_argument("--out", type=Path, default=None, help="zip path (default: <outdir>/<name>_reports.zip)")
    ap.add_argument("--force", action="store_true", help="overwrite an existing zip")
    args = ap.parse_args()

    outdir = args.outdir.resolve()
    if not outdir.is_dir():
        sys.exit("ERROR: outdir not a directory: %s" % outdir)
    name = args.name or outdir.name
    top = "%s_reports" % name
    zip_path = args.out or (outdir / ("%s.zip" % top))
    assets = outdir / "assets"
    if not assets.is_dir():
        sys.exit("ERROR: %s missing" % assets)
    if args.samples:
        sample_dirs = [outdir / s for s in args.samples]
        for d in sample_dirs:
            if not (d / "clinical" / ("%s_report.html" % d.name)).is_file():
                sys.exit("ERROR: no report for %s" % d.name)
    else:
        sample_dirs = find_samples(outdir)
    if not sample_dirs:
        sys.exit("ERROR: no <S>/clinical/<S>_report.html under %s" % outdir)
    if zip_path.exists():
        if not args.force:
            sys.exit("ERROR: %s exists (use --force)" % zip_path)
        zip_path.unlink()

    stats = {"samples": {}, "warnings": [], "index_links_rewritten": 0}
    with tempfile.TemporaryDirectory(prefix="run_bundle_") as tmp:
        staging = Path(tmp) / top
        staging.mkdir()
        shutil.copytree(assets, staging / "assets")
        names = []
        for d in sample_dirs:
            stage_sample(d, staging, stats)
            names.append(d.name)
        stage_index(outdir, staging, names, stats)
        n_files = sum(1 for p in staging.rglob("*") if p.is_file())
        raw = sum(p.stat().st_size for p in staging.rglob("*") if p.is_file())
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in sorted(staging.rglob("*")):
                if p.is_file():
                    zf.write(p, (Path(top) / p.relative_to(staging)).as_posix())

    print("Run bundle: %s" % zip_path)
    print("  samples: %d (%s)" % (len(names), ", ".join(names)))
    for s, st in stats["samples"].items():
        print("  %-24s assets %d  cohort link %d" % (s, st["assets_rewritten"], st["cohort_links_rewritten"]))
    print("  cohort index links rewritten: %d" % stats["index_links_rewritten"])
    print("  contents: %d files, %s raw; zip %s" % (n_files, fmt_bytes(raw), fmt_bytes(zip_path.stat().st_size)))
    for w in stats["warnings"]:
        print("  WARNING: %s" % w)
    return 1 if stats["warnings"] else 0


if __name__ == "__main__":
    sys.exit(main())
