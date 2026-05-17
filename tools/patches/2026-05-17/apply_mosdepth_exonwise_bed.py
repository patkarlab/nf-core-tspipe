#!/usr/bin/env python3
"""
apply_mosdepth_exonwise_bed.py

Switch the MOSDEPTH module's input BED from the segment-level panel BED
to the new exon-collapsed Exonwise BED, so per-exon coverage matches
the legacy clinical-report framing (~1153 exon rows instead of 4589
segment rows).

DECISIONS IMPLEMENTED:
  - REPLACE (not add-second-call): mosdepth uses Exonwise BED exclusively
  - NEW PARAM (not rename): params.exonwise_bed added; params.bed stays
    unchanged for variant callers, CNVkit, HSMETRICS, ABRA2, etc.

FILES MODIFIED (4):
  - nextflow.config
  - conf/gandalf.config
  - subworkflows/local/preprocessing.nf
  - workflows/tspipe.nf

FILES UNCHANGED (verified):
  - conf/modules.config         (MOSDEPTH publishDir tolerates either BED)
  - modules/local/mosdepth.nf   (module is BED-agnostic; no logic change)
  - bin/parse_exon_coverage.py  (canonical Ex_N labels work with existing
                                  parse_gene_exon regex)

AUTHORING DISCIPLINE (from 2026-05-17 morning lessons):
  - Pre-flight md5 verification on every target file
  - Python-built OLD/NEW fixtures, no bash heredoc
  - Escape audit: no Python f-strings around Groovy ${...} interpolation
  - Atomic write via .tmp + os.replace
  - .bak copy of every modified file
  - Idempotent: re-running on already-patched tree detects via anchor
    matching and exits 0 with a clear message
  - All-or-nothing: verification of all 4 files happens BEFORE any write

USAGE:
    python3 apply_mosdepth_exonwise_bed.py            # dry-run (default)
    python3 apply_mosdepth_exonwise_bed.py --apply    # write
    python3 apply_mosdepth_exonwise_bed.py --apply --archive
                                                       # also copy this
                                                       # script into
                                                       # tools/patches/
                                                       # for audit trail

ROLLBACK:
    Each modified file gets a sibling .bak_pre_mosdepth_replace_<ts> copy.
    To roll back: mv the .bak file back over the modified file.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Where the port lives. Override via --port-root if you ever need to point
# this at a different tree (e.g. a staging clone).
# ---------------------------------------------------------------------------
DEFAULT_PORT_ROOT = Path("/goast/hemat_data/nf-core-tspipe")


# ---------------------------------------------------------------------------
# Target files: expected pre-patch md5sums, and the (OLD, NEW) edits to
# apply. Every OLD must appear exactly once in the file. The script
# verifies this before writing anything.
# ---------------------------------------------------------------------------

# --- nextflow.config -------------------------------------------------------
NEXTFLOW_CONFIG_PRE_MD5 = "a6c43f946fb00e33e0f0370badc51620"

OLD_NEXTFLOW_BED_LINE = (
    "    bed                = null   // panel BED\n"
    "    pindel_bed         = null   // optional - pindel target subset\n"
)
NEW_NEXTFLOW_BED_LINE = (
    "    bed                = null   // panel BED\n"
    "    exonwise_bed       = null   // exon-collapsed BED for mosdepth only\n"
    "    pindel_bed         = null   // optional - pindel target subset\n"
)


# --- conf/gandalf.config ---------------------------------------------------
GANDALF_CONFIG_PRE_MD5 = "192d02697f4cf406600a32f6f578d052"

# Note: the ${params.pipeline_root} text is intentional Groovy interpolation.
# Python regular strings (not f-strings) leave it verbatim.
OLD_GANDALF_BED_LINE = (
    '    bed                = "${params.pipeline_root}/bedfiles/'
    'MYOPOOL_240125_UBTF_hg38.bed"\n'
    '    pindel_bed         = "${projectDir}/references/'
    'pindel_targets_flt3_ubtf.bed"\n'
)
NEW_GANDALF_BED_LINE = (
    '    bed                = "${params.pipeline_root}/bedfiles/'
    'MYOPOOL_240125_UBTF_hg38.bed"\n'
    '    exonwise_bed       = "${params.pipeline_root}/bedfiles/'
    'MYOPOOL_240125_UBTF_Exonwise_hg38.bed"\n'
    '    pindel_bed         = "${projectDir}/references/'
    'pindel_targets_flt3_ubtf.bed"\n'
)


# --- subworkflows/local/preprocessing.nf -----------------------------------
PREPROCESSING_NF_PRE_MD5 = "db0eb0b10f90283401a9b7e42199157b"

OLD_PREPROCESSING_TAKE = (
    "    take:\n"
    "        reads_ch\n"
    "        reference_ch\n"
    "        bed_ch\n"
    "        dbsnp_ch       // [vcf, tbi]\n"
    "        mills_ch       // [vcf, tbi]\n"
)
NEW_PREPROCESSING_TAKE = (
    "    take:\n"
    "        reads_ch\n"
    "        reference_ch\n"
    "        bed_ch\n"
    "        exonwise_bed_ch  // exon-collapsed BED for MOSDEPTH/PARSE_EXON_COVERAGE only\n"
    "        dbsnp_ch       // [vcf, tbi]\n"
    "        mills_ch       // [vcf, tbi]\n"
)

OLD_PREPROCESSING_CALLS = (
    "        HSMETRICS(ABRA2.out.bam, reference_ch, bed_ch)\n"
    "        MOSDEPTH(ABRA2.out.bam, bed_ch)\n"
    "        PARSE_EXON_COVERAGE(MOSDEPTH.out.regions_thresholds, bed_ch)\n"
)
NEW_PREPROCESSING_CALLS = (
    "        HSMETRICS(ABRA2.out.bam, reference_ch, bed_ch)\n"
    "        MOSDEPTH(ABRA2.out.bam, exonwise_bed_ch)\n"
    "        PARSE_EXON_COVERAGE(MOSDEPTH.out.regions_thresholds, exonwise_bed_ch)\n"
)


# --- workflows/tspipe.nf ---------------------------------------------------
TSPIPE_NF_PRE_MD5 = "ff64a5ab7347be61c99eb0c182985dd9"

OLD_TSPIPE_VALIDATION = (
    '    if (!params.bed)       { error "Missing --bed (panel BED)"         }\n'
)
NEW_TSPIPE_VALIDATION = (
    '    if (!params.bed)       { error "Missing --bed (panel BED)"         }\n'
    '    if (!params.exonwise_bed) { error "Missing --exonwise_bed (Exonwise hg38 BED for per-exon coverage)" }\n'
)

OLD_TSPIPE_CHANNEL = (
    "    ch_bed       = Channel.value(file(params.bed, checkIfExists: true))\n"
    "    ch_pindel_bed = Channel.value(file(params.pindel_bed, checkIfExists: true))\n"
)
NEW_TSPIPE_CHANNEL = (
    "    ch_bed       = Channel.value(file(params.bed, checkIfExists: true))\n"
    "    ch_exonwise_bed = Channel.value(file(params.exonwise_bed, checkIfExists: true))\n"
    "    ch_pindel_bed = Channel.value(file(params.pindel_bed, checkIfExists: true))\n"
)

OLD_TSPIPE_CALL = (
    "    PREPROCESSING(ch_input, ch_reference, ch_bed, ch_dbsnp, ch_mills)\n"
)
NEW_TSPIPE_CALL = (
    "    PREPROCESSING(ch_input, ch_reference, ch_bed, ch_exonwise_bed, ch_dbsnp, ch_mills)\n"
)


# ---------------------------------------------------------------------------
# TARGETS table -- everything the patch knows how to modify.
# ---------------------------------------------------------------------------
TARGETS = [
    {
        "path": "nextflow.config",
        "pre_md5": NEXTFLOW_CONFIG_PRE_MD5,
        "edits": [
            ("bed_line", OLD_NEXTFLOW_BED_LINE, NEW_NEXTFLOW_BED_LINE),
        ],
    },
    {
        "path": "conf/gandalf.config",
        "pre_md5": GANDALF_CONFIG_PRE_MD5,
        "edits": [
            ("bed_line", OLD_GANDALF_BED_LINE, NEW_GANDALF_BED_LINE),
        ],
    },
    {
        "path": "subworkflows/local/preprocessing.nf",
        "pre_md5": PREPROCESSING_NF_PRE_MD5,
        "edits": [
            ("take_block", OLD_PREPROCESSING_TAKE, NEW_PREPROCESSING_TAKE),
            ("qc_calls",   OLD_PREPROCESSING_CALLS, NEW_PREPROCESSING_CALLS),
        ],
    },
    {
        "path": "workflows/tspipe.nf",
        "pre_md5": TSPIPE_NF_PRE_MD5,
        "edits": [
            ("validation", OLD_TSPIPE_VALIDATION, NEW_TSPIPE_VALIDATION),
            ("channel",    OLD_TSPIPE_CHANNEL,    NEW_TSPIPE_CHANNEL),
            ("call",       OLD_TSPIPE_CALL,       NEW_TSPIPE_CALL),
        ],
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def md5sum_bytes(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def read_bytes(path: Path) -> bytes:
    with path.open("rb") as fh:
        return fh.read()


def write_bytes_atomic(path: Path, data: bytes) -> None:
    """Write to a sibling .tmp file and atomically rename over the target.
    This avoids leaving the file in a half-written state if the process
    is interrupted mid-write.
    """
    tmp = path.with_suffix(path.suffix + ".tmp_patch")
    with tmp.open("wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def classify_anchor(content: str, old: str, new: str) -> str:
    """Decide what state this anchor is in.

    Returns one of:
      'pre'       : OLD found exactly once -> can apply
      'post'      : NEW found exactly once -> already applied
      'duplicate' : OLD or NEW found more than once -> abort
      'missing'   : neither OLD nor NEW found -> abort
      'mixed'     : both OLD and NEW found -> abort (corrupt state)
    """
    n_old = content.count(old)
    n_new = content.count(new)
    if n_old == 1 and n_new == 0:
        return "pre"
    if n_old == 0 and n_new == 1:
        return "post"
    if n_old > 1 or n_new > 1:
        return "duplicate"
    if n_old == 1 and n_new == 1:
        # NEW is a strict superset of OLD here (we extended OLD into NEW),
        # so finding both means the OLD substring still matches inside the
        # NEW substring. Distinguish this by checking string overlap.
        # If OLD is a substring of NEW, post-state will report n_old==1
        # too (because OLD lives inside NEW). Treat that as 'post'.
        if old in new:
            return "post"
        return "mixed"
    return "missing"


def color(s: str, code: str) -> str:
    if not sys.stdout.isatty():
        return s
    return f"\033[{code}m{s}\033[0m"


def green(s):  return color(s, "32")
def yellow(s): return color(s, "33")
def red(s):    return color(s, "31")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port-root", type=Path, default=DEFAULT_PORT_ROOT,
                    help=f"nf-core-tspipe repo root (default: {DEFAULT_PORT_ROOT})")
    ap.add_argument("--apply", action="store_true",
                    help="Actually modify files. Without this flag, the "
                         "script only prints the plan.")
    ap.add_argument("--archive", action="store_true",
                    help="On --apply success, also copy THIS patch script "
                         "into <port-root>/tools/patches/2026-05-17/ for "
                         "the project audit trail.")
    args = ap.parse_args()

    port_root: Path = args.port_root
    if not port_root.is_dir():
        print(red(f"ERROR: port-root not found: {port_root}"), file=sys.stderr)
        return 2

    # ---- Phase 1: load, classify, plan all edits ------------------------
    print(f"Patch: mosdepth-replace -> Exonwise hg38 BED")
    print(f"Port root: {port_root}")
    print()
    print("Phase 1: loading and classifying anchors")
    print()

    plan = []           # list of (target_path, new_content, n_edits_applied)
    any_pre = False     # any anchor in pre state (work to do)
    any_blocking = False
    already_applied_count = 0

    for spec in TARGETS:
        rel = spec["path"]
        path = port_root / rel
        if not path.is_file():
            print(red(f"  MISSING: {rel}"))
            any_blocking = True
            continue

        raw = read_bytes(path)
        actual_md5 = md5sum_bytes(raw)
        content = raw.decode("utf-8")

        print(f"  {rel}")
        print(f"    current md5: {actual_md5}")
        if actual_md5 == spec["pre_md5"]:
            print(f"    state:       {green('PRE-PATCH')} (matches expected pre-md5)")
        else:
            print(f"    expected:    {spec['pre_md5']} (pre-patch)")
            print(f"    state:       {yellow('MODIFIED')} (md5 differs; checking anchors)")

        new_content = content
        n_pre = 0
        n_post = 0
        for name, old, new in spec["edits"]:
            state = classify_anchor(new_content, old, new)
            if state == "pre":
                print(f"      {name:20s} {green('PRE')}  (will apply)")
                new_content = new_content.replace(old, new, 1)
                n_pre += 1
            elif state == "post":
                print(f"      {name:20s} {yellow('POST')} (already applied; skip)")
                n_post += 1
            elif state == "duplicate":
                print(f"      {name:20s} {red('DUPLICATE')} (OLD or NEW found multiple times)")
                any_blocking = True
            elif state == "missing":
                print(f"      {name:20s} {red('MISSING')} (neither OLD nor NEW found; anchor drift)")
                any_blocking = True
            elif state == "mixed":
                print(f"      {name:20s} {red('MIXED')} (both OLD and NEW non-overlapping; corrupt)")
                any_blocking = True

        # Idempotency: only schedule a write if at least one edit was pre-state.
        if n_pre > 0:
            any_pre = True
            plan.append((path, new_content.encode("utf-8"), n_pre, n_post))
        else:
            already_applied_count += 1
        print()

    if any_blocking:
        print(red("ABORT: one or more anchors did not classify cleanly. No files written."))
        return 1

    if not any_pre:
        print(green("All anchors already in POST state. Patch is fully applied; nothing to do."))
        return 0

    # ---- Phase 2: confirm / dry-run gate --------------------------------
    print(f"Phase 2: ready to write {len(plan)} file(s).")
    if already_applied_count:
        print(f"  ({already_applied_count} file(s) already fully applied; will be left alone)")
    print()
    if not args.apply:
        print(yellow("DRY-RUN. No files written. Re-run with --apply to execute."))
        return 0

    # ---- Phase 3: apply -------------------------------------------------
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak_suffix = f".bak_pre_mosdepth_replace_{ts}"
    print("Phase 3: applying")
    for path, new_bytes, n_pre, n_post in plan:
        rel = path.relative_to(port_root)
        bak = path.with_name(path.name + bak_suffix)
        shutil.copy2(path, bak)
        write_bytes_atomic(path, new_bytes)
        post_md5 = md5sum_bytes(read_bytes(path))
        print(f"  {green('APPLIED')} {rel}")
        print(f"    backup:   {bak.relative_to(port_root)}")
        print(f"    new md5:  {post_md5}")
        print(f"    edits:    {n_pre} applied, {n_post} skipped (already post)")
    print()

    # ---- Phase 4 (optional): archive self --------------------------------
    if args.archive:
        archive_dir = port_root / "tools" / "patches" / "2026-05-17"
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_dest = archive_dir / Path(sys.argv[0]).name
        shutil.copy2(sys.argv[0], archive_dest)
        print(f"Phase 4: archived patch script to {archive_dest.relative_to(port_root)}")
        print()

    print(green("Done."))
    print()
    print("Next steps:")
    print("  1. Verify files look right: ")
    print("       cd " + str(port_root))
    print("       git diff nextflow.config conf/gandalf.config "
          "subworkflows/local/preprocessing.nf workflows/tspipe.nf")
    print("  2. Re-run validation against 25NGS1307 to confirm the new ")
    print("     mosdepth call emits 1153 rows and PARSE_EXON_COVERAGE produces ")
    print("     a per-exon TSV with clinical-report-grade granularity.")
    print("  3. Commit the change. Suggested message:")
    print("       feat(mosdepth): use Exonwise BED for per-exon coverage")
    print()
    print("To roll back: ")
    print(f"  for f in $(find {port_root} -name '*{bak_suffix}'); do")
    print('      mv "$f" "${f%%' + bak_suffix + '}"')
    print("  done")

    return 0


if __name__ == "__main__":
    sys.exit(main())
