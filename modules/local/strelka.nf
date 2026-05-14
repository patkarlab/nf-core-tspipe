/*
 * modules/local/strelka.nf
 *
 * Strelka2 germline mode with --targeted flag (the tumor-only somatic
 * convention for panel data without a matched normal).
 *
 * Mirrors scripts/06_variant_callers.py run_strelka2():
 *   1. bgzip + tabix the panel BED
 *   2. python2 configureStrelkaGermlineWorkflow.py --bam --referenceFasta \
 *        --callRegions BED.gz --targeted --runDir strelka_work
 *   3. python2 strelka_work/runWorkflow.py -m local -j N
 *   4. extract strelka_work/results/variants/variants.vcf.gz -> sample.strelka.vcf
 *
 * Strelka2 requires python2; site config sets ext.python2 and ext.strelka_bin
 * to point at the python2 interpreter and configureStrelkaGermlineWorkflow.py
 * respectively. On gandalf:
 *   ext.python2     = '/home/hemat/anaconda3/envs/py2/bin/python'
 *   ext.strelka_bin = '/goast/hemat_data/targeted-seq-pipeline/software/strelka2/bin/configureStrelkaGermlineWorkflow.py'
 *
 * Reference: we use the masked hg38 (production used unmasked). See
 * docs/clinical_decisions.md.
 */

process STRELKA {
    tag        "${meta.id}"
    label      'process_medium'

    input:
        tuple val(meta), path(bam), path(bai)
        tuple path(fasta), path(fai), path(dict)
        path  bed

    output:
        tuple val(meta), path("${meta.id}.strelka.vcf"), emit: vcf
        path  "versions.yml",                             emit: versions
    stub:
        // nf-core stub blocks v1 (apply_nfcore_add_stub_blocks)
        """
        touch ${meta.id}.strelka.vcf versions.yml
        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            stub: true
        END_VERSIONS
        """


    script:
        def py2     = task.ext.python2     ?: 'python2'
        def cfg_bin = task.ext.strelka_bin ?: 'configureStrelkaGermlineWorkflow.py'
        """
        # Strelka requires bgzipped + tabix-indexed BED
        cp ${bed} panel.bed
        bgzip panel.bed
        tabix -p bed panel.bed.gz

        # Configure (py2)
        ${py2} ${cfg_bin} \\
            --bam ${bam} \\
            --referenceFasta ${fasta} \\
            --callRegions panel.bed.gz \\
            --targeted \\
            --runDir strelka_work

        # Run (py2)
        ${py2} strelka_work/runWorkflow.py -m local -j ${task.cpus}

        # Extract final VCF
        gunzip -c strelka_work/results/variants/variants.vcf.gz \\
          > ${meta.id}.strelka.vcf

        cat <<-END_VERSIONS > versions.yml
        \"${task.process}\":
            strelka: \$(grep '^##source_version=' ${meta.id}.strelka.vcf | cut -d= -f2 | head -n1 || echo unknown)
        END_VERSIONS
        """
}
