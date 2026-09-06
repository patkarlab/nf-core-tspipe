#!/usr/bin/env bash
# tools/decon/build_decon_pool.sh  (DECON_V1)
#
# Per-stratum DECoN pool for the twist_myeloid panel:
#   1. decon_ReadInBams.R over the include_in_pon normals of --sex
#      (twist_normals_48_v4.csv) -> pool_<sex>.RData   (serial; ~1-3 min/BAM)
#   2. IdentifyFailures.R on the pool  -> pool_<sex>_Failures.txt (if any)
#   3. makeCNVcalls.R on the pool (LOO within pool, no plots)
#      -> pool_<sex>calls_all.txt   = recurrence list for a future blacklist
#   4. seed assets/twist_myeloid/: decon_pool_<sex>.RData,
#      decon_pool_<sex>_failures.tsv, decon_pool_<sex>_loo_calls.tsv, md5
#
# Env: conda env 'decon' (r-base 4.3, ExomeDepth 1.1.16; tools/decon/README.md).
# Run from the repo root.

set -euo pipefail

SHEET="pon_samplesheets/twist_normals_48_v4.csv"
BED="assets/twist_myeloid/decon_exons.bed"
FASTA="/goast/hemat_data/references/hg38_broad/Homo_sapiens_assembly38.masked.fasta"
OUTDIR="assets/twist_myeloid"
WORKDIR="/goast/hemat_data/pon_twist/decon_pool"
ENVDIR="/home/hemat/anaconda3/envs/decon"
SEX="male"
MINCORR=0.98
MINCOV=100
TRANSPROB=0.01

while [ $# -gt 0 ]; do
    case "$1" in
        --sheet)   SHEET="$2"; shift 2 ;;
        --bed)     BED="$2"; shift 2 ;;
        --fasta)   FASTA="$2"; shift 2 ;;
        --outdir)  OUTDIR="$2"; shift 2 ;;
        --workdir) WORKDIR="$2"; shift 2 ;;
        --env)     ENVDIR="$2"; shift 2 ;;
        --sex)     SEX="$2"; shift 2 ;;
        *) echo "[error] unknown argument: $1" >&2; exit 1 ;;
    esac
done

case "$SEX" in
    male)   MIN_N=20 ;;
    female) MIN_N=6 ;;
    *) echo "[error] --sex must be male or female (got: $SEX)" >&2; exit 1 ;;
esac

RS="$ENVDIR/bin/Rscript"
REPO="$(pwd)"
for f in "$RS" bin/decon_ReadInBams.R tools/decon/IdentifyFailures.R tools/decon/makeCNVcalls.R; do
    [ -e "$f" ] || { echo "[error] missing: $f (run from the repo root)" >&2; exit 1; }
done
for f in "$SHEET" "$BED" "$FASTA"; do
    [ -s "$f" ] || { echo "[error] missing or empty: $f" >&2; exit 1; }
done

WD="$WORKDIR/$SEX"
mkdir -p "$WD"
echo "[ok] stratum=$SEX workdir=$WD"
echo "[ok] ExomeDepth $("$RS" --vanilla -e 'cat(as.character(packageVersion("ExomeDepth")))' 2>/dev/null)"

# ---- 1. BAM list and counts ------------------------------------------------
awk -F',' -v sex="$SEX" 'NR>1 && $2==sex && $6=="true" {print $3}' "$SHEET" > "$WD/bams.txt"
n_bam=$(grep -c . "$WD/bams.txt" || true)
echo "[ok] $SEX include_in_pon normals: $n_bam"
[ "$n_bam" -ge "$MIN_N" ] || { echo "[error] expected >= $MIN_N $SEX normals, found $n_bam" >&2; exit 1; }
while read -r bam; do [ -s "$bam" ] || { echo "[error] BAM missing: $bam" >&2; exit 1; }; done < "$WD/bams.txt"

POOL="$WD/pool_$SEX"
if [ -s "$POOL.RData" ]; then
    echo "[skip] pool counts exist: $POOL.RData"
else
    echo "[run] decon_ReadInBams.R ($n_bam BAMs, serial)"
    "$RS" --vanilla "$REPO/bin/decon_ReadInBams.R" --bams "$WD/bams.txt" --bed "$REPO/$BED" --fasta "$FASTA" --out "$POOL" > "$WD/readinbams.log" 2>&1
fi
[ -s "$POOL.RData" ] || { echo "[error] pool RData missing (see $WD/readinbams.log)" >&2; exit 1; }

# ---- 2. Pool QC (exon and sample failures) --------------------------------
echo "[run] IdentifyFailures.R"
( cd "$WD" && "$RS" --vanilla "$REPO/tools/decon/IdentifyFailures.R" --RData "$POOL.RData" --mincorr "$MINCORR" --mincov "$MINCOV" --out "pool_$SEX" > identifyfailures.log 2>&1 )
FAIL="$WD/pool_${SEX}_Failures.txt"
if [ -s "$FAIL" ]; then
    echo "[ok] failures: $(( $(wc -l < "$FAIL") - 1 )) rows"
else
    printf 'Sample\tExon\tType\tGene\tInfo\n' > "$FAIL"
    echo "[ok] failures: none"
fi
if awk -F'\t' 'NR>1 && $3=="Whole sample" {f=1} END{exit !f}' "$FAIL"; then
    echo "[warn] whole-sample failures inside the pool:"; awk -F'\t' 'NR>1 && $3=="Whole sample"' "$FAIL"
fi

# ---- 3. Within-pool LOO calls (recurrence list) ---------------------------
echo "[run] makeCNVcalls.R (LOO within pool, no plots)"
( cd "$WD" && "$RS" --vanilla "$REPO/tools/decon/makeCNVcalls.R" --RData "$POOL.RData" --transProb "$TRANSPROB" --out "pool_${SEX}calls" --plot None > makecnvcalls.log 2>&1 )
LOO="$WD/pool_${SEX}calls_all.txt"
[ -s "$LOO" ] || { echo "[error] LOO calls missing (see $WD/makecnvcalls.log)" >&2; exit 1; }
echo "[ok] LOO calls: $(( $(wc -l < "$LOO") - 1 )) rows over $n_bam normals"

# ---- 4. Seed assets --------------------------------------------------------
cp "$POOL.RData" "$OUTDIR/decon_pool_$SEX.RData"
cp "$FAIL"       "$OUTDIR/decon_pool_${SEX}_failures.tsv"
cp "$LOO"        "$OUTDIR/decon_pool_${SEX}_loo_calls.tsv"
( cd "$OUTDIR" && md5sum "decon_pool_$SEX.RData" "decon_pool_${SEX}_failures.tsv" "decon_pool_${SEX}_loo_calls.tsv" "$(basename "$BED")" > "decon_pool_$SEX.md5" )
echo "[ok] seeded:"; cat "$OUTDIR/decon_pool_$SEX.md5"
echo "[done] DECoN pool build complete ($SEX stratum, n=$n_bam)"
