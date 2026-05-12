#!/usr/bin/env bash
# =============================================================================
# download_annovar_db.sh
# Downloads ANNOVAR annotation databases for hg38.
# =============================================================================
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PIPELINE_DIR="$(dirname "${SCRIPT_DIR}")"
ANNOVAR_DIR="${PIPELINE_DIR}/software/annovar"
HUMANDB_DIR="${ANNOVAR_DIR}/humandb"
ANNOTATE="${ANNOVAR_DIR}/annotate_variation.pl"
BUILDVER="hg38"

log()  { echo -e "\n[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
warn() { echo -e "\n[WARNING] $*"; }
err()  { echo -e "\n[ERROR] $*" >&2; }

# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------
if [[ ! -x "${ANNOTATE}" ]]; then
    err "annotate_variation.pl not found at ${ANNOTATE}"
    err "Install ANNOVAR first. See setup_environment.sh for instructions."
    exit 1
fi

mkdir -p "${HUMANDB_DIR}"

# ---------------------------------------------------------------------------
# Database list
# ---------------------------------------------------------------------------
# Gene-based annotation
GENE_DBS=(
    refGene
)

# Filter-based annotation (use -webfrom annovar for pre-built downloads)
FILTER_DBS=(
    # Functional prediction
    cosmic94_coding
    clinvar_20220320
    dbnsfp42a
    dbscsnv11
    intervar_20180118

    # Population frequencies
    gnomad30_genome
    gnomad40_genome
    gnomad40_exome
    exac03
    esp6500siv2_all
    abraom
    korean_wgs
    kaviar_20150923

    # dbSNP
    avsnp150

    # 1000 Genomes
    1000g2015aug
)

# ---------------------------------------------------------------------------
# Download helper
# ---------------------------------------------------------------------------
download_db() {
    local db="$1"
    local mode="$2"   # "gene" or "filter"

    log "Downloading ${db} (${BUILDVER}, ${mode})..."

    local cmd=("${ANNOTATE}" -buildver "${BUILDVER}" -downdb)

    if [[ "${mode}" == "gene" ]]; then
        cmd+=("${db}" "${HUMANDB_DIR}")
    else
        cmd+=(-webfrom annovar "${db}" "${HUMANDB_DIR}")
    fi

    if "${cmd[@]}" 2>&1 | tail -3; then
        log "  OK: ${db}"
    else
        warn "  FAILED: ${db} — check network or ANNOVAR license."
    fi
}

# ---------------------------------------------------------------------------
# Run downloads
# ---------------------------------------------------------------------------
log "=== ANNOVAR Database Download ==="
log "Build:    ${BUILDVER}"
log "Target:   ${HUMANDB_DIR}"
log "Databases: ${#GENE_DBS[@]} gene-based + ${#FILTER_DBS[@]} filter-based"

for db in "${GENE_DBS[@]}"; do
    download_db "${db}" "gene"
done

for db in "${FILTER_DBS[@]}"; do
    download_db "${db}" "filter"
done

# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------
log "=== Verification ==="

ALL_DBS=("${GENE_DBS[@]}" "${FILTER_DBS[@]}")
ok=0
fail=0

printf "\n%-30s %s\n" "DATABASE" "STATUS"
printf "%-30s %s\n" "------------------------------" "------"

for db in "${ALL_DBS[@]}"; do
    # Check for at least one file matching this database name
    if ls "${HUMANDB_DIR}/${BUILDVER}_${db}"* &>/dev/null; then
        printf "%-30s %s\n" "${db}" "OK"
        ok=$((ok + 1))
    else
        printf "%-30s %s\n" "${db}" "MISSING"
        fail=$((fail + 1))
    fi
done

echo ""
log "Downloaded: ${ok}/${#ALL_DBS[@]} databases"
if [[ ${fail} -gt 0 ]]; then
    warn "${fail} database(s) failed. Re-run this script to retry."
fi

log "Databases stored in: ${HUMANDB_DIR}"
