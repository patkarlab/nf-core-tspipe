/*
 * modules/local/flt3_itd_ext.nf
 *
 * FLT3_ITD_EXT (Tan & Roberts 2020) via Docker container.
 *
 * Original scripts/09_flt3_itd.py used:
 *   docker run --rm -v {bam_dir}:/data -v {out_dir}:/out \
 *              -w /biosoft/FLT3_ITD_ext --user $(id -u):$(id -g) \
 *              zhkddocker/flt3_itd_ext:v1.1 \
 *              perl FLT3_ITD_ext.pl -b /data/{bam_name} -o /out -n HC -g hg38
 *
 * In Nextflow, when the docker profile is active, Nextflow handles the volume
 * mount and -w/-u flags automatically. We just stage the BAM into the work dir
 * and Nextflow mounts that work dir into the container at runtime — which
 * eliminates the absolute-path mounting issue flagged in the original porting
 * notes.
 *
 * The container path /biosoft/FLT3_ITD_ext is the tool's install dir; we run
 * the perl entry-point with bare relative paths.
 */

process FLT3_ITD_EXT {
    tag        "${meta.id}"
    label      'process_low'
    label      'error_ignore'   // non-fatal per original orchestrator semantics

    container  'local/flt3_itd_ext:v0.2'
    // No containerOptions: v0.2's PATH wrapper /usr/local/bin/flt3_itd_ext
    // handles the cd-to-install-dir requirement internally, so the
    // container runs with CWD = Nextflow work dir for both Docker and
    // Singularity profiles.

    input:
        tuple val(meta), path(bam), path(bai)

    output:
        tuple val(meta), path("flt3_itd_ext_out/${meta.id}.final_FLT3_ITD.vcf"),         emit: vcf
        tuple val(meta), path("flt3_itd_ext_out/${meta.id}.final_FLT3_ITD_summary.txt"), emit: summary
        tuple val(meta), path("flt3_itd_ext_out/"),                                       emit: out_dir, optional: true
    stub:
        // nf-core stub blocks v2 (matches `vcf` named emit on flt3_itd_ext_out/*.vcf)
        """
        mkdir -p flt3_itd_ext_out
        touch flt3_itd_ext_out/${meta.id}.final_FLT3_ITD.vcf
        touch flt3_itd_ext_out/${meta.id}.final_FLT3_ITD_summary.txt
        """


    script:
        // Absolute paths via \$(pwd) -- the wrapper cd's into the install
        // dir before exec'ing perl, so relative paths in -b/-o would
        // resolve against /biosoft/FLT3_ITD_ext instead of Nextflow's
        // work dir. \$(pwd) is evaluated by bash at runtime inside the
        // container, where CWD is the bind-mounted work dir.
        """
        mkdir -p flt3_itd_ext_out
        flt3_itd_ext \\
            -b \$(pwd)/${bam} \\
            -o \$(pwd)/flt3_itd_ext_out \\
            -n HC \\
            -g hg38
        """
}
