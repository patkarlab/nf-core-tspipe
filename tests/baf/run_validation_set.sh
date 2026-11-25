#!/usr/bin/env bash
# tests/baf/run_validation_set.sh -- the validation set of BAF_HETLOSS_V1, old detector against new.
#
#   bash tests/baf/run_validation_set.sh OUTPUT_DIRECTORY [events|specificity|all]
#   BASE=/path/to/SAMPLE/cnv_gatk/SAMPLE bash tests/baf/run_validation_set.sh OUTPUT_DIRECTORY real
#
# Part "events": clone-fraction titrations of planted events on synthetic samples (20 replicates
# per level). Part "specificity": synthetic samples without any event, clean, contaminated and at
# reduced depth (1,300 samples). "all" runs these two; about 12 minutes on one core, and the two
# parts can run side by side.
#
# Part "real": the same titrations planted in a real sample, which keeps its own noise at every
# site that is not redrawn (see titrate_het_loss.py, --base). BASE is the prefix of the sample's
# .allelicCounts.tsv and .denoisedCR.tsv. Choose a sample without events; ARMS (default
# "11q 17p 13q 20q") names the arms for the copy-neutral titration and must not include an arm
# that carries an event in that sample. This part needs patient data and is therefore run on
# the analysis server, not in the repository's own tests.
#
# Every run of every sample is written to a TSV in OUTPUT_DIRECTORY and the per-level tables to
# events.txt, specificity.txt and real.txt. Seeds are fixed, so a re-run reproduces the tables.
# The synthetic tables of the change that introduced the test are in docs/audit/2026-11-25/.
set -euo pipefail

OUT=${1:?usage: run_validation_set.sh OUTPUT_DIRECTORY [events|specificity|all|real]}
PART=${2:-all}
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
T="${HERE}/titrate_het_loss.py"
PY=${PYTHON:-python3}
mkdir -p "${OUT}"

events() {
    {
    "${PY}" "${T}" --arm 11q --type cnloh --levels 0,0.2,0.4,0.6,0.7,0.75,0.8,0.85,0.9,0.95,0.98,1.0 --out "${OUT}/A_11q_cnloh.tsv"; echo
    "${PY}" "${T}" --arm 17p --type cnloh --levels 0.6,0.8,0.85,0.9,0.95,1.0 --out "${OUT}/B_17p_cnloh.tsv"; echo
    "${PY}" "${T}" --arm 9p  --type cnloh --levels 0.6,0.8,0.85,0.9,0.95,1.0 --out "${OUT}/C_9p_cnloh.tsv"; echo
    "${PY}" "${T}" --arm 20q --type cnloh --levels 0.6,0.8,0.85,0.9,0.95,1.0 --out "${OUT}/D_20q_cnloh.tsv"; echo
    "${PY}" "${T}" --arm 7q  --type del --sex male --levels 0.5,0.8,0.9,0.95,1.0 --out "${OUT}/E_7q_del.tsv"; echo
    "${PY}" "${T}" --arm 8q  --type gain --levels 0.5,1.0 --out "${OUT}/F_8q_gain.tsv"; echo
    "${PY}" "${T}" --arm 11q --type cnloh --contamination 0.05 --levels 0.8,0.9,0.95,1.0 --out "${OUT}/G_11q_cnloh_contamination_005.tsv"; echo
    "${PY}" "${T}" --arm 11q --type cnloh --depth-scale 0.25 --levels 0.9,0.95,1.0 --out "${OUT}/H1_11q_cnloh_depth_025.tsv"; echo
    "${PY}" "${T}" --arm 11q --type cnloh --depth-scale 0.10 --levels 0.9,0.95,1.0 --out "${OUT}/H2_11q_cnloh_depth_010.tsv"; echo
    "${PY}" "${T}" --arm 11q --type cnloh --region chr11:90000000-135086622 --levels 0.6,0.8,0.9,0.95,1.0 --out "${OUT}/I_11q_distal_cnloh.tsv"
    } > "${OUT}/events.txt"
    echo "[ok] events: ${OUT}/events.txt"
}

specificity() {
    {
    "${PY}" "${T}" --arm none --replicates 200 --sex female --seed 1000 --out "${OUT}/S1_clean_female.tsv"; echo
    "${PY}" "${T}" --arm none --replicates 200 --sex male --seed 5000 --out "${OUT}/S2_clean_male.tsv"; echo
    for c in 0.02 0.05 0.10 0.20; do
        "${PY}" "${T}" --arm none --replicates 100 --sex female --seed 9000 --contamination "${c}" --out "${OUT}/S3_contamination_${c}.tsv"; echo
    done
    for d in 0.25 0.10 0.05; do
        "${PY}" "${T}" --arm none --replicates 100 --sex male --seed 12000 --depth-scale "${d}" --out "${OUT}/S4_depth_${d}.tsv"; echo
    done
    } > "${OUT}/specificity.txt"
    echo "[ok] specificity: ${OUT}/specificity.txt"
}

real() {
    if [ -z "${BASE:-}" ]; then
        echo "[error] set BASE to the prefix of the .allelicCounts.tsv and .denoisedCR.tsv of a real sample" >&2
        exit 2
    fi
    local levels=0,0.6,0.7,0.8,0.85,0.9,0.95,0.98,1.0
    {
    for arm in ${ARMS:-11q 17p 13q 20q}; do
        "${PY}" "${T}" --base "${BASE}" --arm "${arm}" --type cnloh --levels "${levels}" --out "${OUT}/R_${arm}_cnloh.tsv"; echo
    done
    "${PY}" "${T}" --base "${BASE}" --arm 7q --type del --levels 0.5,0.8,0.9,0.95,1.0 --out "${OUT}/R_7q_del.tsv"; echo
    "${PY}" "${T}" --base "${BASE}" --arm 11q --type cnloh --region chr11:90000000-135086622 --levels 0.6,0.8,0.9,0.95,1.0 --out "${OUT}/R_11q_distal_cnloh.tsv"
    } > "${OUT}/real.txt"
    echo "[ok] real sample: ${OUT}/real.txt"
}

case "${PART}" in
    events)      events ;;
    specificity) specificity ;;
    all)         events; specificity ;;
    real)        real ;;
    *)           echo "[error] unknown part '${PART}' (events, specificity, all or real)" >&2; exit 2 ;;
esac
