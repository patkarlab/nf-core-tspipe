/*
 * modules/local/cnvkit.nf
 *
 * nf-core CNV wiring v1 (apply_nfcore_cnv_wiring_part2)
 *
 * CNVKit-based copy-number calling with a sex-matched PoN.
 * Wraps bin/cnvkit.py, which is itself the ported and trimmed version of
 * production scripts/12_cnv_calling.py (sex auto-inference removed; sex
 * resolved upstream via meta.sex).
 *
 * PGC_ARG_V1: task.ext.args is appended to the wrapper command
 * (empty by default). Per-panel configs use it to pass
 * --panel-gene-chroms; legacy panels are unaffected.
 *
 * PoN selection logic:
 *   meta.sex == 'male'   -> pon_male
 *   meta.sex == 'female' -> pon_female
 *   meta.sex not male/female -> params.cnv_sex_fallback stratum (default
 *     male; SEXSTRAT_V1) with a warning; chrX is not interpretable then.
 *   The LOO summary and noisy-bin blacklist follow the same stratum.
 *
 * Both PoN files are staged (small cost); only one is referenced by
 * cnvkit.py batch. Outputs follow the production naming convention so
 * downstream modules (CNV_PLOTS, ZSCORE_CNV, CNV_CONCORDANCE,
 * CNV_CLINICAL_REPORT) can consume by exact basename.
 */

process CNVKIT {
    tag        "${meta.id}"
    label      'process_medium'

    conda      'bioconda::cnvkit=0.9.10 conda-forge::pandas=2.1.4 conda-forge::numpy=1.26'
    container  'quay.io/biocontainers/cnvkit:0.9.10--pyhdfd78af_0'

    input:
        tuple val(meta), path(bam), path(bai)
        tuple path(fasta), path(fai), path(dict)
        path  bed
        path  pon_male
        path  pon_female
        path  noisy_bins
        path  loo_summary
        path  noisy_bins_female,  stageAs: 'female_stratum/*'   // MARKER SEXSTRAT_V1
        path  loo_summary_female, stageAs: 'female_stratum/*'   // SEXSTRAT_V1

    output:
        // Downstream-consumed bin/segment/genemetrics outputs
        tuple val(meta), path("${meta.id}.cnr"),                       emit: cnr
        tuple val(meta), path("${meta.id}.cns"),                       emit: cns
        tuple val(meta), path("${meta.id}.call.cns"),                  emit: call_cns
        tuple val(meta), path("${meta.id}.genemetrics.annotated.tsv"), emit: genemetrics
        // Side-channel exports (optional; failures are non-fatal in bin/cnvkit.py)
        tuple val(meta), path("${meta.id}.seg"),                       emit: seg,         optional: true
        tuple val(meta), path("${meta.id}.cnv.vcf"),                   emit: vcf,         optional: true
        tuple val(meta), path("${meta.id}.genemetrics.tsv"),           emit: genemetrics_raw, optional: true
        // Plots produced inline by cnvkit.py batch / scatter
        tuple val(meta), path("${meta.id}.scatter.png"),               emit: scatter_png, optional: true
        tuple val(meta), path("${meta.id}.scatter.chr*.png"),          emit: chr_scatters, optional: true
        tuple val(meta), path("${meta.id}.final-diagram.pdf"),         emit: diagram_pdf, optional: true
        tuple val(meta), path("${meta.id}.final-scatter.png"),         emit: final_scatter_png, optional: true
        tuple val(meta), path("${meta.id}.final-scatter.pdf"),         emit: final_scatter_pdf, optional: true
    stub:
        // nf-core stub blocks v1 (apply_nfcore_add_stub_blocks)
        """
        touch ${meta.id}.cnr ${meta.id}.cns ${meta.id}.call.cns ${meta.id}.genemetrics.annotated.tsv ${meta.id}.seg ${meta.id}.cnv.vcf ${meta.id}.genemetrics.tsv ${meta.id}.scatter.png ${meta.id}.scatter.chr1.png ${meta.id}.final-diagram.pdf ${meta.id}.final-scatter.png ${meta.id}.final-scatter.pdf
        """


    script:
        def sex       = meta.sex ?: 'unknown'
        // SEXSTRAT_V1: PoN, LOO summary and noisy bins follow one stratum;
        // params.cnv_sex_fallback (default male) when sex is not male/female.
        def stratum = (meta.sex in ['male', 'female']) ? meta.sex : (params.cnv_sex_fallback ?: 'male')
        def pon_use   = (stratum == 'female') ? pon_female : pon_male
        def noisy_use = (stratum == 'female') ? noisy_bins_female : noisy_bins
        def loo_use   = (stratum == 'female') ? loo_summary_female : loo_summary
        """
        echo "[SEXSTRAT] ${meta.id}: sex=${sex} stratum=${stratum} pon=${pon_use} loo=${loo_use} blacklist=${noisy_use}"
        if [ "${sex}" != "${stratum}" ]; then
            echo "[WARN] meta.sex=${sex} for ${meta.id}; using the ${stratum} stratum (params.cnv_sex_fallback). chrX copy ratio is not interpretable." >&2
        fi

        # Matplotlib/fontconfig need a writable cache dir; the container's
        # default ($HOME/.config/matplotlib) is not writable.
        export MPLCONFIGDIR=\$PWD/.mpl
        export XDG_CACHE_HOME=\$PWD/.cache
        mkdir -p \$MPLCONFIGDIR \$XDG_CACHE_HOME

        cnvkit_wrapper.py \\
            --bam ${bam} \\
            -s ${meta.id} \\
            -o . \\
            --pon ${pon_use} \\
            --sex ${sex} \\
            --blacklist ${noisy_use} \\
            --loo-summary ${loo_use} ${task.ext.args ?: ''}
        """
}
