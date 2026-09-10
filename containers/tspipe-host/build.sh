#!/usr/bin/env bash
# containers/tspipe-host/build.sh -- build local/tspipe-host:v1 on gandalf, smoke-test it, export it.
#
#   1. verify src/CHECKSUMS.md5 (pack_envs.sh output) and the four install trees
#   2. docker build --network=host (BuildKit RUN steps on gandalf have no DNS otherwise)
#   3. smoke test inside the image as the calling user (uid:gid, like Nextflow's docker profile)
#   4. docker save | gzip -> $RELEASE_DIR/local-tspipe-host-v1.docker.tar.gz (+ md5), for clinical-23
#   5. singularity build -> $SINGULARITY_CACHE/local-tspipe-host-v1.img (Nextflow's cache name for local/tspipe-host:v1)
#
# Usage: bash containers/tspipe-host/build.sh [--no-export]   (run under setsid with a log; 20-40 min)
set -euo pipefail
TAG=${TAG:-v1}
IMAGE=local/tspipe-host:$TAG
REPO=/goast/hemat_data/nf-core-tspipe
HERE=$REPO/containers/tspipe-host
RELEASE_DIR=${RELEASE_DIR:-/goast/hemat_data/tspipe_release/images}
SINGULARITY_CACHE=${SINGULARITY_CACHE:-/goast/hemat_data/targeted-seq-pipeline/singularity_cache}
EXPORT=1; [ "${1:-}" = "--no-export" ] && EXPORT=0
cd "$HERE"
echo "[start] $(date '+%F %T') image=$IMAGE export=$EXPORT"
echo "[1] verify src/"
(cd src && md5sum -c CHECKSUMS.md5)
for d in strelka2 annovar oncovi vardict; do [ -d "src/$d" ] || { echo "MISSING src/$d"; exit 1; }; done
[ -f src/annovar/table_annovar.pl ] || { echo "MISSING src/annovar/table_annovar.pl"; exit 1; }
[ ! -d src/annovar/humandb ] || { echo "src/annovar/humandb must not be in the build context"; exit 1; }
du -sh src
echo "[2] docker build  $(date +%T)"
docker build --network=host -t "$IMAGE" -f Dockerfile . 2>&1 | tail -25
docker image inspect "$IMAGE" --format 'size: {{.Size}} bytes  id: {{.Id}}  created: {{.Created}}'
echo "[3] smoke test  $(date +%T)"
docker run --rm -u "$(id -u):$(id -g)" -v "$HERE/smoke_test.sh:/tmp/smoke_test.sh:ro" "$IMAGE" bash /tmp/smoke_test.sh
echo "[3] smoke test PASSED"
if [ "$EXPORT" = 1 ]; then
    mkdir -p "$RELEASE_DIR"
    OUT="$RELEASE_DIR/local-tspipe-host-$TAG.docker.tar.gz"
    echo "[4] docker save -> $OUT  $(date +%T)"
    docker save "$IMAGE" | gzip -1 > "$OUT.part" && mv "$OUT.part" "$OUT"
    (cd "$RELEASE_DIR" && md5sum "$(basename "$OUT")" | tee "$OUT.md5") && ls -la "$OUT"
    SIF="$SINGULARITY_CACHE/local-tspipe-host-$TAG.img"
    echo "[5] singularity build -> $SIF  $(date +%T)"
    rm -f "$SIF.part"
    singularity build "$SIF.part" "docker-daemon://$IMAGE" && mv "$SIF.part" "$SIF" && ls -la "$SIF"
    md5sum "$SIF" | tee "$RELEASE_DIR/local-tspipe-host-$TAG.img.md5"
    echo "[5b] singularity smoke  $(date +%T)"
    singularity exec -B "$HERE" "$SIF" bash "$HERE/smoke_test.sh" | grep -c '^\[ok\]' | sed 's/^/singularity ok checks: /'
fi
echo "[end] $(date '+%F %T')"
