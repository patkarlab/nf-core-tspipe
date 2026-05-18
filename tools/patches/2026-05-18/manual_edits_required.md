# Manual edits required after running both apply scripts

Two integration points are not auto-edited because the script can't
safely guess what already exists at those sites.

This file reflects the Option 2 (slim clinical/) decision -- FLT3
per-tool VCFs and getitd tree are NOT published; consensus TSV only.

## 1. workflows/tspipe.nf -- ORGANIZE_OUTPUT wiring

At the top of the file with the other includes, add:

```groovy
include { ORGANIZE_OUTPUT } from '../modules/local/organize_output'
```

Inside the `workflow TSPIPE { ... }` body, AFTER the ANNOTATION call
and BEFORE the closing brace, add:

```groovy
// ----- 7. ORGANIZE_OUTPUT: build clinical/ deliverable tree ---------
ch_organize = PREPROCESSING.out.final_bam                                // tuple(meta, bam, bai)
    .join(ANNOTATION.out.clinical_tsv)                                   // + clinical_tsv
    .join(ANNOTATION.out.filtered_tsv)                                   // + filtered_tsv (new emit, part 1)
    .join(VARIANT_CALLING.out.u2af1_report,  remainder: true)            // + u2af1_report (new emit, part 1) [may be null]
    .join(VARIANT_CALLING.out.u2af1_tsv,     remainder: true)            // + u2af1_rescue [may be null]
    .join(FLT3_ITD.out.consensus_tsv)                                    // + flt3_consensus
    .join(PREPROCESSING.out.hsmetrics)                                   // + hsmetrics
    .join(PREPROCESSING.out.exon_coverage)                               // + exon_coverage
    .join(PREPROCESSING.out.fastp_html)                                  // + fastp_html (new emit, part 2)
    .join(PREPROCESSING.out.dashboard)                                   // + dashboard
    .join(CNV_CALLING.out.clinical_report)                               // + cnv_clinical_tsv
    .join(CNV_CALLING.out.cnvkit_diagram_pdf)                            // + cnvkit_diagram (new emit, part 2)
    .join(CNV_CALLING.out.cnvkit_scatter_png)                            // + cnvkit_scatter (new emit, part 2)
    .join(CNV_CALLING.out.plots_dir)                                     // + cnvkit_plots_dir

ORGANIZE_OUTPUT(ch_organize)
```

You can also delete the commented-out `REPORTING(...)` stub block at
the bottom of the workflow body -- it was placeholder for this exact
work and is no longer needed.

Caveats:

- `remainder: true` keeps the row when the channel emitted nothing
  for a sample. The `stageAs: 'NO_FILE_*'` directives in the
  module input block materialize a placeholder filename for those
  nulls; `bin/organize_output.py` skips inputs whose name starts
  with `NO_FILE_`.
- If any non-optional join silently drops a sample (channel mismatch
  on meta), ORGANIZE_OUTPUT just won't run for that sample. If you
  prefer fail-loud, swap each `.join(X)` for
  `.join(X, failOnMismatch: true)`.

## 2. main.nf -- workflow.onComplete cleanup hook

Append to the end of main.nf (there is no existing onComplete block;
this is a fresh add):

```groovy
workflow.onComplete {
    if (params.keep_intermediates) {
        log.info "params.keep_intermediates=true; preserving any scratch under ${params.outdir}/<sample>/"
        return
    }
    if (!workflow.success) {
        log.info "Pipeline did not complete successfully; preserving any scratch for debugging."
        return
    }

    // Filesystem-mismatch sanity check: if work/ and outdir are on
    // different mounts, publishDir mode 'link' silently degraded to copy.
    def workDev = ['stat', '-c', '%d', workflow.workDir.toString()].execute().text.trim()
    def outRoot = file(params.outdir).exists() ? file(params.outdir) : file(params.outdir).parent
    def outDev  = ['stat', '-c', '%d', outRoot.toString()].execute().text.trim()
    if (workDev != outDev) {
        log.warn "workDir (${workflow.workDir}) and outdir (${params.outdir}) are on different filesystems (dev ${workDev} vs ${outDev}). publishDir mode 'link' silently fell back to copy; disk usage is higher than designed."
    }

    // Per-sample scratch cleanup. In the current state of this pipeline
    // only sample_dashboard.nf has a publishDir directive, so this is
    // mostly defense-in-depth -- if anyone adds publishDir to another
    // module later, the cleanup catches it. clinical/ inodes survive
    // via their own hardlinks.
    def scratchSubdirs = [
        'bqsr', 'markdup', 'mosdepth', 'trimmed', 'aligned',
        'cnv/zscore', 'cnv/concordance', 'cnv/annotated', 'cnv',
        'variant_callers', 'flt3', 'abra2',
        'hsmetrics', 'exon_coverage', 'dashboard', 'annotation',
        'cnv_consensus', 'cnvkit', 'somaticseq',
    ]
    def outDir = file(params.outdir)
    if (!outDir.exists()) return
    outDir.eachFile { sampleDir ->
        if (!sampleDir.isDirectory()) return
        if (sampleDir.name == 'pipeline_info') return
        if (sampleDir.name == 'default') return
        scratchSubdirs.each { sub ->
            def target = new File(sampleDir.toString(), sub)
            if (target.exists()) target.deleteDir()
        }
    }
    log.info "Cleanup complete. Final per-sample layout: <outdir>/<sample>/clinical/"
}
```

## After both manual edits land

1. Stub-mode DAG validation:
   ```
   nextflow run . -profile test,singularity \
     --input  /tmp/cnv_wiring/validation_samplesheet.csv \
     --outdir /tmp/organize_test \
     -stub
   ```
2. Real run on 25NGS1307; confirm clinical/ tree matches the layout
   described in docs/audit/2026-05-18/SESSION_NOTES_addendum_option2.md.
3. `du -shL /goast/hemat_data/nfcore_runs/<run>/25NGS1307` -- expect ~5 GB.
4. Inspect that the only scratch left under each sample dir is
   pipeline_info/, with clinical/ being the rest.
