# containers/tspipe-host/Dockerfile -- local/tspipe-host:v1 (FREEZE A1)
#
# One image for every HOST-class tspipe process. The seven conda environments that the
# processes use on gandalf are unpacked from conda-pack tarballs (containers/tspipe-host/src/,
# built by pack_envs.sh) under /opt/envs/<name>, byte-for-byte the gandalf environments minus
# the AnnotSV annotation bundle. The four external installs sit under /opt/.
#
#   /opt/envs/targeted-seq   bwa-mem2 samtools abra2 gatk 4.6.2.0 cnvkit 0.9.12 freebayes
#                            vardict-java varscan pindel python 3.10 (pandas jinja2 pysam) R
#   /opt/envs/vep            ensembl-vep 105.0 (perl 5.26) -- called by bin/annotate.py run_vep
#   /opt/envs/py2            python 2.7 for Strelka2 and Platypus
#   /opt/envs/purecn         R + PureCN 2.16.0 (params.purecn_extdata -> /opt/envs/purecn/lib/R/library/PureCN/extdata)
#   /opt/envs/decon          R 4.3 + ExomeDepth 1.1.16 (DECoN)
#   /opt/envs/hmftools       Java 21 + AMBER / COBALT / PURPLE jars (params.hmf_env -> /opt/envs/hmftools)
#   /opt/envs/reconCNV       python 3.6 + bokeh 1.4
#   /opt/strelka2            Strelka2 release (ext.strelka_bin -> /opt/strelka2/bin/configureStrelkaGermlineWorkflow.py)
#   /opt/annovar             table_annovar.pl and friends; humandb is reference data, bind-mounted
#   /opt/oncovi              OncoVI engine + resources (params.oncovi_dir -> /opt/oncovi)
#   /opt/vardict             VarDictJava helpers (ext.vardict_helpers_dir -> /opt/vardict/bin)
#
# The default PATH puts targeted-seq first. Processes that need another env first get their PATH
# from the config (conf/containers.config), not from the image.
#
# Build (gandalf, from containers/tspipe-host/): docker build --network=host -t local/tspipe-host:v1 .
# Multi-stage so the tarballs never land in a final-image layer.

FROM ubuntu:22.04 AS unpack
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates rsync && rm -rf /var/lib/apt/lists/*
COPY src/ /src/
RUN set -eu; \
    for env in targeted-seq vep py2 purecn decon hmftools reconCNV; do \
        echo "[unpack] $env"; \
        mkdir -p /opt/envs/$env; \
        tar -xzf /src/$env.tar.gz -C /opt/envs/$env; \
        PATH=/opt/envs/$env/bin:$PATH /opt/envs/$env/bin/conda-unpack; \
        rm -f /src/$env.tar.gz; \
    done; \
    rsync -a /src/strelka2/ /opt/strelka2/; \
    rsync -a /src/annovar/  /opt/annovar/; \
    rsync -a /src/oncovi/   /opt/oncovi/; \
    rsync -a /src/vardict/  /opt/vardict/; \
    rm -rf /src; \
    chmod -R a+rX /opt

FROM ubuntu:22.04
LABEL org.opencontainers.image.title="tspipe-host" \
      org.opencontainers.image.description="nf-core-tspipe host environments (conda-pack of gandalf envs) for the FREEZE release" \
      org.opencontainers.image.version="v1"
ENV DEBIAN_FRONTEND=noninteractive
# procps: Nextflow's task wrapper uses ps for tracing; the rest are runtime libs conda envs may
# expect from the OS (libgomp for R/BLAS builds, libxrender/libxext for R graphics).
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates procps bzip2 curl less locales tzdata libgomp1 libxrender1 libxext6 libxt6 fontconfig libtiff5 libquadmath0 \
    && rm -rf /var/lib/apt/lists/* \
    && locale-gen en_US.UTF-8
COPY --from=unpack /opt /opt
ENV TSPIPE_ENV_ROOT=/opt/envs \
    TSPIPE_VEP_BIN=/opt/envs/vep/bin/vep \
    PATH=/opt/envs/targeted-seq/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8 \
    MPLCONFIGDIR=/tmp/mplconfig XDG_CACHE_HOME=/tmp/xdg-cache
RUN mkdir -p /tmp/mplconfig /tmp/xdg-cache && chmod 1777 /tmp/mplconfig /tmp/xdg-cache
CMD ["/bin/bash"]
