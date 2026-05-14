/*
 * modules/local/u2af1_rescue.nf
 *
 * Pileup-based rescue for U2AF1 hotspot mutations in GRCh38.
 *
 * U2AF1 has a 153 kb paralog at chr21p (chr21:6427259-6580181) added in
 * GRCh38. Even after masking, standard variant callers filter out the
 * remaining MQ=0 reads at the canonical locus and miss somatic U2AF1
 * variants (S34F, S34Y, Q157P) - critical drivers in MDS/AML.
 *
 * This module calls bin/u2af1_rescue.py which does pileup at the three
 * hotspots WITH include_mq0=True, bypassing MAPQ filters.
 *
 * Reference: Miller CA et al. J Mol Diagn 2022;24(3):219-223. PMID 35041928.
 */

process U2AF1_RESCUE {
    tag        "${meta.id}"
    label      'process_low'

    conda      'bioconda::pysam=0.22.0'

    input:
        tuple val(meta), path(bam), path(bai)

    output:
        tuple val(meta), path("${meta.id}_u2af1_rescue.tsv"),        emit: tsv
        tuple val(meta), path("${meta.id}_u2af1_pileup_report.txt"), emit: report
    stub:
        // nf-core stub blocks v1 (apply_nfcore_add_stub_blocks)
        """
        touch ${meta.id}_u2af1_rescue.tsv ${meta.id}_u2af1_pileup_report.txt
        """


    script:
        def min_vaf   = task.ext.min_vaf   ?: '0.01'
        def min_alt   = task.ext.min_alt   ?: '3'
        def min_depth = task.ext.min_depth ?: '20'
        """
        u2af1_rescue.py \\
            --bam ${bam} \\
            --sample ${meta.id} \\
            --outdir . \\
            --min-vaf ${min_vaf} \\
            --min-alt-count ${min_alt} \\
            --min-depth ${min_depth} \\
            --check-paralog
        """
}
