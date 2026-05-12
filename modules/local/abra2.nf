/*
 * modules/local/abra2.nf
 *
 * ABRA2 indel realignment. The conda abra2 wrapper is:
 *   exec java -jar /path/abra2.jar "$@"
 * with JVM flags coming from the JAVA_TOOL_OPTIONS env var (default -Xmx4G).
 * So we set memory via export, not as a positional argument.
 *
 * Mirrors scripts/05_abra2.py.
 */

process ABRA2 {
    tag        "${meta.id}"
    label      'process_high'

    input:
        tuple val(meta), path(bam), path(bai)
        tuple path(fasta), path(fai), path(dict)
        path  bed

    output:
        tuple val(meta), path("${meta.id}.final.bam"), path("${meta.id}.final.bam.bai"), emit: bam
        path  "versions.yml",                                                             emit: versions

    script:
        def args = task.ext.args ?: '--mer 0.025 --mad 5000'
        def mem_gb = task.memory ? task.memory.toGiga() : 16
        """
        # ABRA2 requires the BED sorted in reference dictionary order
        sort -k1,1 -k2,2n ${bed} > targets.sorted.bed

        # JVM heap goes via the wrapper's env-var convention, not as a CLI arg
        export JAVA_TOOL_OPTIONS="-Xmx${mem_gb}g"

        abra2 \\
            --in ${bam} \\
            --out ${meta.id}.abra.bam \\
            --ref ${fasta} \\
            --targets targets.sorted.bed \\
            --threads ${task.cpus} \\
            ${args}

        samtools sort -@ ${task.cpus} -o ${meta.id}.final.bam ${meta.id}.abra.bam
        samtools index -@ ${task.cpus} ${meta.id}.final.bam
        rm -f ${meta.id}.abra.bam

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            abra2: \$(abra2 2>&1 | grep -oP 'ABRA2 version \\K\\S+' | head -n1)
            samtools: \$(samtools --version | head -n1 | sed 's/samtools //')
        END_VERSIONS
        """
}
