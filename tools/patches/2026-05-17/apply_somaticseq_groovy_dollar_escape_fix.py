#!/usr/bin/env python3
"""
apply_somaticseq_groovy_dollar_escape_fix.py - 2026-05-17

Hotfix for Patch C: the rationale comment I inserted into the inner
sort loop contained an unescaped `$VCF` reference. Inside a Nextflow
script block, every `$identifier` is a Groovy string-template
interpolation, regardless of whether the surrounding text is meant
as a shell comment (Groovy renders the string first; only AFTER that
does bash see the `#` and treat the line as a comment). Groovy
could not resolve a variable named VCF in the surrounding scope, so
the task setup failed with:

    No such variable: VCF -- Check script
    'modules/local/somaticseq.nf' at line: 91

before any bash ran.

Fix: change `$VCF` to `\\$VCF` in the comment. The bash render turns
`\\$` into `$`, leaving the comment as `# ... so $VCF here can be ...`
which bash then ignores entirely. Same one-character escape convention
used everywhere else in the module.

Idempotent. Writes a timestamped backup next to the target:
  somaticseq.nf.bak_groovy_dollar_escape_<YYYYMMDD_HHMMSS>
"""

import datetime
import pathlib
import sys

TARGET = pathlib.Path(
    "/goast/hemat_data/nf-core-tspipe/modules/local/somaticseq.nf"
)

# The offending line, exactly as it appears on disk. 16 spaces of
# indentation matching the inner-loop body context.
OLD_LINE = "                # in its FLT3+UBTF scope, so $VCF here can be\n"

# Same line with `$VCF` -> `\$VCF`. In Python source, "\\$" represents
# the literal two-character sequence `\$` that bash will later see
# after Groovy renders.
NEW_LINE = "                # in its FLT3+UBTF scope, so \\$VCF here can be\n"


def main() -> int:
    if not TARGET.is_file():
        print(f"ERROR: target file not found: {TARGET}", file=sys.stderr)
        return 1

    text = TARGET.read_text()

    if NEW_LINE in text:
        print("ERROR: patch already applied (NEW_LINE present). "
              "Refusing to double-apply.", file=sys.stderr)
        return 1

    n_old = text.count(OLD_LINE)
    if n_old == 0:
        print("ERROR: OLD_LINE not found in target. The file may have "
              "been modified since this patch was written.",
              file=sys.stderr)
        return 1
    if n_old > 1:
        print(f"ERROR: OLD_LINE appears {n_old} times in target "
              "(expected exactly 1).", file=sys.stderr)
        return 1

    new_text = text.replace(OLD_LINE, NEW_LINE)
    if new_text == text:
        print("ERROR: no substitution took effect. Refusing to write.",
              file=sys.stderr)
        return 1

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.parent / f"{TARGET.name}.bak_groovy_dollar_escape_{ts}"
    backup.write_text(text)
    print(f"backup: {backup}")

    TARGET.write_text(new_text)
    print(f"patched: {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
