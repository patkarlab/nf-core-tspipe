/*
 * modules/local/freebayes.nf
 *
 * FreeBayes somatic caller. Production runs with bare defaults
 * (scripts/06_variant_callers.py run_freebayes()):
 *
 *   freebayes -f ref -b bam -t bed > sample.freebayes.vcf
 *
 * Module default matches production. Sites can pass conservative tuning
 * flags via gandalf.config ext.args. See docs/clinical_decisions.md for
 * the gandalf-specific MQ/BQ overrides.
 */

process FREEBAYES {
    tag        "${meta.id}"
    label      'process_medium'

    input:
        tuple val(meta), path(bam), path(bai)
        tuple path(fasta), path(fai), path(dict)
        path  bed

    output:
        tuple val(meta), path("${meta.id}.freebayes.vcf"), emit: vcf
        path  "versions.yml",                               emit: versions

    script:
        def args = task.ext.args ?: ''
        """
        freebayes \\
            -f ${fasta} \\
            -b ${bam} \\
            -t ${bed} \\
            ${args} \\
          > ${meta.id}.freebayes.vcf

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            freebayes: \$(freebayes --version 2>&1 | grep -oP 'v\\K[0-9.]+' | head -n1 || echo unknown)
        END_VERSIONS
        """
}
