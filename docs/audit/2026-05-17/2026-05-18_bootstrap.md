# 2026-05-18 — Next-Session Bootstrap

## Where we left off

End of 2026-05-17: five commits shipped across both repos (see `end_of_day_summary.md` in the same directory). Dashboard validated on 25NGS1307. Output: mean coverage **2,994×**, 5 low-coverage exons listed, 64.7%/35.3% selected/off-bait. Self-contained 200 KB HTML at `<outdir>/<sample>/dashboard/<sample>_dashboard.html`.

## Today's opener — ORGANIZE_OUTPUT module

User-selected priority. Two layers of mess to fix:

### Layer 1 — within `<outdir>/<sample>/`

Pipeline scratch (`bqsr/`, `markdup/`, `mosdepth/`, `trimmed/`, `aligned/`) publishes alongside real deliverables. Clinical team has to navigate noise to find the real outputs.

**Approach:** port production's `scripts/20_organize_output.py` as a new Nextflow process `ORGANIZE_OUTPUT` that runs after all other phases complete. It builds a `<outdir>/<sample>/clinical/` subdirectory containing only the deliverables, mirroring production's `{sample}_analysis/` layout.

**Key design decision:** production's script uses filesystem globs (looks in `sample_dir/abra2/`, etc.). The port version should take **explicit channel inputs** instead so failures are loud (an upstream module renaming its output breaks the channel join, vs silently missing a file). The trade-off is verbosity in the wiring; it's worth it for clinical reliability.

**Inputs the module needs (all keyed on `meta.id`):**

| Source channel | Files | Where they go in `clinical/` |
|---|---|---|
| `ABRA2.out.bam` | `{sample}.final.bam` + `.bai` | top-level (single copy, see below) |
| `ANNOTATION.out.clinical_final_tsv` | `{sample}.somaticseq.clinical.final.tsv` (with multi-name fallback per production lines 149–174) | top-level |
| `ANNOTATION.out.filtered_tsv` | `{sample}.somaticseq.filtered.tsv` | top-level |
| `ANNOTATION.out.u2af1_report` | `{sample}_u2af1_pileup_report.txt` | top-level (when present) |
| `ANNOTATION.out.u2af1_rescue` | `{sample}_u2af1_rescue.tsv` (when present + >100 bytes) | top-level |
| `ANNOTATION.out.igv_report` | `{sample}_igv_report.html` | top-level (when present) |
| `FLT3_CONSENSUS.out.tsv` | `{sample}_flt3_consensus.tsv` | top-level (headline FLT3 result) |
| `FLT3_ITD_EXT.out.vcf` + summary | `{sample}.final_FLT3_ITD.vcf`, `{sample}.final_FLT3_ITD_summary.txt` | `flt3_itd/` |
| `FILT3R.out.vcf` + `.json` | `{sample}_filt3r.results.{vcf,json}` | `flt3_itd/` |
| `GETITD.out.tree` | per-tool tree | `flt3_itd/getitd/` (excluding `out_needle` files; verbose) |
| `PINDEL_FLT3.out.vcf` | `pindel_flt3.vcf` | `flt3_itd/` (when present) |
| `HSMETRICS.out.metrics` | `{sample}_hsmetrics.txt` | top-level |
| `PARSE_EXON_COVERAGE.out.tsv` | `{sample}_exon_coverage.tsv` | top-level |
| `FASTP.out.html` | `{sample}_fastp.html` | top-level |
| `SAMPLE_DASHBOARD.out.html` | `{sample}_dashboard.html` *(NEW vs production)* | top-level |
| `CNV_CONSENSUS.out.dir` | full subdir, **excluding `clinical_report.txt`** (verbose text; the TSV is the real artifact) | `cnv_consensus/` |
| `CNVKIT_PLOTS.out.dir` | `{sample}.final-diagram.pdf`, `{sample}.final-scatter.png`, and the four plot subdirs (`combined`, `overview`, `per_chromosome`, `per_gene`) | `cnvkit_plots/` |

**NOT applicable to this pipeline (omit from the port):**
- SV calls (delly, gridss, lumpy, manta, svaba) — this pipeline doesn't run SV callers; production does but we don't port that
- SV annotation — same reason
- `sv_calls/`, `sv_annotation/` subdirs in production's script — skip entirely

**Disposition of intermediate scratch (the real reason ORGANIZE_OUTPUT matters):**

Steady-state clinical operation should keep ONLY `clinical/` per sample. The other 11 subdirs (`bqsr/`, `markdup/`, `mosdepth/`, `trimmed/`, `aligned/`, `cnv/zscore/`, `cnv/concordance/`, `cnv/annotated/`, `somaticseq/<sample>.somaticseq_workdir/`, `variant_callers/{deepsomatic,freebayes,mutect2,pindel,platypus,strelka,u2af1_rescue,vardict,varscan}/`, `flt3/` raw inputs) are pipeline scratch and should be **deleted** once ORGANIZE_OUTPUT completes successfully.

Today I wrote "keep them for debugging" — that was wrong for a clinical pipeline at steady state. The whole point of organizing outputs is so the next 100 runs don't each leave 1+ GB of intermediates behind. Debug from `work/` when you need to.

Per-sample current state is 6.3 GB, of which ~5 GB is the BAM (deliverable) and ~1.3 GB is scratch + duplicated metadata.

**The doubled-BAM problem:** the BAM is currently published to `abra2/`. If ORGANIZE_OUTPUT naively `cp`s it to `clinical/`, that's two physical 5 GB copies per sample. The fix:

1. **Hardlink, don't copy** — `cp -l` or `ln` for files on the same filesystem. Same inode, single physical block of data, two paths. The xfs filesystem (confirmed from `nextflow.log: Work-dir: /goast/hemat_data/nf-core-tspipe/work [xfs]`) supports hardlinks.
2. **Then delete** the source path (`abra2/<sample>.final.bam`). The inode survives because `clinical/<sample>.final.bam` still references it.

This pattern works for every file deliverable, not just the BAM, so the whole `clinical/` is hardlinks of the original publishDir locations, and the cleanup step then removes those original locations leaving just the `clinical/` references.

**Cleanup step pattern:**

```bash
# Inside ORGANIZE_OUTPUT script block, after all hardlinks succeed
# and pass file-exists verification:
if [[ "${params.keep_intermediates}" != "true" ]]; then
    for d in bqsr markdup mosdepth trimmed aligned \
             cnv/zscore cnv/concordance cnv/annotated \
             somaticseq/${meta.id}.somaticseq_workdir \
             variant_callers \
             flt3/flt3_itd_ext flt3/filt3r flt3/getitd \
             abra2 hsmetrics exon_coverage dashboard annotation; do
        rm -rf "${params.outdir}/${meta.id}/${d}"
    done
fi
```

`params.keep_intermediates` defaults to `false`. Validation runs can opt out with `--keep_intermediates true`. The dashboard, annotation, hsmetrics, exon_coverage, abra2 subdirs ARE in the cleanup list because we've hardlinked their contents into `clinical/` already.

**End state per sample:**

```
<outdir>/<sample>/
├── clinical/                    ← everything clinicians need
│   ├── <sample>.final.bam
│   ├── <sample>.final.bam.bai
│   ├── <sample>.somaticseq.clinical.final.tsv
│   ├── <sample>.somaticseq.filtered.tsv
│   ├── <sample>_flt3_consensus.tsv
│   ├── <sample>_exon_coverage.tsv
│   ├── <sample>_hsmetrics.txt
│   ├── <sample>_dashboard.html
│   ├── <sample>_fastp.html
│   ├── <sample>_igv_report.html         (when present)
│   ├── <sample>_u2af1_pileup_report.txt
│   ├── cnv_consensus/
│   ├── cnvkit_plots/
│   └── flt3_itd/
└── pipeline_info/                       ← nf-core trace/timeline; keep
```

Disk per sample: ~5 GB (single BAM, hardlinked). No doubled BAM, no scratch dirs. Down from ~6.3 GB today.

**Suggested module signature (sketch):**

```nextflow
process ORGANIZE_OUTPUT {
    tag        "${meta.id}"
    label      'process_low'
    container  'docker://broadinstitute/gatk:4.5.0.0'   // python3 + stdlib only
    publishDir "${params.outdir}/${meta.id}", mode: 'copy'

    input:
        tuple val(meta),
              path(bam), path(bai),
              path(clinical_tsv),
              path(filtered_tsv),
              path(flt3_consensus),
              path(exon_coverage),
              path(hsmetrics),
              path(dashboard),
              path(fastp_html),
              path(igv_report,         stageAs: "optional_igv_report.html")
              path(u2af1_report,       stageAs: "optional_u2af1_report.txt")
              path(u2af1_rescue,       stageAs: "optional_u2af1_rescue.tsv")
              // ... directory inputs for CNV consensus, CNV plots, FLT3 per-tool
        val keep_intermediates  // params.keep_intermediates, default false

    output:
        tuple val(meta), path("clinical/"), emit: clinical
        path "versions.yml",                emit: versions

    script:
        // Note: 'mode: hardlink' for the script's own copies is not a thing in
        // bash; we use `ln` directly. publishDir's mode (above) is 'copy' for
        // the resulting clinical/ tree, which is correct — Nextflow's own work
        // dir contains hardlinks that get materialized once into the publishDir.
        """
        organize_output.py \\
            --sample            ${meta.id} \\
            --outdir            "${params.outdir}/${meta.id}" \\
            --bam               ${bam} \\
            --bai               ${bai} \\
            --clinical-tsv      ${clinical_tsv} \\
            --filtered-tsv      ${filtered_tsv} \\
            --flt3-consensus    ${flt3_consensus} \\
            --exon-coverage     ${exon_coverage} \\
            --hsmetrics         ${hsmetrics} \\
            --dashboard         ${dashboard} \\
            --fastp-html        ${fastp_html} \\
            --igv-report        ${igv_report} \\
            --u2af1-report      ${u2af1_report} \\
            --u2af1-rescue      ${u2af1_rescue} \\
            ${keep_intermediates ? '--keep-intermediates' : ''}

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            python: \$(python3 --version 2>&1 | awk '{print \$2}')
        END_VERSIONS
        """
}
```

The `bin/organize_output.py` is a thin Python script (stdlib only — `shutil`, `pathlib`, `os`, `argparse`) that:

1. Creates `<outdir>/<sample>/clinical/` and its required subdirs.
2. Hardlinks each input file into the corresponding `clinical/` location (`os.link(src, dest)`).
3. Verifies each hardlink resolves to the expected file (`stat().st_ino == src.stat().st_ino` per link).
4. If `--keep-intermediates` is NOT set: deletes the 11 scratch subdirs listed earlier.
5. Prints a summary: total files in `clinical/`, total size on disk (use `os.lstat().st_size` and de-dup by inode so hardlinks aren't double-counted).

~150 lines. The "explicit args instead of filesystem discovery" is the major divergence from production's `20_organize_output.py`; mostly it's the same idiom of `safe_copy` + per-deliverable handling.

### Layer 2 — `nfcore_runs/` parent dir proliferation

17+ dated run directories from a single day's experimentation. Nextflow doesn't manage retention.

**Approach:**

1. **Cleanup the existing garbage** with a script (one-liner today; can be in `tools/`):
   ```bash
   # Keep only the latest validated run, delete the rest
   cd /goast/hemat_data/nfcore_runs
   KEEP=25NGS1307_dashboard_20260517_191849
   for d in 25NGS1307_*/; do
       d=${d%/}
       [[ "$d" == "$KEEP" ]] && continue
       echo "rm -rf $d"
   done
   # Add `| sh` after review to actually delete
   ```

2. **Adopt a stable run-naming convention** so this doesn't recur:
   ```bash
   # For ongoing validation:
   --outdir /goast/hemat_data/nfcore_runs/<sample>/latest    # gets clobbered each run

   # For preserving a milestone:
   --outdir /goast/hemat_data/nfcore_runs/<sample>/v_2026-05-17_dashboard
   ```

3. **Optionally add a `tools/clean_runs.py`** that lists run dirs older than N days, shows their size, and deletes on `--apply` with a `--keep <pattern>` exclusion. Same authoring discipline as other patches (dry-run default).

## Carry-forward backlog (after ORGANIZE_OUTPUT)

In rough priority order:

### Real correctness items

- **B1: Per-caller VCF discrepancy** — 3 variants on 25NGS1307 missing one caller's vote each between port and production. Likely a `BCFTOOLS_NORM` / filter chain difference.
- **B2: 69-entry annotated-tier port-only residual** — port produces 69 variants production filters out. Diagnose whether benign (different thresholds) or over-permissive.
- **B3: Phase 1 stub verification** — `VARIANT_VALIDATOR`, `ONCOVI`, `FLT3_TO_VARIANTS` may still be stub-only. Confirm each is real or fill in.
- **B4: KMT2A-PTD not yet detected** on 25NGS1307. Pindel + GRIDSS handling needs review.
- **B5: Rescue_Note column** missing in annotated TSV (production has it).

### Cosmetic polish (batch as one patch when ready)

- **C1: Oddball exon labels** — `ANKRD26_Ex_5'UTR`, `NOTCH1_Ex_3'UTR`, `NPM1_Ex_intr_10_part`. Extend regex in `bin/parse_exon_coverage.py`:
  ```python
  m = re.match(r"^(.+?)_[Ee][Xx]_?(\d+[A-Za-z]?|[35]'UTR|intr_\d+_part)$", label)
  ```
- **C2: Leading-zero strip** — `Ex_03` → `Ex_3` for consistency.
- **C3: `PTPN` shows truncated** — should be `PTPN11`. Make the gene-side regex greedy:
  ```python
  m = re.match(r"^(.+)_[Ee][Xx]_?(\d+[A-Za-z]?)$", label)  # greedy (.+) not (.+?)
  ```
- **C4: `params.panel_name` warning** — add `panel_name = "MYOPOOL hg38"` to `nextflow.config` params block.
- **C5: Picard `COVERAGE_CAP=200`** — bump to 100000 if you want the depth-related Picard fields back. Currently the dashboard sidesteps them, so optional.

## Operational details to keep handy

| Path | What |
|---|---|
| `/goast/hemat_data/nf-core-tspipe/` | nf-core port root |
| `/home/hemat/targeted-seq-pipeline/` | production root |
| `/tmp/cnv_wiring/validation_samplesheet.csv` | validation samplesheet (25NGS1307) |
| `/goast/hemat_data/nfcore_runs/25NGS1307_dashboard_20260517_191849/` | latest validated run output (the "keep" directory) |
| `/goast/hemat_data/targeted-seq-pipeline/bedfiles/MYOPOOL_240125_UBTF_Exonwise_hg38.bed` | 1,153-exon canonical BED (deployed today) |
| `/goast/hemat_data/targeted-seq-pipeline/bedfiles/MYOPOOL_240125_UBTF_IntronOnly_hg38.bed` | 10 CSF1R intron probes |
| `/home/hemat/targeted-seq-pipeline/scripts/20_organize_output.py` | reference implementation for ORGANIZE_OUTPUT (production) |
| `/home/hemat/targeted-seq-pipeline/scripts/10b_exon_coverage.py` | reference for the parse_exon_coverage port |

## Validation expectations on 25NGS1307 (so you know what "correct" looks like)

For ORGANIZE_OUTPUT, success criteria are mostly file-existence: every named file from the table above should exist in `clinical/`, and any optional ones not present in this sample's output should not cause the process to fail (use `optional: true` on those inputs in the module).

Coverage numbers should not change from today's run:
- Mean coverage: 2,994×
- Low-cov exons: 5 (MYB Ex_1, PHIP Ex_03, SF1 Ex_1, PTPN Ex_01, PRPF40B Ex_1)
- Selected / off-bait: 64.7% / 35.3%

If any of those values drift, something upstream changed inadvertently.
