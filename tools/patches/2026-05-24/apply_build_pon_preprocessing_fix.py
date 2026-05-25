#!/usr/bin/env python3
"""
apply_build_pon_preprocessing_fix.py

Fixes BUILD_PON's stale PREPROCESSING invocation in workflows/build_pon.nf.

Background
----------
TSPIPE calls PREPROCESSING with 6 channels (workflows/tspipe.nf:120):

    PREPROCESSING(ch_input, ch_reference, ch_bed,
                  ch_exonwise_bed, ch_dbsnp, ch_mills)

BUILD_PON was last updated when PREPROCESSING had a 3-channel signature,
producing the runtime error first surfaced by the 2026-05-24 stub run:

    Workflow `BUILD_PON:PREPROCESSING` declares 6 input channels but 3 were given
     -- Check script 'workflows/build_pon.nf' at line: 67

This script brings BUILD_PON's invocation in line with TSPIPE's, mirroring
the value-channel construction patterns from workflows/tspipe.nf so the
PoN-build path benefits from the same proven channel shapes.

Changes
-------
1. Adds --exonwise_bed, --dbsnp_vcf, --mills_vcf to the Validate block so
   missing params fail with a clear message instead of a cryptic Nextflow
   stack trace.
2. Converts ch_bed from a queue channel (Channel.fromPath) to a value
   channel (Channel.value). Closes the open item from 2026-05-16 about
   ch_bed being a queue channel; even though only PREPROCESSING consumes
   ch_bed in BUILD_PON, several downstream processes inside PREPROCESSING
   itself (fastp, BWA, mosdepth) read it.
3. Constructs ch_exonwise_bed, ch_dbsnp, ch_mills using the exact patterns
   from tspipe.nf lines 47-65.
4. Passes all 6 channels into PREPROCESSING(...) at the existing call site.

Safety
------
- Aborts cleanly if the target file content has drifted from the expected
  baseline (the str.replace pre-flight counts each old-string occurrence
  and refuses to proceed if not exactly 1).
- Writes workflows/build_pon.nf.bak_apply_build_pon_preprocessing_fix_<ts>
  before modifying.
- Idempotent: re-running after a successful apply detects the 6-channel
  marker and exits 0 with no changes.

Usage
-----
    python3 tools/patches/2026-05-24/apply_build_pon_preprocessing_fix.py

Rollback
--------
    cp workflows/build_pon.nf.bak_apply_build_pon_preprocessing_fix_<ts> \\
       workflows/build_pon.nf
"""

import datetime
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path("/goast/hemat_data/nf-core-tspipe")
TARGET = REPO_ROOT / "workflows" / "build_pon.nf"
TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BAK_SUFFIX = f".bak_apply_build_pon_preprocessing_fix_{TS}"

# -----------------------------------------------------------------------------
# Edit 1: validation block
# -----------------------------------------------------------------------------

VALIDATE_OLD = """    // ----- Validate -----------------------------------------------------
    if (!params.input)     { error "Missing --input (samplesheet of normals)"   }
    if (!params.reference) { error "Missing --reference (hg38 masked FASTA)"    }
    if (!params.bed)       { error "Missing --bed (panel BED)"                  }"""

VALIDATE_NEW = """    // ----- Validate -----------------------------------------------------
    if (!params.input)        { error "Missing --input (samplesheet of normals)"     }
    if (!params.reference)    { error "Missing --reference (hg38 masked FASTA)"      }
    if (!params.bed)          { error "Missing --bed (panel BED)"                    }
    if (!params.exonwise_bed) { error "Missing --exonwise_bed (exon-collapsed BED for mosdepth)" }
    if (!params.dbsnp_vcf)    { error "Missing --dbsnp_vcf (BQSR known-sites)"       }
    if (!params.mills_vcf)    { error "Missing --mills_vcf (BQSR known-sites)"       }"""

# -----------------------------------------------------------------------------
# Edit 2: channel construction
# -----------------------------------------------------------------------------

CHANNELS_OLD = """    ch_bed       = Channel.fromPath(params.bed, checkIfExists: true)"""

CHANNELS_NEW = """    // ch_bed is a VALUE channel (matches TSPIPE): a queue channel of a single
    // element would be consumed by the first downstream process and starve
    // subsequent consumers (fastp, BWA, mosdepth all read ch_bed).
    ch_bed          = Channel.value(file(params.bed, checkIfExists: true))
    ch_exonwise_bed = Channel.value(file(params.exonwise_bed, checkIfExists: true))

    // Known-sites VCFs for BQSR. Each tuple is [vcf, tbi]. Mirrors TSPIPE.
    ch_dbsnp = Channel.value([
        file(params.dbsnp_vcf, checkIfExists: true),
        file(params.dbsnp_vcf + '.tbi', checkIfExists: true)
    ])
    ch_mills = Channel.value([
        file(params.mills_vcf, checkIfExists: true),
        file(params.mills_vcf + '.tbi', checkIfExists: true)
    ])"""

# -----------------------------------------------------------------------------
# Edit 3: PREPROCESSING call
# -----------------------------------------------------------------------------

CALL_OLD = """    PREPROCESSING(ch_normals, ch_reference, ch_bed)"""
CALL_NEW = """    PREPROCESSING(ch_normals, ch_reference, ch_bed, ch_exonwise_bed, ch_dbsnp, ch_mills)"""

# -----------------------------------------------------------------------------
# Idempotency marker (unique post-fix string)
# -----------------------------------------------------------------------------

ALREADY_APPLIED_MARKER = (
    "PREPROCESSING(ch_normals, ch_reference, ch_bed, "
    "ch_exonwise_bed, ch_dbsnp, ch_mills)"
)


def main() -> int:
    if not TARGET.exists():
        print(f"ERROR: target not found: {TARGET}", file=sys.stderr)
        return 1

    content = TARGET.read_text()

    if ALREADY_APPLIED_MARKER in content:
        print(f"No-op: {TARGET} already shows the 6-channel PREPROCESSING call.")
        return 0

    # Pre-flight: every OLD chunk must appear exactly once. If any block has
    # drifted (whitespace, edits, etc.), abort BEFORE writing the backup so
    # we don't leave a partially-applied file behind.
    edits = [
        ("validation block", VALIDATE_OLD, VALIDATE_NEW),
        ("channel construction", CHANNELS_OLD, CHANNELS_NEW),
        ("PREPROCESSING call", CALL_OLD, CALL_NEW),
    ]
    for name, old, _new in edits:
        count = content.count(old)
        if count != 1:
            print(
                f"ERROR: expected exactly 1 occurrence of '{name}' baseline, "
                f"found {count}. File may have drifted; aborting without changes.",
                file=sys.stderr,
            )
            return 2

    # Backup
    backup = TARGET.with_name(TARGET.name + BAK_SUFFIX)
    shutil.copy2(TARGET, backup)
    print(f"Backed up: {backup}")

    # Apply
    new_content = content
    for _name, old, new in edits:
        new_content = new_content.replace(old, new)

    TARGET.write_text(new_content)
    print(f"Patched:   {TARGET}")
    print()
    print("Edits applied:")
    print("  1. Validate block now checks --exonwise_bed, --dbsnp_vcf, --mills_vcf")
    print("  2. ch_bed converted to value channel; ch_exonwise_bed/ch_dbsnp/ch_mills added")
    print("  3. PREPROCESSING() now called with 6 channels (matches TSPIPE)")
    print()
    print(f"To rollback:")
    print(f"  cp {backup} {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
