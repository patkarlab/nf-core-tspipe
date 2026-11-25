/*
 * tests/baf/cnv_baf_cnloh_module.nf -- runs the CNV_BAF_CNLOH module itself (its real script
 * block, not the stub) on one sample. Started by tests/baf/run_module_test.sh, which makes the
 * synthetic inputs; not meant to be launched by hand.
 */
nextflow.enable.dsl = 2

include { CNV_BAF_CNLOH } from '../../modules/local/cnv_baf_cnloh'

workflow {
    ch_in = Channel.of( [ [ id: params.sample, sex: 'female' ],
                          file(params.allelic,  checkIfExists: true),
                          file(params.denoised, checkIfExists: true) ] )
    CNV_BAF_CNLOH( ch_in,
                   file(params.snp_bed,    checkIfExists: true),
                   file(params.background, checkIfExists: true) )
    CNV_BAF_CNLOH.out.summary.view { meta, f -> "[module] ${meta.id} summary: ${f}" }
}
