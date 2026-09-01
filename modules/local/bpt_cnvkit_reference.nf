/*
 * modules/local/bpt_cnvkit_reference.nf
 *
 * Pooled CNVkit reference for one stratum. NO -y, ever: sex is handled by
 * stratification, not by the haploid-X flag. params.male_reference is
 * retired for this panel (2026-08-30 design doc v3).
 */

process BPT_CNVKIT_REFERENCE {
    tag   "${stratum}"
    label 'process_medium'

    input:
        val  stratum
        path cov_files
        path fasta
        path fai

    output:
        tuple val(stratum), path("cnvkit_pon_${stratum}.cnn"), emit: ref

    stub:
        """
        touch cnvkit_pon_${stratum}.cnn
        """

    script:
        def extra = task.ext.args ?: ''
        """
        n_t=\$(ls *.targetcoverage.cnn 2>/dev/null | wc -l)
        n_a=\$(ls *.antitargetcoverage.cnn 2>/dev/null | wc -l)
        echo "[ok] stratum=${stratum}: \$n_t target / \$n_a antitarget coverage files"
        if [ "\$n_t" -lt 2 ]; then
            echo "[error] stratum=${stratum}: need >= 2 target coverage files, found \$n_t" >&2
            exit 1
        fi
        if [ "\$n_t" -lt 20 ]; then
            echo "[warn] stratum=${stratum}: only \$n_t normals; 24/stratum is the design comfort level"
        fi

        cnvkit.py reference \\
            *.targetcoverage.cnn *.antitargetcoverage.cnn \\
            --fasta ${fasta} \\
            ${extra} \\
            -o cnvkit_pon_${stratum}.cnn

        echo "[ok] wrote cnvkit_pon_${stratum}.cnn (no -y; sex handled by stratification)"
        """
}
