#!/usr/bin/env bash
# tools/hmftools/build_panel_resources.sh  (HMF_PANEL_V1)
#
# Panel resources for AMBER/COBALT/PURPLE targeted mode on the twist_myeloid
# panel, trained on the include_in_pon normals of the samplesheet:
#   1. target regions BED: panel.combined.filtered.bed, primary contigs only,
#      reference order
#   2. COBALT tumour-only per normal (raw ratios; parallel)
#   3. NormalisationFileBuilder -> target regions normalisation TSV
#      (sample_id_file with SampleId,Gender from the sheet; AMBER not needed)
#   4. driver gene panel TSV for our genes (bin/make_driver_gene_panel.py)
#   5. seed assets/twist_myeloid/hmftools/ + md5 + versions
# Run from the repo root. Env: conda env 'hmftools' (tools/hmftools/setup_hmftools.sh).

set -euo pipefail

SHEET="pon_samplesheets/twist_normals_48_v4.csv"
BED="assets/twist_myeloid/panel.combined.filtered.bed"
FASTA="/goast/hemat_data/references/hg38_broad/Homo_sapiens_assembly38.masked.fasta"
HMF="/goast/hemat_data/references/hmftools/hmf_pipeline_resources.38_v3.0.0--8"
ENVDIR="/home/hemat/anaconda3/envs/hmftools"
OUTDIR="assets/twist_myeloid/hmftools"
WORKDIR="/goast/hemat_data/pon_twist/hmftools_panel"
JOBS=8
THREADS=6
XMX="8G"
ONLY_DRIVERS=0

while [ $# -gt 0 ]; do
    case "$1" in
        --sheet)   SHEET="$2"; shift 2 ;;
        --bed)     BED="$2"; shift 2 ;;
        --fasta)   FASTA="$2"; shift 2 ;;
        --hmf)     HMF="$2"; shift 2 ;;
        --env)     ENVDIR="$2"; shift 2 ;;
        --outdir)  OUTDIR="$2"; shift 2 ;;
        --workdir) WORKDIR="$2"; shift 2 ;;
        --jobs)    JOBS="$2"; shift 2 ;;
        --threads) THREADS="$2"; shift 2 ;;
        --only-drivers) ONLY_DRIVERS=1; shift ;;
        *) echo "[error] unknown argument: $1" >&2; exit 1 ;;
    esac
done

JAVA="$ENVDIR/bin/java"
COBALT_JAR=$(ls "$ENVDIR"/share/hmftools-cobalt-*/cobalt.jar | head -1)
GC="$HMF/dna/copy_number/GC_profile.1000bp.38.cnp"
DIPLOID="$HMF/dna/copy_number/DiploidRegions.38.bed.gz"
HMF_DRIVERS="$HMF/common/DriverGenePanel.38.tsv"
for f in "$JAVA" "$COBALT_JAR" "$GC" "$DIPLOID" "$HMF_DRIVERS" "$SHEET" "$BED" "$FASTA" bin/make_driver_gene_panel.py \
         assets/twist_myeloid/panel_gene_chroms.tsv; do
    [ -e "$f" ] || { echo "[error] missing: $f" >&2; exit 1; }
done
mkdir -p "$WORKDIR/cobalt" "$OUTDIR"
REPO="$(pwd)"

TARGET_BED="$OUTDIR/target_regions.twist_myeloid.38.bed"
NORM="$OUTDIR/target_regions.cobalt_normalisation.twist_myeloid.38.tsv"
if [ "$ONLY_DRIVERS" -eq 0 ]; then
# ---- 1. target regions BED -------------------------------------------------
awk 'BEGIN{n=0; for(i=1;i<=22;i++){o["chr"i]=i}; o["chrX"]=23; o["chrY"]=24}
     $1 in o {print o[$1]"\t"$0}' "$BED" | sort -k1,1n -k3,3n | cut -f2- > "$TARGET_BED"
echo "[ok] target regions BED: $(wc -l < "$TARGET_BED") rows -> $TARGET_BED"

# ---- 2. COBALT tumour-only on the include_in_pon normals -------------------
awk -F',' 'NR>1 && $6=="true" {print $1","$3","toupper($2)}' "$SHEET" > "$WORKDIR/samples.csv"
n=$(wc -l < "$WORKDIR/samples.csv"); echo "[ok] training normals: $n"
[ "$n" -ge 20 ] || { echo "[error] fewer than 20 training samples" >&2; exit 1; }

export JAVA COBALT_JAR GC DIPLOID FASTA WORKDIR THREADS XMX
run_cobalt() {
    local id="$1" bam="$2" out="$WORKDIR/cobalt/$1"
    if [ -s "$out/$id.cobalt.ratio.tsv.gz" ]; then echo "[skip] cobalt $id"; return 0; fi
    mkdir -p "$out"
    "$JAVA" -Xmx"$XMX" -jar "$COBALT_JAR" -tumor "$id" -tumor_bam "$bam" -output_dir "$out" \
        -ref_genome "$FASTA" -ref_genome_version 38 -gc_profile "$GC" -tumor_only_diploid_bed "$DIPLOID" \
        -threads "$THREADS" > "$out/cobalt.log" 2>&1 \
        && echo "[ok] cobalt $id" || { echo "[error] cobalt failed: $id (see $out/cobalt.log)"; return 9; }
}
export -f run_cobalt
cut -d',' -f1,2 "$WORKDIR/samples.csv" | tr ',' ' ' | xargs -P "$JOBS" -n 2 bash -c 'run_cobalt "$0" "$1"'
n_ok=$(ls "$WORKDIR"/cobalt/*/*.cobalt.ratio.tsv.gz 2>/dev/null | wc -l)
echo "[ok] cobalt ratio files: $n_ok"
[ "$n_ok" -eq "$n" ] || { echo "[error] cobalt outputs $n_ok != samples $n" >&2; exit 1; }

# ---- 3. normalisation file --------------------------------------------------
{ echo "SampleId,Gender"; cut -d',' -f1,3 "$WORKDIR/samples.csv"; } > "$WORKDIR/sample_ids.csv"
build_norm() {
    "$JAVA" -Xmx"$XMX" -cp "$COBALT_JAR" com.hartwig.hmftools.cobalt.norm.NormalisationFileBuilder \
        -sample_id_file "$WORKDIR/sample_ids.csv" -cobalt_dir "$1" -ref_genome_version 38 \
        -gc_profile "$GC" -target_regions_bed "$REPO/$TARGET_BED" -output_file "$REPO/$NORM" -log_debug > "$WORKDIR/norm_builder.log" 2>&1
}
echo "[run] NormalisationFileBuilder (per-sample dirs via wildcard)"
if build_norm "$WORKDIR/cobalt/*/" && [ -s "$NORM" ]; then
    echo "[ok] normalisation file (wildcard layout)"
else
    echo "[warn] wildcard layout failed; retrying with a flat directory"
    mkdir -p "$WORKDIR/cobalt_flat"; for f in "$WORKDIR"/cobalt/*/*.cobalt.*; do ln -f "$f" "$WORKDIR/cobalt_flat/" 2>/dev/null || cp "$f" "$WORKDIR/cobalt_flat/"; done
    build_norm "$WORKDIR/cobalt_flat/" && [ -s "$NORM" ] || { echo "[error] NormalisationFileBuilder failed (see $WORKDIR/norm_builder.log)" >&2; tail -20 "$WORKDIR/norm_builder.log"; exit 1; }
    echo "[ok] normalisation file (flat layout)"
fi
echo "[ok] normalisation rows: $(wc -l < "$NORM")"; head -3 "$NORM"
fi

# ---- 4. driver gene panel: every gene named in the target BED ---------------
GENES_TSV="$WORKDIR/panel_genes_from_bed.tsv"
awk -F'\t' '$4 !~ /^bb\.|_SNP_|Antitarget|^het_|_5UTR$/ {n=$4; sub(/_exon_.*$/, "", n); sub(/_[0-9]+$/, "", n); print $1"\t"n}' "$TARGET_BED" \
    | sort -u | awk -F'\t' '{g[$1]=(g[$1]?g[$1]",":"") $2} END{for(c in g) print c"\t"g[c]}' > "$GENES_TSV"
echo "[ok] panel genes from the BED: $(tr ',' '\n' < <(cut -f2 "$GENES_TSV") | wc -l)"
python3 bin/make_driver_gene_panel.py --hmf-panel "$HMF_DRIVERS" \
    --panel-genes "$GENES_TSV" \
    --roles assets/myeloid_driver_genes.tsv \
    --out "$OUTDIR/DriverGenePanel.twist_myeloid.38.tsv" \
    --provenance "$OUTDIR/DriverGenePanel.twist_myeloid.38.provenance.tsv"

# ---- 5. record ----------------------------------------------------------------
n=${n:-$(awk -F',' 'NR>1 && $6=="true"' "$SHEET" | wc -l)}
{
    echo "date: $(date -Is)"
    echo "cobalt: $("$JAVA" -jar "$COBALT_JAR" -version 2>&1 | head -1)"
    echo "hmf_resources: $HMF"
    echo "training: $n normals from $SHEET (include_in_pon=true, both strata)"
    echo "target_bed_rows: $(wc -l < "$TARGET_BED")"
} > "$OUTDIR/versions.txt"
( cd "$OUTDIR" && md5sum target_regions.twist_myeloid.38.bed target_regions.cobalt_normalisation.twist_myeloid.38.tsv DriverGenePanel.twist_myeloid.38.tsv > hmftools_panel.md5 )
echo "[done] seeded $OUTDIR:"; cat "$OUTDIR/hmftools_panel.md5"
