# Output

Per-sample layout under `${params.outdir}/{sample}/`:

```
results/{sample}/
├── trimmed/                  # fastp output + JSON/HTML reports
├── aligned/                  # BWA + samtools sort BAM
├── markdup/                  # MarkDuplicates BAM + metrics
├── bqsr/                     # BQSR-recalibrated BAM + recal table
├── abra2/                    # Final indel-realigned BAM
│
├── variant_callers/
│   ├── mutect2/
│   ├── vardict/
│   ├── varscan/
│   ├── strelka/
│   ├── freebayes/
│   ├── platypus/
│   └── deepsomatic/
├── somaticseq/               # Ensemble consensus VCF
├── pindel/                   # Pindel VCF for indels
│
├── flt3/                     # FLT3-ITD 4-tool ensemble
│   ├── flt3_itd_ext/         # FLT3_ITD_EXT outputs
│   ├── filt3r/               # filt3r JSON + VCF
│   ├── getitd/               # getITD output dir
│   ├── pindel_flt3.vcf       # Pindel subset for FLT3 region
│   └── {sample}_flt3_consensus.tsv   # Final consensus call
│
├── cnv/
│   ├── cnvkit/
│   ├── exon_cnv/
│   ├── zscore_cnv/
│   ├── concordance/          # Per-gene merged calls
│   └── clinical_report.tsv
│
├── sv/                       # Manta/Delly/SvABA outputs + AnnotSV
│
├── annotation/
│   ├── {sample}.vep.tsv      # VEP + ANNOVAR
│   ├── {sample}.filtered.tsv # All variants with FILTER column populated
│   ├── {sample}.clinical.tsv # FILTER == PASS only
│   ├── {sample}.validated.tsv# After VariantValidator HGVS check
│   ├── {sample}.oncovi.tsv   # OncoVI oncogenicity scores
│   └── {sample}.final.tsv    # Includes FLT3 ITD rows + Confirmed_by_FLT3_ITD_ensemble tags
│
├── qc/
│   ├── hsmetrics.txt
│   └── exon_coverage.tsv
│
└── deliverables/             # Bundle for clinical sign-out (organize_output.py)
    ├── variants.tsv
    ├── cnv_report.tsv
    ├── sv_report.tsv
    ├── flt3_itd/
    └── igv_reports.html
```

Plus a top-level `pipeline_info/` directory with Nextflow's execution
report, timeline, trace, and DAG.
