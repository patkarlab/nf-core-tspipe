/*
 * modules/local/bqsr.nf
 *
 * GATK4 BaseRecalibrator + ApplyBQSR.
 *
 * Known-sites VCFs (dbSNP138, Mills indels) come in as explicit inputs from
 * the subworkflow, sourced from params.dbsnp_vcf and params.mills_vcf in the
 * site config. This lets us point at different VCF locations on different
 * servers without editing the module.
 */

process GATK4_BQSR {
    tag        "${meta.id}"
    label      'process_medium'

    container  'broadinstitute/gatk:4.5.0.0'

    input:
        tuple val(meta), path(bam), path(bai)
        tuple path(fasta), path(fai), path(dict)
        tuple path(dbsnp_vcf), path(dbsnp_tbi)
        tuple path(mills_vcf), path(mills_tbi)

    output:
        tuple val(meta), path("${meta.id}_final.bam"), path("${meta.id}_final.bam.bai"), emit: bam
        path  "${meta.id}_recal.table",                                                    emit: table
        path  "versions.yml",                                                              emit: versions

    script:
        def mem = task.memory ? "-Xmx${task.memory.toGiga()}g" : ''
        """
        gatk --java-options "${mem}" BaseRecalibrator \\
            -I ${bam} \\
            -R ${fasta} \\
            --known-sites ${dbsnp_vcf} \\
            --known-sites ${mills_vcf} \\
            -O ${meta.id}_recal.table

        gatk --java-options "${mem}" ApplyBQSR \\
            -R ${fasta} \\
            -I ${bam} \\
            --bqsr-recal-file ${meta.id}_recal.table \\
            -O ${meta.id}_final.bam

        if [ -f ${meta.id}_final.bai ]; then
            mv ${meta.id}_final.bai ${meta.id}_final.bam.bai
        fi

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            gatk4: \$(gatk --version 2>&1 | grep -oP '\\d+\\.\\d+\\.\\d+\\.\\d+' | head -n1)
        END_VERSIONS
        """
}
