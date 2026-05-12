/*
 * modules/local/mutect2.nf
 *
 * GATK4 Mutect2 in tumor-only mode with gnomAD germline resource.
 * One of seven somatic callers from scripts/06_variant_callers.py.
 *
 * The other six callers (VarDict, VarScan, Strelka, FreeBayes, Platypus,
 * DeepSomatic) follow the same module structure -- inputs: BAM+ref+bed,
 * outputs: tuple(meta, vcf). See scripts/06_variant_callers.py for the exact
 * command lines to wrap.
 */

process GATK4_MUTECT2 {
    tag        "${meta.id}"
    label      'process_medium'

    conda      'bioconda::gatk4=4.5.0.0'
    container  'broadinstitute/gatk:4.5.0.0'

    input:
        tuple val(meta), path(bam), path(bai)
        tuple path(fasta), path(fai), path(dict)
        path  bed

    output:
        tuple val(meta), path("${meta.id}.mutect2.vcf.gz"),     emit: vcf
        tuple val(meta), path("${meta.id}.mutect2.vcf.gz.tbi"), emit: tbi
        tuple val(meta), path("${meta.id}.mutect2.stats"),      emit: stats
        path  "versions.yml",                                    emit: versions

    script:
        def mem    = task.memory ? "-Xmx${task.memory.toGiga()}g" : ''
        def gnomad = params.gnomad_af_only
                       ? "--germline-resource ${params.gnomad_af_only}"
                       : ''
        """
        gatk --java-options "${mem}" Mutect2 \\
            -R ${fasta} \\
            -I ${bam} \\
            -L ${bed} \\
            ${gnomad} \\
            -O ${meta.id}.mutect2.vcf.gz

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            gatk4: \$(gatk --version 2>&1 | grep -oP '\\d+\\.\\d+\\.\\d+\\.\\d+' | head -n1)
        END_VERSIONS
        """
}
