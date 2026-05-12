/*
 * modules/local/deepsomatic.nf
 *
 * Google DeepSomatic v1.10 in WES_TUMOR_ONLY mode.
 *
 * Key differences from production scripts/06_variant_callers.py run_deepsomatic():
 *   - WES_TUMOR_ONLY model (production used WGS + matched normal BAM, which
 *     we don't have for this panel)
 *   - --use_default_pon_filtering=true: filters germline using DeepSomatic's
 *     bundled PoN VCF (dbSNP + gnomAD + 1000G).
 *
 * Reference: https://github.com/google/deepsomatic/blob/r1.10/docs/deepsomatic-case-study-wgs-tumor-only.md
 *
 * Container: docker://google/deepsomatic:1.10.0 (~10 GB)
 * Runtime: 20-40 min on 600x panel BAM (neural-net inference is slow)
 */

process DEEPSOMATIC {
    tag        "${meta.id}"
    label      'process_medium'

    container  'docker://google/deepsomatic:1.10.0'

    input:
        tuple val(meta), path(bam), path(bai)
        tuple path(fasta), path(fai), path(dict)
        path  bed

    output:
        tuple val(meta), path("${meta.id}.deepsomatic.vcf.gz"),     emit: vcf
        tuple val(meta), path("${meta.id}.deepsomatic.vcf.gz.tbi"), emit: tbi
        path  "versions.yml",                                        emit: versions

    script:
        def model = task.ext.model_type ?: 'WES_TUMOR_ONLY'
        """
        mkdir -p logs intermediate

        run_deepsomatic \\
            --model_type=${model} \\
            --ref=${fasta} \\
            --reads_tumor=${bam} \\
            --output_vcf=${meta.id}.deepsomatic.vcf.gz \\
            --sample_name_tumor=${meta.id} \\
            --num_shards=${task.cpus} \\
            --logging_dir=logs \\
            --intermediate_results_dir=intermediate \\
            --use_default_pon_filtering=true \\
            --regions=${bed}

        # Drop heavy intermediates - keep only final VCF + tbi
        rm -rf intermediate logs

        cat <<-END_VERSIONS > versions.yml
        \"${task.process}\":
            deepsomatic: \$(run_deepsomatic --version 2>&1 | grep -oP 'DeepSomatic version \\K\\S+' | head -n1 || echo '1.10.0')
        END_VERSIONS
        """
}
