# containers/

Vendored Dockerfiles for the three local images that the pipeline
references but Biocontainers does not provide:

| Image                       | Subdirectory             | Source                                                 |
|-----------------------------|--------------------------|--------------------------------------------------------|
| `local/flt3_itd_ext:v0.2`   | `containers/flt3_itd_ext/` | Thin wrapper on `zhkddocker/flt3_itd_ext:v1.1`        |
| `local/filt3r:v0.1`         | `containers/filt3r/`       | Built from upstream gitlab (Baudry 2022)              |
| `local/getitd:v0.1`         | `containers/getitd/`       | Panel-configured getITD (Blaette 2019)                |

These three are referenced as `container` directives in
`modules/local/{flt3_itd_ext,filt3r,getitd}.nf`. The Singularity image
cache on the run host needs corresponding `.sif` files; Nextflow
auto-converts from Docker on first encounter if the local Docker
daemon has the image, but for clean-install sites you'll typically
build on a workstation with Docker, then `docker save` and `singularity
build` on the run host.

## Building the images

From the repository root:

```bash
# 1. flt3_itd_ext wrapper (depends on upstream zhkddocker pull)
cd containers/flt3_itd_ext
docker build -t local/flt3_itd_ext:v0.2 .
cd ../..

# 2. filt3r (build-from-source; ~5-10 min on a workstation)
cd containers/filt3r
docker build -t local/filt3r:v0.1 .
cd ../..

# 3. getitd (PANEL-SPECIFIC — see note below)
cd containers/getitd
# Verify that getitd/anno/amplicon.txt and getitd/anno/amplicon_kayser.tsv
# match the panel you intend to run against. For a different panel,
# regenerate them via upstream make_getitd_config.py before building.
docker build -t local/getitd:v0.1 .
cd ../..
```

## Panel-specific note for getitd

The `containers/getitd/getitd/anno/` directory contains a WT amplicon
reference (`amplicon.txt`) and a chr13/transcript/protein annotation
(`amplicon_kayser.tsv`) that are specific to the MYOPOOL panel
against masked hg38. They are not vanilla upstream getITD files;
they were generated for the lab's panel design by upstream getITD's
`make_getitd_config.py`.

If you change the panel BED or the reference build, you must
regenerate these two files before rebuilding `local/getitd:v0.1`, or
the tool will look for ITDs in the wrong genomic context. See the
header comment in `containers/getitd/Dockerfile` for the regeneration
command.

## Image catalogue alternatives

For each tool, two production-quality paths exist:

- **flt3_itd_ext:** the upstream `zhkddocker/flt3_itd_ext:v1.1` image
  already works for command-line use. Our wrapper image exists
  specifically to (a) add `procps` for Nextflow and (b) provide a
  PATH-resident wrapper script. If you don't need the wrapper, you
  could change `modules/local/flt3_itd_ext.nf` to point at the
  upstream image and invoke `perl /biosoft/FLT3_ITD_ext/FLT3_ITD_ext.pl`
  directly with explicit `cd`; the current wrapper just makes the
  module's `script:` block tidier.

- **filt3r:** the build-from-source `Dockerfile` is the one used to
  produce the current `local/filt3r:v0.1`. A slim deployment variant
  (`Dockerfile.deploy`) is also vendored in `containers/filt3r/`; it
  ships a pre-built static binary and produces a ~10 MB Alpine image
  instead of the ~1.7 GB gcc image. Use it for production once you
  trust the binary.

- **getitd:** no good alternative. The panel-configured `anno/` files
  must be inside the image, and no Biocontainer publishes them. The
  vendored Dockerfile is the canonical build path.

## Cache provisioning workflow

For a fresh site that wants the images without rebuilding from scratch:

```bash
# On gandalf (or any host that already has the images cached)
docker save -o /tmp/local-images.tar \
    local/flt3_itd_ext:v0.2 \
    local/filt3r:v0.1 \
    local/getitd:v0.1

# Transfer /tmp/local-images.tar to the destination, then:
docker load -i /tmp/local-images.tar

# To convert to Singularity .sif for HPC hosts:
mkdir -p ~/singularity_cache
for img in local/flt3_itd_ext:v0.2 local/filt3r:v0.1 local/getitd:v0.1; do
    safe_name=$(echo "$img" | tr '/:' '_-')
    singularity build "~/singularity_cache/${safe_name}.sif" "docker-daemon://${img}"
done
```

The `tar` file for all three images is roughly 1 GB. Compress with
gzip if bandwidth-limited (`docker save ... | gzip > local-images.tar.gz`).
