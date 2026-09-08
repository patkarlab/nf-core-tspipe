# CAVA 2.0.15 (sicotteh/CAVA, maintained successor of RahmanTeam/CAVA), Python 3.
# Pinned to the master commit verified on 2026-09-08. Rebuild only with a new pin.
#
# Build (gandalf: BuildKit needs the host network namespace for DNS):
#   docker build --network=host -t local/cava:v2.0.15 containers/cava/
# Convert for the singularity profile:
#   singularity build /goast/hemat_data/targeted-seq-pipeline/singularity_cache/local-cava-v2.0.15.img \
#       docker-daemon://local/cava:v2.0.15
# Runtime check:
#   docker run --rm local/cava:v2.0.15 cava --version    # 2.0.15

FROM python:3.11-slim-bookworm

ARG CAVA_COMMIT=398eb1d6ff635925fedb7dcd88a9a6617d1a7c3b

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get -o Acquire::ForceIPv4=true update \
 && apt-get -o Acquire::ForceIPv4=true install -y --no-install-recommends \
        git build-essential zlib1g-dev libbz2-dev liblzma-dev libcurl4-openssl-dev \
        bedtools tabix procps \
 && rm -rf /var/lib/apt/lists/*

RUN pip install "CAVA @ git+https://github.com/sicotteh/CAVA.git@${CAVA_COMMIT}" \
 && cava --version \
 && echo "${CAVA_COMMIT}" > /opt/CAVA_COMMIT

WORKDIR /data
CMD ["cava", "--help"]
