#!/usr/bin/env bash
# tools/hmftools/setup_hmftools.sh  (HMF_SETUP_V1)
#
# One-time: conda env 'hmftools' (AMBER, COBALT, PURPLE from bioconda; Java 17
# comes as a dependency) and the WiGiTS GRCh38 resource bundle. Idempotent:
# skips what exists. Writes versions.txt beside the resources.
#
#   bash tools/hmftools/setup_hmftools.sh [--env-name hmftools] [--dest /goast/hemat_data/references/hmftools]
set -euo pipefail

ENV_NAME="hmftools"
DEST="/goast/hemat_data/references/hmftools"
BUNDLE_URL="https://data.oncoanalyser.com/r2/reference/dist/v1/hartwig/pipeline_resources/hmf_pipeline_resources.38_v3.0.0--8.tar.gz"
CONDA_BASE="${CONDA_BASE:-/home/hemat/anaconda3}"

while [ $# -gt 0 ]; do
    case "$1" in
        --env-name) ENV_NAME="$2"; shift 2 ;;
        --dest)     DEST="$2"; shift 2 ;;
        --bundle-url) BUNDLE_URL="$2"; shift 2 ;;
        *) echo "[error] unknown argument: $1" >&2; exit 1 ;;
    esac
done

CONDA="$CONDA_BASE/bin/conda"
[ -x "$CONDA" ] || { echo "[error] conda not found at $CONDA" >&2; exit 1; }
if [ -x "$CONDA_BASE/bin/mamba" ]; then SOLVER="$CONDA_BASE/bin/mamba"; else SOLVER="$CONDA"; fi

# ---- 1. conda env --------------------------------------------------------
if [ -x "$CONDA_BASE/envs/$ENV_NAME/bin/purple" ] || [ -x "$CONDA_BASE/envs/$ENV_NAME/bin/PURPLE" ]; then
    echo "[skip] env $ENV_NAME exists"
else
    echo "[run] creating env $ENV_NAME (amber, cobalt, purple from bioconda)"
    "$SOLVER" create -y -n "$ENV_NAME" -c conda-forge -c bioconda \
        hmftools-amber hmftools-cobalt hmftools-purple
fi
ENVBIN="$CONDA_BASE/envs/$ENV_NAME/bin"
ls "$ENVBIN" | grep -iE "^(amber|cobalt|purple|java)$" | sed 's/^/[ok] binary: /'
"$ENVBIN/java" -version 2>&1 | head -1 | sed 's/^/[ok] /'

# ---- 2. resource bundle --------------------------------------------------
mkdir -p "$DEST"
TAR="$DEST/$(basename "$BUNDLE_URL")"
if [ -s "$TAR" ] && [ -f "$DEST/.extracted" ]; then
    echo "[skip] bundle already downloaded and extracted: $TAR"
else
    echo "[run] downloading $BUNDLE_URL"
    curl -L --retry 5 --retry-delay 10 -C - -o "$TAR" "$BUNDLE_URL"
    echo "[run] extracting"
    tar -xzf "$TAR" -C "$DEST"
    touch "$DEST/.extracted"
fi

# ---- 3. inventory of what PURPLE/AMBER/COBALT need -----------------------
echo "[ok] key files (empty lines = missing, report them):"
for pat in "GC_profile.1000bp.38.cnp" "DiploidRegions.38.bed.gz" "AmberGermlineSites.38.tsv.gz" \
           "DriverGenePanel.38.tsv" "KnownHotspots.somatic.38.vcf.gz" "ensembl_gene_data.csv" "cohort_germline_del_freq.38.csv"; do
    f=$(find "$DEST" -name "$pat" 2>/dev/null | head -1)
    printf '   %-36s %s\n' "$pat" "${f:-MISSING}"
done

# ---- 4. versions ----------------------------------------------------------
{
    echo "date: $(date -Is)"
    echo "env: $ENV_NAME"
    "$CONDA" list -n "$ENV_NAME" 2>/dev/null | grep -iE "^(hmftools|openjdk)" || true
    echo "bundle: $BUNDLE_URL"
    echo "bundle_md5: $(md5sum "$TAR" | cut -d' ' -f1)"
} > "$DEST/versions.txt"
echo "[done] $(cat "$DEST/versions.txt" | tr '\n' ' | ')"
