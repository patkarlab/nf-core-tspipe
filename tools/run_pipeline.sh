#!/usr/bin/env bash
# tools/run_pipeline.sh - Interactive wrapper for the nf-core-tspipe pipeline.
#
# Prompts for the variables that change between runs (samplesheet, output
# directory) and falls through to sensible defaults if the user hits enter.
# Forwards any extra args ($@) to nextflow run so flags like -resume, -stub,
# --panel, --keep_intermediates still work.
#
# Defaults assume the canonical gandalf layout. Override via prompt or env vars:
#   TSPIPE_REPO       path to nf-core-tspipe checkout
#   TSPIPE_OUTDIR     output directory for this run
#   TSPIPE_SAMPLES    samplesheet CSV path
#   TSPIPE_PROFILE    nextflow -profile string

set -eo pipefail

REPO_DEFAULT="${TSPIPE_REPO:-/goast/hemat_data/nf-core-tspipe}"
OUTDIR_BASE="${TSPIPE_OUTDIR_BASE:-/goast/hemat_data/nfcore_runs}"
SAMPLES_DEFAULT="${TSPIPE_SAMPLES:-/tmp/cnv_wiring/validation_samplesheet.csv}"
PROFILE_DEFAULT="${TSPIPE_PROFILE:-singularity}"

prompt_with_default() {
    local label="$1"
    local default="$2"
    local reply
    read -r -p "${label} [${default}]: " reply
    echo "${reply:-$default}"
}

echo "=== nf-core-tspipe interactive launcher ==="
REPO=$(prompt_with_default "Repo checkout" "$REPO_DEFAULT")
SAMPLES=$(prompt_with_default "Samplesheet CSV" "$SAMPLES_DEFAULT")

run_label_default="run_$(date +%Y%m%d_%H%M%S)"
RUN_LABEL=$(prompt_with_default "Run label (used in outdir)" "$run_label_default")
OUTDIR_DEFAULT="${OUTDIR_BASE}/${RUN_LABEL}"
OUTDIR=$(prompt_with_default "Output directory" "$OUTDIR_DEFAULT")

PROFILE=$(prompt_with_default "Nextflow profile" "$PROFILE_DEFAULT")

# Filesystem-mismatch warning: hardlinks require same mount as work/.
WORK_DEV=$(stat -c '%d' "${REPO}/work" 2>/dev/null || stat -c '%d' "${REPO}")
OUTDIR_PARENT=$(dirname "$OUTDIR")
mkdir -p "$OUTDIR_PARENT"
OUT_DEV=$(stat -c '%d' "$OUTDIR_PARENT")
if [[ "$WORK_DEV" != "$OUT_DEV" ]]; then
    cat >&2 <<EOF
WARNING: outdir ($OUTDIR) and work dir ($REPO/work) are on different
filesystems (dev $WORK_DEV vs $OUT_DEV). publishDir mode 'link' will silently
fall back to copy; expect ~2x disk usage and slower publishing.
Press Ctrl-C to abort, or Enter to continue anyway.
EOF
    read -r _
fi

echo
echo "Launching:"
echo "  cd $REPO"
echo "  nextflow run . \\"
echo "    -profile $PROFILE \\"
echo "    --input  $SAMPLES \\"
echo "    --outdir $OUTDIR \\"
[[ $# -gt 0 ]] && echo "    $* \\"
echo

cd "$REPO"
exec nextflow run . \
    -profile "$PROFILE" \
    --input  "$SAMPLES" \
    --outdir "$OUTDIR" \
    "$@"
