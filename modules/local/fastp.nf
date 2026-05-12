/*
 * modules/local/fastp.nf
 *
 * Adapter trimming with fastp. Mirrors scripts/01_trim_adapters.py:
 *   fastp -i R1 -I R2 -o {sample}_trim_R1.fastq -O {sample}_trim_R2.fastq \
 *         --adapter_fasta {adapters} -w {threads} -h {html} -j {json}
 */

process FASTP {
    tag        "${meta.id}"
    label      'process_low'

    conda      'bioconda::fastp=0.23.4'
    container  'quay.io/biocontainers/fastp:0.23.4--h5f740d0_0'

    input:
        tuple val(meta), path(reads1), path(reads2)

    output:
        tuple val(meta), path("*_trim_R1.fastq.gz"), path("*_trim_R2.fastq.gz"), emit: reads
        path  "*.html",                                                          emit: html
        path  "*.json",                                                          emit: json
        path  "versions.yml",                                                    emit: versions

    script:
        def args  = task.ext.args ?: ''
        def adapt = params.adapters ? "--adapter_fasta ${params.adapters}" : ''
        """
        fastp \\
            -i ${reads1} \\
            -I ${reads2} \\
            -o ${meta.id}_trim_R1.fastq.gz \\
            -O ${meta.id}_trim_R2.fastq.gz \\
            ${adapt} \\
            -w ${task.cpus} \\
            -h ${meta.id}_fastp.html \\
            -j ${meta.id}_fastp.json \\
            ${args}

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            fastp: \$(fastp --version 2>&1 | sed 's/fastp //')
        END_VERSIONS
        """
}
