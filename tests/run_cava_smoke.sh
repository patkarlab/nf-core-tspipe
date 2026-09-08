#!/usr/bin/env bash
# Smoke test for the CAVA image + catalog on gandalf. Run from the nf-core-tspipe root.
set -euo pipefail
IMG=${IMG:-/goast/hemat_data/targeted-seq-pipeline/singularity_cache/local-cava-v2.0.15.img}
REF=${REF:-/goast/hemat_data/targeted-seq-pipeline/references/hg38_broad/Homo_sapiens_assembly38.masked.fasta}
CAT=${CAT:-$(pwd)/assets/cava/mane-1.5-grch38-refseq/CAVA_MANE_1.5_GRCh38_REFSEQ.gz}
WD=$(mktemp -d /tmp/cava_smoke.XXXX)
sed -e "s#__REFERENCE__#${REF}#" -e "s#__CATALOG__#${CAT}#" assets/cava/cava_config.template.txt > "${WD}/config.txt"
singularity exec -B /goast:/goast -B "$(pwd)":"$(pwd)" -B "${WD}":"${WD}" "${IMG}" \
    cava -c "${WD}/config.txt" -i "$(pwd)/tests/cava_smoke.vcf" -o "${WD}/out" | grep -E "ERROR|runtime" || true
python3 - "${WD}/out.vcf" tests/cava_smoke.expected.tsv <<'PY'
import sys, csv
vcf, exp = sys.argv[1], sys.argv[2]
want = {(r["CHROM"], r["POS"], r["REF"], r["ALT"]): r for r in csv.DictReader(open(exp), delimiter="\t")}
fails = 0
for line in open(vcf):
    if line.startswith("#"):
        continue
    f = line.rstrip("\n").split("\t")
    info = dict(kv.split("=", 1) for kv in f[7].split(";") if "=" in kv)
    key = (f[0], f[1], f[3], f[4])
    e = want.get(key)
    if e is None:
        continue
    for col in ("CAVA_GENE", "CAVA_TRANSCRIPT", "CAVA_CSN", "CAVA_CLASS", "CAVA_ALTANN"):
        if info.get(col, ".") != e[col]:
            fails += 1
            print(f"FAIL {key} {col}: got {info.get(col)!r} expected {e[col]!r}")
print("PASS" if fails == 0 else f"{fails} mismatches")
PY
echo "workdir: ${WD}"
