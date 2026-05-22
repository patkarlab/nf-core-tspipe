#!/usr/bin/env bash
#
# launch_tspipe.sh
#
# Launch the nf-core-tspipe Nextflow pipeline with a VariantValidator (VV)
# health preflight check. If VV is unreachable on the initial probe, the
# wrapper attempts a bounded auto-recovery (one cycle of the standard
# SOP procedure: docker compose up -d, then start gunicorn, then wait
# for warm-up). Nextflow is only launched once VV returns HTTP 200.
#
# Exit codes:
#   0   nextflow exited successfully
#   10  VV preflight failed; nextflow NOT launched
#   N   any other code is propagated from nextflow itself
#
# Usage:
#   ./launch_tspipe.sh [-- nextflow_arg ...]
#
# Examples:
#   ./launch_tspipe.sh
#       Uses defaults below to launch the standard batch.
#
#   OUTDIR=test_run/20260522_144827 ./launch_tspipe.sh
#       Override the output directory (e.g. for a resume).
#
#   ./launch_tspipe.sh -- -with-trace -with-report
#       Pass additional flags through to nextflow.
#
# All configuration is via environment variables — see CONFIGURATION below.
# See docs/sops/vv_troubleshooting.md for the manual SOP this wrapper automates.
#

set -euo pipefail

# ======================================================================
# CONFIGURATION (override via environment variables before invocation)
# ======================================================================

# VV REST endpoint
VV_URL="${VV_URL:-http://localhost:5001}"

# Test variant exercised on the health probe.
# COL1A1 c.589G>T — single SNV in a canonical MANE transcript. Stable.
VV_TEST_PATH="${VV_TEST_PATH:-VariantValidator/variantvalidator/GRCh38/NM_000088.4:c.589G%3ET/all?content-type=application/json}"

# Docker compose directory and REST container name
VV_COMPOSE_DIR="${VV_COMPOSE_DIR:-$HOME/targeted-seq-pipeline/software/rest_variantValidator}"
VV_CONTAINER="${VV_CONTAINER:-rest_variantvalidator-rest-variantvalidator-1}"

# Timeouts (seconds)
VV_PROBE_TIMEOUT="${VV_PROBE_TIMEOUT:-10}"
VV_WARMUP_SECONDS="${VV_WARMUP_SECONDS:-90}"

# Nextflow run parameters — override these to launch a different batch
PIPELINE_DIR="${PIPELINE_DIR:-/goast/hemat_data/nf-core-tspipe}"
SAMPLESHEET="${SAMPLESHEET:-samplesheet.csv}"
OUTDIR="${OUTDIR:-test_run/$(date +%Y%m%d_%H%M%S)}"
PROFILE="${PROFILE:-gandalf,singularity}"
EXTRA_NEXTFLOW_ARGS="${EXTRA_NEXTFLOW_ARGS:--resume -bg}"

# ======================================================================
# Implementation
# ======================================================================

log() {
    printf '[%(%Y-%m-%d %H:%M:%S)T] [launch_tspipe] %s\n' -1 "$*"
}

err() {
    printf '[%(%Y-%m-%d %H:%M:%S)T] [launch_tspipe] ERROR: %s\n' -1 "$*" >&2
}

# Returns 0 if VV returns HTTP 200 on the test query, 1 otherwise.
vv_health_check() {
    local code
    code=$(curl -sf -o /dev/null -w '%{http_code}' \
            --max-time "$VV_PROBE_TIMEOUT" \
            "${VV_URL}/${VV_TEST_PATH}" 2>/dev/null || true)
    if [[ "$code" == "200" ]]; then
        return 0
    fi
    log "VV health probe returned: HTTP ${code:-unknown}"
    return 1
}

# Returns 0 if recovery procedure completed, 1 if any step failed.
# Does NOT re-probe VV — caller is expected to re-run vv_health_check.
vv_attempt_recovery() {
    log "Attempting VV auto-recovery (one cycle)."

    # Step 1: ensure containers are up (idempotent)
    log "  docker compose up -d (in $VV_COMPOSE_DIR)"
    if ! ( cd "$VV_COMPOSE_DIR" && docker compose up -d ) >/tmp/launch_tspipe_compose.log 2>&1 ; then
        err "  docker compose up -d failed; see /tmp/launch_tspipe_compose.log"
        return 1
    fi
    sleep 5

    # Step 2: ensure gunicorn is running inside the REST container
    local gunicorn_running=0
    if docker exec "$VV_CONTAINER" ps -ef 2>/dev/null | grep -E '[g]unicorn' >/dev/null ; then
        log "  gunicorn already running inside $VV_CONTAINER"
        gunicorn_running=1
    else
        log "  gunicorn NOT running; starting it inside $VV_CONTAINER"
        if ! docker exec -d "$VV_CONTAINER" bash -c \
            'cd /app/rest_VariantValidator && gunicorn -b 0.0.0.0:5000 --timeout 600 app --threads=5' ; then
            err "  failed to start gunicorn inside $VV_CONTAINER"
            return 1
        fi
    fi

    # Step 3: warm-up wait (skip if we never restarted gunicorn AND the probe
    # has been failing — that suggests something else is wrong, but caller will
    # detect it on the re-probe)
    if [[ $gunicorn_running -eq 0 ]]; then
        log "  waiting ${VV_WARMUP_SECONDS}s for gunicorn worker to warm up"
        sleep "$VV_WARMUP_SECONDS"
    else
        log "  brief 10s pause to allow transient blip to clear"
        sleep 10
    fi

    return 0
}

# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

# Pull any args after `--` as extra nextflow args
EXTRA_FROM_CLI=""
if [[ $# -gt 0 ]]; then
    if [[ "$1" == "--" ]]; then
        shift
        EXTRA_FROM_CLI="$*"
    else
        err "Unknown argument: $1"
        err "Usage: $0 [-- nextflow_arg ...]"
        exit 2
    fi
fi

log "=== nf-core-tspipe launch wrapper ==="
log "PIPELINE_DIR=$PIPELINE_DIR"
log "SAMPLESHEET=$SAMPLESHEET"
log "OUTDIR=$OUTDIR"
log "PROFILE=$PROFILE"
log "VV_URL=$VV_URL"

# Sanity check on pipeline directory
if [[ ! -d "$PIPELINE_DIR" ]]; then
    err "Pipeline directory does not exist: $PIPELINE_DIR"
    exit 2
fi

# ---- Preflight ----
log "VV preflight: probing $VV_URL"
if vv_health_check ; then
    log "VV preflight: OK (HTTP 200)"
else
    log "VV preflight: initial probe FAILED. Attempting auto-recovery."
    if ! vv_attempt_recovery ; then
        err "VV preflight: recovery step itself failed."
        err "  See docs/sops/vv_troubleshooting.md and run the manual procedure."
        exit 10
    fi

    log "VV preflight: re-probing after recovery"
    if ! vv_health_check ; then
        err "VV preflight: still FAILING after auto-recovery."
        err "  Run the diagnostic SOP at docs/sops/vv_troubleshooting.md"
        err "  Useful first command:"
        err "    docker exec $VV_CONTAINER tail -n 100 /tmp/vv_error.log"
        exit 10
    fi
    log "VV preflight: OK after recovery (HTTP 200)"
fi

# ---- Launch ----
cd "$PIPELINE_DIR"

NEXTFLOW_CMD=( nextflow run .
    --input "$SAMPLESHEET"
    --outdir "$OUTDIR"
    -profile "$PROFILE"
)

# Append extra args
# shellcheck disable=SC2206
EXTRA_ALL=( $EXTRA_NEXTFLOW_ARGS $EXTRA_FROM_CLI )
NEXTFLOW_CMD+=( "${EXTRA_ALL[@]}" )

log "Launching:"
log "  ${NEXTFLOW_CMD[*]}"

# exec replaces the wrapper process with nextflow so signals propagate cleanly
exec "${NEXTFLOW_CMD[@]}"
