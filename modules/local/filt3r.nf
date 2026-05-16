/*
 * modules/local/filt3r.nf
 *
 * filt3r (Baudry et al., Bioinformatics 2022) FLT3-ITD detection via
 * k-mer assembly against an FLT3 exon14/15 reference. Container
 * `local/filt3r:v0.1` was built from /home/hemat/programs/filt3r/
 * (in-tree Dockerfile).
 *
 * Container layout:
 *   /filt3r/filt3r                       (compiled binary; NOT on PATH)
 *   /filt3r/data/flt3_exon14-15.fa       (k-mer reference)
 *
 * Production invocation in scripts/09_flt3_itd.py:
 *   filt3r --ref data/flt3_exon14-15.fa -k 12 \
 *          --sequences R1,R2 --nb-threads N --vcf \
 *          --out <sample>_filt3r.results.json
 *
 * Two output files are written: the JSON (requested via --out) and a
 * sibling VCF (produced because --vcf was passed). The consensus
 * parser reads only the VCF; the JSON is retained for audit because
 * it contains per-read alignment evidence the VCF does not.
 *
 * k=12 is the validated default per Baudry 2022; overrideable via
 * task.ext.kmer in conf/modules.config without editing this module.
 */

process FILT3R {
    tag        "${meta.id}"
    label      'process_low'
    label      'error_ignore'   // soft-fail per production orchestrator semantics

    container  'local/filt3r:v0.1'

    input:
        tuple val(meta), path(r1), path(r2)

    output:
        tuple val(meta), path("${meta.id}_filt3r.results.vcf"),  emit: vcf
        tuple val(meta), path("${meta.id}_filt3r.results.json"), emit: json

    stub:
        // nf-core stub blocks v1 (apply_nfcore_add_stub_blocks)
        """
        touch ${meta.id}_filt3r.results.vcf
        touch ${meta.id}_filt3r.results.json
        """

    script:
        def kmer = task.ext.kmer ?: 12
        """
        /filt3r/filt3r \\
            --ref         /filt3r/data/flt3_exon14-15.fa \\
            -k            ${kmer} \\
            --sequences   ${r1},${r2} \\
            --nb-threads  ${task.cpus} \\
            --vcf \\
            --out         ${meta.id}_filt3r.results.json
        """
}
