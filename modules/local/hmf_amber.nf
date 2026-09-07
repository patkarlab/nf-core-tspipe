/*
 * modules/local/hmf_amber.nf  (HMF_PURPLE_V1)
 *
 * AMBER tumour-only in panel mode: BAF at the HMF germline heterozygous
 * sites within 300 bp of a target (panel filters: depth > 25, both alleles
 * >= 2 reads, VAF >= 0.05). Also reports sex and contamination. Host env
 * 'hmftools' (conf/twist_apply.config PATH override; container = null).
 */

process HMF_AMBER {
    tag   "${meta.id}"
    label 'process_medium'

    input:
        tuple val(meta), path(bam), path(bai)
        tuple path(fasta), path(fai), path(dict)
        path loci
        path target_bed

    output:
        tuple val(meta), path("amber"),                                emit: dir
        tuple val(meta), path("amber/${meta.id}.amber.baf.tsv.gz"),    emit: baf
        tuple val(meta), path("amber/${meta.id}.amber.qc"),            emit: qc
        tuple val(meta), path("${meta.id}.amber.log"),              emit: log, optional: true   // MARKER HMF_PURPLE_V1b

    stub:
        """
        mkdir -p amber
        printf 'chromosome\\tposition\\ttumorBAF\\n' | gzip > amber/${meta.id}.amber.baf.tsv.gz
        printf 'QCStatus\\tPASS\\n' > amber/${meta.id}.amber.qc
        """

    script:
        def xmx = task.memory ? Math.max(4, task.memory.toGiga() - 2) : 8
        """
        java -Xmx${xmx}g -jar \$(ls ${params.hmf_env}/share/hmftools-amber-*/amber.jar) \\
            -tumor ${meta.id} -tumor_bam ${bam} \\
            -loci ${loci} \\
            -ref_genome ${fasta} -ref_genome_version 38 \\
            -target_regions_bed ${target_bed} \\
            -output_dir amber -threads ${task.cpus} > ${meta.id}.amber.log 2>&1
        """
}
