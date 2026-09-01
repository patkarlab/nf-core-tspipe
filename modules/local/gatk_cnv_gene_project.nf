/*
 * modules/local/gatk_cnv_gene_project.nf  (TGC_V1)
 *
 * Projects called copy-ratio segments onto the panel's exonwise gene
 * intervals (concordance-comparable with CNVkit genemetrics) and draws
 * a matplotlib genome plot of denoised bins + segment means. Replaces
 * the GATK R plotters (R optparse/data.table absent on the host env).
 */

process GATK_CNV_GENE_PROJECT {
    tag   "${meta.id}"
    label 'process_low'

    input:
        tuple val(meta), path(called), path(denoised)
        path exonwise

    output:
        tuple val(meta), path("${meta.id}.gatk_cnv.genes.tsv"), emit: genes
        tuple val(meta), path("${meta.id}.gatk_cnv.png"),       emit: plot, optional: true

    stub:
        """
        touch ${meta.id}.gatk_cnv.genes.tsv ${meta.id}.gatk_cnv.png
        """

    script:
        """
        gatk_cnv_gene_project.py \\
            --called ${called} \\
            --denoised ${denoised} \\
            --exonwise ${exonwise} \\
            --sample ${meta.id} \\
            --out-tsv ${meta.id}.gatk_cnv.genes.tsv \\
            --out-plot ${meta.id}.gatk_cnv.png
        """
}
