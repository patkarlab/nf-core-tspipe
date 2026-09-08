/*
 * modules/local/mnv_merge.nf  (MNV_MERGE_V1, N2)
 *
 * Re-join multi-nucleotide variants that SomaticSeq decomposed into SNVs,
 * before VEP sees the VCF. Evidence comes from the callers that emit MNVs
 * natively: the Mutect2 (FilterMutectCalls) VCF -- MNV records and PGT/PID
 * phase sets -- and the VarDict VCF. Merged records are ADDED; components
 * stay and are tagged INFO MNV_PARENT so variant_filter.py can demote them
 * (Filter MNV_COMPONENT) and let the MNV inherit BLACKLIST /
 * COMMON_POLYMORPHISM from its parts. See docs/sops/mnv_merge.md.
 *
 * Container: GATK image (Python 3.6); bin/mnv_merge.py is stdlib only and
 * reads the reference through the .fai index.
 */

process MNV_MERGE {
    tag        "${meta.id}"
    label      'process_low'
    container  'docker://broadinstitute/gatk:4.5.0.0'

    input:
        tuple val(meta), path(consensus_vcf), path(mutect2_vcf), path(vardict_vcf)
        tuple path(fasta), path(fai), path(dict)

    output:
        tuple val(meta), path("${meta.id}.somaticseq.mnv.vcf"), emit: vcf
        path "versions.yml", emit: versions

    stub:
        """
        cp ${consensus_vcf} ${meta.id}.somaticseq.mnv.vcf
        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            stub: true
        END_VERSIONS
        """

    script:
        """
        mnv_merge.py \\
            --consensus ${consensus_vcf} \\
            --mutect2-raw ${mutect2_vcf} \\
            --vardict ${vardict_vcf} \\
            --reference ${fasta} \\
            --sample ${meta.id} \\
            --out ${meta.id}.somaticseq.mnv.vcf

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            python: \$(python3 --version 2>&1 | awk '{print \$2}')
            mnv_merge: 'MNV_MERGE_V1'
        END_VERSIONS
        """
}
