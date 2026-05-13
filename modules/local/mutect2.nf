/*
 * modules/local/mutect2.nf
 *
 * GATK4 Mutect2 tumor-only with gnomAD germline resource, followed by
 * FilterMutectCalls.
 *
 * Command-line mirrors scripts/06_variant_callers.py run_mutect2() PLUS the
 * FilterMutectCalls post-step that the prior session validated as a one-off
 * rerun but never integrated into the production scripts. This module bakes
 * it in for the nf-core port.
 *
 * Reference: we use the MASKED hg38 (same as preprocessing) on purpose.
 * Production used unmasked hg38, which causes U2AF1 paralog read-collapse
 * and silent loss of clinically important U2AF1 variants in MDS/AML.
 * Masked reference forces reads onto the canonical locus and restores
 * sensitivity. See docs/clinical_decisions.md.
 *
 * Output channels:
 *   vcf, tbi          = FilterMutectCalls output (with FILTER tags annotated;
 *                       all records present). This is what SomaticSeq expects
 *                       as --mutect2-vcf input - it uses the FILTER column
 *                       as a feature in ensemble decisions.
 *   vcf_raw, tbi_raw  = raw Mutect2 output (pre-FilterMutectCalls) for audit
 *   stats             = Mutect2 stats file (input to FilterMutectCalls)
 *   filtering_stats   = FilterMutectCalls filtering-statistics report
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
        // Primary: FilterMutectCalls output (annotated, all records)
        tuple val(meta), path("${meta.id}.mutect2.vcf.gz"),         emit: vcf
        tuple val(meta), path("${meta.id}.mutect2.vcf.gz.tbi"),     emit: tbi
        // Audit: raw Mutect2 output (pre-FilterMutectCalls)
        tuple val(meta), path("${meta.id}.mutect2.raw.vcf.gz"),     emit: vcf_raw
        tuple val(meta), path("${meta.id}.mutect2.raw.vcf.gz.tbi"), emit: tbi_raw
        // Stats files
        tuple val(meta), path("${meta.id}.mutect2.raw.vcf.gz.stats"),      emit: stats
        tuple val(meta), path("${meta.id}.mutect2.filteringStats.tsv"),    emit: filtering_stats
        path  "versions.yml",                                              emit: versions

    script:
        def mem = task.memory ? "-Xmx${task.memory.toGiga()}g" : ''
        """
        # Step 1: Mutect2 - raw call set with stats
        gatk --java-options "${mem}" Mutect2 \\
            -R ${fasta} \\
            -I ${bam} \\
            -O ${meta.id}.mutect2.raw.vcf.gz \\
            --germline-resource ${gnomad} \\
            -L ${bed} \\
            --min-base-quality-score 25 \\
            --native-pair-hmm-threads ${task.cpus}

        # Step 2: FilterMutectCalls - apply orientation-bias / strand-bias /
        # clustered-events / etc. filters; produces FILTER-annotated VCF.
        # SomaticSeq consumes this as --mutect2-vcf and uses FILTER as a feature.
        gatk --java-options "${mem}" FilterMutectCalls \\
            -R ${fasta} \\
            -V ${meta.id}.mutect2.raw.vcf.gz \\
            --stats ${meta.id}.mutect2.raw.vcf.gz.stats \\
            --filtering-stats ${meta.id}.mutect2.filteringStats.tsv \\
            -O ${meta.id}.mutect2.vcf.gz

        # Summary to stderr (shows up in Nextflow log)
        RAW_N=\$(zcat ${meta.id}.mutect2.raw.vcf.gz | grep -cv '^#' || echo 0)
        FILT_N=\$(zcat ${meta.id}.mutect2.vcf.gz | grep -cv '^#' || echo 0)
        PASS_N=\$(zcat ${meta.id}.mutect2.vcf.gz | awk '!/^#/ && \$7=="PASS"' | wc -l)
        echo "[MUTECT2 ${meta.id}] raw=\${RAW_N}  post-filter records=\${FILT_N}  PASS=\${PASS_N}" 1>&2
        echo "[MUTECT2 ${meta.id}] FILTER tag distribution:" 1>&2
        zcat ${meta.id}.mutect2.vcf.gz | awk '!/^#/ {c[\$7]++} END {for (k in c) print "  "k": "c[k]}' 1>&2

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            gatk4: \$(gatk --version 2>&1 | grep -oP '\\d+\\.\\d+\\.\\d+\\.\\d+' | head -n1)
        END_VERSIONS
        """
}
