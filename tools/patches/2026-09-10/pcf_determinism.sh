#!/usr/bin/env bash
# tools/patches/2026-09-10/pcf_determinism.sh -- is the AMBER/COBALT PCF segmentation reproducible?
#
# run8 host-vs-image showed byte-identical amber.baf.tsv.gz / cobalt.ratio.tsv.gz but differing
# .pcf files on three samples, and PURPLE differences downstream on two of them. This re-runs ONE
# completed task twice, on the same inputs, in the same image, and diffs the outputs: if the two
# repeats differ, the segmentation is non-deterministic and the golden regression needs a numeric
# tolerance on PURPLE-derived tables rather than byte equality.
#
# Usage: bash tools/patches/2026-09-10/pcf_determinism.sh <task_work_dir> [outdir]
#   e.g. bash ... $(nextflow log <run> -f tag,workdir | awk '/26CGH1292.*/&&/cobalt/{print $NF}' | head -1)
# The original task dir is never written to; copies are made under outdir (default /tmp/pcf_test).
set -euo pipefail
TASK=${1:?task work dir}
OUT=${2:-/tmp/pcf_test}
[ -f "$TASK/.command.sh" ] || { echo "not a task dir: $TASK"; exit 1; }
LAUNCH=$(grep -oE "singularity exec [^\"']*" "$TASK/.command.run" | head -1)
IMG=$(echo "$LAUNCH" | grep -oE "[^ ]*\.img" | head -1)
ENVPATH=$(echo "$LAUNCH" | grep -oE "\-\-env PATH=[^ ]*" | head -1)
echo "task : $TASK"
echo "image: ${IMG:-<none, host task>}"
echo "path : ${ENVPATH:-<default>}"
rm -rf "$OUT"; mkdir -p "$OUT"
for r in a b; do
    cp -a "$TASK" "$OUT/$r"
    ( cd "$OUT/$r"
      find . -maxdepth 1 -newer .command.sh -type f ! -name ".command.*" -delete 2>/dev/null || true
      if [ -n "$IMG" ]; then
          singularity exec -B /goast ${ENVPATH:+$ENVPATH} "$IMG" bash .command.sh > .rerun.log 2>&1 || echo "[warn] rerun $r exit $?"
      else
          bash .command.sh > .rerun.log 2>&1 || echo "[warn] rerun $r exit $?"
      fi
    )
    echo "[done] repeat $r"
done
echo "---- outputs that differ between the two repeats"
diff -rq --no-dereference "$OUT/a" "$OUT/b" 2>/dev/null | grep -vE "\.command|\.exitcode|\.rerun\.log|\.nextflow" || echo "(none: byte-identical repeats)"
echo "---- pcf files"
for f in $(cd "$OUT/a" && find . -name "*.pcf" | sort); do
    printf "%-46s a=%s b=%s\n" "$f" "$(md5sum "$OUT/a/$f" | cut -c1-8)" "$(md5sum "$OUT/b/$f" | cut -c1-8)"
done
