#!/usr/bin/env bash
# containers/tspipe-host/pack_envs.sh -- FREEZE A1, step 1 of the host image.
#
# conda-pack the seven conda environments that the HOST-class processes use on gandalf
# (targeted-seq, vep, py2, purecn, decon, hmftools, reconCNV) and copy the four external
# installs (Strelka2, ANNOVAR scripts without humandb, OncoVI, VarDictJava helpers) into
# containers/tspipe-host/src/. The Dockerfile unpacks each tarball under /opt/envs/<name>
# and runs conda-unpack, so the image carries the same bytes as gandalf.
#
# targeted-seq: share/AnnotSV_annotations (32 GB) and share/AnnotSV are excluded (AnnotSV is
# not called by any tspipe process; SV_CALLERS / SV_ANNOTATE are unreached stubs), and the one
# editable package (variantconvert 2.0.1) is skipped by conda-pack and its source copied to
# src/variantconvert/ so the Dockerfile can pip-install it if the pipeline needs it.
#
# Idempotent: an existing complete tarball is not rebuilt (delete it to force). Safe to run
# under setsid with a log. Writes src/CHECKSUMS.md5 at the end.
# v2: conda-pack infers the format from the suffix, so partial archives are written to
# src/.partial/<env>.tar.gz and moved up when complete (a ".part" suffix is rejected).

set -euo pipefail

REPO=/goast/hemat_data/nf-core-tspipe
ROOT="$REPO/containers/tspipe-host"
SRC="$ROOT/src"
CONDA=/home/hemat/anaconda3
PACK="$CONDA/bin/conda-pack"
THREADS="${PACK_THREADS:-16}"

PART="$SRC/.partial"
mkdir -p "$SRC" "$PART"
rm -f "$SRC"/*.part
echo "[start] $(date '+%F %T')  src=$SRC threads=$THREADS"
"$PACK" --version

pack() {
    local env="$1"; shift
    local out="$SRC/$env.tar.gz"
    if [ -s "$out" ]; then
        echo "[skip] $env: $out exists ($(du -h "$out" | cut -f1))"
        return 0
    fi
    echo "[pack] $env  $(date +%T)"
    rm -f "$PART/$env.tar.gz"
    "$PACK" -p "$CONDA/envs/$env" -o "$PART/$env.tar.gz" --format tar.gz --n-threads "$THREADS" --ignore-missing-files "$@"
    mv "$PART/$env.tar.gz" "$out"
    echo "[done] $env -> $(du -h "$out" | cut -f1)  $(date +%T)"
}

# targeted-seq: drop the AnnotSV annotation bundle and skip the editable install.
pack targeted-seq --ignore-editable-packages \
    --exclude 'share/AnnotSV_annotations/*' \
    --exclude 'share/AnnotSV/*'
pack vep
pack py2
pack purecn
pack decon
pack hmftools
pack reconCNV

copy_tree() {
    local name="$1" from="$2"; shift 2
    echo "[copy] $name <- $from"
    rsync -a --delete "$@" "$from/" "$SRC/$name/"
    du -sh "$SRC/$name"
}
copy_tree strelka2 /goast/hemat_data/targeted-seq-pipeline/software/strelka2
copy_tree annovar  /goast/hemat_data/targeted-seq-pipeline/software/annovar --exclude 'humandb' --exclude 'humandb/**'
copy_tree oncovi   /home/hemat/targeted-seq-pipeline/software/oncovi
copy_tree vardict  /goast/hemat_data/programs/VarDictJava/build/install/VarDict

# Source of the editable package, kept beside the tarballs in case a pipeline script imports it.
VC_DIR=$("$CONDA/envs/targeted-seq/bin/python" - <<'PY' 2>/dev/null || true
import os, variantconvert
print(os.path.dirname(os.path.dirname(os.path.abspath(variantconvert.__file__))))
PY
)
if [ -n "${VC_DIR:-}" ] && [ -d "$VC_DIR" ]; then
    copy_tree variantconvert "$VC_DIR" --exclude '.git'
    echo "[info] variantconvert source: $VC_DIR"
else
    echo "[info] variantconvert source not located (import failed); skipped"
fi

cd "$SRC"
find . -maxdepth 1 -type f -name '*.tar.gz' -exec md5sum {} \; | sort -k2 > CHECKSUMS.md5
echo "---- src/ contents"
du -sh "$SRC"/* | sort -h
cat CHECKSUMS.md5
echo "[end] $(date '+%F %T')"
