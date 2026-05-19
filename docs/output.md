# Output

This document describes the directory layout the pipeline produces.
All paths are relative to `${params.outdir}`, the value passed to
`--outdir`. Publishing rules come from `conf/modules.config`; this
document reflects the layout produced by `workflows/tspipe.nf` as of
commit `dd0a3c6` and verified against the 2026-05-19 multi-sample
validation run.

## Top-level structure

```
${outdir}/
├── <sample>/                   # One directory per sample
│   ├── clinical/               # Deliverable tree (sign-out artefacts)
│   ├── trimmed/                # Per-stage intermediates...
│   ├── aligned/                # ...kept for debugging
│   ├── markdup/
│   ├── ...
│   └── annotation/
├── pipeline_info/              # Run-level Nextflow reports
└── work/                       # Nextflow scratch (deleted on success
                                #   for subworkflow-level hashes; the
                                #   rest can be cleaned up by hand)
```

The **clinical/** tree under each sample is the deliverable. Everything
else under `<sample>/` is per-stage intermediate output retained for
debugging and re-runs; it is safe to delete once clinical artefacts are
signed out.

## Clinical deliverable (`<sample>/clinical/`)

Assembled by `ORGANIZE_OUTPUT`, which publishes with `mode = 'copy'`
(byte copies, not symlinks) so the directory SFTPs cleanly and
survives `work/` cleanup. From the 2026-05-19 16-sample validation
run, every sample produced exactly this set:

```
<sample>/clinical/
├── <sample>_dashboard.html                  # Per-sample QC + variants dashboard
├── <sample>_fastp.html                      # fastp QC report
├── <sample>_hsmetrics.txt                   # Picard HsMetrics summary
├── <sample>_exon_coverage.tsv               # Per-exon coverage table
├── <sample>.final.bam                       # ABRA2 indel-realigned BAM (hardlinked)
├── <sample>.final.bam.bai                   # BAM index
├── <sample>.somaticseq.clinical.final.tsv   # Clinical variant TSV (PASS only, with annotations)
├── <sample>.somaticseq.filtered.tsv         # All variants with FILTER populated
├── <sample>_flt3_consensus.tsv              # 4-tool FLT3-ITD consensus
├── <sample>_igv_report.html                 # IGV.js variant pileup viewer
├── cnv_consensus/                           # Per-gene CNV calls (clinical-ready)
└── cnvkit_plots/                            # Per-chromosome scatter plots
```

The IGV pileup HTML loads `igv.js` from `cdn.jsdelivr.net` at view
time; reviewers' browsers need network access to that CDN for the
pileup panel to render.

## Per-stage intermediates (`<sample>/`)

Useful for debugging or re-running individual stages. None of these
are required for clinical sign-out.

### Preprocessing

```
<sample>/
├── trimmed/                   # fastp: <sample>.trimmed.fastq.gz, <sample>.fastp.json, <sample>.fastp.html
├── aligned/                   # BWA-MEM2 output BAM (unsorted intermediate)
├── markdup/                   # Picard MarkDuplicates: <sample>.markdup.bam, .bai, .metrics.txt
├── bqsr/                      # GATK4 BQSR: <sample>.bqsr.bam, .bai, .table
└── abra2/                     # ABRA2 indel realignment: <sample>.final.bam, .bai
                               #   (final.bam is the BAM used by every downstream caller)
```

### QC

```
<sample>/
├── hsmetrics/                 # Picard HsMetrics: <sample>.hsmetrics.txt, <sample>.interval_list
├── mosdepth/                  # mosdepth: <sample>.regions.bed.gz, .summary.txt, .dist.txt
└── exon_coverage/             # Parsed per-exon table: <sample>.exon_coverage.tsv
```

### Variant calling

```
<sample>/variant_callers/
├── mutect2/                   # GATK4 Mutect2 VCF
├── vardict/                   # VarDictJava VCF + intermediate TSV
├── varscan/                   # VarScan2 VCF
├── strelka/                   # Strelka2 germline VCF
├── freebayes/                 # FreeBayes VCF
├── platypus/                  # Platypus VCF
├── pindel/                    # Pindel VCF + the Pindel-FLT3 region subset (.flt3.vcf.gz)
├── deepsomatic/               # Google DeepSomatic VCF.gz + .tbi
└── u2af1_rescue/              # U2AF1 paralog-rescue TSV + pileup report
```

The eight per-caller VCFs are inputs to SomaticSeq; the U2AF1 rescue
output is folded into the final annotation TSV.

### Ensemble and FLT3-ITD

```
<sample>/
├── somaticseq/                # SomaticSeq ensemble VCF (SNV + indel, sorted, indexed)
└── flt3/
    ├── flt3_itd_ext/          # FLT3_ITD_EXT output directory
    ├── filt3r/                # filt3r JSON + VCF
    ├── getitd/                # getITD output directory
    └── <sample>_flt3_consensus.tsv   # Consensus across 4 callers
```

The 4-caller FLT3-ITD ensemble comprises FLT3_ITD_EXT, the
Pindel-FLT3 region filter (Pindel VCF is at
`variant_callers/pindel/<sample>.flt3.vcf.gz`), filt3r, and getITD.
The consensus TSV is also copied into `clinical/`.

### CNV calling

```
<sample>/cnv/
├── cnvkit/                    # CNVKit batch outputs: .cnr, .cns, diagram PDF, scatter PNGs
├── zscore/                    # Z-score per-gene TSV
├── plots/                     # Top-level CNV PDFs
│   └── details/               # Per-chromosome, per-gene, and overview plot subtrees
├── concordance/               # Per-gene CNVKit-vs-LOO concordance TSV
├── report/                    # Clinical CNV report (TSV + TXT)
└── annotated/                 # CNV calls with ClinGen / cytoband annotation TSV
```

The `cnvkit_plots/` and `cnv_consensus/` directories surfaced in
`clinical/` are subsets of this tree, byte-copied by
`ORGANIZE_OUTPUT`.

### Annotation

```
<sample>/annotation/
├── <sample>.vep.tsv                         # VEP + ANNOVAR combined
├── <sample>.somaticseq.filtered.tsv         # All variants with FILTER populated
├── <sample>.somaticseq.clinical.tsv         # FILTER == PASS only
├── <sample>.somaticseq.clinical.final.tsv   # After VV + OncoVI + FLT3 rows merged in
└── (intermediate validated / oncovi TSVs)
```

VARIANT_FILTER, VARIANT_VALIDATOR, ONCOVI, and FLT3_TO_VARIANTS all
publish into the same directory. The headline output is
`<sample>.somaticseq.clinical.final.tsv`, which is copied into
`clinical/`.

## Run-level outputs (`${outdir}/`)

### `pipeline_info/`

Nextflow's standard reporting suite, configured in
`nextflow.config:121-139`. Filenames include a timestamp so concurrent
runs do not overwrite each other.

```
pipeline_info/
├── execution_report_<timestamp>.html        # Full execution report
├── execution_timeline_<timestamp>.html      # Gantt-style timeline
├── execution_trace_<timestamp>.txt          # Per-task tab-separated trace
│                                            #   (status, runtime, CPU, peak memory, exit code)
└── pipeline_dag_<timestamp>.svg             # DAG visualisation
```

The trace file is the most useful artefact for postmortem analysis:
which tasks failed, which ran long, which hit memory ceilings.

### `work/`

Nextflow's per-process scratch. Grows large during execution; the
`workflow.onComplete` block in `main.nf` cleans subworkflow-level
hashes on success. The rest can be deleted by hand once clinical
artefacts are signed out:

```bash
rm -rf "${outdir}/work"
```

Keep `work/` while debugging a failed run — `work/<hash>/.command.{sh,out,err,log}`
holds the exact command and stderr for each failed task.

## `BUILD_PON` workflow outputs

When run with `-entry BUILD_PON`, outputs land in a different layout:

```
${outdir}/
├── pon/
│   ├── cnvkit_pon_build/
│   │   └── pon_reference.cnn                # Mixed-sex PoN
│   ├── cnvkit_pon_male.cnn                  # Sex-stratified PoNs
│   ├── cnvkit_pon_female.cnn
│   ├── cnvkit_pon_sex_assignment.tsv        # Per-normal chrX-based sex classification
│   └── loo_qc/                              # Per-normal leave-one-out QC artefacts
├── references/
│   └── <panel>/                             # Panel-namespaced artefacts (default: myeloid)
│       ├── cnvkit_loo_summary.tsv
│       └── cnvkit_noisy_bins.bed
└── pipeline_info/
```

To wire these into the main `TSPIPE` workflow, either:

- Copy them into `assets/<panel>/` in the repo (overwriting the
  shipped versions), or
- Pass them via the `--cnv_pon_male`, `--cnv_pon_female`,
  `--cnv_loo_summary`, `--cnv_noisy_bins`, and `--cnv_noise_profile`
  parameters.

See `docs/usage_pon.md` for the full BUILD_PON walkthrough.
