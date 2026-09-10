# containers/mocha/Dockerfile  --  local/mocha:v1
#
# bcftools 1.20 with the MoChA plugins (mocha, mochatools, extendFMT; freeseek/mocha commit
# 95686b7, plugin version 2025-08-19), SHAPEIT5 5.1.1 from bioconda, and python3 for the
# bin/ helper scripts of the MOCHA_17P module in nf-core-tspipe.
#
# The bcftools tarball and the plugin sources are fetched on the host (with md5 checks) into
# containers/mocha/src/ by tools/patches/2026-09-09/build_mocha_v1.sh, so the image build
# needs no GitHub access; only apt and conda.anaconda.org are contacted during the build.
#
# Build on gandalf (BuildKit RUN steps have no DNS there without host networking):
#   tools/patches/2026-09-09/build_mocha_v1.sh
#   (docker build --network=host -t local/mocha:v1 containers/mocha/ after the fetch stage)
# Must stay Docker-runnable for clinical-23.

FROM mambaorg/micromamba:1.5.10-jammy

USER root
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential bzip2 ca-certificates python3 \
      zlib1g-dev libbz2-dev liblzma-dev libgsl-dev libcurl4-openssl-dev libssl-dev libdeflate-dev \
 && rm -rf /var/lib/apt/lists/*

ARG BCFTOOLS_VERSION=1.20

# src/bcftools-1.20.tar.bz2 and src/mocha/{mocha,beta_binom,genome_rules}.h,{mocha,mochatools,extendFMT}.c
COPY src/ /tmp/src/

# bcftools and the MoChA plugins are compiled together: the plugin sources go into plugins/
# before make, and make install places every plugins/*.so in libexec/bcftools. Built with
# the system toolchain before conda enters PATH, so configure links the system libcurl and GSL.
RUN cd /tmp \
 && tar xjf src/bcftools-${BCFTOOLS_VERSION}.tar.bz2 \
 && cd bcftools-${BCFTOOLS_VERSION} \
 && cp /tmp/src/mocha/*.h /tmp/src/mocha/*.c plugins/ \
 && ./configure --prefix=/opt/bcftools --enable-libgsl \
 && make -j4 \
 && make install \
 && cd /tmp && rm -rf bcftools-${BCFTOOLS_VERSION} src

# SHAPEIT5 from bioconda (binaries are installed as SHAPEIT5_<tool>; unprefixed aliases added).
# The conda htslib pulled in as a dependency also provides bgzip and tabix.
RUN micromamba install -y -n base -c conda-forge -c bioconda shapeit5=5.1.1 \
 && micromamba clean --all --yes \
 && for b in phase_common phase_rare ligate switch; do \
      ln -s /opt/conda/bin/SHAPEIT5_$b /opt/conda/bin/$b; \
    done

ENV PATH=/opt/bcftools/bin:/opt/conda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    BCFTOOLS_PLUGINS=/opt/bcftools/libexec/bcftools

# Behave identically under Docker and Singularity: no micromamba entrypoint wrapper.
ENTRYPOINT []
WORKDIR /data

# Build-time smoke test. The plugins exit 255 when printing usage, and +mocha reads stdin
# when given no file, so stdin is closed explicitly on every call.
RUN bcftools --version </dev/null | head -1 \
 && (bcftools +mocha </dev/null 2>&1 || true) | grep -m1 'version 20' \
 && (bcftools +mochatools -h </dev/null 2>&1 || true) | grep -m1 'fasta-ref' \
 && (bcftools +extendFMT </dev/null 2>&1 || true) | grep -m1 'Extend format' \
 && phase_common --help </dev/null 2>&1 | grep -m1 -i 'phase' \
 && tabix --version </dev/null | head -1 \
 && python3 --version
