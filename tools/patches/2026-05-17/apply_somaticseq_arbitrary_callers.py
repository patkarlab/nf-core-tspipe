#!/usr/bin/env python3
"""
apply_somaticseq_arbitrary_callers.py - 2026-05-17

Patch modules/local/somaticseq.nf to restore Pindel and DeepSomatic in
the arbitrary-caller loop, matching production's 8-caller setup, and
to insert an SV pre-filter that strips symbolic-allele records before
splitVcf.py sees them.

Background. The current loop iterates only over FreeBayes and Platypus.
A comment dated 2026-05-17 in the module attributes the prior drop to
"SomaticSeq preprocessing loop crashes during their iteration in ways
that proved hard to pin down within a single debug session", and asserts
that "production's 07_somaticseq.py uses the 6-caller stable baseline".
The latter claim is incorrect. Production's 07_somaticseq.py docstring
lists 8 callers, CALLER_LABELS has 8 entries, and main() processes all
8 inputs as first-class CLI arguments. The "6-caller baseline" framing
was a rationalization. Production runs 8 callers cleanly.

Three of the six clinically-significant variants missing from the port's
25NGS1307 clinical TSV in the 2026-05-16 audit (SETD2 p.Pro1916His,
TET2 p.Ser142Tyr, TET2 p.Glu1250Ter) are FreeBayes + DeepSomatic
two-caller calls. With DeepSomatic dropped, they collapse to NUM_TOOLS=1
in the port and fail to clear the filter. Restoring DeepSomatic should
recover these three variants directly. Pindel re-enabling is also
required for KMT2A-PTD validation (priority 6 in the bootstrap), since
KMT2A-PTD is a structural rearrangement that Pindel calls.

Pindel crash mechanism. Pindel emits records with symbolic-allele ALTs
(<INS>, <DEL>, <DUP>, <INV>, <NON_REF>, <*>) and occasionally breakend
notation (e.g. "G]chr5:1000]"). SomaticSeq's splitVcf.py classifies
records as SNV or INDEL by comparing REF and ALT string lengths, and
crashes or silently misclassifies on symbolic alleles since they aren't
plain nucleotide strings. The new awk pre-filter keeps header lines
verbatim and passes through only records whose REF and ALT columns
match the regex /^[ACGTNacgtn]+$/ (REF) and /^[ACGTNacgtn,]+$/ (ALT,
allowing commas for multi-allelic). Symbolic ALTs, "." (no-call), and
breakend notation are all dropped.

The filter is conceptually a no-op for FreeBayes and Platypus, which
only emit plain nucleotide alleles in this pipeline's regime. For
DeepSomatic, the filter is precautionary — DeepSomatic emits standard
SNV/INDEL records in PASS-only mode but may include <NON_REF> or <*>
placeholder records in some configurations.

Logging. The filter logs the dropped-record count to stderr per caller,
which gives us visible attribution if a future Pindel run produces an
unexpected fraction of symbolic records.

Two changes:

  (1) Replace the dropped-callers comment + the truncated for-loop
      line with a comment explaining the SV pre-filter and a four-
      entry for-loop that includes Pindel and DeepSomatic.

  (2) Insert the awk pre-filter inside the loop body, between the
      header-only-skip check and the sort step. The anchor before the
      sort is "# Sort the source VCF (headers first, then chr/pos
      sort)" — the patch wraps that line in the new block so a single
      str_replace handles the insertion unambiguously.

Idempotent: refuses to re-apply if Pindel is already in the for-loop.

Writes a timestamped backup next to the target:
  somaticseq.nf.bak_arbitrary_callers_<YYYYMMDD_HHMMSS>
"""

import datetime
import pathlib
import sys

TARGET = pathlib.Path(
    "/goast/hemat_data/nf-core-tspipe/modules/local/somaticseq.nf"
)

# ---------------------------------------------------------------------------
# Change 1: re-enable Pindel and DeepSomatic in the for-loop iterator.
# ---------------------------------------------------------------------------

OLD_LOOP = r'''        # NOTE 2026-05-17: pindel and deepsomatic temporarily dropped from
        # the arbitrary-caller loop. Both produce valid VCFs upstream but the
        # SomaticSeq preprocessing loop crashes during their iteration in ways
        # that proved hard to pin down within a single debug session.
        # Production's 07_somaticseq.py uses the 6-caller stable baseline.
        # Revisit pindel+deepsomatic integration in a dedicated session.
        for ENTRY in "freebayes:${freebayes_vcf}" "platypus:${platypus_vcf}"; do
'''

NEW_LOOP = r'''        # 2026-05-17: arbitrary-caller loop covers all four arbitrary
        # callers, matching production's 8-caller setup in
        # scripts/07_somaticseq.py. Pindel was previously dropped because
        # splitVcf.py crashes on its symbolic-allele records (SV calls
        # like <INS>/<DEL>, breakend notation, <NON_REF>). The SV
        # pre-filter inserted further down strips those before splitVcf
        # runs, which lets Pindel contribute SNV/INDEL votes without
        # affecting flow for FreeBayes and Platypus (which only emit
        # plain alleles). DeepSomatic is also re-enabled; in this
        # pipeline it runs in PASS-only mode and rarely emits symbolic
        # records, but the same pre-filter protects against the corner
        # cases. If a caller still crashes after this change, the
        # filter's per-caller stderr logging makes the failure mode
        # visible in .command.err.
        for ENTRY in "freebayes:${freebayes_vcf}" "platypus:${platypus_vcf}" "pindel:${pindel_vcf}" "deepsomatic:${deepsomatic_vcf}"; do
'''

# ---------------------------------------------------------------------------
# Change 2: insert SV pre-filter before the sort step.
#
# Anchor: the header-only-skip block plus the immediately-following
# "Sort the source VCF" comment line, which together appear exactly
# once in the script block.
# ---------------------------------------------------------------------------

OLD_SORT_ANCHOR = r'''            N=\$(grep -cv '^#' "\$SRC" 2>/dev/null) || N=0
            if [ "\$N" -eq 0 ]; then
                echo "[somaticseq] \$CALLER: header-only, skipping" 1>&2
                continue
            fi

            # Sort the source VCF (headers first, then chr/pos sort)
            SORTED="\${CALLER}.sorted.vcf"
'''

NEW_SORT_ANCHOR = r'''            N=\$(grep -cv '^#' "\$SRC" 2>/dev/null) || N=0
            if [ "\$N" -eq 0 ]; then
                echo "[somaticseq] \$CALLER: header-only, skipping" 1>&2
                continue
            fi

            # Strip symbolic-allele records before splitVcf.py sees them.
            # SomaticSeq's arbitrary-caller path only handles plain SNVs
            # and INDELs; symbolic alleles (Pindel SVs like <INS>/<DEL>,
            # <NON_REF>, <*>, breakends like "G]chr5:1000]") and "." no-
            # call ALTs crash or get misclassified by splitVcf.py. The
            # awk filter keeps header lines verbatim and passes through
            # only records whose REF is plain nucleotides (A/C/G/T/N,
            # any case) and whose ALT is plain nucleotides with commas
            # allowed for multi-allelic. No-op for FreeBayes and Platypus.
            FILTERED="\${CALLER}.snv_indel_only.vcf"
            awk 'BEGIN{FS=OFS="\\t"} /^#/ {print; next} \$4 ~ /^[ACGTNacgtn]+\$/ && \$5 ~ /^[ACGTNacgtn,]+\$/ {print}' "\$SRC" > "\$FILTERED"
            N_FILT=\$(grep -cv '^#' "\$FILTERED" 2>/dev/null) || N_FILT=0
            DROPPED=\$((N - N_FILT))
            if [ "\$DROPPED" -gt 0 ]; then
                echo "[somaticseq] \$CALLER: dropped \$DROPPED non-SNV/INDEL records (symbolic alleles, SVs, breakends, no-calls)" 1>&2
            fi
            if [ "\$N_FILT" -eq 0 ]; then
                echo "[somaticseq] \$CALLER: no SNV/INDEL records after filter, skipping" 1>&2
                continue
            fi
            N=\$N_FILT
            SRC="\$FILTERED"

            # Sort the source VCF (headers first, then chr/pos sort)
            SORTED="\${CALLER}.sorted.vcf"
'''


# Sentinel for already-applied detection: the four-entry for-loop is a
# distinctive substring that should only appear if NEW_LOOP has been
# substituted into the file.
SENTINEL = '"pindel:${pindel_vcf}" "deepsomatic:${deepsomatic_vcf}"'


def main() -> int:
    if not TARGET.is_file():
        print(f"ERROR: target file not found: {TARGET}", file=sys.stderr)
        return 1

    text = TARGET.read_text()

    if SENTINEL in text:
        print("ERROR: patch already applied (Pindel + DeepSomatic already "
              "in the for-loop). Refusing to double-apply.", file=sys.stderr)
        return 1

    n_loop = text.count(OLD_LOOP)
    if n_loop == 0:
        print("ERROR: OLD_LOOP not found in target. The file may have "
              "been modified since this patch was written. Inspect "
              "manually before retrying.", file=sys.stderr)
        return 1
    if n_loop > 1:
        print(f"ERROR: OLD_LOOP appears {n_loop} times in target "
              "(expected exactly 1). Refusing to apply an ambiguous "
              "patch.", file=sys.stderr)
        return 1

    n_sort = text.count(OLD_SORT_ANCHOR)
    if n_sort == 0:
        print("ERROR: OLD_SORT_ANCHOR not found in target. Inspect "
              "manually before retrying.", file=sys.stderr)
        return 1
    if n_sort > 1:
        print(f"ERROR: OLD_SORT_ANCHOR appears {n_sort} times in "
              "target. Refusing to apply an ambiguous patch.",
              file=sys.stderr)
        return 1

    # Apply both substitutions in memory, then write atomically.
    new_text = text.replace(OLD_LOOP, NEW_LOOP)
    new_text = new_text.replace(OLD_SORT_ANCHOR, NEW_SORT_ANCHOR)

    # Defensive: confirm both substitutions actually changed something.
    if new_text == text:
        print("ERROR: no substitutions took effect. Refusing to write.",
              file=sys.stderr)
        return 1

    # Backup matches the repo's existing .bak_<tag>_<ts> convention.
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.parent / f"{TARGET.name}.bak_arbitrary_callers_{ts}"
    backup.write_text(text)
    print(f"backup: {backup}")

    TARGET.write_text(new_text)
    print(f"patched: {TARGET}")
    print("inspect with:")
    print(f"  diff {backup} {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
