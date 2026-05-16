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
    stub:
        // nf-core stub blocks v1 (apply_nfcore_add_stub_blocks)
        """
        touch ${meta.id}_flt3_R1.fastq.gz ${meta.id}_flt3_R2.fastq.gz
        """


    script:
        // chr13:28,003,000-28,101,000 hg38 (entire FLT3 gene body plus margin)
        def region = task.ext.flt3_region ?: 'chr13:28003000-28101000'
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
