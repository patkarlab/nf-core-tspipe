# getitd — Dockerfile for the lab's panel-configured getITD
#
# Image produced: local/getitd:v0.1 (~306 MB)
#
# Build:
#   docker build -t local/getitd:v0.1 .
#
# Sources:
#   Upstream: https://github.com/tjblaette/getitd
#   Paper:    Blaette et al., Leukemia 2019,
#             https://doi.org/10.1038/s41375-019-0526-5
#
# IMPORTANT: panel-specific build context required.
#
# This Dockerfile copies a `getitd/` subdirectory into /opt/getitd/
# inside the image. That `getitd/` is NOT a vanilla clone of the
# upstream repo. It is a clone augmented with two lab-specific files
# under getitd/anno/:
#
#   - amplicon.txt           WT amplicon reference sequence for the
#                            lab's MYOPOOL panel (FLT3 exon 14/15
#                            region as covered by the panel design).
#   - amplicon_kayser.tsv    chr13 / transcript / protein-coordinate
#                            annotation for the same panel.
#
# Both files are produced by upstream getITD's make_getitd_config.py
# from the panel BED and the reference FASTA. For a different panel
# (or a different reference build), regenerate them before building
# the image, otherwise getITD will report ITDs against a WT sequence
# that does not match what the panel actually captures.
#
# To regenerate (on the host, in a checkout of upstream getITD):
#   python make_getitd_config.py \
#       --panel-bed /path/to/panel.bed \
#       --reference /path/to/hg38.fasta \
#       --output-dir ./anno
#
# Then copy ./anno/amplicon.txt and ./anno/amplicon_kayser.tsv into
# this directory's getitd/anno/ before building.
#
# The current getitd/ build context (as shipped in this directory)
# encodes the MYOPOOL panel against masked hg38, validated against
# 25NGS1307 (45 bp ITD positive).

FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends procps \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir biopython pandas numpy

# Copy the panel-configured getITD tree into /opt/getitd/. See the note
# above for what's expected to be inside this directory.
COPY getitd/ /opt/getitd/

WORKDIR /opt/getitd

# The nf-core module (modules/local/getitd.nf) invokes
#   python /opt/getitd/getitd.py
#       -reference /opt/getitd/anno/amplicon.txt
#       -anno      /opt/getitd/anno/amplicon_kayser.tsv
# from the Nextflow work directory (where the FASTQs are staged). Both
# absolute paths are required because getITD's defaults are relative to
# CWD, not to the install dir.
