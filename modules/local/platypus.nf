/*
 * modules/local/platypus.nf
 *
 * Platypus callVariants. Mirrors scripts/06_variant_callers.py run_platypus():
 *
 *   1. Convert BED -> regions.txt (chr:start-end per line)
 *   2. platypus callVariants --bamFiles --refFile --output --regions
 *        --nCPU N --minFlank=0 --filterDuplicates=0 --minMapQual=50
 *        --maxVariants=6 --minReads=6
 *
 * Platypus is a py2 tool. gandalf.config beforeScript puts py2 env first on
 * PATH so the conda wrapper resolves correctly.
 *
 * Production flag notes:
 *   --filterDuplicates=0  : count marked duplicates as valid reads.
 *                           Platypus has its own dup-handling downstream.
 *   --minMapQual=50       : strict MAPQ (matches VarDict's -O 50)
 *   --maxVariants=6       : cap multi-allelic explosion
 *   --minReads=6          : min coverage to attempt calling
 *   --minFlank=0          : don't trim flanking bases for indel context
 */

process PLATYPUS {
    tag        "${meta.id}"
    label      'process_medium'

    input:
        tuple val(meta), path(bam), path(bai)
        tuple path(fasta), path(fai), path(dict)
        path  bed

    output:
        tuple val(meta), path("${meta.id}.platypus.vcf"), emit: vcf
        path  "versions.yml",                              emit: versions
    stub:
        // nf-core stub blocks v1 (apply_nfcore_add_stub_blocks)
        """
        touch ${meta.id}.platypus.vcf versions.yml
        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            stub: true
        END_VERSIONS
        """


    script:
        """
        # BED -> Platypus regions format (chr:start-end, one per line)
        awk '/^#/ {next} {print \$1":"\$2"-"\$3}' ${bed} > platypus_regions.txt

        platypus callVariants \\
            --bamFiles=${bam} \\
            --refFile=${fasta} \\
            --output=${meta.id}.platypus.vcf \\
            --nCPU=${task.cpus} \\
            --minFlank=0 \\
            --filterDuplicates=0 \\
            --minMapQual=50 \\
            --maxVariants=6 \\
            --minReads=6 \\
            --regions=platypus_regions.txt

        cat <<-END_VERSIONS > versions.yml
        \"${task.process}\":
            platypus: \$(grep '^##source=' ${meta.id}.platypus.vcf | sed 's/##source=Platypus_Version_//' | head -n1 || echo unknown)
        END_VERSIONS
        """
}
