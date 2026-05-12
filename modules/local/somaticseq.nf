/*
 * modules/local/somaticseq.nf
 *
 * SomaticSeq ensemble merge. Replaces scripts/07_somaticseq.py.
 *
 * Combines outputs from the seven somatic callers into a consensus VCF.
 * SomaticSeq runs as: somaticseq_parallel.py paired -tumor BAM ... <per-caller VCFs>
 */

process SOMATICSEQ_ENSEMBLE {
    tag        "${meta.id}"
    label      'process_high'

    conda      'bioconda::somaticseq=3.7.4'
    container  'lethalfang/somaticseq:3.7.4'

    input:
        tuple val(meta), path(mutect2_vcf), path(vardict_vcf), path(varscan_vcf), path(strelka_vcf), path(freebayes_vcf), path(platypus_vcf), path(deepsomatic_vcf)
        tuple val(_meta2), path(bam), path(bai)
        tuple path(fasta), path(fai), path(dict)
        path  bed

    output:
        tuple val(meta), path("${meta.id}.somaticseq.vcf"), emit: vcf
        path  "somaticseq_workdir/Consensus.s*.vcf",         emit: caller_consensus
        path  "versions.yml",                                emit: versions

    script:
        """
        somaticseq_parallel.py \\
            --output-directory somaticseq_workdir \\
            --genome-reference ${fasta} \\
            --inclusion-region ${bed} \\
            --threads ${task.cpus} \\
            single \\
              --bam-file        ${bam} \\
              --mutect2-vcf     ${mutect2_vcf} \\
              --vardict-vcf     ${vardict_vcf} \\
              --varscan-vcf     ${varscan_vcf} \\
              --strelka-vcf     ${strelka_vcf} \\
              --vcf-format

        cp somaticseq_workdir/Consensus.sSNV.vcf ${meta.id}.somaticseq.snv.vcf
        cp somaticseq_workdir/Consensus.sINDEL.vcf ${meta.id}.somaticseq.indel.vcf

        # concat SNV+INDEL
        cat ${meta.id}.somaticseq.snv.vcf | grep '^#'  >  ${meta.id}.somaticseq.vcf
        cat ${meta.id}.somaticseq.snv.vcf | grep -v '^#' >> ${meta.id}.somaticseq.vcf
        cat ${meta.id}.somaticseq.indel.vcf | grep -v '^#' >> ${meta.id}.somaticseq.vcf

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            somaticseq: \$(somaticseq_parallel.py --version 2>&1 | sed 's/.*v//')
        END_VERSIONS
        """
}
