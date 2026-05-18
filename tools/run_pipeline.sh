#!/usr/bin/env bash
# tools/run_pipeline.sh - Production launcher for nf-core-tspipe.
#
# Daily clinical workflow:
#   1. Build samplesheet (./tools/make_samplesheet.sh or by hand)
#   2. Run this script
#   3. Walk away (~4-8 hours for a typical run)
#
# Forwards any extra args ($@) to nextflow run so flags like -resume, -stub,
# --panel, --keep_intermediates still work.
#
# Env overrides:
#   TSPIPE_REPO       path to nf-core-tspipe checkout
#   TSPIPE_SAMPLES    samplesheet CSV path
#   TSPIPE_PROFILE    nextflow -profile string
#   TSPIPE_SKIP_PREFLIGHT  set to 1 to skip preflight checks (not recommended)

set -eo pipefail

REPO_DEFAULT="${TSPIPE_REPO:-/goast/hemat_data/nf-core-tspipe}"
OUTDIR_BASE="${TSPIPE_OUTDIR_BASE:-/goast/hemat_data/nfcore_runs}"
SAMPLES_DEFAULT="${TSPIPE_SAMPLES:-}"
PROFILE_DEFAULT="${TSPIPE_PROFILE:-gandalf,singularity}"

prompt_with_default() {
    local label="$1"
    local default="$2"
    local reply
    if [[ -n "$default" ]]; then
        read -r -p "${label} [${default}]: " reply
        echo "${reply:-$default}"
    else
        read -r -p "${label}: " reply
        echo "${reply}"
    fi
}

echo "============================================================"
echo "nf-core-tspipe launcher"
echo "============================================================"
REPO=$(prompt_with_default "Repo checkout" "$REPO_DEFAULT")
SAMPLES=$(prompt_with_default "Samplesheet CSV" "$SAMPLES_DEFAULT")

if [[ -z "$SAMPLES" ]]; then
    echo "ERROR: samplesheet path required" >&2
    echo "Tip: build one with: ${REPO}/tools/make_samplesheet.sh /path/to/fastq_dir > /tmp/today.csv" >&2
    exit 1
fi
if [[ ! -f "$SAMPLES" ]]; then
    echo "ERROR: samplesheet not found: $SAMPLES" >&2
    exit 1
fi

run_label_default="run_$(date +%Y%m%d_%H%M%S)"
RUN_LABEL=$(prompt_with_default "Run label (used in outdir name)" "$run_label_default")
OUTDIR="${OUTDIR_BASE}/${RUN_LABEL}"
PROFILE=$(prompt_with_default "Nextflow profile" "$PROFILE_DEFAULT")

LOG="/tmp/${RUN_LABEL}.log"

# ---- Preflight checks ------------------------------------------------------
if [[ "${TSPIPE_SKIP_PREFLIGHT:-0}" != "1" ]]; then
    echo
    echo "=== Preflight ==="

    # Samplesheet sanity
    sample_count=$(($(wc -l < "$SAMPLES") - 1))
    if [[ "$sample_count" -lt 1 ]]; then
        echo "ERROR: samplesheet has 0 samples (only header?)" >&2
        exit 1
    fi
    echo "  samplesheet: $sample_count samples"

    # Verify each FASTQ exists
    missing=0
    while IFS=, read -r sample r1 r2 sex; do
        [[ "$sample" == "sample" ]] && continue
        [[ -z "$sample" ]] && continue
        if [[ ! -f "$r1" ]]; then
            echo "    MISSING R1 for $sample: $r1" >&2
            missing=$((missing+1))
        fi
        if [[ ! -f "$r2" ]]; then
            echo "    MISSING R2 for $sample: $r2" >&2
            missing=$((missing+1))
        fi
    done < "$SAMPLES"
    if [[ "$missing" -gt 0 ]]; then
        echo "ERROR: $missing FASTQ files missing — fix samplesheet" >&2
        exit 1
    fi
    echo "  all FASTQs present"

    # Nextflow not already running
    if ps -ef | grep -E '[n]extflow.*tspipe' | grep -v grep > /dev/null; then
        echo "ERROR: another Nextflow tspipe run is active; refusing to launch a second one" >&2
        echo "  ps -ef | grep -E '[n]extflow.*tspipe'  to inspect" >&2
        exit 1
    fi
    echo "  no other Nextflow runs active"

    # VV REST containers
    vv_up=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -c '^rest_variantvalidator' || true)
    if [[ "$vv_up" -lt 4 ]]; then
        echo "ERROR: expected 4 VariantValidator containers, found $vv_up" >&2
        echo "  start: cd ~/targeted-seq-pipeline/software/rest_variantValidator && docker compose up -d" >&2
        exit 1
    fi
    http_code=$(curl -sf -o /dev/null -w '%{http_code}' --max-time 10 \
        "http://localhost:5001/VariantValidator/variantvalidator/GRCh38/NM_000088.4:c.589G%3ET/all?content-type=application/json" \
        2>/dev/null || echo "FAIL")
    if [[ "$http_code" != "200" ]]; then
        echo "ERROR: VV REST not responding (http=$http_code)" >&2
        echo "  restart API: docker exec -d rest_variantvalidator-rest-variantvalidator-1 bash -c 'cd /app/rest_VariantValidator && gunicorn -b 0.0.0.0:5000 --timeout 600 app --threads=5'" >&2
        exit 1
    fi
    echo "  VariantValidator REST: 4 containers up, HTTP 200"

    # Host conda + production scripts (used by VV/ONCOVI/FLT3_TO_VARIANTS modules)
    for f in /home/hemat/anaconda3/envs/targeted-seq/bin/python \
             /home/hemat/targeted-seq-pipeline/scripts/15_oncovi.py \
             /home/hemat/targeted-seq-pipeline/scripts/17_variant_validator.py \
             /home/hemat/targeted-seq-pipeline/scripts/17b_flt3_to_variants.py; do
        if [[ ! -f "$f" ]]; then
            echo "ERROR: missing: $f" >&2
            exit 1
        fi
    done
    echo "  host conda env + production scripts: present"

    # Disk space (rough heuristic: ~25 GB peak per sample for work + outdir)
    free_kb=$(df --output=avail /goast/hemat_data | tail -1)
    free_gb=$((free_kb / 1024 / 1024))
    need_gb=$((sample_count * 25))
    if [[ "$free_gb" -lt "$need_gb" ]]; then
        echo "WARNING: only $free_gb GB free; $sample_count samples may need ~$need_gb GB" >&2
        echo "  Continuing anyway. Press Ctrl-C in next 5s to abort."
        sleep 5
    else
        echo "  disk: $free_gb GB free (estimated need ~$need_gb GB)"
    fi
fi

mkdir -p "$OUTDIR_BASE"

# ---- Summary + confirm -----------------------------------------------------
echo
echo "============================================================"
echo "LAUNCH PLAN"
echo "============================================================"
echo "  repo:       $REPO"
echo "  samples:    $SAMPLES ($sample_count samples)"
echo "  outdir:     $OUTDIR"
echo "  profile:    $PROFILE"
echo "  log:        $LOG"
[[ $# -gt 0 ]] && echo "  extra args: $*"
echo
read -r -p "Launch now? [Y/n]: " confirm
case "${confirm:-Y}" in
    [Yy]|[Yy][Ee][Ss]) ;;
    *) echo "Aborted."; exit 1 ;;
esac

# ---- Background launch -----------------------------------------------------
cd "$REPO"

# nohup + & detaches from this shell so the run survives SSH disconnect.
# Output goes to LOG; stdin closed (no terminal needed).
nohup nextflow run . \
    -profile "$PROFILE" \
    --input  "$SAMPLES" \
    --outdir "$OUTDIR" \
    "$@" > "$LOG" 2>&1 < /dev/null &

NF_PID=$!
echo "$NF_PID" > "/tmp/${RUN_LABEL}.pid"

# Verify it stayed alive
sleep 8
if ! kill -0 "$NF_PID" 2>/dev/null; then
    echo "ERROR: Nextflow died within 8 seconds. First 50 lines of log:" >&2
    head -50 "$LOG" >&2
    exit 1
fi

echo
echo "============================================================"
echo "RUN LAUNCHED — PID $NF_PID, detached from this terminal"
echo "============================================================"
echo
echo "MONITOR ANY TIME (safe to disconnect SSH and come back):"
echo "  tail -f $LOG"
echo
echo "QUICK STATUS:"
echo "  grep -oE '\] (Cached|Submitted|Completed) process' $LOG | sort | uniq -c"
echo
echo "PER-MODULE PROGRESS:"
echo "  for m in FASTP BWA_MEM ABRA2 GATK4_MUTECT2 SOMATICSEQ_ENSEMBLE VEP_ANNOTATE VARIANT_FILTER ORGANIZE_OUTPUT; do"
echo "    n=\$(grep -c \"Submitted process.*\${m} \" $LOG 2>/dev/null)"
echo "    echo \"  \$m: \$n submitted\""
echo "  done"
echo
echo "STILL ALIVE?"
echo "  kill -0 $NF_PID 2>/dev/null && echo running || echo stopped"
echo
echo "WHEN DONE — VALIDATE deliverables:"
echo "  RUN=$OUTDIR"
echo "  echo \"Symlinks (must be 0):       \$(find \$RUN -path '*/clinical/*' -type l 2>/dev/null | wc -l)\""
echo "  echo \"Final BAMs (must be $sample_count):  \$(find \$RUN -path '*/clinical/*.final.bam' 2>/dev/null | wc -l)\""
echo "  echo \"Clinical TSVs (must be $sample_count): \$(find \$RUN -path '*/clinical/*clinical.final.tsv' 2>/dev/null | wc -l)\""
echo
echo "OUTPUT: each sample's deliverable tree at $OUTDIR/<sample>/clinical/"
echo "============================================================"
