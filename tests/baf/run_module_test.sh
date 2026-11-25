#!/usr/bin/env bash
# tests/baf/run_module_test.sh -- the CNV_BAF_CNLOH module, run by Nextflow with its real script.
#
# tests/baf/run_baf_tests.py calls bin/baf_cnloh_detect.py directly. This test goes through the
# module instead, with the thresholds of conf/twist_apply.config: it fails if the module's command
# line and the script's options have drifted apart, if an output the module declares is not
# written, or if one of the three switches (baf_het_loss, baf_segment_votes, baf_roh_votes) does
# not reach the script.
#
#   bash tests/baf/run_module_test.sh
#
# Needs nextflow and python3 on PATH; no container, no data outside the repository. About a minute.
set -euo pipefail
REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
WORK=$(mktemp -d "${TMPDIR:-/tmp}/baf_module_test.XXXXXX")
trap 'rm -rf "$WORK"' EXIT
fail=0
check() { if [ "$2" = "$3" ]; then echo "ok   $1"; else echo "FAIL $1  -- got '$2', expected '$3'"; fail=1; fi; }

python3 "$REPO/tests/baf/simulate_baf_sample.py" --sample MODTEST --out-prefix "$WORK/MODTEST" \
    --event 11q:cnloh:0.90 > /dev/null

cat > "$WORK/test.config" <<CFG
// the detector is a bin/ script of the pipeline; this test's project directory is tests/baf
process.beforeScript = 'export PATH=$REPO/bin:\$PATH'
process.executor     = 'local'
singularity.enabled  = false
docker.enabled       = false
CFG

run_module() {   # $1 = tag, further args go to nextflow
    local tag=$1; shift
    ( cd "$WORK" && nextflow -c "$REPO/conf/twist_apply.config" -c "$WORK/test.config" \
          run "$REPO/tests/baf/cnv_baf_cnloh_module.nf" -ansi-log false -w "$WORK/work_$tag" \
          --sample MODTEST --allelic "$WORK/MODTEST.allelicCounts.tsv" --denoised "$WORK/MODTEST.denoisedCR.tsv" \
          --snp_bed "$REPO/assets/twist_myeloid/snp_sites.baf.bed" \
          --background "$REPO/assets/twist_myeloid/baf_background.tsv" "$@" > "$WORK/$tag.log" 2>&1 ) \
        || { echo "FAIL nextflow run ($tag)"; tail -20 "$WORK/$tag.log"; exit 1; }
    find "$WORK/work_$tag" -name MODTEST.baf.summary.tsv | head -1
}

s=$(run_module on)
check "module, defaults: 11q called CNLOH"            "$(awk -F'\t' '$2=="11q"{print $15}' "$s")" "CNLOH"
check "module, defaults: confidence HIGH"             "$(awk -F'\t' '$2=="11q"{print $16}' "$s")" "HIGH"
check "module, defaults: evidence het_loss_residual"  "$(awk -F'\t' '$2=="11q"{print $25}' "$s")" "het_loss_residual"
d=$(dirname "$s")
check "module writes the sites table"                 "$([ -s "$d/MODTEST.baf.sites.tsv" ] && echo yes || echo no)" "yes"
check "module command line carries no --no-het-loss"  "$(grep -c -- '--no-het-loss' "$d/.command.sh" || true)" "0"
check "module command line carries no advisory switch" "$(grep -c -e '--loh-segment-advisory' -e '--roh-advisory' "$d/.command.sh" || true)" "0"

s=$(run_module off --baf_het_loss false)
check "module, baf_het_loss false: 11q as BAF_V2 (INDETERMINATE)" "$(awk -F'\t' '$2=="11q"{print $15}' "$s")" "INDETERMINATE"
check "module, baf_het_loss false: --no-het-loss on the command line" "$(grep -c -- '--no-het-loss' "$(dirname "$s")/.command.sh" || true)" "1"

s=$(run_module advisory --baf_segment_votes false --baf_roh_votes false)
check "module, both votes switched off: 11q still called CNLOH (an arm-level call is not affected)" "$(awk -F'\t' '$2=="11q"{print $15}' "$s")" "CNLOH"
check "module, baf_segment_votes false: --loh-segment-advisory on the command line" "$(grep -c -- '--loh-segment-advisory' "$(dirname "$s")/.command.sh" || true)" "1"
check "module, baf_roh_votes false: --roh-advisory on the command line" "$(grep -c -- '--roh-advisory' "$(dirname "$s")/.command.sh" || true)" "1"

[ "$fail" = 0 ] && echo "module test passed" || { echo "module test FAILED"; exit 1; }
