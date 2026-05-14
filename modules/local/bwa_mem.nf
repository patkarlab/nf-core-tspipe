/*
 * modules/local/bwa_mem.nf
 *
 * BWA-MEM2 alignment, piped to samtools sort. The original pipeline used
 * bwa-mem2 (its FASTA index is in .bwt.2bit.64 + .0123 format, not classic).
 *
 * Inputs:
 *   - paired reads
 *   - reference FASTA + .fai + .dict
 *   - the BWA-mem2 index files (.amb .ann .pac .bwt.2bit.64 .0123) staged
 *     alongside the FASTA so bwa-mem2 finds them.
 */

process BWA_MEM {
    tag        "${meta.id}"
    label      'process_medium'

    input:
        tuple val(meta), path(reads1), path(reads2)
        tuple path(fasta), path(fai), path(dict)
        path  bwa_index

    output:
        tuple val(meta), path("${meta.id}.bam"), emit: bam
        path  "versions.yml",                    emit: versions
    stub:
        // nf-core stub blocks v1 (apply_nfcore_add_stub_blocks)
        """
        touch ${meta.id}.bam versions.yml
        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            stub: true
        END_VERSIONS
        """


    script:
        def args = task.ext.args ?: ''
        """
        bwa-mem2 mem \\
            ${args} \\
            -t ${task.cpus} \\
            -R "@RG\\tID:${meta.id}\\tPL:ILLUMINA\\tLB:HC\\tSM:${meta.id}\\tPI:200" \\
            ${fasta} \\
            ${reads1} ${reads2} \\
          | samtools sort -@ ${task.cpus} -o ${meta.id}.bam -

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            bwa-mem2: \$(bwa-mem2 version 2>&1 | head -n1)
            samtools: \$(samtools --version | head -n1 | sed 's/samtools //')
        END_VERSIONS
        """
}
