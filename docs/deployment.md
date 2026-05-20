# Moving to a new server

This doc covers the gandalf-specific shortcut: pulling references, PoN
artefacts, and other large assets across from gandalf rather than
re-downloading or rebuilding from scratch.

**Prerequisite.** Finish [`docs/INSTALL.md`](INSTALL.md) on the
destination server first. Nextflow, Singularity, Docker, the
VariantValidator REST stack, the container catalogue, and the site
config are all install-time concerns covered there. This doc is the
final, gandalf-specific step.

Cross-references:

- [`docs/INSTALL.md`](INSTALL.md) — install everything else from scratch
- [`docs/testing.md`](testing.md) — post-install smoke tests, used for validation below
- [`docs/usage_pon.md`](usage_pon.md) — rebuild the PoN on the destination instead of rsyncing

## What to rsync from gandalf

| Source on gandalf                                                                  | Destination on new site            | Size    | Notes                                                                                                                  |
|------------------------------------------------------------------------------------|------------------------------------|---------|------------------------------------------------------------------------------------------------------------------------|
| `/goast/hemat_data/targeted-seq-pipeline/references/hg38_broad/`                   | `<refs_root>/hg38_broad/`          | ~50 GB  | Broad's hg38 bundle plus known-sites VCFs. Can also be re-downloaded via `assets/training/download_hg38_resources.sh`. |
| `/goast/hemat_data/targeted-seq-pipeline/references/<masked_fasta>*`               | `<refs_root>/`                     | ~3 GB   | The U2AF1/UBTF-paralog-masked variant. Produced by `assets/training/run_masked_realign.sh`.                            |
| `/goast/hemat_data/targeted-seq-pipeline/bedfiles/`                                | `<refs_root>/bedfiles/`            | <50 MB  | Panel BEDs (myeloid, etc.).                                                                                            |
| `/goast/hemat_data/targeted-seq-pipeline/vep_cache/`                               | `<refs_root>/vep_cache/`           | ~25 GB  | Tied to a specific VEP version; mismatched VEP gives mismatched annotation strings.                                    |
| `/goast/hemat_data/targeted-seq-pipeline/annovar_db/`                              | `<refs_root>/annovar_db/`          | ~120 GB | ANNOVAR databases. Not redistributable — only rsync between sites with valid ANNOVAR registration.                     |
| `/goast/hemat_data/nf-core-tspipe/assets/myeloid/cnvkit_pon_{male,female}.cnn`     | `<clone>/assets/myeloid/`          | ~3 MB   | Sex-stratified CNV PoN. Alternative: rebuild on destination via `BUILD_PON` ([`docs/usage_pon.md`](usage_pon.md)).      |
| `/goast/hemat_data/nf-core-tspipe/assets/myeloid/loo_bin_noise_profile.tsv`        | `<clone>/assets/myeloid/`          | <1 MB   | LOO bin noise profile produced by the same `BUILD_PON` run.                                                            |
| `/goast/hemat_data/nf-core-tspipe/assets/references/cytoBand_hg38.txt`             | `<clone>/assets/references/`       | <1 MB   | hg38 cytoband annotation.                                                                                              |
| `/goast/hemat_data/nf-core-tspipe/assets/references/ClinGen_gene_curation_list_GRCh38.tsv` | `<clone>/assets/references/` | <1 MB   | ClinGen gene curation list.                                                                                            |

Aggregate is roughly **200 GB** end to end if you take everything. The
ANNOVAR DB is by far the largest single item; if its size is prohibitive
on the destination, your ANNOVAR registration lets you download a
smaller per-database subset directly.

The asset files in the bottom four rows are not tracked in git (binary
and/or large). Rsyncing them is the standard way to seed a destination
clone without rebuilding the PoN; the alternative is to run `BUILD_PON`
on the destination.

## rsync invocation

```bash
# From the new server, with SSH access to gandalf.
REFS=/data/tspipe_refs
CLONE=/data/nf-core-tspipe          # your git clone of the pipeline
mkdir -p ${REFS}

# References (the big ones)
rsync -avh --progress --partial \
    hemat@gandalf:/goast/hemat_data/targeted-seq-pipeline/references/ \
    ${REFS}/references/

rsync -avh --progress --partial \
    hemat@gandalf:/goast/hemat_data/targeted-seq-pipeline/bedfiles/ \
    ${REFS}/bedfiles/

rsync -avh --progress --partial \
    hemat@gandalf:/goast/hemat_data/targeted-seq-pipeline/vep_cache/ \
    ${REFS}/vep_cache/

rsync -avh --progress --partial \
    hemat@gandalf:/goast/hemat_data/targeted-seq-pipeline/annovar_db/ \
    ${REFS}/annovar_db/

# Asset files (panel-namespaced PoN + reference data) into your repo clone
rsync -avh --progress --partial \
    hemat@gandalf:/goast/hemat_data/nf-core-tspipe/assets/ \
    ${CLONE}/assets/
```

`--partial` lets you resume mid-file if the SSH connection drops, which
matters at 100+ GB transfers. Add `--bwlimit=NNNN` (KB/s) if the gandalf
side needs throttling. For badly latent links, `tar | ssh tar -x` over a
screen session is sometimes faster than rsync's per-file overhead, but
rsync is the safer default.

## Site-specific config differences

Per [`docs/INSTALL.md`](INSTALL.md), you have already written
`conf/<yoursite>.config` from `conf/site_template.config`. The values
that will *differ from gandalf* are:

| Param                                                                | Likely new value                                       |
|----------------------------------------------------------------------|--------------------------------------------------------|
| `pipeline_root`                                                      | Destination references root (e.g. `/data/tspipe_refs`) |
| `reference`                                                          | `${pipeline_root}/<masked_fasta>`                      |
| `bed`                                                                | `${pipeline_root}/bedfiles/<panel>.bed`                |
| `dbsnp_vcf`, `mills_vcf`, `gnomad_af_only`, `vep_cache`, `annovar_db`| All under `${pipeline_root}/...`                       |
| `max_cpus`, `max_memory`, `max_time`                                 | Match the destination host's hardware                  |
| Singularity / Apptainer cache directory                              | Point at a large persistent disk on the destination    |

Everything else (process resource labels, `conf/modules.config`
behaviour, `singularity.enabled` etc.) should be unchanged across sites.
If you find yourself needing to override module-level config, that's a
signal to fix upstream rather than fork.

## Validation

Run the post-install smoke tests from
[`docs/testing.md`](testing.md):

1. **Phase 1** (config parse) — verifies the new profile is registered cleanly.
2. **Phase 2** (`-stub` mode) — exercises the DAG against the rsynced asset paths without invoking any tool.
3. **Phase 3** (one-sample real run) — first run that pulls containers and actually runs the pipeline.

Then run a sample on the new server for which you have a known-good
clinical TSV from gandalf, and diff:

```bash
diff <(sort gandalf_run/<sample>/clinical/<sample>.clinical.tsv) \
     <(sort newsite_run/<sample>/clinical/<sample>.clinical.tsv) \
     > clinical.diff
wc -l clinical.diff
```

**Expected (benign) differences**

- VEP annotation strings if the VEP cache version differs between sites.
- CNVKit log2 ratios if the PoN was rebuilt on the destination rather
  than rsynced (different normals cohort yields a different baseline).
- Mutect2 PASS/REJECT calls near germline boundaries if the gnomAD AF-only
  VCF was updated between the two runs.

**Not acceptable**

- Variants present in one run and absent in the other.
- FLT3-ITD length or VAF differences for the same sample.
- The FILTER column flipping between PASS and BLACKLIST for the same
  variant — usually a sign of a mismatched `snv_blacklist` file.

## Out of scope

Container vendoring for the three local FLT3 tools (`filt3r`, `getitd`,
`flt3_itd_ext`) is tracked in
[`docs/INSTALL.md#open-items`](INSTALL.md#open-items). The current
operational answer is to `docker save` the images from gandalf and load
them on the destination; see INSTALL.md for the exact command sequence.

A `BUILD_PON` rebuild on the destination is covered in
[`docs/usage_pon.md`](usage_pon.md); pick it over the rsync route when
the destination's normals cohort differs materially from gandalf's.
