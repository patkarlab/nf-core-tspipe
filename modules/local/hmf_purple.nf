/*
\1; MARKER HMF_PURPLE_V1c: .purple.qc)
 *
 * PURPLE tumour-only, targeted: purity/ploidy fit from AMBER BAF and COBALT
 * ratios, absolute and allele-specific copy number per segment and gene,
 * QC status. No somatic or SV VCF in v1 (excluded from the tumour-only fit
 * anyway); charts off. A non-zero exit writes FAILED sentinels through
 * purple_gene_table.py so the consensus join survives. Host env 'hmftools'.
 */

process HMF_PURPLE {
    tag   "${meta.id}"
    label 'process_medium'

    input:
        tuple val(meta), path(amber_dir), path(cobalt_dir)
        tuple path(fasta), path(fai), path(dict)
        path gc_profile
        path ensembl_dir
        path driver_panel
        path hotspots
        path target_bed
        path target_norm

    output:
        tuple val(meta), path("purple"),                              emit: dir,     optional: true
        tuple val(meta), path("${meta.id}.purple.h_genes.tsv"),       emit: genes
        tuple val(meta), path("${meta.id}.purple.h_summary.tsv"),     emit: summary
        tuple val(meta), path("${meta.id}.purple.log"),              emit: log, optional: true   // MARKER HMF_PURPLE_V1b

    stub:
        """
        mkdir -p purple
        printf 'gene\\th_call\\th_cn_min\\th_cn_max\\th_macn_min\\th_loh\\th_expected_cn\\n' > ${meta.id}.purple.h_genes.tsv
        printf 'sample\\tstatus\\tmethod\\tpurity\\tploidy\\tgender\\ttrusted\\tcomment\\n${meta.id}\\tSTUB\\tNA\\tNA\\tNA\\tNA\\tFALSE\\tstub\\n' > ${meta.id}.purple.h_summary.tsv
        """

    script:
        def xmx = task.memory ? Math.max(4, task.memory.toGiga() - 2) : 8
        def sex = meta.sex ?: 'unknown'
        """
        set +e
        java -Xmx${xmx}g -jar \$(ls ${params.hmf_env}/share/hmftools-purple-*/purple.jar) \\
            -tumor ${meta.id} \\
            -amber_dir ${amber_dir} -cobalt_dir ${cobalt_dir} \\
            -ref_genome ${fasta} -ref_genome_version 38 \\
            -gc_profile ${gc_profile} \\
            -ensembl_data_dir ${ensembl_dir} \\
            -driver_gene_panel ${driver_panel} -somatic_hotspots ${hotspots} \\
            -target_regions_bed ${target_bed} \\
            -no_charts -threads ${task.cpus} -output_dir purple > ${meta.id}.purple.log 2>&1
        rc=\$?
        set -e
        if [ "\$rc" -ne 0 ] || [ ! -s purple/${meta.id}.purple.purity.tsv ]; then
            echo "[warn] PURPLE exited \$rc for ${meta.id}; writing FAILED sentinels (see ${meta.id}.purple.log)"
            purple_gene_table.py --sample ${meta.id} --failed \\
                --out-genes ${meta.id}.purple.h_genes.tsv --out-summary ${meta.id}.purple.h_summary.tsv
        else
            purple_gene_table.py --sample ${meta.id} --sex ${sex} \\
                --purity purple/${meta.id}.purple.purity.tsv \\
                --qc purple/${meta.id}.purple.qc \\
                --genes purple/${meta.id}.purple.cnv.gene.tsv \\
                --out-genes ${meta.id}.purple.h_genes.tsv --out-summary ${meta.id}.purple.h_summary.tsv
        fi
        """
}
