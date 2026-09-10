#!/usr/bin/env bash
# containers/tspipe-host/build_v1_1.sh -- build, verify and export local/tspipe-host:v1.1.
# Runs the full smoke test plus a reconCNV import check, then exports the Docker tar and the
# Singularity image under the names Nextflow expects. Keeps v1 until v1.1 is proven.
set -euo pipefail
TAG=v1.1
IMAGE=local/tspipe-host:$TAG
HERE=/goast/hemat_data/nf-core-tspipe/containers/tspipe-host
RELEASE_DIR=${RELEASE_DIR:-/goast/hemat_data/tspipe_release/images}
SINGULARITY_CACHE=${SINGULARITY_CACHE:-/goast/hemat_data/targeted-seq-pipeline/singularity_cache}
cd "$HERE"
echo "[start] $(date '+%F %T') $IMAGE"
df -h /home | tail -1
echo "[1] build"
docker build --network=host -f Dockerfile.v1.1 -t "$IMAGE" . 2>&1 | tail -12
docker image inspect "$IMAGE" --format 'size: {{.Size}} bytes  id: {{.Id}}'
echo "[2] smoke test"
docker run --rm -u "$(id -u):$(id -g)" -v "$HERE/smoke_test.sh:/tmp/smoke_test.sh:ro" "$IMAGE" bash /tmp/smoke_test.sh
docker run --rm -u "$(id -u):$(id -g)" "$IMAGE" bash -c 'PATH=/opt/envs/reconCNV/bin:$PATH python -c "import bokeh, PIL.Image; from bokeh.layouts import row, column, layout; print(\"reconCNV imports ok\", bokeh.__version__)"'
echo "[3] export"
mkdir -p "$RELEASE_DIR"
OUT="$RELEASE_DIR/local-tspipe-host-$TAG.docker.tar.gz"
docker save "$IMAGE" | gzip -1 > "$OUT.part" && mv "$OUT.part" "$OUT"
(cd "$RELEASE_DIR" && md5sum "$(basename "$OUT")" | tee "$OUT.md5")
SIF="$SINGULARITY_CACHE/local-tspipe-host-$TAG.img"
rm -f "$SIF.part"
singularity build "$SIF.part" "docker-daemon://$IMAGE" && mv "$SIF.part" "$SIF"
ls -la "$SIF"; md5sum "$SIF" | tee "$RELEASE_DIR/local-tspipe-host-$TAG.img.md5"
echo "[4] singularity check"
singularity exec -B "$HERE" "$SIF" bash "$HERE/smoke_test.sh" | grep -c '^\[ok\]' | sed 's/^/singularity ok checks: /'
singularity exec "$SIF" bash -c 'PATH=/opt/envs/reconCNV/bin:$PATH python -c "from bokeh.layouts import row; import PIL.Image; print(\"reconCNV imports ok under singularity\")"'
df -h /home | tail -1
echo "[end] $(date '+%F %T')"
