/*
 * modules/local/styled_scatter.nf  (VIZ_V1)
 *
 * bin/cnvkit_scatter_styled.py --batch: CNVkit's scatter logic with a clean
 * presentation and a BAF panel (het SNPs from the raw Mutect2 VCF):
 * overview/ (genome), per_chromosome/, per_gene/ (called genes from the
 * annotated genemetrics). CNVkit container (cnvlib + matplotlib).
 */

process STYLED_SCATTER {
    tag        "${meta.id}"
    label      'process_low'
    container  'quay.io/biocontainers/cnvkit:0.9.10--pyhdfd78af_0'

    input:
        tuple val(meta), path(cnr), path(cns), path(vcf), path(genemetrics)

    output:
        tuple val(meta), path("styled_scatter"), emit: dir

    stub:
        """
        mkdir -p styled_scatter/overview styled_scatter/per_chromosome styled_scatter/per_gene
        """

    script:
        def sex = meta.sex ?: 'unknown'
        def vcf_arg = vcf ? "--vcf ${vcf}" : ''
        def gm_arg  = genemetrics ? "--genemetrics ${genemetrics}" : ''
        """
        export MPLCONFIGDIR=\$PWD/.mpl
        export XDG_CACHE_HOME=\$PWD/.cache
        mkdir -p \$MPLCONFIGDIR \$XDG_CACHE_HOME styled_scatter

        cnvkit_scatter_styled.py --batch --outdir styled_scatter \\
            --cnr ${cnr} --cns ${cns} ${vcf_arg} ${gm_arg} \\
            --sample ${meta.id} --sex ${sex} > ${meta.id}.styled_scatter.log 2>&1
        echo "[ok] ${meta.id}: \$(find styled_scatter -name '*.png' | wc -l) styled scatter PNGs"
        """
}
