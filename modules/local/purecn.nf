/*
 * modules/local/purecn.nf  (PCN_V1)
 *
 * PureCN purity/ploidy/integer-CN + LOH, tumor-only, against the
 * male-stratum NormalDB. Consumes the raw Mutect2 VCF (all variants,
 * germline included -- what the purity model needs). --sex from
 * meta.sex so chrX is modelled correctly.
 *
 * ROBUSTNESS: purity fitting can legitimately fail on copy-flat
 * samples (the held-out-normal pilots are exactly that). A PureCN.R
 * failure therefore writes sentinel outputs (summary status=FAILED,
 * header-only gene table) and exits 0 with a loud [warn], keeping the
 * per-sample DAG and the consensus join alive. Real tumor samples that
 * fail will surface as FAILED rows in the consensus summary, never
 * silently.
 */

process PURECN {
    tag   "${meta.id}"
    label 'process_medium'

    input:
        tuple val(meta), path(tumor_cov), path(vcf)
        path normaldb
        path intervals

    output:
        tuple val(meta), path("${meta.id}.purecn.genes.tsv"),   emit: genes
        tuple val(meta), path("${meta.id}.purecn.summary.tsv"), emit: summary
        tuple val(meta), path("${meta.id}*.csv"),               emit: raw_csv,  optional: true
        tuple val(meta), path("${meta.id}.rds"),                emit: rds,      optional: true
        tuple val(meta), path("${meta.id}*.pdf"),               emit: pdfs,     optional: true
        tuple val(meta), path("${meta.id}_dnacopy.seg"),        emit: seg,      optional: true

    stub:
        """
        touch ${meta.id}.purecn.genes.tsv ${meta.id}.purecn.summary.tsv
        """

    script:
        def sex   = meta.sex == 'male' ? 'M' : (meta.sex == 'female' ? 'F' : '?')
        def extra = task.ext.args ?: ''
        """
        set +e
        Rscript ${params.purecn_extdata}/PureCN.R \\
            --sampleid ${meta.id} \\
            --tumor ${tumor_cov} \\
            --vcf ${vcf} \\
            --normaldb ${normaldb} \\
            --intervals ${intervals} \\
            --genome hg38 \\
            --sex ${sex} \\
            --out ${meta.id} \\
            --cores ${task.cpus} \\
            --seed 123 \\
            ${extra} \\
            --force > ${meta.id}.purecn.log 2>&1
        rc=\$?
        set -e
        if [ "\$rc" -ne 0 ]; then
            echo "[warn] PureCN.R exited \$rc for ${meta.id}; writing FAILED sentinels (see ${meta.id}.purecn.log)"
            purecn_gene_table.py --sample ${meta.id} --failed \\
                --out-genes ${meta.id}.purecn.genes.tsv \\
                --out-summary ${meta.id}.purecn.summary.tsv
        else
            purecn_gene_table.py --sample ${meta.id} \\
                --genes ${meta.id}_genes.csv \\
                --loh ${meta.id}_loh.csv \\
                --solution ${meta.id}.csv \\
                --out-genes ${meta.id}.purecn.genes.tsv \\
                --out-summary ${meta.id}.purecn.summary.tsv
        fi
        """
}
