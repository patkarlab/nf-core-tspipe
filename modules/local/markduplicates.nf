/*
 * modules/local/markduplicates.nf
 *
 * GATK4 MarkDuplicates. Mirrors scripts/03_mark_duplicates.py:
 *   gatk MarkDuplicates -I {input.bam} -O {sample}_markdups.bam -M {metrics}
 */

process PICARD_MARKDUPLICATES {
    tag        "${meta.id}"
    label      'process_medium'

    conda      'bioconda::gatk4=4.5.0.0'
    container  'broadinstitute/gatk:4.5.0.0'

    input:
        tuple val(meta), path(bam)

    output:
        tuple val(meta), path("${meta.id}_markdups.bam"), path("${meta.id}_markdups.bam.bai"), emit: bam
        path  "${meta.id}_markdup_metrics.txt",                                                  emit: metrics
        path  "versions.yml",                                                                    emit: versions

    script:
        def args = task.ext.args ?: ''
        def mem  = task.memory ? "-Xmx${task.memory.toGiga()}g" : ''
        """
        gatk --java-options "${mem}" MarkDuplicates \\
            -I ${bam} \\
            -O ${meta.id}_markdups.bam \\
            -M ${meta.id}_markdup_metrics.txt \\
            --CREATE_INDEX true \\
            ${args}

        # gatk creates a .bai alongside the .bam; align naming to .bam.bai
        if [ -f ${meta.id}_markdups.bai ]; then
            mv ${meta.id}_markdups.bai ${meta.id}_markdups.bam.bai
        fi

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            gatk4: \$(gatk --version 2>&1 | grep -oP '\\d+\\.\\d+\\.\\d+\\.\\d+' | head -n1)
        END_VERSIONS
        """
}
