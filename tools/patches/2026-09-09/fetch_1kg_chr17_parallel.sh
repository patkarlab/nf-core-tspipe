#!/usr/bin/env bash
# tools/patches/2026-09-09/fetch_1kg_chr17_parallel.sh
#
# Finish the 1000G chr17 phased-panel download with N parallel HTTP range requests (EBI
# serves ranges, 206). Keeps the bytes already in the partial file, fetches the rest as
# N parts, verifies every part's size, appends them in order, verifies the final size, then
# fetches the .tbi. Each part retries from where it stopped until it is complete.
#
# Usage: N=8 tools/patches/2026-09-09/fetch_1kg_chr17_parallel.sh
# Log:   /tmp/1kg_chr17_parallel.log (run it detached: setsid ... & disown)

set -euo pipefail

P=/goast/hemat_data/references/1000G_hg38_phased
BASE=https://ftp.1000genomes.ebi.ac.uk/vol1/ftp/data_collections/1000G_2504_high_coverage/working/20220422_3202_phased_SNV_INDEL_SV
F=1kGP_high_coverage_Illumina.chr17.filtered.SNV_INDEL_SV_phased_panel.vcf.gz
SIZE=861943967
TBI_SIZE=81164
N=${N:-8}
MAX_ATTEMPTS=40

cd "$P"
exec 9> "$P/.fetch.lock"
if ! flock -n 9; then echo "[error] another fetch is running (lock $P/.fetch.lock)"; exit 1; fi

# stop any sequential wget still appending to the file
pkill -u "$USER" -f 'wget.*1000genomes' 2>/dev/null || true
sleep 2

fetch_part() {   # fetch_part <index> <start> <end>
    local i=$1 s=$2 e=$3 part="$F.part.$1" want=$(( $3 - $2 + 1 )) have=0 attempt=0
    : > "$part"
    while :; do
        have=$(stat -c %s "$part")
        if [ "$have" -ge "$want" ]; then break; fi
        attempt=$((attempt + 1))
        if [ "$attempt" -gt "$MAX_ATTEMPTS" ]; then echo "[part $i] giving up at $have of $want bytes"; return 1; fi
        curl -s --max-time 1800 --speed-limit 1000 --speed-time 60 -r $((s + have))-$e "$BASE/$F" >> "$part" || true
    done
    echo "[part $i] complete ($want bytes, $attempt attempt(s))"
}

have=$(stat -c %s "$F" 2>/dev/null || echo 0)
if [ "$have" -ge "$SIZE" ]; then
    echo "[skip] $F already has $have bytes"
else
    remaining=$((SIZE - have))
    chunk=$(( (remaining + N - 1) / N ))
    echo "[fetch] $have of $SIZE bytes present; fetching $remaining bytes as $N parts of <= $chunk"
    rm -f "$F".part.*
    pids=()
    for i in $(seq 0 $((N - 1))); do
        s=$((have + i * chunk)); e=$((s + chunk - 1))
        [ "$e" -ge "$SIZE" ] && e=$((SIZE - 1))
        [ "$s" -gt "$e" ] && continue
        fetch_part "$i" "$s" "$e" &
        pids+=($!)
    done
    fail=0
    for pid in "${pids[@]}"; do wait "$pid" || fail=1; done
    if [ "$fail" -ne 0 ]; then echo "[error] a part failed; partial file untouched, parts kept"; exit 1; fi
    for i in $(seq 0 $((N - 1))); do
        [ -f "$F.part.$i" ] && cat "$F.part.$i" >> "$F"
    done
    final=$(stat -c %s "$F")
    if [ "$final" -ne "$SIZE" ]; then echo "[error] assembled size $final != $SIZE; parts kept"; exit 1; fi
    rm -f "$F".part.*
    echo "[ok] $F assembled: $final bytes"
fi

if [ "$(stat -c %s "$F.tbi" 2>/dev/null || echo 0)" -ne "$TBI_SIZE" ]; then
    echo "[fetch] $F.tbi"
    curl -s --retry 10 --retry-delay 10 -o "$F.tbi" "$BASE/$F.tbi"
fi
ls -l "$P"
echo "[done] $(date)"
