/*
 * modules/local/vep_annotate.nf
 *
 * Annotate a SomaticSeq VCF with VEP + ANNOVAR, emit a merged 29-column
 * flat TSV. Wraps bin/annotate.py, which is a port of production
 * scripts/13_annotate.py with the combined-VCF branch removed.
 *
 * VEP runs via `conda run -n vep vep ...` inside annotate.py -- the vep
 * env has its own Perl @INC and we must let conda activate it for the
 * duration of the vep invocation. ANNOVAR runs via the targeted-seq
 * env's perl, already on PATH via gandalf.config beforeScript.
 *
 * Inputs:
 *   vcf       -- SomaticSeq consensus VCF
 *   fasta+fai+dict -- reference genome (staged together by Nextflow)
 *
 * Output:
 *   ${meta.id}.annotated.tsv  -- 29-column flat TSV, schema in
 *                                bin/annotate.py COLUMNS
 *   versions.yml              -- software versions for the final report
 */

process VEP_ANNOTATE {
    tag        "${meta.id}"
    label      'process_medium'

    conda      'conda-forge::pandas=2.1.4'

    input:
        tuple val(meta), path(vcf)
        tuple path(fasta), path(fai), path(dict)

    output:
        tuple val(meta), path("${meta.id}.annotated.tsv"), emit: tsv
        path  "versions.yml",                              emit: versions

    stub:
        // Touch the declared outputs so the DAG validates in -stub mode
        // without actually running VEP or ANNOVAR.
        """
        touch ${meta.id}.annotated.tsv
        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            stub: true
        END_VERSIONS
        """

    script:
        """
        annotate.py \\
            --somaticseq-vcf ${vcf} \\
            --sample-name ${meta.id} \\
            --reference ${fasta} \\
            --vep-cache ${params.vep_cache} \\
            --annovar-script ${params.annovar_script} \\
            --annovar-db ${params.annovar_db} \\
            --output ${meta.id}.annotated.tsv \\
            --vep-fork ${task.cpus}

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            python: \$(python --version 2>&1 | sed 's/Python //')
            perl:   \$(perl -e 'print substr(\$^V, 1)')
        END_VERSIONS
        """
}
