#!/usr/bin/env nextflow
/*
 * nf-core-tspipe : Targeted-sequencing pipeline for leukemia / myeloid malignancies
 *
 * Two entry workflows:
 *
 *   1. TSPIPE    (default) -- per-sample analysis pipeline.
 *                Replaces scripts/run_sample_pipeline.py.
 *                Run with:   nextflow run main.nf --input samplesheet.csv ...
 *
 *   2. BUILD_PON           -- one-off resource builder. Takes a samplesheet
 *                of normal samples and produces the CNV PoN files that
 *                TSPIPE consumes (cnvkit_pon.cnn, loo_summary.tsv,
 *                loo_bin_noise_profile.tsv, etc.).
 *                Replaces scripts/run_masked_realign.sh + 12c_cnv_loo_qc.py
 *                + 12c_build_sex_pon.py.
 *                Run with:   nextflow run main.nf -entry BUILD_PON --input normals.csv ...
 */

nextflow.enable.dsl = 2

include { TSPIPE    } from './workflows/tspipe'
include { BUILD_PON } from './workflows/build_pon'

// Default entry: the per-sample pipeline.
// Run with:   nextflow run main.nf --input samplesheet.csv ...
workflow {
    TSPIPE()
}

// To run the PoN build instead:
//   nextflow run main.nf -entry BUILD_PON --input normals.csv ...
// (BUILD_PON is the named workflow imported above; Nextflow lets -entry select
//  any workflow visible at top level of main.nf.)


// ---------------------------------------------------------------------------
// Post-run hook: cleanup and disk sanity check
// ---------------------------------------------------------------------------
// Runs once after the full DAG finishes. Defense-in-depth scratch sweeper
// (clinical/ is the only thing that should remain under <outdir>/<sample>/)
// plus a filesystem-mismatch warning that catches the case where outdir
// landed on a different mount from work/ -- in which case publishDir
// mode 'link' silently degraded to copy and disk usage will be higher
// than designed. params.keep_intermediates=true skips the sweep.

workflow.onComplete {
    if (params.keep_intermediates) {
        log.info "params.keep_intermediates=true; preserving any scratch under ${params.outdir}/<sample>/"
        return
    }
    if (!workflow.success) {
        log.info "Pipeline did not complete successfully; preserving any scratch for debugging."
        return
    }

    def workDev = ['stat', '-c', '%d', workflow.workDir.toString()].execute().text.trim()
    def outRoot = file(params.outdir).exists() ? file(params.outdir) : file(params.outdir).parent
    def outDev  = ['stat', '-c', '%d', outRoot.toString()].execute().text.trim()
    if (workDev != outDev) {
        log.warn "workDir (${workflow.workDir}) and outdir (${params.outdir}) are on different filesystems (dev ${workDev} vs ${outDev}). publishDir mode 'link' silently fell back to copy; disk usage is higher than designed."
    }

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
