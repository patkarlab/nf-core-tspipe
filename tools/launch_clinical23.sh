#!/usr/bin/env bash
# tools/launch_clinical23.sh -- launch nf-core-tspipe on clinical-23.
#
# Use this instead of launch_tspipe.sh, whose defaults are for the development host: it launches
# with `-profile gandalf,singularity`, which resolves every reference under /goast and fails on
# this cluster with "No such file or directory: /goast/...". That is not a reference problem; it
# is the wrong profile.
#
# This wrapper supplies everything a run on this site needs and refuses the two launches that
# produce wrong or incomplete results rather than an obvious failure:
#
#   * the head process must run on the login node. DASHBOARD (GeneBe, MobiDetails, CancerVar,
#     OncoKB) and VARIANT_VALIDATOR run wherever Nextflow runs, and compute nodes here cannot
#     resolve external names. A run whose head process sat on a compute node on 2026-09-09
#     produced reports with silently empty annotation sections. Do not submit this script with
#     qsub; run it on ln1 and let PBS receive the computational tasks.
#   * the panel overlay and the site parameter file must both be present, or the run fails at
#     AMBER with a missing hmftools resource.
#
# Usage, from the pipeline directory on ln1:
#     bash tools/launch_clinical23.sh <samplesheet.csv> <run name> [extra nextflow args]
# e.g.
#     bash tools/launch_clinical23.sh myrun.csv myrun_20260915
#     bash tools/launch_clinical23.sh myrun.csv myrun_20260915 -resume
#
# The run is detached: it continues after you log out. Progress goes to /tmp/<run name>.log.

set -uo pipefail

SAMPLESHEET=${1:-}
RUN=${2:-}
shift 2 2>/dev/null || true
EXTRA=("$@")

PIPELINE_DIR=${PIPELINE_DIR:-$HOME/pipelines/nf-core-tspipe-v1.0.0}
SCRATCH=${SCRATCH:-/scratch/patkarlab-clinical}
PROFILE=${PROFILE:-clinical23,singularity}
PANEL_CONFIG=${PANEL_CONFIG:-conf/twist_apply.config}
PARAMS_FILE=${PARAMS_FILE:-params_clinical23.yaml}
VV_URL=${VV_URL:-https://rest.variantvalidator.org}
LOGIN_NODE=${LOGIN_NODE:-ln1}

log() { printf '[%s] %s\n' "$(date '+%F %T')" "$*"; }
die() { printf '[%s] ERROR: %s\n' "$(date '+%F %T')" "$*" >&2; exit 1; }

[ -n "$SAMPLESHEET" ] && [ -n "$RUN" ] || die "usage: bash tools/launch_clinical23.sh <samplesheet.csv> <run name> [extra nextflow args]"

# ---- refuse to run from a batch job -------------------------------------------------------
# checked before anything else, so the reason given is the real one
if [ -n "${PBS_JOBID:-}" ]; then
    die "this is running inside a PBS job ($PBS_JOBID). The head process must run on $LOGIN_NODE:
  the dashboard's annotation lookups and VariantValidator need internet access, which compute
  nodes do not have, and they fail silently rather than stopping the run. Run this script
  directly on $LOGIN_NODE; the computational tasks are submitted to PBS by Nextflow itself."
fi
if [ "$(hostname -s)" != "$LOGIN_NODE" ]; then
    die "running on $(hostname -s), expected $LOGIN_NODE. See the note above; override with LOGIN_NODE= if the login node has been renamed."
fi

cd "$PIPELINE_DIR" || die "pipeline directory not found: $PIPELINE_DIR"

# ---- inputs --------------------------------------------------------------------------------
[ -f "$SAMPLESHEET" ] || die "samplesheet not found: $SAMPLESHEET"
[ -f "$PANEL_CONFIG" ] || die "panel overlay not found: $PANEL_CONFIG"
[ -f "$PARAMS_FILE" ]  || die "site parameter file not found: $PARAMS_FILE (it redirects the hmftools reference paths; without it the run fails at AMBER)"

missing=0
while IFS=, read -r sample f1 f2 rest; do
    [ "$sample" = "sample" ] && continue
    [ -z "${sample:-}" ] && continue
    for f in "$f1" "$f2"; do
        [ -f "$f" ] || { echo "  missing FASTQ: $f" >&2; missing=1; }
    done
done < "$SAMPLESHEET"
[ "$missing" = 0 ] || die "one or more FASTQ files in $SAMPLESHEET do not exist"
n=$(( $(wc -l < "$SAMPLESHEET") - 1 ))

OUTDIR=${OUTDIR:-$SCRATCH/$RUN}
WORKDIR=${WORKDIR:-$SCRATCH/work_$RUN}
LOG=/tmp/${RUN}.log
[ -e "$OUTDIR" ] && log "note: $OUTDIR exists; outputs will be added to it (use -resume for an interrupted run)"

# ---- no concurrent run against the same work directory --------------------------------------
if pgrep -u "$USER" -f "nextflow.*-w $WORKDIR" >/dev/null 2>&1 || pgrep -u "$USER" -f "$RUN" >/dev/null 2>&1; then
    die "a Nextflow process for this run appears to be active. Wait for it to exit (Nextflow holds a session lock) before resuming."
fi

# ---- VariantValidator preflight --------------------------------------------------------------
log "VariantValidator preflight: $VV_URL"
code=$(curl -s -m 15 -o /dev/null -w '%{http_code}' "$VV_URL/" 2>/dev/null)
if [ "$code" = "200" ]; then
    log "VariantValidator preflight: OK"
else
    die "VariantValidator endpoint returned '$code' from $(hostname -s). The annotation step will fail.
  Check outbound access, then retry. To proceed deliberately without it, re-run with
  VV_URL=<endpoint> after confirming the service is reachable."
fi

# ---- disk ------------------------------------------------------------------------------------
avail=$(df -BG --output=avail "$SCRATCH" | tail -1 | tr -dc 0-9)
need=$(( n * 28 ))
log "space on $SCRATCH: ${avail} GB available, approximately ${need} GB needed for ${n} sample(s)"
[ "$avail" -gt "$need" ] || die "insufficient space on $SCRATCH"

# ---- launch ------------------------------------------------------------------------------------
log "pipeline   $PIPELINE_DIR ($(git describe --tags 2>/dev/null || echo 'not a git checkout'))"
log "samples    $n from $SAMPLESHEET"
log "profile    $PROFILE"
log "overlays   $PANEL_CONFIG, $PARAMS_FILE"
log "outdir     $OUTDIR"
log "workdir    $WORKDIR"
log "log        $LOG"
[ ${#EXTRA[@]} -gt 0 ] && log "extra      ${EXTRA[*]}"

setsid nextflow run . \
    --input "$SAMPLESHEET" \
    --outdir "$OUTDIR" \
    -w "$WORKDIR" \
    -profile "$PROFILE" \
    -c "$PANEL_CONFIG" \
    -params-file "$PARAMS_FILE" \
    -ansi-log false \
    "${EXTRA[@]}" \
    > "$LOG" 2>&1 < /dev/null &
disown

sleep 20
if pgrep -u "$USER" -f "nextflow.*$RUN" >/dev/null 2>&1 || pgrep -u "$USER" -f "nextflow-.*one.jar run" >/dev/null 2>&1; then
    log "launched. Monitor with:"
    log "  grep -cE 'Submitted process' $LOG"
    log "  grep -E 'ERROR|terminated with' $LOG | tail"
    log "  qstat -u $USER | grep -c nf-TSPIPE"
    log "Complete when $LOG contains 'Cleanup complete'."
else
    printf '\n---- first lines of %s ----\n' "$LOG" >&2
    tail -20 "$LOG" >&2
    die "Nextflow exited immediately; see $LOG"
fi
