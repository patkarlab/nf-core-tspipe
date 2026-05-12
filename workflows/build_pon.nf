/*
 * workflows/build_pon.nf
 *
 * PoN-build workflow. Takes a samplesheet of normal samples (FASTQs or BAMs)
 * and produces the CNV resources that the main per-sample pipeline consumes:
 *
 *     - cnvkit_pon.cnn              (combined PoN reference)
 *     - cnvkit_pon_male.cnn         (sex-matched PoNs)
 *     - cnvkit_pon_female.cnn
 *     - loo_summary.tsv             (per-normal LOO QC summary)
 *     - loo_bin_noise_profile.tsv   (per-bin mean/stdev log2)
 *     - cnvkit_noisy_bins.bed       (bins called CNV in >10% of normals)
 *     - cnvkit_pon_sex_assignment.tsv
 *
 * Replaces the chain in assets/training/:
 *     run_masked_realign.sh        + run_masked_realign_cnv_negatives.sh
 *  -> run_batch_preprocessing.py   (now native Nextflow channels)
 *  -> cnvkit.py batch (PoN-build)
 *  -> 12c_cnv_loo_qc.py
 *  -> 12c_build_sex_pon.py
 *
 * Entry point:
 *     nextflow run main.nf -entry BUILD_PON --input normals.csv ...
 *
 * The PREPROCESSING subworkflow is the same one the main pipeline uses --
 * normals go through fastp -> BWA -> markdup -> BQSR -> ABRA2 just like
 * tumor samples.
 */

include { PREPROCESSING     } from '../subworkflows/local/preprocessing'
include { CNVKIT_PON_BUILD  } from '../modules/local/cnvkit_pon_build'
include { CNV_LOO_QC        } from '../modules/local/cnv_loo_qc'
include { BUILD_SEX_PON     } from '../modules/local/build_sex_pon'

workflow BUILD_PON {

    // ----- Validate -----------------------------------------------------
    if (!params.input)     { error "Missing --input (samplesheet of normals)"   }
    if (!params.reference) { error "Missing --reference (hg38 masked FASTA)"    }
    if (!params.bed)       { error "Missing --bed (panel BED)"                  }

    // ----- Channels -----------------------------------------------------
    ch_reference = Channel.value([
        file(params.reference, checkIfExists: true),
        file(params.reference + '.fai', checkIfExists: true),
        file(params.reference.replaceFirst(/\.fa(sta)?$/, '.dict'), checkIfExists: true)
    ])
    ch_bed       = Channel.fromPath(params.bed, checkIfExists: true)

    // Parse the normals samplesheet -- same schema as the main pipeline.
    // Samples flagged as exclude=true (e.g. OCIAML3) get filtered out before
    // they reach CNVKIT_PON_BUILD, so they're never part of the PoN.
    ch_normals = Channel.fromPath(params.input, checkIfExists: true)
        .splitCsv(header: true)
        .filter { row -> (row.exclude ?: 'false').toLowerCase() != 'true' }
        .map { row ->
            def meta = [
                id:  row.sample,
                sex: row.sex ?: 'unknown'
            ]
            [ meta,
              file(row.fastq_1, checkIfExists: true),
              file(row.fastq_2, checkIfExists: true) ]
        }

    // ----- 1. Preprocess every normal in parallel ------------------------
    PREPROCESSING(ch_normals, ch_reference, ch_bed)

    // PREPROCESSING.out.final_bam = [meta, bam, bai] per sample
    // We want one big channel of files (BAMs and indices flattened) for the
    // PoN build, which calls cnvkit.py batch with --normal <bam1> <bam2> ...
    ch_all_bams = PREPROCESSING.out.final_bam
        .map { meta, bam, bai -> [bam, bai] }
        .flatten()
        .collect()

    // ----- 2. CNVKit batch in PoN-build mode -----------------------------
    CNVKIT_PON_BUILD(ch_all_bams, ch_reference, ch_bed)

    // ----- 3. Leave-one-out QC -------------------------------------------
    CNV_LOO_QC(CNVKIT_PON_BUILD.out.build_dir, ch_bed)

    // ----- 4. Sex-matched PoNs -------------------------------------------
    BUILD_SEX_PON(
        CNVKIT_PON_BUILD.out.build_dir,
        CNV_LOO_QC.out.iterations
    )

    // ----- 5. Publish outputs --------------------------------------------
    // publishDir on each process (see conf/modules.config) already copies
    // outputs into ${params.outdir}/. The user then points the main pipeline's
    // params.cnv_pon, params.cnv_loo_summary, params.cnv_noise_profile,
    // params.cnv_noisy_bins at those files.
}
