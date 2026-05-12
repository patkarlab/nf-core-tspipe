/*
 * modules/local/mutect2.nf
 *
 * GATK4 Mutect2 tumor-only with gnomAD germline resource.
 *
 * Command-line mirrors scripts/06_variant_callers.py run_mutect2():
 *   gatk Mutect2 -R ref -I bam -O vcf --germline-resource gnomad -L bed
 *                --min-base-quality-score 25 --native-pair-hmm-threads N
 *
 * Reference: we use the MASKED hg38 (same as preprocessing) on purpose.
 * Production used unmasked hg38, which causes U2AF1 paralog read-collapse
 * and silent loss of clinically important U2AF1 variants in MDS/AML.
 * Masked reference forces reads onto the canonical locus and restores
 * sensitivity. See docs/clinical_decisions.md.
 */

process GATK4_MUTECT2 {
    tag        "${meta.id}"
    label      'process_medium'

    container  'broadinstitute/gatk:4.5.0.0'

    input:
        tuple val(meta), path(bam), path(bai)
        tuple path(fasta), path(fai), path(dict)
        path  bed
        path  gnomad
        path  gnomad_tbi

    output:
        tuple val(meta), path("${meta.id}.mutect2.vcf.gz"),     emit: vcf
        tuple val(meta), path("${meta.id}.mutect2.vcf.gz.tbi"), emit: tbi
        tuple val(meta), path("${meta.id}.mutect2.vcf.gz.stats"),  emit: stats
        path  "versions.yml",                                    emit: versions

    script:
        def mem = task.memory ? "-Xmx${task.memory.toGiga()}g" : ''
        """
        gatk --java-options "${mem}" Mutect2 \\
            -R ${fasta} \\
            -I ${bam} \\
            -O ${meta.id}.mutect2.vcf.gz \\
            --germline-resource ${gnomad} \\
            -L ${bed} \\
            --min-base-quality-score 25 \\
            --native-pair-hmm-threads ${task.cpus}

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            gatk4: \$(gatk --version 2>&1 | grep -oP '\\d+\\.\\d+\\.\\d+\\.\\d+' | head -n1)
        END_VERSIONS
        """
}
