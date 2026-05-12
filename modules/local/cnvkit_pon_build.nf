/*
 * modules/local/cnvkit_pon_build.nf
 *
 * Run cnvkit.py batch in PoN-build mode:
 *   - takes all normal BAMs at once
 *   - produces per-sample target/antitarget .cnn coverage files
 *   - produces a combined reference (pon_reference.cnn)
 *
 * Equivalent to:
 *   cnvkit.py batch --normal <bam1> <bam2> ... \
 *                   --targets panel.bed \
 *                   --fasta reference.fasta \
 *                   --output-reference pon_reference.cnn \
 *                   --output-dir cnvkit_pon_build
 *
 * Used by workflows/build_pon.nf only.
 */

process CNVKIT_PON_BUILD {
    tag        "pon_build"
    label      'process_high'
    label      'process_long'

    conda      'bioconda::cnvkit=0.9.10'
    container  'quay.io/biocontainers/cnvkit:0.9.10--pyhdfd78af_0'

    input:
        path  bams_and_bais  // a flat list of all .final.bam and .final.bam.bai files
        tuple path(fasta), path(fai), path(dict)
        path  bed

    output:
        path  "cnvkit_pon_build/pon_reference.cnn",                        emit: pon
        path  "cnvkit_pon_build/*.targetcoverage.cnn",                     emit: target_cov
        path  "cnvkit_pon_build/*.antitargetcoverage.cnn",                 emit: antitarget_cov
        path  "cnvkit_pon_build",                                          emit: build_dir
        path  "versions.yml",                                              emit: versions

    script:
        """
        # Collect BAMs (skip .bai files)
        BAMS=\$(ls *.final.bam 2>/dev/null | sort | tr '\\n' ' ')

        cnvkit.py batch \\
            --normal \$BAMS \\
            --targets ${bed} \\
            --fasta ${fasta} \\
            --output-reference cnvkit_pon_build/pon_reference.cnn \\
            --output-dir cnvkit_pon_build \\
            -p ${task.cpus}

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            cnvkit: \$(cnvkit.py version | sed 's/cnvkit v//')
        END_VERSIONS
        """
}
