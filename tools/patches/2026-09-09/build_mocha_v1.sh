#!/usr/bin/env bash
# tools/patches/2026-09-09/build_mocha_v1.sh
#
# Build local/mocha:v1 from containers/mocha/Dockerfile on gandalf and export it to the
# Singularity cache as local-mocha-v1.img.
#
# Stages:
#   fetch    bcftools 1.20 tarball + MoChA plugin sources (pinned commit) into
#            containers/mocha/src/ on the host, md5-verified; skipped when already present
#   preflight conda.anaconda.org reachable from a container with --network=host
#   build    docker build --network=host
#   check    smoke test under Docker
#   export   singularity build from the Docker daemon (docker-archive fallback)
#   check    smoke test under Singularity
#
# Idempotent: existing sources and an existing image file are kept unless removed by hand.
# Logs: /tmp/mocha_build.log (docker build), /tmp/mocha_sif.log (singularity build)

set -euo pipefail

REPO=/goast/hemat_data/nf-core-tspipe
CTX=$REPO/containers/mocha
SRC=$CTX/src
CACHE=/goast/hemat_data/targeted-seq-pipeline/singularity_cache
TAG=local/mocha:v1
IMG=$CACHE/local-mocha-v1.img
BUILD_LOG=/tmp/mocha_build.log
SIF_LOG=/tmp/mocha_sif.log

BCFTOOLS_VERSION=1.20
BCFTOOLS_URL=https://github.com/samtools/bcftools/releases/download/${BCFTOOLS_VERSION}/bcftools-${BCFTOOLS_VERSION}.tar.bz2
BCFTOOLS_MD5=5cfb124c7d9e4db6c5a4e6080a2f27f8
# freeseek/mocha master on 2026-09-09; plugin version string 2025-08-19
MOCHA_COMMIT=95686b7b65f53a490513be76bb120e5fc20a8bcf
MOCHA_RAW=https://raw.githubusercontent.com/freeseek/mocha/${MOCHA_COMMIT}

SMOKE='bcftools --version </dev/null | head -1;
       (bcftools +mocha </dev/null 2>&1 || true) | grep -m1 "version 20";
       phase_common --help </dev/null 2>&1 | head -1;
       tabix --version </dev/null | head -1;
       python3 --version'

cd "$REPO"
if [ ! -f "$CTX/Dockerfile" ]; then
    echo "[error] $CTX/Dockerfile not found" >&2
    exit 1
fi

# ---------------------------------------------------------------- fetch (host side)
mkdir -p "$SRC/mocha"
cat > "$SRC/MD5SUMS" <<MD5
${BCFTOOLS_MD5}  bcftools-${BCFTOOLS_VERSION}.tar.bz2
99ea9f5aa2b923e5a78957eed977026d  mocha/mocha.h
f16f5b161b7deabc3b45b5d0f1bd0b72  mocha/beta_binom.h
d2321158884d7409369d588501006095  mocha/genome_rules.h
ef88b7b6a6f47e76201821f5f0d0f336  mocha/mocha.c
40964f1989b2affbd3a8663fad027ce2  mocha/mochatools.c
f1689481accf1582a521dcc8f0daf603  mocha/extendFMT.c
MD5

if [ ! -s "$SRC/bcftools-${BCFTOOLS_VERSION}.tar.bz2" ]; then
    echo "[fetch] $BCFTOOLS_URL"
    wget -q -O "$SRC/bcftools-${BCFTOOLS_VERSION}.tar.bz2.part" "$BCFTOOLS_URL"
    mv "$SRC/bcftools-${BCFTOOLS_VERSION}.tar.bz2.part" "$SRC/bcftools-${BCFTOOLS_VERSION}.tar.bz2"
fi
for f in mocha.h beta_binom.h genome_rules.h mocha.c mochatools.c extendFMT.c; do
    if [ ! -s "$SRC/mocha/$f" ]; then
        echo "[fetch] $MOCHA_RAW/$f"
        wget -q -O "$SRC/mocha/$f.part" "$MOCHA_RAW/$f"
        mv "$SRC/mocha/$f.part" "$SRC/mocha/$f"
    fi
done
echo "[verify] md5sum -c src/MD5SUMS"
(cd "$SRC" && md5sum -c MD5SUMS)
echo "[verify] $(grep -m1 MOCHA_VERSION "$SRC/mocha/mocha.c")"

# ---------------------------------------------------------------- preflight (conda reachable)
echo "[preflight] conda channels reachable from a --network=host container"
if ! docker run --rm --network=host mambaorg/micromamba:1.5.10-jammy \
        micromamba search -c conda-forge -c bioconda shapeit5=5.1.1 2>&1 | grep -q '5\.1\.1'; then
    echo "[warn] could not confirm shapeit5=5.1.1 via conda from inside a container;"
    echo "       the build will fail at the micromamba step if conda.anaconda.org is unreachable"
fi

# ---------------------------------------------------------------- build
echo "[build] docker build --network=host -t $TAG $CTX  (log: $BUILD_LOG)"
if ! docker build --network=host -t "$TAG" "$CTX" > "$BUILD_LOG" 2>&1; then
    echo "[error] docker build failed; last lines of $BUILD_LOG:" >&2
    tail -40 "$BUILD_LOG" >&2
    exit 1
fi

echo "[check] docker run $TAG"
docker run --rm "$TAG" bash -c "$SMOKE"

# ---------------------------------------------------------------- export
if [ -e "$IMG" ]; then
    echo "[skip] $IMG already exists; remove it to re-export"
else
    echo "[export] singularity build $IMG docker-daemon://$TAG  (log: $SIF_LOG)"
    if ! singularity build "$IMG" "docker-daemon://$TAG" > "$SIF_LOG" 2>&1; then
        echo "[retry] docker-daemon export failed; falling back to docker save + docker-archive"
        docker save "$TAG" -o /tmp/mocha_v1.tar
        singularity build "$IMG" docker-archive:///tmp/mocha_v1.tar >> "$SIF_LOG" 2>&1
        rm -f /tmp/mocha_v1.tar
    fi
fi

echo "[check] singularity exec $IMG"
singularity exec "$IMG" bash -c "$SMOKE"

ls -l "$IMG"
echo "[done] $TAG built and exported to $IMG"
