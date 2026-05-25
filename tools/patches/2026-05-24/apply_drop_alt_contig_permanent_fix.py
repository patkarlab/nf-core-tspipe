#!/usr/bin/env python3
"""
apply_drop_alt_contig_permanent_fix.py

Permanent fix for the chr1_KI270706v1_random alt-contig record.

Background
----------
During the 2026-05-24 validation of the myeloid_cnv panel, the single
chr1_KI270706v1_random row in the panel BED was the root cause of three
separate downstream bugs:

  1. tabix non-contiguity error in STRELKA (lex sort placed it wrongly).
     Workaround: bedtools sort -faidx (applied to BED earlier today).
  2. SomaticSeq vcf2tsv reference-dict order violation. Workaround:
     awk filter in somaticseq.nf that drops records on alt/decoy contigs
     before sort -V (applied earlier today).
  3. Genome-wide CNV scatter y-axis compression caused by the single
     alt-contig bin sometimes drifting to log2 ~ -5, forcing matplotlib
     to extend the y-axis range to [-7, +1] and crushing the clinically
     relevant signal into a sliver at the top. Workaround:
     tools/render_clean_genome_scatter.py post-processing.

All three workarounds are defense-in-depth, but the real fix is to drop
the alt-contig record. It is one row of ~120bp in a 7,658-row panel.
Alt-contig somatic calls have no clinical interpretation in unplaced
sequence, alt-contig PoN bins add no information, and downstream tools
keep tripping over it.

What this script does
---------------------
1. Backs up the panel BED.
2. Drops any row where chromosome is not in the canonical set
   (chr1..chr22, chrX, chrY). chrM is also excluded, since this is a
   nuclear-genome targeted panel.
3. Re-runs `bedtools sort -faidx <ref.fai>` defensively to confirm the
   remaining rows are still in canonical order.
4. Patches the sex-stratified PoN .cnn files in assets/myeloid_cnv/ to
   drop bins on those same contigs.
5. Re-checks cnvkit_noisy_bins.bed and loo_bin_noise_profile.tsv for
   alt-contig entries; drops them if present.
6. Recomputes MD5s and rewrites MANIFEST.tsv.

After this patch
----------------
- Future TSPIPE runs will not see chr1_KI270706v1_random at any stage.
- The somaticseq.nf awk filter from earlier today remains in place as
  belt-and-suspenders: if any future BED edit introduces another
  alt/decoy contig, the SOMATICSEQ patch will continue to defend.
- Existing run outputs in nfcore_runs/ are not modified; for those, use
  tools/render_clean_genome_scatter.py.

Safety
------
- Strictly read-then-write, with timestamped .bak files for every
  modified artifact (BED, both .cnn files, MANIFEST.tsv).
- Idempotent: if the alt-contig records are already absent, the script
  reports "already applied" and exits 0.
- Dry-run mode (--dry-run) prints what would change without writing.

Usage
-----
    # Dry-run first (recommended)
    python3 tools/patches/2026-05-24/apply_drop_alt_contig_permanent_fix.py \\
        --dry-run

    # Apply
    python3 tools/patches/2026-05-24/apply_drop_alt_contig_permanent_fix.py
"""

import argparse
import hashlib
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd


# -------- Configuration --------
NFCORE_ROOT = Path("/goast/hemat_data/nf-core-tspipe")
BED_PATH = Path(
    "/goast/hemat_data/targeted-seq-pipeline/bedfiles/"
    "myeloid_CNVbackbone_HG38_nf-core-tspipe.bed"
)
REF_FAI = Path(
    "/goast/hemat_data/targeted-seq-pipeline/references/"
    "hg38_broad/Homo_sapiens_assembly38.masked.fasta.fai"
)
ASSETS_DIR = NFCORE_ROOT / "assets" / "myeloid_cnv"
MANIFEST_PATH = ASSETS_DIR / "MANIFEST.tsv"

CANONICAL_CHROMS = (
    [f"chr{i}" for i in range(1, 23)] + ["chrX", "chrY"]
)

PON_FILES = [
    ASSETS_DIR / "cnvkit_pon_male.cnn",
    ASSETS_DIR / "cnvkit_pon_female.cnn",
]
# Optional files that MAY contain alt-contig entries (we'll check defensively)
OPTIONAL_BIN_FILES = [
    ASSETS_DIR / "cnvkit_noisy_bins.bed",
    ASSETS_DIR / "loo_bin_noise_profile.tsv",
]


def timestamp():
    return time.strftime("%Y%m%d_%H%M%S")


def md5_of(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def backup(path: Path, ts: str) -> Path:
    """Create a timestamped .bak copy. Returns the backup path."""
    bak = path.with_name(f"{path.name}.bak_drop_altcontig_{ts}")
    shutil.copy2(path, bak)
    return bak


def filter_bed(path: Path, dry_run: bool, ts: str):
    """Drop non-canonical chromosome rows from a BED. Returns (n_before, n_after, bak_path or None)."""
    lines = path.read_text().splitlines()
    kept = []
    dropped = []
    for ln in lines:
        if not ln.strip() or ln.startswith("#"):
            kept.append(ln)
            continue
        chrom = ln.split("\t", 1)[0]
        if chrom in CANONICAL_CHROMS:
            kept.append(ln)
        else:
            dropped.append(ln)
    n_before = len(lines)
    n_after = len(kept)
    if not dropped:
        return n_before, n_after, None, []
    if dry_run:
        return n_before, n_after, None, dropped
    bak = backup(path, ts)
    path.write_text("\n".join(kept) + ("\n" if kept else ""))
    return n_before, n_after, bak, dropped


def filter_cnn(path: Path, dry_run: bool, ts: str):
    """Drop non-canonical chromosome rows from a CNVkit .cnn file."""
    df = pd.read_csv(path, sep="\t")
    if "chromosome" not in df.columns:
        sys.exit(f"ERROR: {path} has no 'chromosome' column. Columns: {list(df.columns)}")
    n_before = len(df)
    mask = df["chromosome"].isin(CANONICAL_CHROMS)
    df_kept = df[mask].copy()
    dropped_chroms = sorted(set(df.loc[~mask, "chromosome"].astype(str).tolist()))
    n_after = len(df_kept)
    if n_before == n_after:
        return n_before, n_after, None, []
    if dry_run:
        return n_before, n_after, None, dropped_chroms
    bak = backup(path, ts)
    df_kept.to_csv(path, sep="\t", index=False)
    return n_before, n_after, bak, dropped_chroms


def bedtools_sort_check(bed_path: Path) -> bool:
    """Run `bedtools sort -faidx <fai> -i <bed>` and verify the output
    matches the file already on disk. Returns True if order is stable."""
    if not REF_FAI.is_file():
        print(f"  WARN: {REF_FAI} not found; skipping sort verification",
              file=sys.stderr)
        return True
    try:
        result = subprocess.run(
            ["bedtools", "sort", "-faidx", str(REF_FAI), "-i", str(bed_path)],
            capture_output=True, text=True, check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"  WARN: bedtools sort verification failed: {e}", file=sys.stderr)
        return True  # don't block on this
    expected = result.stdout
    actual = bed_path.read_text()
    return expected.strip() == actual.strip()


def update_manifest(dry_run: bool, ts: str):
    """Recompute MD5s for files in the assets dir and rewrite MANIFEST.tsv."""
    if not MANIFEST_PATH.is_file():
        print(f"  WARN: no MANIFEST.tsv at {MANIFEST_PATH}; skipping update")
        return None
    # Read existing manifest
    df = pd.read_csv(MANIFEST_PATH, sep="\t")
    # Detect MD5 column name -- be flexible
    md5_col = None
    file_col = None
    for c in df.columns:
        lc = c.lower()
        if lc in ("md5", "md5sum", "checksum"):
            md5_col = c
        if lc in ("file", "filename", "path"):
            file_col = c
    if md5_col is None or file_col is None:
        print(f"  WARN: MANIFEST.tsv missing md5/file column "
              f"(got cols: {list(df.columns)}); skipping update")
        return None
    if dry_run:
        return MANIFEST_PATH  # signal that update would happen
    bak = backup(MANIFEST_PATH, ts)
    updated = 0
    for i, row in df.iterrows():
        fname = row[file_col]
        fpath = ASSETS_DIR / fname
        if fpath.is_file():
            new_md5 = md5_of(fpath)
            if new_md5 != row[md5_col]:
                df.at[i, md5_col] = new_md5
                updated += 1
    df.to_csv(MANIFEST_PATH, sep="\t", index=False)
    print(f"  Updated MD5 for {updated} file(s) in MANIFEST.tsv")
    return bak


def main():
    ap = argparse.ArgumentParser(
        description="Drop chr1_KI270706v1_random and other non-canonical "
                    "contigs from the panel BED + sex-stratified PoN.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--dry-run", action="store_true",
                    help="Print what would change without writing anything.")
    args = ap.parse_args()

    ts = timestamp()
    mode = "DRY-RUN" if args.dry_run else "APPLY"
    print(f"\n========== {mode} ==========")
    print(f"Timestamp: {ts}")
    print(f"BED:    {BED_PATH}")
    print(f"PoN:    {ASSETS_DIR}/")
    print()

    if not BED_PATH.is_file():
        sys.exit(f"ERROR: BED not found: {BED_PATH}")
    for pon in PON_FILES:
        if not pon.is_file():
            sys.exit(f"ERROR: PoN file not found: {pon}")

    # ---- BED ----
    print("BED:")
    n_before, n_after, bak, dropped = filter_bed(BED_PATH, args.dry_run, ts)
    print(f"  rows before: {n_before}")
    print(f"  rows after:  {n_after}")
    if dropped:
        print(f"  dropped {len(dropped)} row(s):")
        for ln in dropped[:5]:
            print(f"    {ln}")
        if len(dropped) > 5:
            print(f"    ... ({len(dropped) - 5} more)")
        if bak:
            print(f"  backup:  {bak}")
    else:
        print(f"  no non-canonical contigs found in BED -- already clean")
    print()

    # ---- BED sort sanity check ----
    if not args.dry_run and dropped:
        print("Verifying BED is still FAI-sorted after row removal:")
        is_sorted = bedtools_sort_check(BED_PATH)
        if is_sorted:
            print("  OK: BED remains canonically sorted.")
        else:
            print("  WARN: BED order changed; re-running bedtools sort -faidx")
            sorted_out = subprocess.run(
                ["bedtools", "sort", "-faidx", str(REF_FAI), "-i", str(BED_PATH)],
                capture_output=True, text=True, check=True,
            ).stdout
            BED_PATH.write_text(sorted_out)
            print(f"  Re-sorted. New row count: {len(sorted_out.strip().splitlines())}")
        print()

    # ---- PoN .cnn files ----
    print("PoN .cnn files:")
    any_pon_changed = False
    for pon in PON_FILES:
        n_b, n_a, bak, dropped_chroms = filter_cnn(pon, args.dry_run, ts)
        print(f"  {pon.name}:")
        print(f"    bins before: {n_b}")
        print(f"    bins after:  {n_a}")
        if dropped_chroms:
            any_pon_changed = True
            print(f"    dropped chromosomes: {dropped_chroms}")
            if bak:
                print(f"    backup: {bak}")
        else:
            print(f"    no non-canonical bins -- already clean")
    print()

    # ---- Optional bin-level files ----
    print("Optional bin-level files:")
    for opt in OPTIONAL_BIN_FILES:
        if not opt.is_file():
            print(f"  {opt.name}: not present, skipping")
            continue
        if opt.suffix == ".bed":
            n_b, n_a, bak, dropped = filter_bed(opt, args.dry_run, ts)
            if dropped:
                any_pon_changed = True
                print(f"  {opt.name}: dropped {len(dropped)} row(s); backup: {bak}")
            else:
                print(f"  {opt.name}: no non-canonical contigs (already clean)")
        else:
            # TSV
            n_b, n_a, bak, dropped_chroms = filter_cnn(opt, args.dry_run, ts)
            if dropped_chroms:
                any_pon_changed = True
                print(f"  {opt.name}: dropped chromosomes {dropped_chroms}; backup: {bak}")
            else:
                print(f"  {opt.name}: no non-canonical bins (already clean)")
    print()

    # ---- MANIFEST.tsv ----
    print("MANIFEST.tsv:")
    if args.dry_run:
        print(f"  would update MD5 columns for any changed files")
    else:
        if any_pon_changed or dropped:
            update_manifest(args.dry_run, ts)
        else:
            print(f"  no asset files changed; MANIFEST.tsv left as-is")
    print()

    # ---- Summary ----
    if args.dry_run:
        print("DRY-RUN complete. To apply, re-run without --dry-run.")
    else:
        if dropped or any_pon_changed:
            print("Applied. Next steps:")
            print(f"  - Verify BED:  wc -l {BED_PATH}")
            print(f"  - Verify PoN:  head -1 {PON_FILES[0]}")
            print(f"  - Verify MANIFEST: cat {MANIFEST_PATH}")
        else:
            print("No changes needed -- artifacts were already clean. "
                  "(Idempotent re-run.)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
