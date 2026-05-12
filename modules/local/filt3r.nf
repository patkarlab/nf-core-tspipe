/*
 * modules/local/filt3r.nf
 *
 * filt3r (Baudry 2022). FLT3-ITD k-mer based caller on FASTQ input.
 *
 * Original install path: /home/hemat/programs/filt3r/filt3r
 *   reference: /home/hemat/programs/filt3r/data/flt3_exon14-15.fa
 *   k-mer = 12 (validated default)
 *
 * Until a public bioconda package lands, this module assumes a local
 * conda env or container with filt3r on PATH. Override via process.container
 * in nextflow.config.
 */

process FILT3R {
    tag        "${meta.id}"
    label      'process_low'
    label      'error_ignore'

    // filt3r is not on bioconda yet; build a custom container or use a local
    // install via -profile standard.
    // container 'your-registry/filt3r:0.4.0'

    input:
        tuple val(meta), path(reads1), path(reads2)

    output:
        tuple val(meta), path("${meta.id}_filt3r.json"), emit: calls, optional: true
        tuple val(meta), path("${meta.id}_filt3r.vcf"),  emit: vcf,   optional: true

    script:
        def kmer = task.ext.kmer ?: 12
        def ref  = params.filt3r_ref ?: '/home/hemat/programs/filt3r/data/flt3_exon14-15.fa'
        """
        filt3r \\
            -k ${kmer} \\
            --ref ${ref} \\
            --sequences ${reads1},${reads2} \\
            --vcf > ${meta.id}_filt3r.json
        # The vcf flag emits VCF to a fixed path - check upstream tool docs
        if [ -f filt3r.vcf ]; then mv filt3r.vcf ${meta.id}_filt3r.vcf; fi
        """
}
