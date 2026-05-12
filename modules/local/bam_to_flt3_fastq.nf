/*
 * modules/local/bam_to_flt3_fastq.nf
 *
 * Extract FLT3-region paired FASTQs from a BAM. Mirrors scripts/bam_to_flt3_fastq.py:
 *   samtools view -b -@ T bam chr13:28,034,000-28,036,000 |
 *     samtools sort -n -@ T -O bam - |
 *     samtools fastq -@ T -1 R1 -2 R2 -s singletons -0 /dev/null -n -
 */

process BAM_TO_FLT3_FASTQ {
    tag        "${meta.id}"
    label      'process_low'

    conda      'bioconda::samtools=1.18'
    container  'quay.io/biocontainers/samtools:1.18--h50ea8bc_1'

    input:
        tuple val(meta), path(bam), path(bai)

    output:
        tuple val(meta), path("${meta.id}_flt3_R1.fastq.gz"), path("${meta.id}_flt3_R2.fastq.gz"), emit: reads

    script:
        // chr13:28,034,000-28,036,000 hg38 (covers FLT3 exons 13-15 with margin)
        def region = task.ext.flt3_region ?: 'chr13:28033000-28036000'
        """
        samtools view -b -@ ${task.cpus} ${bam} ${region} \\
          | samtools sort -n -@ ${task.cpus} -O bam - \\
          | samtools fastq -@ ${task.cpus} \\
                -1 ${meta.id}_flt3_R1.fastq.gz \\
                -2 ${meta.id}_flt3_R2.fastq.gz \\
                -s ${meta.id}_flt3_singletons.fastq.gz \\
                -0 /dev/null -n -

        # Fail fast if region had no reads
        if [ ! -s ${meta.id}_flt3_R1.fastq.gz ] || [ ! -s ${meta.id}_flt3_R2.fastq.gz ]; then
            echo "ERROR: empty FLT3 FASTQ for ${meta.id}" >&2
            exit 1
        fi
        """
}
