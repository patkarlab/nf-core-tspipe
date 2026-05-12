#!/usr/bin/env bash
# =============================================================================
# run_masked_realign.sh
# Re-align all 25 BNC normal samples against the GRC-exclusion-masked GRCh38
# reference, then rebuild the CNVKit panel-of-normals.
# =============================================================================
set -euo pipefail

PIPELINE_DIR="/goast/hemat_data/targeted-seq-pipeline"
MASKED_REF="${PIPELINE_DIR}/references/hg38_broad/Homo_sapiens_assembly38.masked.fasta"
BED="${PIPELINE_DIR}/bedfiles/MYOPOOL_240125_UBTF_hg38.bed"
FASTQ_DIR="${PIPELINE_DIR}/BNC_fastq"
OUTDIR="${PIPELINE_DIR}/results_masked"
PON_OUTPUT="${PIPELINE_DIR}/references/cnvkit_hg38_pon.cnn"
PON_BUILD_DIR="${OUTDIR}/cnvkit_pon_build"

echo "=== Masked Reference Realignment Pipeline ==="
echo "Reference: ${MASKED_REF}"
echo "FASTQs:    ${FASTQ_DIR}"
echo "Output:    ${OUTDIR}"
echo "Started:   $(date)"
echo ""

# -------------------------------------------------------
# Step 0: Back up existing PoN
# -------------------------------------------------------
if [ -f "${PON_OUTPUT}" ]; then
    BACKUP="${PON_OUTPUT%.cnn}.unmasked_ref.cnn.bak"
    if [ ! -f "${BACKUP}" ]; then
        echo "[backup] Backing up existing PoN: ${PON_OUTPUT} -> ${BACKUP}"
        cp "${PON_OUTPUT}" "${BACKUP}"
    else
        echo "[backup] Backup already exists: ${BACKUP}"
    fi
fi

# Also back up sex-specific PoNs if they exist
for suffix in _male _female; do
    src="${PIPELINE_DIR}/references/cnvkit_hg38_pon${suffix}.cnn"
    dst="${PIPELINE_DIR}/references/cnvkit_hg38_pon${suffix}.unmasked_ref.cnn.bak"
    if [ -f "${src}" ] && [ ! -f "${dst}" ]; then
        echo "[backup] Backing up: ${src} -> ${dst}"
        cp "${src}" "${dst}"
    fi
done

echo ""

# -------------------------------------------------------
# Step 1: Re-align all 25 BNC samples (steps 01-05)
# -------------------------------------------------------
echo "=== Step 1: Realigning BNC samples ==="

python "${PIPELINE_DIR}/scripts/run_batch_preprocessing.py" \
    --fastq-dir "${FASTQ_DIR}" \
    --bed "${BED}" \
    --outdir "${OUTDIR}" \
    --threads 8 \
    --reference "${MASKED_REF}" \
    --skip-pon

REALIGN_EXIT=$?
if [ ${REALIGN_EXIT} -ne 0 ]; then
    echo "ERROR: Batch preprocessing exited with code ${REALIGN_EXIT}"
    echo "Continuing to PoN build with whatever samples succeeded..."
fi

echo ""
echo "=== Step 1 complete: $(date) ==="
echo ""

# -------------------------------------------------------
# Step 2: Rebuild CNVKit PoN from masked-ref BAMs
# -------------------------------------------------------
echo "=== Step 2: Rebuilding CNVKit PoN ==="

# Collect all final BAMs
BAMS=()
for bam in "${OUTDIR}"/BNC*/abra2/*.final.bam; do
    if [ -f "${bam}" ]; then
        BAMS+=("${bam}")
    fi
done

echo "Found ${#BAMS[@]} BAMs for PoN build"

if [ ${#BAMS[@]} -lt 2 ]; then
    echo "ERROR: Need at least 2 BAMs for PoN build, got ${#BAMS[@]}"
    exit 1
fi

mkdir -p "${PON_BUILD_DIR}"

cnvkit.py batch \
    --normal "${BAMS[@]}" \
    --targets "${BED}" \
    --fasta "${MASKED_REF}" \
    --output-reference "${PON_OUTPUT}" \
    --output-dir "${PON_BUILD_DIR}"

echo ""
echo "=== Step 2 complete: $(date) ==="
echo "PoN written to: ${PON_OUTPUT}"
ls -lh "${PON_OUTPUT}"

echo ""
echo "=== All done: $(date) ==="
