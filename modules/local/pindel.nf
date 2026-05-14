/*
 * modules/local/pindel.nf
 *
 * Pindel large-indel / structural variant caller.
 * Mirrors scripts/08_pindel.py:
 *   1. config.txt: BAM<TAB>insert_size<TAB>sample
 *   2. pindel -f REF -i config -c ALL -j BED -o PREFIX -T N
 *   3. pindel2vcf -r REF -P PREFIX -R hg38 -d 20250101 -v VCF
 *
 * BED is the focused pindel_targets_hg38.bed (479 regions on indel-prone
 * myeloid genes: FLT3, CALR, CEBPA, KMT2A, ASXL1, TP53, RUNX1, TET2,
 * UBTF, CBL, ETV6, IKZF1, CDKN2A/B). Used for both Stage 2 SomaticSeq
 * ensemble and Stage 3 FLT3-ITD consensus.
 */

process PINDEL {
    tag        "${meta.id}"
    label      'process_medium'

    input:
        tuple val(meta), path(bam), path(bai)
        tuple path(fasta), path(fai), path(dict)
        path  bed

    output:
        tuple val(meta), path("${meta.id}.pindel.vcf"), emit: vcf
        path  "versions.yml",                           emit: versions
    stub:
        // nf-core stub blocks v1 (apply_nfcore_add_stub_blocks)
        """
        touch ${meta.id}.pindel.vcf versions.yml
        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            stub: true
        END_VERSIONS
        """


    script:
        def insert_size = task.ext.insert_size ?: '300'
        """
        # Step 1: write Pindel config
        BAM_ABS=\$(realpath ${bam})
        printf '%s\t${insert_size}\t%s\n' "\$BAM_ABS" '${meta.id}' > config.txt

        # Step 2: run Pindel on focused BED, all chromosomes
        pindel \\
            -f ${fasta} \\
            -i config.txt \\
            -c ALL \\
            -j ${bed} \\
            -o ${meta.id}_pindel \\
            -T ${task.cpus}

        # Step 3: convert to VCF
        pindel2vcf \\
            -r ${fasta} \\
            -P ${meta.id}_pindel \\
            -R hg38 \\
            -d 20250101 \\
            -v ${meta.id}.pindel.vcf

        # Clean up bulky intermediates
        rm -f ${meta.id}_pindel_D ${meta.id}_pindel_SI ${meta.id}_pindel_INV \\
              ${meta.id}_pindel_TD ${meta.id}_pindel_LI ${meta.id}_pindel_BP \\
              ${meta.id}_pindel_RP ${meta.id}_pindel_CloseEndMapped

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            pindel: \$(pindel 2>&1 | grep -oP 'Pindel version \\K\\S+' | head -n1 || echo unknown)
        END_VERSIONS
        """
}
