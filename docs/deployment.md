# Moving to a new server

Once the pipeline runs correctly on gandalf, porting it to another server should
be ~1 day of work: a config file, a reference download, and a smoke test.

## Checklist

```
[ ] 1. Install Nextflow on the new server
[ ] 2. Install Singularity (or Docker)
[ ] 3. Mirror reference + resource files
[ ] 4. Write conf/<newsite>.config
[ ] 5. Register the new profile in nextflow.config
[ ] 6. Run Phase 2-3 from docs/testing.md (parse + one-sample run)
[ ] 7. Compare against gandalf output
```

## 1. Install Nextflow

```bash
curl -s https://get.nextflow.io | bash
sudo mv nextflow /usr/local/bin/   # or to ~/bin/
nextflow -version
```

## 2. Install Singularity (or use Docker)

Singularity is preferred for HPC; Docker is easier on personal workstations.
On Ubuntu/Debian:

```bash
sudo apt install singularity-container
# or for a container-runtime fallback:
sudo apt install docker.io
sudo usermod -aG docker $USER     # log out + log in
```

Container images will be pulled automatically on first run. Set a persistent
cache so they're not re-downloaded:

```bash
mkdir -p /large_disk/singularity_cache
# Set this in your site config -- see step 4.
```

## 3. Mirror reference files

The cheap-and-cheerful approach: `rsync` from gandalf.

```bash
# On the new server:
NEW_PIPELINE_ROOT=/data/tspipe
mkdir -p $NEW_PIPELINE_ROOT

# Pull references (this is the big one -- ~200 GB for VEP + ANNOVAR + hg38)
rsync -avh --progress \
    hemat@gandalf:/goast/hemat_data/targeted-seq-pipeline/references/ \
    $NEW_PIPELINE_ROOT/references/

rsync -avh --progress \
    hemat@gandalf:/goast/hemat_data/targeted-seq-pipeline/bedfiles/ \
    $NEW_PIPELINE_ROOT/bedfiles/

# Pon-built outputs (cnvkit_pon, loo_summary etc.) -- if you trust them on
# the new server. If you want to rebuild from scratch on the new server,
# skip this and run -entry BUILD_PON over there.
rsync -avh --progress \
    hemat@gandalf:/goast/hemat_data/targeted-seq-pipeline/pon_normals/ \
    $NEW_PIPELINE_ROOT/pon_normals/
```

Alternatively, for the reference genome itself, you can re-download:

```bash
# Broad's bundle has the original hg38 + known sites.
# Easier to re-download than to rsync the 50GB.
bash assets/training/download_hg38_resources.sh
# Then create the masked variant per your masking protocol.
```

## 4. Write the site config

Start from the template:

```bash
cp conf/site_template.config conf/<yoursite>.config
```

Then edit the file. The critical knobs:

| Param                   | What it points to                                |
| ----------------------- | ------------------------------------------------ |
| `pipeline_root`         | Your new base directory                          |
| `reference`             | hg38 (masked) FASTA                              |
| `bed`                   | Panel BED                                        |
| `cnv_pon`, `cnv_*`      | PoN files (rsync'd or rebuilt)                   |
| `snv_blacklist`         | The hand-curated TSV                             |
| `vep_cache`, `annovar_db` | Annotation database directories                |
| `max_cpus`, `max_memory`, `max_time` | Match the new machine             |

For **Strategy A (containers everywhere)** — easiest:
- DON'T set `vardict_bin`, `getitd_path`, `filt3r_bin`, etc.
- DON'T add a `process.beforeScript` block.
- The modules already declare `container = 'quay.io/biocontainers/...'` so
  Nextflow will pull on first run.

For **Strategy B (local installs)** — faster:
- Install the same conda envs you had on gandalf (`targeted-seq` + `py2`).
- Set the tool paths as in `conf/gandalf.config`.
- Set `process.beforeScript` to put your env on PATH.

## 5. Register the profile

In `nextflow.config`:

```groovy
profiles {
    ...
    gandalf {
        includeConfig 'conf/gandalf.config'
    }
    yoursite {                                 // add this
        includeConfig 'conf/yoursite.config'
    }
}
```

## 6. Smoke test

Same as Phase 2-3 in `docs/testing.md`:

```bash
# Config syntactically valid?
nextflow config -profile yoursite

# One-sample run
nextflow run main.nf -profile yoursite,singularity \
    --input test_samplesheet.csv \
    --outdir test_results -resume
```

## 7. Compare against gandalf output

Pick the same validation sample you used on gandalf (25NGS1307 with its known
45bp FLT3-ITD), run the new server, then diff the clinical outputs:

```bash
diff <(sort gandalf_run/25NGS1307/annotation/25NGS1307.clinical.tsv) \
     <(sort newserver_run/25NGS1307/annotation/25NGS1307.clinical.tsv) \
     > clinical.diff
wc -l clinical.diff
```

Acceptable differences: VEP cache version mismatch (different annotation
strings), CNVKit if the PoN was rebuilt on the new server (different log2
ratios), Mutect2 if the gnomAD VCF was updated.

NOT acceptable: variants present in one and absent in the other, FLT3-ITD
length/VAF differences, FILTER column flipping between PASS and BLACKLIST.

## Containerizing the custom tools

The four tools that aren't in bioconda will hold you back on a fresh server:

1. **FLT3_ITD_EXT** — already a Docker image: `zhkddocker/flt3_itd_ext:v1.1`. Works on any server with Docker or Singularity.

2. **getITD** — Python script + `anno/` directory. Build a container once:
   ```dockerfile
   FROM continuumio/miniconda3:latest
   RUN pip install pysam pandas numpy biopython
   COPY getitd/ /opt/getitd/
   ENV PATH=/opt/getitd:$PATH
   ```
   Build and push to your registry, then set `container = 'your-registry/getitd:1.5.15'` in `modules/local/getitd.nf`.

3. **filt3r** — C++ binary. Either build a container, or copy the static binary to the new server and add to PATH.

4. **VarDict** — Java tool. Bioconda has it (`bioconda::vardict-java`). The original install was from a build directory because they wanted a specific version; on the new server, just `conda install vardict-java` and let the module find it.

5. **Pindel** — Bioconda has it. `conda install pindel`. Simpler than the source build the original used.

Doing this once saves you copying conda envs around every time you provision a server. The bioconda container references in the module files mean a fresh server with only Singularity installed can run the entire pipeline (modulo the four tools above).
