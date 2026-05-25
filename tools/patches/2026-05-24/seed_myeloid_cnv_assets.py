#!/usr/bin/env python3
"""
seed_myeloid_cnv_assets.py

Seeds assets/myeloid_cnv/ from the artifacts produced by a completed
BUILD_PON --panel myeloid_cnv run. Sources files from two locations:

    --outdir    BUILD_PON outdir (sex-stratified PoN and sex assignment)
    --work-loo  Nextflow work dir for the CNV_LOO_QC process
                (LOO summary, noisy bins, bin noise profile -- these
                failed to publishDir-link in the 2026-05-24 run, so we
                source them directly from the work dir)

Layout produced
---------------
    assets/myeloid_cnv/
        cnvkit_pon_male.cnn               (BUILD_SEX_PON, outdir)
        cnvkit_pon_female.cnn             (BUILD_SEX_PON, outdir)
        cnvkit_loo_summary.tsv            (CNV_LOO_QC, work dir)
        cnvkit_noisy_bins.bed             (CNV_LOO_QC, work dir)
        loo_bin_noise_profile.tsv         (CNV_LOO_QC, work dir)
        cnvkit_pon_sex_assignment.tsv     (BUILD_SEX_PON, outdir; provenance)
        MANIFEST.tsv                      (generated -- per-file md5 + source)

These five "consumer" filenames match exactly the asset-default fallback
paths declared in nextflow.config:
    cnv_pon_male       -> assets/${panel}/cnvkit_pon_male.cnn
    cnv_pon_female     -> assets/${panel}/cnvkit_pon_female.cnn
    cnv_loo_summary    -> assets/${panel}/cnvkit_loo_summary.tsv
    cnv_noisy_bins     -> assets/${panel}/cnvkit_noisy_bins.bed
    cnv_noise_profile  -> assets/${panel}/loo_bin_noise_profile.tsv
so TSPIPE runs with --panel myeloid_cnv will pick these up via the
fallback without any per-param --cnv_pon_* CLI flags.

The sex-assignment TSV is included for audit but isn't consumed by any
TSPIPE param.

NOT seeded (user action required)
---------------------------------
    cnv_scatter_regions.txt
        The existing assets/myeloid/cnv_scatter_regions.txt was
        hand-curated for the legacy MYOPOOL panel. The myeloid_cnv panel
        adds a 3,069-tile CNV backbone, so the scatter regions list may
        need extending. This script does NOT fabricate one.

Safety
------
- Pre-flight reads every source file and validates format/size BEFORE
  touching the destination. Any failure aborts without partial seeding.
- Destination md5 is re-computed after copy and compared to the source
  md5; mismatch aborts.
- Refuses to write into a non-empty assets/myeloid_cnv/ unless --force.

Usage
-----
    python3 tools/patches/2026-05-24/seed_myeloid_cnv_assets.py \\
        --outdir   /goast/hemat_data/nfcore_runs/pon_myeloid_cnv_20260524_104140 \\
        --work-loo /goast/hemat_data/nf-core-tspipe/work/74/4a45951314871dadf957b5afd259ef
"""

import argparse
import datetime
import hashlib
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path("/goast/hemat_data/nf-core-tspipe")
ASSET_DIR = REPO_ROOT / "assets" / "myeloid_cnv"


SOURCES = [
    {
        "dest":      "cnvkit_pon_male.cnn",
        "from":      "outdir",
        "rel":       Path("pon") / "cnvkit_pon_male.cnn",
        "validate":  "cnvkit_cnn",
        "min_bytes": 1_000_000,
    },
    {
        "dest":      "cnvkit_pon_female.cnn",
        "from":      "outdir",
        "rel":       Path("pon") / "cnvkit_pon_female.cnn",
        "validate":  "cnvkit_cnn",
        "min_bytes": 1_000_000,
    },
    {
        "dest":      "cnvkit_loo_summary.tsv",
        "from":      "work_loo",
        "rel":       Path("references") / "myeloid_cnv" / "cnvkit_loo_summary.tsv",
        "validate":  "loo_summary_tsv",
        "min_bytes": 1_000,
    },
    {
        "dest":      "cnvkit_noisy_bins.bed",
        "from":      "work_loo",
        "rel":       Path("references") / "myeloid_cnv" / "cnvkit_noisy_bins.bed",
        "validate":  "bed",
        "min_bytes": 1_000,
    },
    {
        "dest":      "loo_bin_noise_profile.tsv",
        "from":      "work_loo",
        "rel":       Path("loo_qc") / "loo_bin_noise_profile.tsv",
        "validate":  "noise_profile_tsv",
        "min_bytes": 100_000,
    },
    {
        "dest":      "cnvkit_pon_sex_assignment.tsv",
        "from":      "outdir",
        "rel":       Path("pon") / "cnvkit_pon_sex_assignment.tsv",
        "validate":  "sex_assignment_tsv",
        "min_bytes": 100,
    },
]


def md5_of(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(64 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


# ---- Validators -----------------------------------------------------------
# Each returns (ok: bool, message: str).


def validate_cnvkit_cnn(path: Path) -> tuple[bool, str]:
    """CNVkit .cnn mandatory columns: chromosome, start, end, gene, log2.
    Optional columns vary by build path (depth, spread, weight, gc, rmask):
    target coverage .cnn includes weight; cnvkit.py reference output may
    have spread instead of (or alongside) weight depending on cnvkit version.
    """
    with path.open() as f:
        header = f.readline().rstrip("\n").split("\t")
    required = {"chromosome", "start", "end", "gene", "log2"}
    missing = required - set(header)
    if missing:
        return False, f"missing required CNVkit .cnn columns: {sorted(missing)}"
    # Count data rows for sanity
    with path.open() as f:
        n_rows = sum(1 for _ in f) - 1
    return True, f"ok ({len(header)} cols, {n_rows} bins)"


def validate_loo_summary_tsv(path: Path) -> tuple[bool, str]:
    with path.open() as f:
        header = f.readline().rstrip("\n").split("\t")
    expected = {"gene", "chromosome", "mean_log2", "stdev_log2", "n_samples"}
    missing = expected - set(header)
    if missing:
        return False, f"missing LOO summary columns: {sorted(missing)}"
    with path.open() as f:
        n_rows = sum(1 for _ in f) - 1
    if n_rows < 10:
        return False, f"only {n_rows} data rows (expected >=10)"
    return True, f"ok ({n_rows} genes)"


def validate_noise_profile_tsv(path: Path) -> tuple[bool, str]:
    with path.open() as f:
        header = f.readline().rstrip("\n").split("\t")
    if "stdev_log2" not in header and "stdev" not in header:
        return False, f"no stdev column in header: {header}"
    with path.open() as f:
        n_rows = sum(1 for _ in f) - 1
    if n_rows < 1000:
        return False, f"only {n_rows} bin rows (expected >>1000)"
    return True, f"ok ({n_rows} bins)"


def validate_bed(path: Path) -> tuple[bool, str]:
    with path.open() as f:
        first = f.readline().rstrip("\n")
    cols = first.split("\t")
    if not first.startswith("chr") or len(cols) < 3:
        return False, f"first row not BED-shaped: {first[:80]}"
    try:
        int(cols[1]); int(cols[2])
    except (IndexError, ValueError):
        return False, "start/end columns not integers"
    with path.open() as f:
        n_rows = sum(1 for _ in f)
    return True, f"ok ({n_rows} bins)"


def validate_sex_assignment_tsv(path: Path) -> tuple[bool, str]:
    with path.open() as f:
        header = f.readline().rstrip("\n").split("\t")
    if not {"sample", "sex"}.issubset(set(header)):
        return False, f"missing required columns; got {header}"
    sex_idx = header.index("sex")
    rows = path.read_text().splitlines()[1:]
    n_male   = sum(1 for r in rows if len(r.split("\t")) > sex_idx
                   and r.split("\t")[sex_idx] == "male")
    n_female = sum(1 for r in rows if len(r.split("\t")) > sex_idx
                   and r.split("\t")[sex_idx] == "female")
    return True, f"ok ({n_male} male, {n_female} female)"


VALIDATORS = {
    "cnvkit_cnn":         validate_cnvkit_cnn,
    "loo_summary_tsv":    validate_loo_summary_tsv,
    "noise_profile_tsv":  validate_noise_profile_tsv,
    "bed":                validate_bed,
    "sex_assignment_tsv": validate_sex_assignment_tsv,
}


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Seed assets/myeloid_cnv/ from a completed BUILD_PON run.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--outdir",   type=Path, required=True,
                    help="BUILD_PON outdir (contains pon/cnvkit_pon_{male,female}.cnn)")
    ap.add_argument("--work-loo", type=Path, required=True,
                    help="Nextflow CNV_LOO_QC work dir (contains references/myeloid_cnv/ and loo_qc/)")
    ap.add_argument("--force",    action="store_true",
                    help="Overwrite existing assets/myeloid_cnv/ contents.")
    args = ap.parse_args()

    # ---- Pre-flight 1: source roots ----
    if not args.outdir.is_dir():
        print(f"ERROR: --outdir not a directory: {args.outdir}", file=sys.stderr)
        return 1
    if not args.work_loo.is_dir():
        print(f"ERROR: --work-loo not a directory: {args.work_loo}", file=sys.stderr)
        return 1

    source_roots = {"outdir": args.outdir, "work_loo": args.work_loo}

    # ---- Pre-flight 2: every source file exists, big enough, and validates ----
    plans = []
    for spec in SOURCES:
        src = source_roots[spec["from"]] / spec["rel"]
        if not src.is_file():
            print(f"ERROR: source missing: {src}", file=sys.stderr)
            return 2
        size = src.stat().st_size
        if size < spec["min_bytes"]:
            print(
                f"ERROR: {src.name} too small ({size} B, expected >= {spec['min_bytes']} B); "
                f"refusing to seed a truncated artifact",
                file=sys.stderr,
            )
            return 3
        ok, vmsg = VALIDATORS[spec["validate"]](src)
        if not ok:
            print(f"ERROR: {src.name} failed validation ({spec['validate']}): {vmsg}",
                  file=sys.stderr)
            return 4
        plans.append((spec, src, size, vmsg))

    # ---- Pre-flight 3: destination ----
    if ASSET_DIR.exists() and any(ASSET_DIR.iterdir()) and not args.force:
        print(
            f"ERROR: {ASSET_DIR} is non-empty. Pass --force to overwrite.",
            file=sys.stderr,
        )
        return 5
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    # ---- Copy + verify ----
    now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    manifest_rows = [
        ["dest_filename", "source_path", "md5", "size_bytes", "source_mtime_utc", "validation"]
    ]

    print(f"Seeding {ASSET_DIR}/:")
    print(f"  {'file':<35} {'md5':<34} {'size':>12}  validation")
    for spec, src, size, vmsg in plans:
        dst = ASSET_DIR / spec["dest"]
        shutil.copy2(src, dst)
        src_md5 = md5_of(src)
        dst_md5 = md5_of(dst)
        if src_md5 != dst_md5:
            print(f"ERROR: md5 mismatch after copy: {src} -> {dst}\n"
                  f"  source: {src_md5}\n  dest:   {dst_md5}", file=sys.stderr)
            return 6
        src_mtime = datetime.datetime.fromtimestamp(
            src.stat().st_mtime, tz=datetime.timezone.utc
        ).isoformat(timespec="seconds")
        manifest_rows.append(
            [spec["dest"], str(src), src_md5, str(size), src_mtime, vmsg]
        )
        print(f"  {spec['dest']:<35} {src_md5}  {size:>10} B  {vmsg}")

    manifest_path = ASSET_DIR / "MANIFEST.tsv"
    with manifest_path.open("w") as f:
        f.write(f"# Seeded:    {now_utc}\n")
        f.write(f"# Outdir:    {args.outdir}\n")
        f.write(f"# Work LOO:  {args.work_loo}\n")
        f.write(f"# Script:    {Path(__file__).name}\n")
        for row in manifest_rows:
            f.write("\t".join(row) + "\n")
    print(f"\nMANIFEST.tsv written: {manifest_path}")

    # ---- Reminder ----
    legacy_scatter = REPO_ROOT / "assets" / "myeloid" / "cnv_scatter_regions.txt"
    print()
    print("=" * 72)
    print("ACTION REQUIRED")
    print("=" * 72)
    print("cnv_scatter_regions.txt was NOT seeded. The existing file at:")
    print(f"  {legacy_scatter}")
    print("was hand-curated for the legacy MYOPOOL panel. The myeloid_cnv panel")
    print("adds 3,069 backbone bins genome-wide. Decide whether to:")
    print("  - copy the legacy file verbatim (if the scatter regions still apply), OR")
    print("  - extend it with backbone regions of interest, OR")
    print("  - regenerate from scratch against the new BED.")
    print()
    print("Once cnv_scatter_regions.txt is in place, assets/myeloid_cnv/ is complete")
    print("and TSPIPE --panel myeloid_cnv will resolve all CNV params via the asset")
    print("fallback (no --cnv_pon_* CLI flags needed).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
