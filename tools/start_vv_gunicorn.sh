#!/usr/bin/env bash
# start_vv_gunicorn.sh -- ensure the VariantValidator REST gunicorn is
# running inside the VV container, bound to container port 5000.
#
# Why this script exists
# ----------------------
# The upstream VariantValidator docker-compose stack (vendored under
# /goast/hemat_data/targeted-seq-pipeline/software/rest_variantValidator/)
# deliberately leaves PID 1 of the application container as
# 'sleep infinity'. Upstream's design is that the operator launches
# gunicorn manually with 'docker exec' after 'compose up' brings up
# the DBs; see software/rest_variantValidator/docs/DOCKER.md for the
# upstream procedure and rationale.
#
# The host port mapping in compose is 5001 -> container 5000, and
# both the production pipeline (scripts/17_variant_validator.py) and
# the nf-core port (modules/local/variant_validator.nf, bin/variant_validator.py)
# call http://localhost:5001. So gunicorn must be bound to container
# port 5000 after the stack comes up.
#
# On 2026-05-19 the VV stack was migrated to named docker volumes.
# The container restart that came with that migration killed the
# previously-running gunicorn on container port 5000, and the
# re-exec'd gunicorn went to container port 8000 instead. Result:
# the nextflow run failed at VARIANT_VALIDATOR with 'Cannot connect
# to VV'. The workaround at the time was a second 'docker exec -d'
# starting another gunicorn on container port 5000. This script
# turns that workaround into an idempotent, documented procedure so
# any future container restart can be recovered with one command.
#
# What it does
# ------------
# 1. Verifies the VV container is present and running.
# 2. Detects any existing gunicorn bound to container port 5000.
#    By default, kills it (matches operator's prior debugging
#    pattern of pkill-then-relaunch). With --no-restart, leaves an
#    existing gunicorn alone and only verifies readiness.
# 3. Launches gunicorn via 'docker exec -d', bound to container
#    port 5000, with the same flag set the pipeline expects.
# 4. Polls http://localhost:<host-port>/ until any HTTP code in
#    1xx-4xx is returned (5xx is gunicorn-broken; 000 is
#    not-listening). Times out after --timeout seconds.
#
# Container PID 1 ('sleep infinity') is unchanged. Other ports
# (8000, 5050, 9000) and other gunicorns inside the container are
# left untouched.
#
# Audit memos (nf-core repo):
#   docs/audit/2026-05-19/morning_findings.md
#   docs/audit/2026-05-19/d1d2_real_data_findings.md

set -euo pipefail

CONTAINER="rest_variantvalidator-rest-variantvalidator-1"
CONTAINER_PORT="5000"
HOST_PORT="5001"
WAIT_TIMEOUT_SEC=60
NO_RESTART=0

usage() {
    cat <<EOF
Usage: $0 [--container NAME] [--port HOST_PORT] [--timeout SECONDS] [--no-restart]

Ensure the VariantValidator REST gunicorn is running on container
port ${CONTAINER_PORT}, reachable on host port ${HOST_PORT}.

Options:
  --container NAME     VV container name (default: ${CONTAINER})
  --port HOST_PORT     Host port to poll for readiness (default: ${HOST_PORT})
  --timeout SECONDS    How long to wait for readiness (default: ${WAIT_TIMEOUT_SEC})
  --no-restart         If a gunicorn on container port ${CONTAINER_PORT}
                       is already running, do not kill it; only verify
                       readiness. (Default: kill and relaunch.)
  -h, --help           Show this help.

Requires sudo for docker commands.
EOF
}

log() { echo "[start_vv_gunicorn] $*"; }
err() { echo "[start_vv_gunicorn] ERROR: $*" >&2; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        --container)  CONTAINER="$2";        shift 2 ;;
        --port)       HOST_PORT="$2";        shift 2 ;;
        --timeout)    WAIT_TIMEOUT_SEC="$2"; shift 2 ;;
        --no-restart) NO_RESTART=1;          shift   ;;
        -h|--help)    usage; exit 0 ;;
        *) err "unknown flag: $1"; usage >&2; exit 1 ;;
    esac
done

# Step 1. Container must exist and be running.
status="$(sudo docker inspect -f '{{.State.Status}}' "${CONTAINER}" 2>/dev/null || echo absent)"
case "${status}" in
    running)
        log "container OK: ${CONTAINER} (running)"
        ;;
    absent)
        err "container '${CONTAINER}' not found"
        err "bring up the stack first:"
        err "  cd /goast/hemat_data/targeted-seq-pipeline/software/rest_variantValidator/"
        err "  sudo docker compose up -d"
        exit 2
        ;;
    *)
        err "container '${CONTAINER}' is in state '${status}', not 'running'"
        err "start it with: sudo docker start ${CONTAINER}"
        exit 2
        ;;
esac

# Step 2. Detect existing gunicorn on container port ${CONTAINER_PORT}.
existing="$(
    sudo docker exec "${CONTAINER}" bash -c \
        "ps -ef | grep -v grep | grep -F gunicorn | grep -F '0.0.0.0:${CONTAINER_PORT}' || true"
)"

if [[ -n "${existing}" ]]; then
    if [[ ${NO_RESTART} -eq 1 ]]; then
        log "existing gunicorn on container port ${CONTAINER_PORT} found; --no-restart, leaving in place:"
        echo "${existing}" | sed 's/^/  /'
    else
        log "existing gunicorn on container port ${CONTAINER_PORT} found; killing:"
        echo "${existing}" | sed 's/^/  /'
        sudo docker exec "${CONTAINER}" bash -c "
            pkill -TERM -f 'gunicorn.*-b 0\\.0\\.0\\.0:${CONTAINER_PORT}' || true
            sleep 2
            pkill -KILL -f 'gunicorn.*-b 0\\.0\\.0\\.0:${CONTAINER_PORT}' 2>/dev/null || true
        "
        existing=""
    fi
fi

# Step 3. Launch fresh gunicorn unless --no-restart kept an existing one.
if [[ -z "${existing}" ]]; then
    log "launching gunicorn on container port ${CONTAINER_PORT}"
    sudo docker exec -d "${CONTAINER}" \
        gunicorn -b "0.0.0.0:${CONTAINER_PORT}" \
                 --workers 1 --threads 5 --timeout 600 \
                 wsgi:app --chdir ./rest_VariantValidator/
fi

# Step 4. Poll host port for readiness.
log "waiting for HTTP response on http://localhost:${HOST_PORT}/ (up to ${WAIT_TIMEOUT_SEC}s)"
deadline=$(( $(date +%s) + WAIT_TIMEOUT_SEC ))
last_code="000"
while [[ $(date +%s) -lt ${deadline} ]]; do
    last_code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "http://localhost:${HOST_PORT}/" || echo 000)"
    if [[ "${last_code}" =~ ^[1-4][0-9][0-9]$ ]]; then
        log "OK: http://localhost:${HOST_PORT}/ responded HTTP ${last_code}"
        exit 0
    fi
    sleep 2
done

err "http://localhost:${HOST_PORT}/ did not respond within ${WAIT_TIMEOUT_SEC}s (last code: ${last_code})"
err "check gunicorn state inside the container:"
err "  sudo docker exec ${CONTAINER} ps -ef | grep -v defunct | grep gunicorn"
exit 3
