/*
 * modules/local/decon.nf  (DECON_V1)
 *
 * Exon-level CNV arm E: DECoN (ExomeDepth) for one test sample against
 * the sex-matched pool of normals. Steps, all in the host 'decon' env
 * (conf/twist_apply.config overrides PATH; container = null):
 *   1. decon_ReadInBams.R on the test BAM alone  -> <id>.counts.RData
 *   2. decon_call_sample.R: append that column to the pool, reference
 *      selection + CallCNVs for the test sample, QC gate (max correlation
 *      with the pool >= decon_min_corr, median count >= decon_min_cov)
 *      -> <id>.decon_all.txt (DECoN layout), <id>.decon_qc.tsv
 *   3. filter_decon_calls.py: PASS / BELOW_BF / LOW_POWER_EXON /
 *      PARALOG_EXON classes (paralog_limited_exons.tsv), BF >= decon_bf
 *   4. decon_gene_table.py: CMX_V2 --decon-genes contract; every gene NA
 *      when the QC gate fails so arm E abstains.
 * The pool RData for the other stratum is staged under female_stratum/
 * and never read. PROBE_VARIANT classification (needs the sample's own
 * variant table) is not wired in v1.
 */

process DECON {
    tag   "${meta.id}"
    label 'process_low'

    input:
        tuple val(meta), path(bam), path(bai)
        tuple path(fasta), path(fai), path(dict)
        path exons_bed
        path pool_male
        path pool_female, stageAs: 'female_stratum/*'
        path paralog_exons

    output:
        tuple val(meta), path("${meta.id}.decon.genes.tsv"),    emit: genes
        tuple val(meta), path("${meta.id}.decon_all.txt"),      emit: calls
        tuple val(meta), path("${meta.id}.decon_filtered.tsv"), emit: filtered
        tuple val(meta), path("${meta.id}.decon_qc.tsv"),       emit: qc
        tuple val(meta), path("${meta.id}.decon.RData"),        emit: rdata, optional: true

    stub:
        """
        printf 'gene\\te_call\\te_bf\\te_n_exons\\te_calls\\te_qc\\n' > ${meta.id}.decon.genes.tsv
        printf 'CNV.ID\\tSample\\tCorrelation\\tN.comp\\tStart.b\\tEnd.b\\tCNV.type\\tN.exons\\tStart\\tEnd\\tChromosome\\tGenomic.ID\\tBF\\tReads.expected\\tReads.observed\\tReads.ratio\\tGene\\tN.exons.gene\\n' > ${meta.id}.decon_all.txt
        cp ${meta.id}.decon_all.txt ${meta.id}.decon_filtered.tsv
        printf 'sample\\tqc_pass\\n${meta.id}\\tSTUB\\n' > ${meta.id}.decon_qc.tsv
        """

    // DECON_V1b: --del-multi-bf (multi-exon deletions at params.decon_del_multi_bf); MARKER DECON_V1b_FIX
    script:
        def stratum  = (meta.sex in ['male', 'female']) ? meta.sex : (params.cnv_sex_fallback ?: 'male')
        def pool_use = (stratum == 'female') ? pool_female : pool_male
        """
        echo "[SEXSTRAT] ${meta.id}: sex=${meta.sex} stratum=${stratum} pool=${pool_use}"
        echo "${bam}" > bams.txt

        Rscript --vanilla ${projectDir}/bin/decon_ReadInBams.R \\
            --bams bams.txt --bed ${exons_bed} --fasta ${fasta} --out ${meta.id}.counts

        Rscript --vanilla ${projectDir}/bin/decon_call_sample.R \\
            --pool ${pool_use} --sample ${meta.id}.counts.RData --id ${meta.id} \\
            --transProb ${params.decon_trans_prob} --mincorr ${params.decon_min_corr} \\
            --mincov ${params.decon_min_cov} --out ${meta.id}.decon

        python3 ${projectDir}/bin/filter_decon_calls.py \\
            --calls ${meta.id}.decon_all.txt --exons ${paralog_exons} \\
            --bf ${params.decon_bf} --del-multi-bf ${params.decon_del_multi_bf} \\
            --out ${meta.id}.decon_filtered.tsv

        python3 ${projectDir}/bin/decon_gene_table.py \\
            --sample ${meta.id} --filtered ${meta.id}.decon_filtered.tsv \\
            --qc ${meta.id}.decon_qc.tsv --bed ${exons_bed} --out ${meta.id}.decon.genes.tsv
        """
}
