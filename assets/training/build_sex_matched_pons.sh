#!/bin/bash
set -euo pipefail

# Build sex-matched CNVKit PONs for lymphoma panel
# Usage: nohup bash build_sex_matched_pons.sh > sex_matched_pon_build.log 2>&1 &

BED="/goast/hemat_data/Lymphoma_data/lymphoma_panel_hg38_clean.bed"
REF="/goast/hemat_data/targeted-seq-pipeline/references/hg38_broad/resources_broad_hg38_v0_Homo_sapiens_assembly38.fasta"
BAM_DIR="/goast/hemat_data/Lymphoma_data/results_gDNA/gDNA_PON"
PON_DIR="/goast/hemat_data/targeted-seq-pipeline/references"
RESULTS="/goast/hemat_data/Lymphoma_data/results_gDNA"

FEMALE_SAMPLES=(
    AARTI-LYMPHOMA
    AARUSHI-LYMPHOMA
    AASIYA-LYMPHOMA
    GOJIRI-LYMPHOMA
    KRISHNA-LYMPHOMA
    NEHA-LYMPHOMA
    PAYEL-LYMPHOMA
    POOJA-LYMPHOMA
    PRATIKSHA-LYMPHOMA
    PRIYA-LYMPHOMA
    PRIYANKA-LYMPHOMA
    SAROJINI-LYMPHOMA
    SIDDHI-LYMPHOMA
    SWAPNALI-LYMPHOMA
    VAIDEHI-LYMPHOMA
)

MALE_SAMPLES=(
    ARPIT-LYMPHOMA
    ATUL-LYMPHOMA
    ELWIN-LYMPHOMA
    NIKHIL-LYMPHOMA
    PRASANNA-LYMPHOMA
    ROHAN-LYMPHOMA
    SHRIKANT-LYMPHOMA
    TANISHQ-LYMPHOMA
    VAIBHAV-LYMPHOMA
)

# Build BAM paths from sample names
get_bams() {
    local -n samples=$1
    local bams=()
    for s in "${samples[@]}"; do
        bams+=("${BAM_DIR}/${s}/abra2/${s}.final.bam")
    done
    echo "${bams[@]}"
}

echo "============================================================"
echo "Building FEMALE PON (${#FEMALE_SAMPLES[@]} normals)"
echo "Started: $(date)"
echo "============================================================"

FEMALE_BAMS=$(get_bams FEMALE_SAMPLES)
mkdir -p "${RESULTS}/cnvkit_pon_female"

cnvkit.py batch \
    --normal ${FEMALE_BAMS} \
    --targets "${BED}" \
    --fasta "${REF}" \
    --output-reference "${PON_DIR}/cnvkit_lymphoma_female_pon.cnn" \
    --output-dir "${RESULTS}/cnvkit_pon_female"

echo ""
echo "Female PON complete: ${PON_DIR}/cnvkit_lymphoma_female_pon.cnn"
echo "Finished: $(date)"

echo ""
echo "============================================================"
echo "Building MALE PON (${#MALE_SAMPLES[@]} normals)"
echo "Started: $(date)"
echo "============================================================"

MALE_BAMS=$(get_bams MALE_SAMPLES)
mkdir -p "${RESULTS}/cnvkit_pon_male"

cnvkit.py batch \
    --normal ${MALE_BAMS} \
    --targets "${BED}" \
    --fasta "${REF}" \
    --output-reference "${PON_DIR}/cnvkit_lymphoma_male_pon.cnn" \
    --output-dir "${RESULTS}/cnvkit_pon_male"

echo ""
echo "Male PON complete: ${PON_DIR}/cnvkit_lymphoma_male_pon.cnn"
echo "Finished: $(date)"

echo ""
echo "============================================================"
echo "BOTH PONs COMPLETE"
echo "============================================================"
echo "Female: ${PON_DIR}/cnvkit_lymphoma_female_pon.cnn (${#FEMALE_SAMPLES[@]} normals)"
echo "Male:   ${PON_DIR}/cnvkit_lymphoma_male_pon.cnn (${#MALE_SAMPLES[@]} normals)"
