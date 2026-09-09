/*
 * modules/local/reconcnv.nf  (VIZ_V1)
 *
 * reconCNV interactive HTML (bokeh) from the CNVkit ratio and segments plus
 * het SNPs from the raw Mutect2 VCF, via bin/prep_reconcnv_inputs.py and the
 * panel config (assets/reconcnv/reconcnv_config_twist_myeloid.json). Host
 * env 'reconCNV' (Python 3.6, bokeh 1.4; conf/twist_apply.config PATH).
 * Never fatal: on failure a placeholder HTML states the error.
 */

process RECONCNV {
    tag   "${meta.id}"
    label 'process_low'

    input:
        tuple val(meta), path(cnr), path(cns), path(vcf)
        tuple path(fasta), path(fai), path(dict)
        path template

    output:
        tuple val(meta), path("reconcnv"), emit: dir

    stub:
        """
        mkdir -p reconcnv && echo '<html><body>stub</body></html>' > reconcnv/${meta.id}.reconcnv.html
        """

    script:
        def sex = meta.sex ?: 'unknown'
        def gender_arg = (meta.sex in ['male', 'female']) ? "-z ${meta.sex}" : ''
        """
        set +e
        mkdir -p reconcnv recon_in
        prep_reconcnv_inputs.py --cnr ${cnr} --cns ${cns} --vcf ${vcf} --fai ${fai} \\
            --template ${template} --outdir recon_in --sex ${sex} > ${meta.id}.reconcnv.log 2>&1
        rc=\$?
        RATIO=\$(ls recon_in/*ratio* 2>/dev/null | head -1 || true)
        GENOME=\$(ls recon_in/*genome* 2>/dev/null | head -1 || true)
        SEG=\$(ls recon_in/*seg* 2>/dev/null | head -1 || true)
        HETVCF=\$(ls recon_in/*.vcf recon_in/*.vcf.gz 2>/dev/null | head -1 || true)
        CONF=\$(ls recon_in/*.json 2>/dev/null | head -1 || true)
        if [ "\$rc" -eq 0 ] && [ -n "\$RATIO" ] && [ -n "\$GENOME" ] && [ -n "\$CONF" ]; then
            SEG_ARG=""; [ -n "\$SEG" ] && SEG_ARG="-s \$SEG"
            VCF_ARG=""; [ -n "\$HETVCF" ] && VCF_ARG="-v \$HETVCF"
            python ${projectDir}/tools/reconcnv/reconCNV.py -r \$RATIO -x \$GENOME -c \$CONF \\
                -d reconcnv -o ${meta.id}.reconcnv.html \$SEG_ARG \$VCF_ARG ${gender_arg} >> ${meta.id}.reconcnv.log 2>&1
            rc=\$?
        fi
        set -e
        if [ "\$rc" -ne 0 ] || [ ! -s reconcnv/${meta.id}.reconcnv.html ]; then
            echo "[warn] reconCNV failed for ${meta.id} (rc=\$rc); see ${meta.id}.reconcnv.log"
            printf '<html><body><p>reconCNV did not complete for %s (rc=%s). Inputs found: ratio=%s genome=%s seg=%s vcf=%s config=%s. See the task log.</p></body></html>' \\
                "${meta.id}" "\$rc" "\$RATIO" "\$GENOME" "\$SEG" "\$HETVCF" "\$CONF" > reconcnv/${meta.id}.reconcnv.html
        fi
        cp ${meta.id}.reconcnv.log reconcnv/ 2>/dev/null || true
        """
}
