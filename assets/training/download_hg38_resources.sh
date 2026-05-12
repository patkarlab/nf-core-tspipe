#!/usr/bin/env bash
# =============================================================================
# download_hg38_resources.sh
# Downloads GATK hg38 resource bundle files from the Broad Institute.
#
# Sources:
#   gs://gcp-public-data--broad-references/hg38/v0/
#   gs://gatk-best-practices/somatic-hg38/
# =============================================================================
set -eo pipefail

OUTDIR="$HOME/references/dbSNPGATK_hg38"
BROAD_URL="https://storage.googleapis.com/gcp-public-data--broad-references/hg38/v0"
SOMATIC_URL="https://storage.googleapis.com/gatk-best-practices/somatic-hg38"

log()  { echo -e "\n[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
warn() { echo -e "\n[WARNING] $*"; }

mkdir -p "${OUTDIR}"

# ---------------------------------------------------------------------------
# Files to download: "local_filename|url"
# ---------------------------------------------------------------------------
FILES=(
    # dbSNP (Broad bundles as dbsnp138 for hg38)
    "Homo_sapiens_assembly38.dbsnp138.vcf.gz|${BROAD_URL}/Homo_sapiens_assembly38.dbsnp138.vcf.gz"
    "Homo_sapiens_assembly38.dbsnp138.vcf.gz.tbi|${BROAD_URL}/Homo_sapiens_assembly38.dbsnp138.vcf.gz.tbi"

    # Mills & 1000G gold standard indels (BQSR, indel realignment)
    "Mills_and_1000G_gold_standard.indels.hg38.vcf.gz|${BROAD_URL}/Mills_and_1000G_gold_standard.indels.hg38.vcf.gz"
    "Mills_and_1000G_gold_standard.indels.hg38.vcf.gz.tbi|${BROAD_URL}/Mills_and_1000G_gold_standard.indels.hg38.vcf.gz.tbi"

    # 1000G high-confidence SNPs (VQSR training)
    "1000G_phase1.snps.high_confidence.hg38.vcf.gz|${BROAD_URL}/1000G_phase1.snps.high_confidence.hg38.vcf.gz"
    "1000G_phase1.snps.high_confidence.hg38.vcf.gz.tbi|${BROAD_URL}/1000G_phase1.snps.high_confidence.hg38.vcf.gz.tbi"

    # Known indels (BQSR)
    "Homo_sapiens_assembly38.known_indels.vcf.gz|${BROAD_URL}/Homo_sapiens_assembly38.known_indels.vcf.gz"
    "Homo_sapiens_assembly38.known_indels.vcf.gz.tbi|${BROAD_URL}/Homo_sapiens_assembly38.known_indels.vcf.gz.tbi"

    # gnomAD AF-only (Mutect2 germline resource) — ~3 GB
    "af-only-gnomad.hg38.vcf.gz|${SOMATIC_URL}/af-only-gnomad.hg38.vcf.gz"
    "af-only-gnomad.hg38.vcf.gz.tbi|${SOMATIC_URL}/af-only-gnomad.hg38.vcf.gz.tbi"
)

# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------
log "=== GATK hg38 Resource Bundle Download ==="
log "Target: ${OUTDIR}"
log "Files:  ${#FILES[@]}"

ok=0
fail=0

for entry in "${FILES[@]}"; do
    fname="${entry%%|*}"
    url="${entry#*|}"
    dest="${OUTDIR}/${fname}"

    if [[ -f "${dest}" ]] && [[ -s "${dest}" ]]; then
        log "  SKIP (exists): ${fname}"
        ok=$((ok + 1))
        continue
    fi

    log "  Downloading: ${fname}..."
    if wget --no-check-certificate -q --show-progress -c "${url}" -O "${dest}"; then
        ok=$((ok + 1))
    else
        warn "  FAILED: ${fname}"
        rm -f "${dest}"
        fail=$((fail + 1))
    fi
done

# ---------------------------------------------------------------------------
# Symlink into project references
# ---------------------------------------------------------------------------
PIPELINE_REF="$(cd "$(dirname "$0")/.." && pwd)/references"
if [[ -d "${PIPELINE_REF}" ]] && [[ ! -e "${PIPELINE_REF}/dbSNPGATK_hg38" ]]; then
    ln -sf "${OUTDIR}" "${PIPELINE_REF}/dbSNPGATK_hg38"
    log "Symlinked: ${PIPELINE_REF}/dbSNPGATK_hg38 -> ${OUTDIR}"
fi

# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------
log "=== Verification ==="

printf "\n%-55s %10s  %s\n" "FILE" "SIZE" "STATUS"
printf "%-55s %10s  %s\n" "-------------------------------------------------------" "----------" "------"

for entry in "${FILES[@]}"; do
    fname="${entry%%|*}"
    dest="${OUTDIR}/${fname}"
    if [[ -f "${dest}" ]] && [[ -s "${dest}" ]]; then
        size=$(du -h "${dest}" | cut -f1)
        printf "%-55s %10s  %s\n" "${fname}" "${size}" "OK"
    else
        printf "%-55s %10s  %s\n" "${fname}" "-" "MISSING"
    fi
done

echo ""
log "Downloaded: ${ok}/${#FILES[@]} files"
if [[ ${fail} -gt 0 ]]; then
    warn "${fail} file(s) failed. Re-run this script to retry."
    exit 1
fi

log "Done. Resources stored in: ${OUTDIR}"
