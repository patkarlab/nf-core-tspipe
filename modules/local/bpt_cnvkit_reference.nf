/*
 * modules/local/bpt_cnvkit_reference.nf
 *
 * Pooled CNVkit reference for one stratum. The male stratum is built
 * with -y (haploid-X reference) so the stored chrX scale matches what
 * the application layer declares; the female stratum is built flagless
 * (diploid-X). See the BPT_HAPLOID_X_V1 note in the script block.
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
        // BPT_HAPLOID_X_V1: the male stratum reference is built haploid-X
        // (-y) to match the application layer (cnvkit_wrapper.py passes -y
        // for male samples). CNVkit sex-normalises inputs to the
        // reference's target scale, so a flagless build from male inputs
        // yields a diploid-X reference. Verified 2026-09-01 on build_v2:
        // ref chrX mean log2 +0.111 vs chr1 -0.113; LOO chrX mean -0.947,
        // fp_loss_rate 0.916 -- systematic offset, not variance.
        def yflag = (stratum == 'male') ? '-y' : ''
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
            ${yflag} \\
            -o cnvkit_pon_${stratum}.cnn

        echo "[ok] wrote cnvkit_pon_${stratum}.cnn (haploid-X flag: '${yflag}')"
        """
}
