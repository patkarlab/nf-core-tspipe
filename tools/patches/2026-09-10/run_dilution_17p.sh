#!/usr/bin/env bash
# BAF_V2 in-silico 17p cnLOH dilution (handoff 2026-09-10 v2 section 2). Run from the repo root.
#   bash tools/patches/2026-09-10/run_dilution_17p.sh [outdir] [tag]     (tag: one of the four configurations, default all)
# Base sample 26CGH60 (diploid 17); clean samples 26CGH1292, 26CGH1480, 26CGH799, 26CGH885.
# Four configurations: realistic 'shift' mode at the current detector parameters, the
# counting-noise-only 'ideal' mode, and 'shift' at --noise-mult 2.0 and 1.5.
# Deterministic (seed 20260910): the server run reproduces the numbers in the audit README.
set -euo pipefail
R=${RUN8:-/goast/hemat_data/twist_val/tspipe_run8}
OUT=${1:-docs/audit/2026-09-10/baf_v2_17p_dilution}
ONLY=${2:-all}
SIM=tools/patches/2026-09-10/simulate_17p_cnloh.py
DET=bin/baf_cnloh_detect.py
BG=assets/twist_myeloid/baf_background.tsv
BED=assets/twist_myeloid/snp_sites.baf.bed
PY=${PY:-python3}
S=26CGH60-TwistMyVal
mkdir -p "$OUT"
CLEAN=""
for c in 26CGH1292 26CGH1480 26CGH799 26CGH885; do
    CLEAN="$CLEAN --clean $c-TwistMyVal=$R/$c-TwistMyVal/cnv_gatk/$c-TwistMyVal.allelicCounts.tsv,$R/$c-TwistMyVal/cnv_gatk/$c-TwistMyVal.denoisedCR.tsv"
done
run () {   # run <tag> <mode> <levels> <extra detector args>
    local tag=$1 mode=$2 levels=$3 extra=${4:-}
    [ "$ONLY" = all ] || [ "$ONLY" = "$tag" ] || return 0
    echo "=============== $tag (mode $mode${extra:+, $extra})"
    $PY $SIM --allelic "$R/$S/cnv_gatk/$S.allelicCounts.tsv" --denoised "$R/$S/cnv_gatk/$S.denoisedCR.tsv" \
        --background $BG --snp-bed $BED --detector $DET --sample $S --mode $mode --levels "$levels" \
        --replicates 20 --threads ${THREADS:-8} $CLEAN ${extra:+--detector-args "$extra"} --outdir "$OUT/work_$tag" \
        2>&1 | grep -v -E "Deprecation|boxplot" | tee "$OUT/${tag}.log"
    for f in dilution_summary.tsv dilution_runs.tsv dilution.png baseline.summary.tsv; do
        [ -f "$OUT/work_$tag/$f" ] && cp "$OUT/work_$tag/$f" "$OUT/${tag}.${f#dilution_}"
    done
    mkdir -p "$OUT/${tag}.clean" && cp "$OUT/work_$tag"/clean/*.summary.tsv "$OUT/${tag}.clean/"
    rm -rf "$OUT/work_$tag"
}
run shift_nm2.5 shift 0,0.02,0.05,0.08,0.10,0.12,0.15,0.20,0.25
run ideal_nm2.5 ideal 0,0.02,0.05,0.08,0.10,0.12,0.15,0.20,0.25
run shift_nm2.0 shift 0,0.05,0.08,0.10,0.12,0.15,0.20 "--noise-mult 2.0"
run shift_nm1.5 shift 0,0.05,0.08,0.10,0.12,0.15,0.20 "--noise-mult 1.5"
echo; echo "results in $OUT:"; ls -1 "$OUT"
