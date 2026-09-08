/*
 * modules/local/spikein_sites.nf  (SPIKEIN_V1, D13)
 *
 * Genotype the panel's germline spike-in SNPs on the final BAM. The panel
 * asset assets/<panel>/spikein_regions.tsv lists regulatory regions (whose
 * coverage already comes through targets.exonwise.bed -> exon_coverage.tsv,
 * nothing to compute here) and germline_snp rows with a 1-based position.
 *
 * GATK CollectAllelicCounts at the SNP positions -> bin/spikein_sites.py
 * (stdlib, Python 3.6) writes <sample>.spikein_snps.tsv: ref/alt counts,
 * depth, allele fraction, hom_ref/het/hom_alt call, risk-allele copies where
 * the asset curates a risk allele.
 *
 * Panels without the asset stage [] and get a header-only table so the
 * ORGANIZE_OUTPUT join still sees every sample.
 *
 * Container: GATK image, as SEX_CHECK.
 */

process SPIKEIN_SITES {
    tag        "${meta.id}"
    label      'process_low'
    container  'docker://broadinstitute/gatk:4.5.0.0'

    input:
        tuple val(meta), path(bam), path(bai)
        tuple path(fasta), path(fai), path(dict)
        path spikein_asset

    output:
        tuple val(meta), path("${meta.id}.spikein_snps.tsv"), emit: tsv
        path "${meta.id}.spikein.allelicCounts.tsv", optional: true, emit: allelic
        path "versions.yml", emit: versions

    stub:
        """
        printf 'sample\\tname\\tgene\\trsid\\trsid_alias\\tchrom\\tpos\\tref\\talt\\tref_count\\talt_count\\tdepth\\talt_af\\tgenotype\\trisk_allele\\trisk_copies\\tstatus\\tdescription\\n' > ${meta.id}.spikein_snps.tsv
        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            stub: true
        END_VERSIONS
        """

    script:
        def xmx = task.memory ? Math.max(2, task.memory.toGiga() - 2) : 4
        def ac  = "${meta.id}.spikein.allelicCounts.tsv"
        def snp_cmd = spikein_asset ? """awk -F'\\t' '!/^#/ && \$2 == "germline_snp" { printf "%s\\t%d\\t%s\\n", \$3, \$6 - 1, \$6 }' ${spikein_asset} | sort -k1,1 -k2,2n > spikein_sites.bed
        n_bed=\$(grep -c . spikein_sites.bed || true)
        echo "[spikein_sites] ${meta.id}: \$n_bed SNP sites from the asset"
        gatk --java-options "-Xmx${xmx}g" CollectAllelicCounts \\
            -I ${bam} \\
            -L spikein_sites.bed \\
            -R ${fasta} \\
            -O ${ac}
        spikein_sites.py \\
            --asset ${spikein_asset} \\
            --allelic-counts ${ac} \\
            --sample ${meta.id} \\
            --out ${meta.id}.spikein_snps.tsv
        """ : """echo '[spikein_sites] ${meta.id}: no spike-in asset for this panel; header-only table'
        printf 'sample\\tname\\tgene\\trsid\\trsid_alias\\tchrom\\tpos\\tref\\talt\\tref_count\\talt_count\\tdepth\\talt_af\\tgenotype\\trisk_allele\\trisk_copies\\tstatus\\tdescription\\n' > ${meta.id}.spikein_snps.tsv
        """
        """
        ${snp_cmd}

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            python: \$(python3 --version 2>&1 | awk '{print \$2}')
            gatk: \$(gatk --version 2>&1 | grep -m1 -oE '[0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+' || echo unknown)
        END_VERSIONS
        """
}
