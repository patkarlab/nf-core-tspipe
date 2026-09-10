#!/usr/bin/env bash
# tools/patches/2026-09-09/mocha17_offline.sh <sample> [<workdir>]
#
# Offline prototype of the MOCHA_17P module, run entirely inside local/mocha:v1:
#   1. bgzip + tabix the catalog-site genotype VCF written by bin/baf_genotypes_vcf.py,
#      adding INFO/AC and AN (bcftools +fill-tags) which SHAPEIT5 requires in the target
#   2. SHAPEIT5 phase_common against the 1000G high-coverage chr17 phased panel
#   3. restore FORMAT/AD,DP,RAD onto the phased genotypes (phase_common keeps GT only)
#   4. INFO/GC from the reference (bcftools +mochatools)
#   5. bcftools +mocha, BAF-only model (--LRR-weight 0; AD-sum coverage is meaningless
#      across capture targets, depth evidence stays with BAF_V2 in the consensus)
#   6. phased-BAF table and a per-arm summary: a consistent sign of pBAF along an arm is
#      the phased signal MoChA models; mean pBAF near 0 with mean |pBAF| > 0 means the
#      imbalance is there but the phasing is not tracking it.
#
# Inputs expected in <workdir> (default /tmp/mocha17/<sample>):
#   <sample>.chr17.genotypes.vcf   from baf_genotypes_vcf.py (--alleles panel table, --require-alleles)
# Panel and map: /goast/hemat_data/references/1000G_hg38_phased/
# Env: THREADS (default 8)

set -euo pipefail

S=${1:?usage: mocha17_offline.sh <sample> [<workdir>]}
O=${2:-/tmp/mocha17/$S}
IMG=/goast/hemat_data/targeted-seq-pipeline/singularity_cache/local-mocha-v1.img
REF=/goast/hemat_data/targeted-seq-pipeline/references/hg38_broad/Homo_sapiens_assembly38.masked.fasta
P=/goast/hemat_data/references/1000G_hg38_phased
PANEL=$P/1kGP_high_coverage_Illumina.chr17.filtered.SNV_INDEL_SV_phased_panel.vcf.gz
MAP=$P/chr17.b38.gmap.gz
THREADS=${THREADS:-8}
GT=$O/$S.chr17.genotypes.vcf

for f in "$GT" "$PANEL" "$PANEL.tbi" "$MAP" "$IMG" "$REF"; do
    if [ ! -s "$f" ]; then echo "[error] missing: $f" >&2; exit 1; fi
done

run() { singularity exec -B /goast,/tmp "$IMG" bash -euo pipefail -c "$1"; }

echo "[1] bgzip + tabix (INFO/AC,AN added: SHAPEIT5 requires them in the target VCF)"
run "bcftools +fill-tags --no-version $GT -Oz -o $GT.gz -- -t AC,AN && tabix -f -p vcf $GT.gz"
echo "    sites: $(run "bcftools view -H $GT.gz | wc -l")  sample: $(run "bcftools query -l $GT.gz")"

echo "[2] SHAPEIT5 phase_common (reference = 1000G chr17, threads $THREADS)"
run "phase_common --input $GT.gz --reference $PANEL --map $MAP --region chr17 --thread $THREADS \
       --output $O/$S.chr17.phased.bcf --log $O/$S.chr17.phase_common.log > $O/$S.chr17.phase_common.stdout 2>&1 \
     && bcftools index -f $O/$S.chr17.phased.bcf"
echo "    phased sites: $(run "bcftools view -H $O/$S.chr17.phased.bcf | wc -l")"
grep -iE 'variant|site|not found|dropped|error|warning' "$O/$S.chr17.phase_common.log" | head -8 || true

echo "[3] restore AD/DP/RAD onto the phased genotypes"
run "bcftools annotate --no-version -a $GT.gz -c FMT/AD,FMT/DP,FMT/RAD -Ob -o $O/$S.chr17.phased.ad.bcf $O/$S.chr17.phased.bcf \
     && bcftools index -f $O/$S.chr17.phased.ad.bcf"
run "bcftools query -f '[%GT\t%AD\n]' $O/$S.chr17.phased.ad.bcf" > "$O/$S.chr17.phased.gt_ad.tsv"
awk -F'\t' '$1=="0|1"||$1=="1|0"{h++} $2=="."{m++} END{printf "    %d phased hets, %d records without AD\n", h+0, m+0}' "$O/$S.chr17.phased.gt_ad.tsv"

echo "[4] INFO/GC from the reference"
run "bcftools +mochatools --no-version $O/$S.chr17.phased.ad.bcf -Ob -o $O/$S.chr17.phased.gc.bcf -- -t GC -f $REF \
     && bcftools index -f $O/$S.chr17.phased.gc.bcf"

echo "[5] bcftools +mocha -g GRCh38 --LRR-weight 0"
run "bcftools +mocha --no-version -g GRCh38 --LRR-weight 0 -o $O/$S.chr17.mocha.bcf -Ob \
       -c $O/$S.chr17.mocha.calls.tsv -z $O/$S.chr17.mocha.stats.tsv -u $O/$S.chr17.mocha.ucsc.bed \
       $O/$S.chr17.phased.gc.bcf > $O/$S.chr17.mocha.log 2>&1"
tail -3 "$O/$S.chr17.mocha.log"
echo "[calls] $O/$S.chr17.mocha.calls.tsv"
cat "$O/$S.chr17.mocha.calls.tsv"
echo "[stats]"
cut -f1-14 "$O/$S.chr17.mocha.stats.tsv"

echo "[6] phased BAF per arm (pBAF = BAF-0.5 for 0|1, 0.5-BAF for 1|0)"
run "bcftools query -f '%CHROM\t%POS\t%REF\t%ALT[\t%GT\t%AD]\n' $O/$S.chr17.mocha.bcf" > "$O/$S.chr17.phased_baf.tsv"
awk -F'\t' '$5=="0|1"||$5=="1|0"{split($6,a,","); d=a[1]+a[2]; if(d>0){b=a[2]/d; pb=($5=="0|1")?(b-0.5):(0.5-b); print $2"\t"pb}}' \
    "$O/$S.chr17.phased_baf.tsv" > "$O/$S.chr17.pbaf.tsv"
awk -F'\t' '{arm=($1<25100000)?"17p":"17q"; s[arm]+=$2; n[arm]++; a[arm]+=($2<0?-$2:$2)}
            END{for(k in n) printf "    %s: %d phased hets, mean pBAF = %+.4f, mean |pBAF| = %.4f\n", k, n[k], s[k]/n[k], a[k]/n[k]}' \
    "$O/$S.chr17.pbaf.tsv" | sort
echo "[done] $O"
