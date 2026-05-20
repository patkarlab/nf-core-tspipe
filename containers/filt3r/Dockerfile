# filt3r — build-from-source Dockerfile
#
# Builds the filt3r binary from upstream gitlab. Reproducible but
# network-dependent at build time and produces a ~1.69 GB image (gcc:11
# base). For a slim production image (~10 MB) built from a pre-compiled
# static binary, see Dockerfile.deploy alongside this file.
#
# Image produced: local/filt3r:v0.1
#
# Build:
#   docker build -t local/filt3r:v0.1 .
#
# Sources:
#   Upstream: https://gitlab.univ-lille.fr/filt3r/filt3r
#   Paper:    Baudry et al., Bioinformatics 2022,
#             https://doi.org/10.1093/bioinformatics/btac093
#
# This Dockerfile preserves the original build sequence that produced
# the gandalf-cached local/filt3r:v0.1 image. The only intentional
# difference vs the original 4-line Dockerfile is the addition of
# --no-install-recommends and an explicit rm /var/lib/apt/lists/*
# in the apt step (smaller layer, more hygienic; doesn't change the
# resulting binary).

FROM gcc:11

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
        cmake \
        time \
    && rm -rf /var/lib/apt/lists/*

# Clone upstream and build. To pin to a specific upstream commit for
# reproducibility, change the `git clone` line to:
#   RUN git clone https://gitlab.univ-lille.fr/filt3r/filt3r.git \
#       && cd filt3r && git checkout <commit-or-tag>
# The currently-deployed local/filt3r:v0.1 was built from the upstream
# tip-of-main as of 2026-05-12; pinning to a tag is recommended for any
# future rebuild.
RUN git clone https://gitlab.univ-lille.fr/filt3r/filt3r.git

RUN cd filt3r \
    && make gatb \
    && make

# The compiled binary lives at /filt3r/filt3r inside the image. The
# nf-core module (modules/local/filt3r.nf) invokes it as
# /filt3r/filt3r and references the bundled k-mer reference at
# /filt3r/data/flt3_exon14-15.fa, which the upstream build process
# copies into the image automatically.
