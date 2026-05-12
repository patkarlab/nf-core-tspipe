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
