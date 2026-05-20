# flt3_itd_ext — thin wrapper around upstream zhkddocker/flt3_itd_ext
#
# Image produced: local/flt3_itd_ext:v0.2 (~1.75 GB)
#
# Build:
#   docker build -t local/flt3_itd_ext:v0.2 .
#
# Sources:
#   Upstream image: zhkddocker/flt3_itd_ext:v1.1 (Docker Hub)
#   Tool authors:   Tan & Roberts 2020
#
# This image adds two things on top of the upstream base:
#
#   1. procps (for `ps`), needed by Nextflow for process accounting.
#
#   2. /usr/local/bin/flt3_itd_ext wrapper script that cd's into the
#      tool's install directory (/biosoft/FLT3_ITD_ext) before invoking
#      perl FLT3_ITD_ext.pl. This lets the nf-core module
#      (modules/local/flt3_itd_ext.nf) call `flt3_itd_ext` from the
#      Nextflow work directory and pass absolute paths via $(pwd),
#      without the script tripping over its install-directory-relative
#      data files.
#
# This Dockerfile was reconstructed from the layer history of the
# gandalf-cached local/flt3_itd_ext:v0.2 image (the original Dockerfile
# was not preserved on disk). The behaviour matches the cached image
# layer-for-layer.

FROM zhkddocker/flt3_itd_ext:v1.1

RUN apt-get update \
    && apt-get install -y --no-install-recommends procps \
    && rm -rf /var/lib/apt/lists/*

# Wrapper script: cd into the install dir, then exec perl with the
# original argv. Lets callers invoke `flt3_itd_ext` from any CWD.
RUN printf '%s\n' \
        '#!/bin/bash' \
        'set -e' \
        'cd /biosoft/FLT3_ITD_ext' \
        'exec perl FLT3_ITD_ext.pl "$@"' \
        > /usr/local/bin/flt3_itd_ext \
    && chmod +x /usr/local/bin/flt3_itd_ext
