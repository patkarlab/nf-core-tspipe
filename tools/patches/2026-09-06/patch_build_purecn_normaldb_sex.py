#!/usr/bin/env python3
"""
patch_build_purecn_normaldb_sex.py -- --sex stratum for the PureCN NormalDB
builder (MARKER PCN_SEX_V1). Handoff item 5, builder half.

Edits to tools/build_purecn_normaldb.sh:
  1. header comment: per-stratum wording
  2. default sheet -> pon_samplesheets/twist_normals_48_v4.csv; SEX=male
  3. --sex male|female argument; after parsing: ASSAY (twist_myeloid /
     twist_myeloid_female), NDB_DIR ($WORKDIR/normaldb_<sex>), MIN_N
     (20 male / 6 female), MD5 name (purecn_normaldb[_female].md5)
  4. BAM selection by $SEX instead of the hard-coded "male"
  5. coverage list built from the selected BAMs (not ls of the shared
     coverage/ directory, which would mix strata)
  6. NormalDB.R writes to NDB_DIR with --assay $ASSAY; NDB path follows
  7. seed step copies the assay-named RDS and PNG; per-stratum md5 file
  8. final message names the stratum

Idempotent; dry run by default; --apply writes with a .bak_pcn_sex_<ts>
backup. Verified with bash -n before writing.
"""

import argparse
import datetime
import os
import re
import shutil
import subprocess
import sys

MARKER = "MARKER PCN_SEX_V1"
TARGET_DEFAULT = "tools/build_purecn_normaldb.sh"


def sub_once(text, pattern, repl, label, flags=re.M):
    rx = re.compile(pattern, flags)
    n = len(rx.findall(text))
    if n != 1:
        raise ValueError("anchor %s: expected 1 match, found %d (%s)" % ("not found" if n == 0 else "not unique", n, label))
    return rx.sub(repl, text, count=1), "[ok] %s" % label


def patch(t):
    notes = []
    t, n = sub_once(t, r"^# tools/build_purecn_normaldb\.sh  \(PCN_V1\)\n",
                    "# tools/build_purecn_normaldb.sh  (PCN_V1; %s: --sex stratum)\n" % MARKER, "header tag")
    notes.append(n)
    t, n = sub_once(t, r"^#   2\. Coverage\.R      -- GC-normalised loess coverage per male normal\n",
                    "#   2. Coverage.R      -- GC-normalised loess coverage per normal of the\n"
                    "#      chosen stratum (--sex male|female; default male)\n", "header step 2")
    notes.append(n)
    t, n = sub_once(t, r'^SHEET="pon_samplesheets/twist_normals_48\.csv"\n',
                    'SHEET="pon_samplesheets/twist_normals_48_v4.csv"\nSEX="male"\n', "defaults")
    notes.append(n)
    t, n = sub_once(t, r'^        --jobs\)    JOBS="\$2"; shift 2 ;;\n',
                    lambda m: m.group(0) + '        --sex)     SEX="$2"; shift 2 ;;\n', "--sex argument")
    notes.append(n)
    t, n = sub_once(
        t,
        r'^RS="\$ENVDIR/bin/Rscript"\n',
        lambda m: (
            'case "$SEX" in\n'
            '    male)   ASSAY="twist_myeloid";        MIN_N=20; MD5NAME="purecn_normaldb.md5" ;;\n'
            '    female) ASSAY="twist_myeloid_female"; MIN_N=6;  MD5NAME="purecn_normaldb_female.md5" ;;\n'
            '    *) echo "[error] --sex must be male or female (got: $SEX)" >&2; exit 1 ;;\n'
            'esac\n'
            'NDB_DIR="$WORKDIR/normaldb_$SEX"\n'
            'echo "[ok] stratum=$SEX assay=$ASSAY normaldb_dir=$NDB_DIR"\n'
            '\n' + m.group(0)),
        "stratum derivations")
    notes.append(n)
    t, n = sub_once(t, r'^mkdir -p "\$WORKDIR/coverage"\n', 'mkdir -p "$WORKDIR/coverage" "$NDB_DIR"\n', "mkdir NDB_DIR")
    notes.append(n)
    t, n = sub_once(t, r"^# ---- 2\. Coverage over the male normals ------------------------------------\n",
                    "# ---- 2. Coverage over the normals of the chosen stratum --------------------\n", "step 2 banner")
    notes.append(n)
    t, n = sub_once(
        t,
        r'^BAMS=\$\(awk -F\',\' \'NR>1 && \$2=="male" && \$6=="true" \{print \$3\}\' "\$SHEET"\)\n'
        r'n_bam=\$\(echo "\$BAMS" \| grep -c \. \|\| true\)\n'
        r'echo "\[ok\] male include_in_pon normals: \$n_bam"\n'
        r'\[ "\$n_bam" -ge 20 \] \|\| \{ echo "\[error\] expected ~24 male normals, found \$n_bam" >&2; exit 1; \}\n',
        'BAMS=$(awk -F\',\' -v sex="$SEX" \'NR>1 && $2==sex && $6=="true" {print $3}\' "$SHEET")\n'
        'n_bam=$(echo "$BAMS" | grep -c . || true)\n'
        'echo "[ok] $SEX include_in_pon normals: $n_bam"\n'
        '[ "$n_bam" -ge "$MIN_N" ] || { echo "[error] expected >= $MIN_N $SEX normals, found $n_bam" >&2; exit 1; }\n',
        "BAM selection by stratum")
    notes.append(n)
    t, n = sub_once(
        t,
        r'^ls "\$WORKDIR"/coverage/\*_coverage_loess\.txt\.gz > "\$WORKDIR/normals_coverage\.list"\n'
        r'n_cov=\$\(wc -l < "\$WORKDIR/normals_coverage\.list"\)\n',
        'COVLIST="$WORKDIR/normals_coverage_$SEX.list"\n'
        ': > "$COVLIST"\n'
        'for bam in $BAMS; do\n'
        '    cov="$WORKDIR/coverage/$(basename "$bam" .bam)_coverage_loess.txt.gz"\n'
        '    [ -s "$cov" ] || { echo "[error] coverage missing: $cov" >&2; exit 1; }\n'
        '    echo "$cov" >> "$COVLIST"\n'
        'done\n'
        'n_cov=$(wc -l < "$COVLIST")\n',
        "coverage list from the selected BAMs")
    notes.append(n)
    t, n = sub_once(
        t,
        r'^    --out-dir "\$WORKDIR" \\\n    --coverage-files "\$WORKDIR/normals_coverage\.list" \\\n    --genome hg38 \\\n    --assay twist_myeloid \\\n',
        '    --out-dir "$NDB_DIR" \\\n    --coverage-files "$COVLIST" \\\n    --genome hg38 \\\n    --assay "$ASSAY" \\\n',
        "NormalDB.R call")
    notes.append(n)
    t, n = sub_once(t, r'^NDB="\$WORKDIR/normalDB_twist_myeloid_hg38\.rds"\n',
                    'NDB="$NDB_DIR/normalDB_${ASSAY}_hg38.rds"\n', "NDB path")
    notes.append(n)
    t, n = sub_once(
        t,
        r'^ls "\$WORKDIR"/interval_weights\*\.png >/dev/null 2>&1 && cp "\$WORKDIR"/interval_weights\*\.png "\$OUTDIR/" \|\| true\n'
        r'\( cd "\$OUTDIR" && md5sum "\$\(basename "\$INTERVALS"\)" "\$\(basename "\$NDB"\)" > purecn_normaldb\.md5 \)\n'
        r'echo "\[ok\] seeded:"\ncat "\$OUTDIR/purecn_normaldb\.md5"\n'
        r'echo "\[done\] PureCN NormalDB build complete \(male stratum, n=\$n_cov\)"\n',
        'ls "$NDB_DIR"/interval_weights_${ASSAY}_*.png >/dev/null 2>&1 && cp "$NDB_DIR"/interval_weights_${ASSAY}_*.png "$OUTDIR/" || true\n'
        '( cd "$OUTDIR" && md5sum "$(basename "$INTERVALS")" "$(basename "$NDB")" > "$MD5NAME" )\n'
        'echo "[ok] seeded:"\ncat "$OUTDIR/$MD5NAME"\n'
        'echo "[done] PureCN NormalDB build complete ($SEX stratum, assay $ASSAY, n=$n_cov)"\n',
        "seed step")
    notes.append(n)
    return t, notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default=TARGET_DEFAULT)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if not os.path.isfile(args.target):
        print("[error] target not found: %s" % args.target)
        sys.exit(1)
    original = open(args.target).read()
    if MARKER in original:
        print("[skip] %s already present" % MARKER)
        sys.exit(0)
    try:
        new_text, notes = patch(original)
    except ValueError as exc:
        print("[error] %s; nothing written" % exc)
        sys.exit(1)
    for n in notes:
        print(n)
    tmp = args.target + ".pcn_sex_check.tmp"
    with open(tmp, "w") as fh:
        fh.write(new_text)
    rc = subprocess.call(["bash", "-n", tmp])
    os.remove(tmp)
    print("[check] marker %d (expected 1); bash -n rc=%d" % (new_text.count(MARKER), rc))
    if new_text.count(MARKER) != 1 or rc != 0:
        print("[error] verification failed; nothing written")
        sys.exit(1)
    if not args.apply:
        print("[dry-run] no changes written; re-run with --apply")
        old_set = set(original.splitlines())
        for line in new_text.splitlines():
            if line not in old_set:
                print("+ " + line)
        sys.exit(0)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = "%s.bak_pcn_sex_%s" % (args.target, ts)
    shutil.copy2(args.target, backup)
    print("[backup] %s" % backup)
    with open(args.target, "w") as fh:
        fh.write(new_text)
    print("[patch] wrote %s" % args.target)


if __name__ == "__main__":
    main()
