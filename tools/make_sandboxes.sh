#!/usr/bin/env bash
# tools/make_sandboxes.sh -- turn a directory of Singularity images into Apptainer sandboxes.
#
# clinical-23's compute nodes have no squashfuse, so Apptainer cannot mount a .sif and instead
# extracts it into /tmp for every task (this wedged a node on 2026-08-30). A sandbox is an
# unpacked directory: Apptainer binds it, no extraction, no squashfuse. Nextflow passes whatever
# path sits at <cacheDir>/<name>.img to `apptainer exec`, so each sandbox keeps the .img name and
# no pipeline config changes between gandalf (.sif) and clinical-23 (sandbox).
#
# Usage:
#   bash tools/make_sandboxes.sh <src_dir_with_images> <dest_cacheDir> [name ...]
#   e.g. bash tools/make_sandboxes.sh /scratch/patkarlab-clinical/tspipe_release/images \
#                                     /scratch/patkarlab-clinical/tspipe_release/sandboxes
#
# Sandboxes are large (a 3.5 GB .sif unpacks to ~13 GB) and consist of many small files, so put
# the destination on a filesystem with room and reasonable metadata performance (Lustre /scratch).
# Existing sandboxes are skipped; delete one to rebuild it. An md5 file beside a source image is
# verified before conversion when present.
set -euo pipefail
SRC=${1:?source directory containing *.img}
DEST=${2:?destination cache directory}
shift 2 || true
export PATH=/soft/apptainer/1.5.1/bin:$PATH
command -v apptainer >/dev/null || { echo "apptainer not on PATH"; exit 1; }
mkdir -p "$DEST"
echo "[start] $(date '+%F %T')  src=$SRC dest=$DEST"
apptainer --version
if [ "$#" -gt 0 ]; then IMAGES=("$@"); else mapfile -t IMAGES < <(cd "$SRC" && ls *.img); fi
for img in "${IMAGES[@]}"; do
    name=$(basename "$img")
    src="$SRC/$name"
    out="$DEST/$name"
    [ -f "$src" ] || { echo "[skip] $name: not in $SRC"; continue; }
    if [ -e "$out" ]; then echo "[skip] $name: $out exists"; continue; fi
    if [ -f "$src.md5" ]; then
        (cd "$SRC" && md5sum -c "$name.md5") || { echo "[FAIL] $name: checksum mismatch"; exit 1; }
    fi
    echo "[build] $name  $(date +%T)"
    rm -rf "$out.part"
    apptainer build --sandbox "$out.part" "$src" > "$DEST/$name.build.log" 2>&1 || {
        echo "[FAIL] $name: see $DEST/$name.build.log"; tail -3 "$DEST/$name.build.log"; exit 1; }
    mv "$out.part" "$out"
    echo "[ok]   $name -> $(du -sh "$out" | cut -f1)"
done
echo "---- sandboxes in $DEST"
du -sh "$DEST"/*.img 2>/dev/null | sort -h
echo "---- exec check"
for img in "${IMAGES[@]}"; do
    name=$(basename "$img")
    [ -d "$DEST/$name" ] || continue
    printf "%-46s " "$name"
    apptainer exec "$DEST/$name" sh -c 'echo ok' 2>&1 | tail -1
done
echo "[end] $(date '+%F %T')"
