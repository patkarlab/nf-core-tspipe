# Release notes — nf-core-tspipe v1.0.0 (clinical freeze)

Frozen 2026-09-10 on gandalf. This is the version intended for deployment to clinical-23 and for
clinical reporting on the Twist myeloid panel. Feature freeze: only portability fixes and release
engineering entered after 2026-09-10 13:45; everything else is v1.1 (see "Deferred" below).

## What defines this release

- Pipeline: `patkarlab/nf-core-tspipe`, tag `v1.0.0`.
- Nextflow 25.10.4 (pinned; `manifest.nextflowVersion`).
- Container image `local/tspipe-host:v1.1` carries every process that previously ran on a gandalf
  conda environment: the seven environments (targeted-seq, vep, py2, purecn, decon, hmftools,
  reconCNV) unpacked under `/opt/envs/`, plus Strelka2, the ANNOVAR scripts, OncoVI and the
  VarDictJava helpers under `/opt/`. Built by `containers/tspipe-host/{pack_envs.sh,Dockerfile,
  build.sh}` from the gandalf environments themselves (`conda-pack`), so the packaged tool versions
  are exactly those validated here — notably GATK 4.6.2.0 and cnvkit 0.9.12, on which the current
  panel of normals depends.
- The remaining processes run on the public images already used in production (GATK 4.5.0.0,
  DeepSomatic 1.10.0, SomaticSeq 3.7.4, fastp, samtools, bcftools, mosdepth, igv-reports, cnvkit)
  and on four local images (cava 2.0.15, filt3r 0.1, flt3_itd_ext 0.2, getitd 0.1).
- Checksums for every image: `docs/release/image_checksums.md5`. Reference data manifest:
  `docs/release/reference_manifest.tsv` (path, size, md5 as validated on gandalf).
- No process depends on a conda environment, a `beforeScript` PATH export or a tool installed on
  the host. `conf/containers.config` assigns the image and the per-process PATH; the site profiles
  carry only paths, resources and the executor.

## Validation

- Eight-sample Twist validation cohort (`pon_samplesheets/twist_val_8_fastq.csv`), full run on the
  frozen image: 451 tasks, no failures, 2 h 33 m
  (`/goast/hemat_data/twist_val/tspipe_run8_img11`).
- Image-to-image reproducibility (`tools/compare_runs.py`, v1 vs v1.1 builds of the same image):
  1233 files identical; every clinical table, consensus table, PURPLE table and BAF output
  identical. The only differences are timestamped logs, files that embed a creation time (zip, PDF,
  `.rds`, HTML reports) and the reconCNV outputs fixed in v1.1
  (`docs/audit/2026-09-11/run8_v1_vs_v11.md`).
- Host-environment vs image (`docs/audit/2026-09-10/run8_host_vs_image.md`): clinical tables,
  annotation, BAF and consensus identical on six of eight samples; VEP output byte-identical,
  which closes audit item Q7. On two samples PURPLE differs — see "Known findings" below.

## Known findings recorded with this release

1. **PURPLE output depends on the C library, not on the pipeline.** AMBER and COBALT produce
   byte-identical `baf.tsv.gz` / `ratio.tsv.gz`, but the PCF segmentation step returns a slightly
   different segment set between an el9 host environment (glibc 2.34) and the image (Ubuntu 22.04,
   glibc 2.35): 121 vs 119 segments on 26CGH1292, with the same segment values to four decimals.
   PURPLE then reports the same purity and ploidy but a `normFactor` and `score` differing in the
   fourth decimal, and copy numbers shifted by about 0.005, which propagates into the consensus
   gene table. Within one environment the step is exactly reproducible (two repeats of the same
   task produce identical output, `tools/patches/2026-09-10/pcf_determinism.sh`). The image is
   therefore the reference: any host running `local/tspipe-host:v1.1` produces the same bytes, and
   the golden regression on a new host compares against the image run, not against a host-
   environment run.
2. **reconCNV needs `libtiff.so.5`** (PIL, via bokeh). Absent from Ubuntu 22.04 and from the packed
   environment; supplied on gandalf by the host OS, which is why it only surfaced inside a
   container. Fixed in image v1.1. When reconCNV fails the module warns and writes a placeholder
   HTML rather than failing the run — a deliberate choice, since reconCNV is a QC view.
3. **VariantValidator** is reached over the public API with `maxForks 1` and a response cache; the
   launcher's preflight is the only supported entry point.

## Deferred to v1.1

Site-level assay model (A3) with the 48-normal re-run and blacklist / `baf_background` rebuild;
BAF_V2c beta-binomial detector with segmentation; female normals and a female PoN; conformity gate;
asset reconciliation; ClinVar refresh; FLT3_ITD_EXT final VCF; per-run calibration of the 17p
window depth; the quality items in list B and the evaluation items in list C. See
`docs/audit/2026-09-10/HANDOFF_FREEZE_v1.md` and the handout register for the full list.

## Deployment

`docs/sops/install_clinical23.md` describes installing this release on a new host: prerequisites,
loading the image set, placing the reference data against the manifest, verification with the stub
DAG, and the eight-sample golden regression.
