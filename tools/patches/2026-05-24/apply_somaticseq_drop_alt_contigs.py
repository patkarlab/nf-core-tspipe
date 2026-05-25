#!/usr/bin/env python3
"""
apply_somaticseq_drop_alt_contigs.py

Adds an alt-contig/decoy filter to the SOMATICSEQ_ENSEMBLE process
(`modules/local/somaticseq.nf`) in its arbitrary-caller preprocessing
loop, immediately after the SV-allele filter and before the sort step.

Why
---
SomaticSeq enforces reference-dictionary ordering on its input VCFs
(chr1..chr22, chrX, chrY, chrM, then alt/decoy contigs). The module's
existing `sort -k1,1V -k2,2g` step misorders alt contigs: version sort
places `chr1_KI270706v1_random` between `chr1` and `chr2` because the
underscore sorts after digits in version-sort lexicography. SomaticSeq's
vcf2tsv then sees alt-contig records appearing before main-chromosome
records and rejects the file with:

    Exception: snv.arb_0.vcf does not seem to be properly sorted:
    chr1_KI270706v1_random 126253 then chrX 124090648.

The other variant callers (Mutect2, VarDict, VarScan, Strelka) escape
this because they sort their output using .dict-aware tooling. Only
the arbitrary-caller path uses `sort -V`.

What this patch does
--------------------
Inserts an awk filter that keeps only records on the canonical hg38
main chromosomes (chr1-chr22, chrX, chrY, chrM) before the sort/split.
Alt-contig somatic calls have no clinical interpretation in targeted
panel sequencing of unplaced sequence, so dropping them from the
SomaticSeq ensemble is safe. CNV calling and the upstream variant
callers still see the alt contig (no upstream cache invalidation).

Idempotency
-----------
Checks for the sentinel comment "Drop alt-contig and decoy records"
before applying. Re-running is a no-op.

Cache effect
------------
Modifying the module file invalidates Nextflow's resume cache for
SOMATICSEQ_ENSEMBLE and downstream only. Variant callers, CNV_CALLING,
FLT3_ITD, and preprocessing remain cached.

Usage
-----
    python3 tools/patches/2026-05-24/apply_somaticseq_drop_alt_contigs.py

Rollback
--------
    cp modules/local/somaticseq.nf.bak_apply_somaticseq_drop_alt_contigs_<ts> \
       modules/local/somaticseq.nf
"""

import datetime
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path("/goast/hemat_data/nf-core-tspipe")
TARGET    = REPO_ROOT / "modules" / "local" / "somaticseq.nf"

TS         = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK_SUFFIX = f".bak_apply_somaticseq_drop_alt_contigs_{TS}"

# Sentinel that exists in the patched file but not the original.
ALREADY_APPLIED_MARKER = "Drop alt-contig and decoy records"

# Anchor: the exact text in the current module.
# Backslash-escaped $ because this is a Groovy double-quoted string in .nf.
# Uses raw string literal r"..." to preserve backslashes faithfully.
OLD_BLOCK = r'''            N=\$N_FILT
            SRC="\$FILTERED"

            # Sort the source VCF (headers first, then chr/pos sort)
            SORTED="\${CALLER}.sorted.vcf"
            grep '^#'   "\$SRC" >  "\$SORTED"
            grep -v '^#' "\$SRC" | sort -k1,1V -k2,2g >> "\$SORTED"'''

# Replacement: same shape, with the new filter inserted before N=/SRC=.
# Note `\\t` in the awk = literal \t in the bash that runs in the container.
NEW_BLOCK = r'''            # ----------------------------------------------------------------
            # Drop alt-contig and decoy records (2026-05-24).
            # SomaticSeq enforces reference-dict ordering: chr1..chr22, chrX,
            # chrY, chrM, then alt/decoy. The `sort -V` below misorders alt
            # contigs (places chr1_KI270706v1_random between chr1 and chr2
            # because `_` sorts after digits in version-sort), and SomaticSeq's
            # vcf2tsv rejects the file. Alt-contig somatic calls have no
            # clinical interpretation in panel sequencing of unplaced sequence,
            # so dropping them here is safe. Upstream variant callers and
            # CNV_CALLING still see the alt contig.
            # ----------------------------------------------------------------
            PURGED="\${CALLER}.main_chroms_only.vcf"
            awk 'BEGIN{FS=OFS="\\t"} /^#/ {print; next} \$1 ~ /^chr([1-9]|1[0-9]|2[0-2]|X|Y|M)\$/ {print}' "\$FILTERED" > "\$PURGED"
            N_PURGE=\$(grep -cv '^#' "\$PURGED" 2>/dev/null) || N_PURGE=0
            DROPPED_ALT=\$((N_FILT - N_PURGE))
            if [ "\$DROPPED_ALT" -gt 0 ]; then
                echo "[somaticseq] \$CALLER: dropped \$DROPPED_ALT records on alt/decoy contigs" 1>&2
            fi
            if [ "\$N_PURGE" -eq 0 ]; then
                echo "[somaticseq] \$CALLER: no main-chromosome records after alt-drop, skipping" 1>&2
                continue
            fi

            N=\$N_PURGE
            SRC="\$PURGED"

            # Sort the source VCF (headers first, then chr/pos sort)
            SORTED="\${CALLER}.sorted.vcf"
            grep '^#'   "\$SRC" >  "\$SORTED"
            grep -v '^#' "\$SRC" | sort -k1,1V -k2,2g >> "\$SORTED"'''


def main() -> int:
    if not TARGET.exists():
        print(f"ERROR: target not found: {TARGET}", file=sys.stderr)
        return 1

    current = TARGET.read_text()

    if ALREADY_APPLIED_MARKER in current:
        print(f"No-op: {TARGET} already contains the alt-contig filter.")
        return 0

    if OLD_BLOCK not in current:
        print(
            f"ERROR: anchor block not found in {TARGET}.\n"
            f"The module may have diverged from the expected layout.",
            file=sys.stderr,
        )
        print(f"\nExpected anchor (first 200 chars):", file=sys.stderr)
        print(OLD_BLOCK[:200], file=sys.stderr)
        return 2

    count = current.count(OLD_BLOCK)
    if count > 1:
        print(
            f"ERROR: anchor matches {count} times; expected 1. "
            f"Refusing to patch ambiguously.",
            file=sys.stderr,
        )
        return 3

    # Backup
    backup = TARGET.with_name(TARGET.name + BAK_SUFFIX)
    shutil.copy2(TARGET, backup)
    print(f"Backed up: {backup}")

    # Apply
    new_content = current.replace(OLD_BLOCK, NEW_BLOCK, 1)
    TARGET.write_text(new_content)
    print(f"Patched:   {TARGET}")
    print()

    # Verify marker now exists
    if ALREADY_APPLIED_MARKER not in TARGET.read_text():
        print("ERROR: marker not present after write. Restoring backup.", file=sys.stderr)
        shutil.copy2(backup, TARGET)
        return 4

    print(f"To inspect the change:")
    print(f"  diff -u {backup} {TARGET}")
    print()
    print(f"To roll back:")
    print(f"  cp {backup} {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
