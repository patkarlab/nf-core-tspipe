#!/usr/bin/env bash
# Re-align 30 cnv_negatives normals against masked GRCh38 reference
# Output goes to same results_masked/ dir as BNC samples
set -euo pipefail

PIPELINE_DIR="/goast/hemat_data/targeted-seq-pipeline"
MASKED_REF="${PIPELINE_DIR}/references/hg38_broad/Homo_sapiens_assembly38.masked.fasta"
BED="${PIPELINE_DIR}/bedfiles/MYOPOOL_240125_UBTF_hg38.bed"
FASTQ_DIR="${PIPELINE_DIR}/cnv_negatives"
OUTDIR="${PIPELINE_DIR}/results_masked"

echo "=== Masked Reference Realignment: cnv_negatives (30 normals) ==="
echo "Reference: ${MASKED_REF}"
echo "FASTQs:    ${FASTQ_DIR}"
echo "Output:    ${OUTDIR}"
echo "Started:   $(date)"
echo ""

python "${PIPELINE_DIR}/scripts/run_batch_preprocessing.py" \
    --fastq-dir "${FASTQ_DIR}" \
    --bed "${BED}" \
    --outdir "${OUTDIR}" \
    --threads 8 \
    --reference "${MASKED_REF}" \
    --skip-pon

echo ""
echo "=== cnv_negatives batch complete: $(date) ==="
