#!/usr/bin/env python3
"""
apply_somaticseq_postprocess_fix.py - 2026-05-17

Patch modules/local/somaticseq_postprocess.nf to fix three independent
bugs in the caller-decision INFO field rename block. The dominant
practical consequence is that the port's bin/annotate.py searches for
the literal string "MVDKFP=" (inherited from production) but the
port's postprocess actually writes "MVDKFPID=" into the merged VCF.
Every variant fails to match downstream, which explains the bulk of
the 369 missing prod-only filtered TSV entries and all 6 missing
clinical variants in the 2026-05-16 audit table.

The three changes:

  (1) Replacement token "MVDKFPID" -> "MVDKFP" (production's
      INFO_TAG; bin/annotate.py matches this exact string).

  (2) caller_labels reorder. SomaticSeq's empirical native-caller
      emit order is Mutect2, VarScan, VarDict, Strelka (confirmed
      from the raw Consensus.sSNV.vcf header description on 25NGS1307:
      "of the 6 algorithms: MuTect, VarScan2, VarDict, Strelka, ..."),
      NOT VarDict before VarScan. Production's 07_somaticseq.py
      carries an explicit comment about this prior-version swap bug.

  (3) Number=N derived from the raw header instead of hardcoded to 8.
      The ensemble currently feeds 6 callers; the raw header is
      Number=6; the data bitmap has 6 columns. Hardcoding 8 produces
      a header/data width mismatch. The fix uses re.search to capture
      Number=N from the existing header, then slices
      caller_labels[:n] so the description and the rewritten header
      both reflect the actual bitmap width. This stays correct after
      Pindel + DeepSomatic are re-enabled (Patch B, separate script),
      and also handles the per-sample skip case.

Idempotent: refuses to re-apply if NEW_BLOCK is already present.
Refuses to apply if OLD_BLOCK is missing or non-unique (file may
have been edited since this patch was written).

Writes a timestamped backup next to the target:
  somaticseq_postprocess.nf.bak_mvdkfp_rename_<YYYYMMDD_HHMMSS>
"""

import datetime
import pathlib
import sys

TARGET = pathlib.Path("/goast/hemat_data/nf-core-tspipe/modules/local/somaticseq_postprocess.nf")

# Exact pre-patch block, copied verbatim from the file as it stood on
# 2026-05-17. The leading 8-space indentation on the python3 line is
# inside the Nextflow script block; lines from "import re, sys" through
# "PYRENAME" are at column 0 because they are inside a bash heredoc
# body, which is read literally.
OLD_BLOCK = r'''        python3 - "\${SAMPLE}.somaticseq.vcf" <<'PYRENAME'
import re, sys
path = sys.argv[1]
caller_labels = ["Mutect2", "VarDict", "VarScan", "Strelka",
                 "FreeBayes", "Platypus", "Pindel", "DeepSomatic"]
label_csv = ", ".join(caller_labels)
with open(path) as f:
    content = f.read()
content = re.sub(
    r'##INFO=<ID=([A-Z]+\\d+),Number=\\d+,Type=\\w+,'
    r'Description="Calling decision of the \\d+ algorithms:[^"]*">',
    f'##INFO=<ID=MVDKFPID,Number=8,Type=String,'
    f'Description="Calling decision of the 8 algorithms: {label_csv}">',
    content,
)
content = re.sub(r'\\b[A-Z]{2,}\\d+(?==)', 'MVDKFPID', content)
with open(path, "w") as f:
    f.write(content)
print(f"[somaticseq_postprocess] renamed caller INFO -> MVDKFPID", file=sys.stderr)
PYRENAME
'''

NEW_BLOCK = r'''        python3 - "\${SAMPLE}.somaticseq.vcf" <<'PYRENAME'
# Rename SomaticSeq's caller-decision INFO field to the stable token
# "MVDKFP" that downstream parsers (bin/annotate.py) look for. We
# match production's INFO_TAG exactly; production's 07_somaticseq.py
# docstring notes downstream parsers match the literal string "MVDKFP".
#
# Number=N is parsed from SomaticSeq's emitted header rather than
# hardcoded, so this stays consistent if a caller's VCF was empty and
# got skipped (N < 8), or if upstream is currently feeding fewer
# callers than the maximum (N = 6 with Pindel + DeepSomatic disabled).
#
# Native-caller emit order is fixed by SomaticSeq itself:
#   MuTect, VarScan2, VarDict, Strelka  (NOT VarDict before VarScan).
# Arbitrary callers follow in the order they were passed to
# somaticseq_parallel.py in modules/local/somaticseq.nf.
import re, sys
path = sys.argv[1]
caller_labels = ["Mutect2", "VarScan", "VarDict", "Strelka",
                 "FreeBayes", "Platypus", "Pindel", "DeepSomatic"]
INFO_TAG = "MVDKFP"

with open(path) as f:
    content = f.read()

# Parse the existing caller-decision header to learn N (bitmap width).
m = re.search(
    r'##INFO=<ID=[A-Z]+\\d+,Number=(\\d+),Type=\\w+,'
    r'Description="Calling decision of the \\d+ algorithms:[^"]*">',
    content,
)
if not m:
    print("[somaticseq_postprocess] WARNING: no caller-decision INFO "
          "header found; nothing renamed", file=sys.stderr)
    sys.exit(0)

n = int(m.group(1))
active = caller_labels[:n]
label_csv = ", ".join(active)

# Rewrite the header to use INFO_TAG and the parsed N, with the
# description listing only the callers that actually contributed.
content = re.sub(
    r'##INFO=<ID=[A-Z]+\\d+,Number=\\d+,Type=\\w+,'
    r'Description="Calling decision of the \\d+ algorithms:[^"]*">',
    f'##INFO=<ID={INFO_TAG},Number={n},Type=String,'
    f'Description="Calling decision of the {n} algorithms: {label_csv}">',
    content,
)
# Rewrite per-record field names. The pattern matches things like
# MVDK01=, MVDK0123=, etc. - uppercase-letters-then-digits followed
# by "=" - and rewrites the prefix to INFO_TAG. Sample IDs and other
# tokens do not match because they lack the uppercase+digits shape
# immediately before an "=".
content = re.sub(r'\\b[A-Z]{2,}\\d+(?==)', INFO_TAG, content)

with open(path, "w") as f:
    f.write(content)

print(f"[somaticseq_postprocess] renamed caller INFO -> {INFO_TAG} "
      f"(Number={n}: {label_csv})", file=sys.stderr)
PYRENAME
'''


def main() -> int:
    if not TARGET.is_file():
        print(f"ERROR: target file not found: {TARGET}", file=sys.stderr)
        return 1

    text = TARGET.read_text()

    if NEW_BLOCK in text:
        print("ERROR: patch already applied (NEW_BLOCK present in file). "
              "Refusing to double-apply.", file=sys.stderr)
        return 1

    n_old = text.count(OLD_BLOCK)
    if n_old == 0:
        print("ERROR: OLD_BLOCK not found in target. The file may have "
              "been modified since this patch was written. Inspect "
              "manually before retrying.", file=sys.stderr)
        return 1
    if n_old > 1:
        print(f"ERROR: OLD_BLOCK appears {n_old} times in target "
              "(expected exactly 1). Refusing to apply an ambiguous "
              "patch.", file=sys.stderr)
        return 1

    # Backup alongside the target, matching the existing .bak_<tag>_<ts>
    # convention seen in this repo (e.g. somaticseq.nf.bak_disable_arb).
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.parent / f"{TARGET.name}.bak_mvdkfp_rename_{ts}"
    backup.write_text(text)
    print(f"backup: {backup}")

    new_text = text.replace(OLD_BLOCK, NEW_BLOCK)
    TARGET.write_text(new_text)
    print(f"patched: {TARGET}")
    print("inspect with:")
    print(f"  diff {backup} {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
