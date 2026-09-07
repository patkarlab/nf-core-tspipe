/*
 * modules/local/hmf_cobalt.nf  (HMF_PURPLE_V1; MARKER HMF_PURPLE_V1a: -target_region_norm_file)
 *
 * COBALT tumour-only in panel mode: read-depth ratios per 1 kb window,
 * GC-normalised, corrected with the panel's target-regions normalisation
 * (trained on the normals), PCF segmented with -pcf_gamma 50. No diploid
 * regions file (not recommended in targeted mode). Host env 'hmftools'.
 */

process HMF_COBALT {
    tag   "${meta.id}"
    label 'process_medium'

    input:
        tuple val(meta), path(bam), path(bai)
        tuple path(fasta), path(fai), path(dict)
        path gc_profile
        path target_norm

    output:
        tuple val(meta), path("cobalt"),                                  emit: dir
        tuple val(meta), path("cobalt/${meta.id}.cobalt.ratio.tsv.gz"),  emit: ratio
        tuple val(meta), path("${meta.id}.cobalt.log"),              emit: log, optional: true   // MARKER HMF_PURPLE_V1b

    stub:
        """
        mkdir -p cobalt
        printf 'chromosome\\tposition\\ttumorReadDepth\\n' | gzip > cobalt/${meta.id}.cobalt.ratio.tsv.gz
        """

    script:
        def xmx = task.memory ? Math.max(4, task.memory.toGiga() - 2) : 8
        """
        java -Xmx${xmx}g -jar \$(ls ${params.hmf_env}/share/hmftools-cobalt-*/cobalt.jar) \\
            -tumor ${meta.id} -tumor_bam ${bam} \\
            -ref_genome ${fasta} -ref_genome_version 38 \\
            -gc_profile ${gc_profile} \\
            -target_region_norm_file ${target_norm} -pcf_gamma ${params.hmf_pcf_gamma} \\
            -output_dir cobalt -threads ${task.cpus} > ${meta.id}.cobalt.log 2>&1
        """
}
