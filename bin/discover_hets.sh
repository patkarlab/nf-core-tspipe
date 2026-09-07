#!/usr/bin/env bash
# bin/discover_hets.sh  (BAF_CATALOG_V1)
# Heterozygous SNP candidates in one BAM over the panel targets, per
# chromosome in parallel. Output: CHROM POS REF ALT DP AD_REF,AD_ALT (no header).
#   discover_hets.sh <bam> <bed> <fasta> <cpus> <out.tsv> [mapq=20] [max_depth=10000]
set -euo pipefail
BAM="$1"; BED="$2"; FASTA="$3"; CPUS="$4"; OUT="$5"; MAPQ="${6:-20}"; MAXDP="${7:-10000}"
command -v bcftools >/dev/null || { echo "[error] bcftools not on PATH" >&2; exit 1; }
TMP=$(mktemp -d ./hets.XXXXXX)
awk -v d="$TMP" '{print > (d "/" $1 ".bed")}' "$BED"
one_chrom() {
    local bed="$1" c
    c=$(basename "$bed" .bed)
    bcftools mpileup -q "$MAPQ" -Q 20 -d "$MAXDP" -a AD,DP -R "$bed" -f "$FASTA" "$BAM" 2>/dev/null \
      | bcftools call -mv 2>/dev/null \
      | bcftools view -g het -v snps 2>/dev/null \
      | bcftools query -f '%CHROM\t%POS\t%REF\t%ALT\t%DP\t[%AD]\n' > "$TMP/$c.hets"
}
export -f one_chrom
export BAM FASTA MAPQ MAXDP TMP
ls "$TMP"/*.bed | xargs -P "$CPUS" -I{} bash -c 'one_chrom "$1"' _ {}
cat "$TMP"/*.hets > "$OUT"
echo "[ok] $(basename "$BAM"): $(wc -l < "$OUT") het SNP candidates over $(ls "$TMP"/*.bed | wc -l) chromosomes"
rm -rf "$TMP"
