/*
 * modules/local/vardict.nf
 *
 * VarDict somatic caller with teststrandbias.R + var2vcf_valid.pl pipe.
 * Mirrors scripts/06_variant_callers.py run_vardict() exactly:
 *
 *   VarDict -G ref -f 0.03 -N sample -b bam -O 50 -c 1 -S 2 -E 3 -g 4 bed
 *     | sed '1d' > raw.tsv
 *   teststrandbias.R < raw.tsv | var2vcf_valid.pl -N sample -E -f 0.03 > vcf
 *
 * The two helper scripts (teststrandbias.R, var2vcf_valid.pl) ship inside the
 * VarDictJava install. On a new server, point ext.vardict_helpers_dir at
 * wherever you installed them, OR install vardict-java via bioconda (which
 * places them on PATH).
 *
 * Fallback: if teststrandbias.R fails (R crashes, no R available), runs
 * var2vcf_valid.pl directly on the raw TSV.
 */

process VARDICT {
    tag        "${meta.id}"
    label      'process_medium'

    input:
        tuple val(meta), path(bam), path(bai)
        tuple path(fasta), path(fai), path(dict)
        path  bed

    output:
        tuple val(meta), path("${meta.id}.vardict.vcf"), emit: vcf
        path  "versions.yml",                             emit: versions

    script:
        // gandalf.config sets ext.vardict_helpers_dir for site-specific paths
        def helpers = task.ext.vardict_helpers_dir ?: ''
        def strandbias = helpers ? "${helpers}/teststrandbias.R" : 'teststrandbias.R'
        def var2vcf    = helpers ? "${helpers}/var2vcf_valid.pl" : 'var2vcf_valid.pl'
        def min_vaf    = task.ext.min_vaf ?: '0.03'
        def min_mq     = task.ext.min_mq  ?: '50'
        """
        # Step 1: VarDict generates a tab-separated raw TSV
        vardict-java \\
            -G ${fasta} \\
            -f ${min_vaf} \\
            -N ${meta.id} \\
            -b ${bam} \\
            -O ${min_mq} \\
            -c 1 -S 2 -E 3 -g 4 \\
            -th ${task.cpus} \\
            ${bed} \\
          | sed '1d' > ${meta.id}.vardict_raw.tsv

        # Step 2: strand-bias test + VCF conversion. Fall back if R is fragile.
        if ${strandbias} < ${meta.id}.vardict_raw.tsv \\
             | ${var2vcf} -N ${meta.id} -E -f ${min_vaf} \\
             > ${meta.id}.vardict.vcf 2>strandbias.err
        then
            # Check the VCF actually has variant lines (R can succeed but emit nothing)
            VARIANT_COUNT=\$(grep -cv '^#' ${meta.id}.vardict.vcf || true)
            if [ "\$VARIANT_COUNT" -eq 0 ] && [ -s ${meta.id}.vardict_raw.tsv ]; then
                echo "[VarDict] teststrandbias.R emitted empty VCF; trying fallback" >&2
                ${var2vcf} -N ${meta.id} -E -f ${min_vaf} \\
                    < ${meta.id}.vardict_raw.tsv \\
                    > ${meta.id}.vardict.vcf
            fi
        else
            echo "[VarDict] teststrandbias.R failed (see strandbias.err); using fallback" >&2
            ${var2vcf} -N ${meta.id} -E -f ${min_vaf} \\
                < ${meta.id}.vardict_raw.tsv \\
                > ${meta.id}.vardict.vcf
        fi

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            vardict-java: \$(vardict-java 2>&1 | grep -oP '[Vv]ar[Dd]ict_v\\K[^ ]+' | head -n1 || echo unknown)
        END_VERSIONS
        """
}
