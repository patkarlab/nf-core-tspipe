#!/usr/bin/env bash
# tools/build_purecn_normaldb.sh  (PCN_V1)
#
# One-time PureCN reference build for the twist_myeloid panel:
#   1. IntervalFile.R  -- panel.combined.filtered.bed -> PureCN intervals
#      (GC + gene annotation; off-target DISABLED: the in-panel CNV
#      backbone already provides genome-wide bins, matching the
#      empty-antitarget doctrine of the CNVkit build).
#   2. Coverage.R      -- GC-normalised loess coverage per male normal
#      (include_in_pon=true rows of the committed samplesheet), run in
#      parallel.
#   3. NormalDB.R      -- normalDB RDS + interval weights.
#   4. Seed assets/twist_myeloid/ + md5 manifest.
#
# Mapping-bias RDS is deliberately deferred (needs a combined normal
# VCF; enhancement item). PureCN.R runs without it.
#
# Env: dedicated conda env, PureCN 2.16.0 (envs/purecn.environment.yml).

set -euo pipefail

SHEET="pon_samplesheets/twist_normals_48.csv"
BED="assets/twist_myeloid/panel.combined.filtered.bed"
FASTA="/goast/hemat_data/references/hg38_broad/Homo_sapiens_assembly38.masked.fasta"
OUTDIR="assets/twist_myeloid"
WORKDIR="/goast/hemat_data/pon_twist/purecn_normaldb"
ENVDIR="/home/hemat/anaconda3/envs/purecn"
JOBS=12
CORES_PER_JOB=2

while [ $# -gt 0 ]; do
    case "$1" in
        --sheet)   SHEET="$2"; shift 2 ;;
        --bed)     BED="$2"; shift 2 ;;
        --fasta)   FASTA="$2"; shift 2 ;;
        --outdir)  OUTDIR="$2"; shift 2 ;;
        --workdir) WORKDIR="$2"; shift 2 ;;
        --env)     ENVDIR="$2"; shift 2 ;;
        --jobs)    JOBS="$2"; shift 2 ;;
        *) echo "[error] unknown argument: $1" >&2; exit 1 ;;
    esac
done

RS="$ENVDIR/bin/Rscript"
EXTDATA="$ENVDIR/lib/R/library/PureCN/extdata"
for f in "$RS" "$EXTDATA/IntervalFile.R" "$EXTDATA/Coverage.R" "$EXTDATA/NormalDB.R"; do
    [ -e "$f" ] || { echo "[error] missing: $f" >&2; exit 1; }
done
for f in "$SHEET" "$BED" "$FASTA"; do
    [ -s "$f" ] || { echo "[error] missing or empty: $f" >&2; exit 1; }
done

mkdir -p "$WORKDIR/coverage"

echo "[ok] PureCN $("$RS" -e 'cat(as.character(packageVersion("PureCN")))' 2>/dev/null)"

# ---- 1. Interval file ------------------------------------------------------
INTERVALS="$WORKDIR/purecn_intervals_twist_myeloid_hg38.txt"
if [ -s "$INTERVALS" ]; then
    echo "[skip] intervals exist: $INTERVALS"
else
    echo "[run] IntervalFile.R"
    "$RS" "$EXTDATA/IntervalFile.R" \
        --in-file "$BED" \
        --fasta "$FASTA" \
        --genome hg38 \
        --out-file "$INTERVALS" \
        --force
fi
n_int=$(grep -vc '^Target' "$INTERVALS" || true)
echo "[ok] intervals: $n_int rows"
[ "$n_int" -ge 5000 ] || { echo "[error] implausibly few interval rows" >&2; exit 1; }

# ---- 2. Coverage over the male normals ------------------------------------
BAMS=$(awk -F',' 'NR>1 && $2=="male" && $6=="true" {print $3}' "$SHEET")
n_bam=$(echo "$BAMS" | grep -c . || true)
echo "[ok] male include_in_pon normals: $n_bam"
[ "$n_bam" -ge 20 ] || { echo "[error] expected ~24 male normals, found $n_bam" >&2; exit 1; }

echo "$BAMS" | xargs -P "$JOBS" -I{} bash -c '
    bam="{}"
    base=$(basename "$bam" .bam)
    out="'"$WORKDIR"'/coverage/${base}_coverage_loess.txt.gz"
    if [ -s "$out" ]; then
        echo "[skip] $base"
    else
        "'"$RS"'" "'"$EXTDATA"'/Coverage.R" \
            --bam "$bam" \
            --intervals "'"$INTERVALS"'" \
            --out-dir "'"$WORKDIR"'/coverage" \
            --cores '"$CORES_PER_JOB"' \
            --force > "'"$WORKDIR"'/coverage/${base}.log" 2>&1 \
        && echo "[ok] $base" || { echo "[error] Coverage failed: $base (see log)"; exit 9; }
    fi
'

ls "$WORKDIR"/coverage/*_coverage_loess.txt.gz > "$WORKDIR/normals_coverage.list"
n_cov=$(wc -l < "$WORKDIR/normals_coverage.list")
echo "[ok] loess coverage files: $n_cov"
[ "$n_cov" -eq "$n_bam" ] || { echo "[error] coverage count $n_cov != bam count $n_bam" >&2; exit 1; }

# ---- 3. NormalDB -----------------------------------------------------------
echo "[run] NormalDB.R"
"$RS" "$EXTDATA/NormalDB.R" \
    --out-dir "$WORKDIR" \
    --coverage-files "$WORKDIR/normals_coverage.list" \
    --genome hg38 \
    --assay twist_myeloid \
    --force

NDB="$WORKDIR/normalDB_twist_myeloid_hg38.rds"
[ -s "$NDB" ] || { echo "[error] NormalDB output missing: $NDB" >&2; exit 1; }

# ---- 4. Seed assets --------------------------------------------------------
cp "$INTERVALS" "$OUTDIR/"
cp "$NDB" "$OUTDIR/"
ls "$WORKDIR"/interval_weights*.png >/dev/null 2>&1 && cp "$WORKDIR"/interval_weights*.png "$OUTDIR/" || true
( cd "$OUTDIR" && md5sum "$(basename "$INTERVALS")" "$(basename "$NDB")" > purecn_normaldb.md5 )
echo "[ok] seeded:"
cat "$OUTDIR/purecn_normaldb.md5"
echo "[done] PureCN NormalDB build complete (male stratum, n=$n_cov)"
