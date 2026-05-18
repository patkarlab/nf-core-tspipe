#!/usr/bin/env bash
# tools/make_samplesheet.sh - Build a nf-core-tspipe samplesheet CSV from a
# FASTQ directory.
#
# Handles two naming conventions on gandalf:
#   - sequencer: <id>-(MyOPool|MyOpool|MyoPool|MyeloidOPool)_S<N>_R1_001.fastq.gz
#   - stripped:  <id>-(MyOPool|MyOpool|MyoPool|MyeloidOPool)_R1.fastq.gz
#
# Output columns: sample,fastq_1,fastq_2,sex
# Sex defaults to "unknown" for all samples (CNVKIT auto-detects).
#
# Usage:
#   tools/make_samplesheet.sh /path/to/fastq_dir
#   tools/make_samplesheet.sh /path/to/fastq_dir -o /tmp/samplesheet.csv
#   tools/make_samplesheet.sh /path/to/fastq_dir --exclude 25NGS336,26CGH14
#   tools/make_samplesheet.sh /path/to/fastq_dir --min-size 500   # MB
#   tools/make_samplesheet.sh /path/to/fastq_dir --sex 25NGS1307=male,25NGS336=female

set -eo pipefail

FASTQ_DIR=""
OUTPUT=""
EXCLUDE=""
MIN_SIZE_MB=0
SEX_OVERRIDES=""

usage() {
    cat >&2 <<EOF
Usage: $0 FASTQ_DIR [options]
Options:
  -o, --output FILE         Write to FILE (default: stdout)
  --exclude ID1,ID2,...     Skip these sample IDs
  --min-size MB             Skip samples with R1 smaller than MB megabytes
  --sex ID=male,ID2=female  Override sex per sample (defaults: unknown)
  -h, --help                Show this help
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -o|--output)   OUTPUT="$2"; shift 2 ;;
        --exclude)     EXCLUDE="$2"; shift 2 ;;
        --min-size)    MIN_SIZE_MB="$2"; shift 2 ;;
        --sex)         SEX_OVERRIDES="$2"; shift 2 ;;
        -h|--help)     usage; exit 0 ;;
        -*)            echo "Unknown flag: $1" >&2; usage; exit 1 ;;
        *)             [[ -z "$FASTQ_DIR" ]] && FASTQ_DIR="$1" || { echo "extra arg: $1" >&2; exit 1; }; shift ;;
    esac
done

if [[ -z "$FASTQ_DIR" ]]; then
    usage
    exit 1
fi
if [[ ! -d "$FASTQ_DIR" ]]; then
    echo "ERROR: not a directory: $FASTQ_DIR" >&2
    exit 1
fi

# Build exclude regex
exclude_re=""
if [[ -n "$EXCLUDE" ]]; then
    exclude_re="^($(echo "$EXCLUDE" | tr ',' '|'))$"
fi

# Resolve sex overrides into a lookup
declare -A SEX_MAP
if [[ -n "$SEX_OVERRIDES" ]]; then
    IFS=',' read -ra pairs <<< "$SEX_OVERRIDES"
    for p in "${pairs[@]}"; do
        id="${p%%=*}"
        s="${p##*=}"
        SEX_MAP["$id"]="$s"
    done
fi

write() {
    if [[ -n "$OUTPUT" ]]; then
        echo "$1" >> "$OUTPUT"
    else
        echo "$1"
    fi
}

# Truncate output file if specified
if [[ -n "$OUTPUT" ]]; then
    : > "$OUTPUT"
fi

# Header
write "sample,fastq_1,fastq_2,sex"

found=0
skipped=0
declare -A SEEN_IDS

for r1 in "$FASTQ_DIR"/*_R1*.fastq.gz; do
    [[ -f "$r1" ]] || continue
    bn=$(basename "$r1")

    # Detect convention and extract clean sample id + matching R2 path
    if [[ "$bn" =~ ^(.+)-(MyOPool|MyOpool|MyoPool|MyeloidOPool)_S[0-9]+_R1_001\.fastq\.gz$ ]]; then
        clean_id="${BASH_REMATCH[1]}"
        r2=$(echo "$r1" | sed 's/_R1_001/_R2_001/')
    elif [[ "$bn" =~ ^(.+)-(MyOPool|MyOpool|MyoPool|MyeloidOPool)_R1\.fastq\.gz$ ]]; then
        clean_id="${BASH_REMATCH[1]}"
        r2=$(echo "$r1" | sed 's/_R1\.fastq\.gz/_R2.fastq.gz/')
    else
        echo "  SKIP: unrecognized naming: $bn" >&2
        skipped=$((skipped+1))
        continue
    fi

    # Dedupe: if both sequencer and stripped exist for the same sample, take sequencer (newer)
    if [[ -n "${SEEN_IDS[$clean_id]:-}" ]]; then
        echo "  SKIP duplicate sample id: $clean_id (already added from another file)" >&2
        skipped=$((skipped+1))
        continue
    fi

    # R2 present
    if [[ ! -f "$r2" ]]; then
        echo "  SKIP: $clean_id (no matching R2)" >&2
        skipped=$((skipped+1))
        continue
    fi

    # Exclude list
    if [[ -n "$exclude_re" ]] && [[ "$clean_id" =~ $exclude_re ]]; then
        echo "  SKIP excluded: $clean_id" >&2
        skipped=$((skipped+1))
        continue
    fi

    # Min size
    if [[ "$MIN_SIZE_MB" -gt 0 ]]; then
        size_bytes=$(stat -c%s "$r1")
        size_mb=$((size_bytes / 1024 / 1024))
        if [[ "$size_mb" -lt "$MIN_SIZE_MB" ]]; then
            echo "  SKIP small ($size_mb MB < $MIN_SIZE_MB MB): $clean_id" >&2
            skipped=$((skipped+1))
            continue
        fi
    fi

    # Sex
    sex="${SEX_MAP[$clean_id]:-unknown}"

    write "${clean_id},${r1},${r2},${sex}"
    SEEN_IDS[$clean_id]=1
    found=$((found+1))
done

echo "  found: $found, skipped: $skipped" >&2
if [[ -n "$OUTPUT" ]]; then
    echo "  wrote: $OUTPUT" >&2
fi
