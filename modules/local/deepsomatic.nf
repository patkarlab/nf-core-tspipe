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
 *
 * Output filter semantics (matches production scripts/06_variant_callers.py):
 *   Raw DeepSomatic output contains all FILTER tags (typical 500+ records:
 *   PASS / GERMLINE / RefCall / NoCall / PON). Feeding all of these into
 *   SomaticSeq as a single "DeepSomatic" caller channel pollutes the
 *   ensemble with germline calls. Production filters to PASS-only before
 *   handing to SomaticSeq; this module mirrors that by emitting:
 *     vcf      = PASS-only (primary; what SomaticSeq subworkflow consumes)
 *     vcf_raw  = unfiltered (audit trail; written to results/ but not piped
 *                onward)
 *
 *   On a typical myeloid panel sample, expect ~500 raw / ~5-20 PASS.
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
        // Primary outputs: PASS-only (consumed by SomaticSeq subworkflow)
        tuple val(meta), path("${meta.id}.deepsomatic.vcf.gz"),         emit: vcf
        tuple val(meta), path("${meta.id}.deepsomatic.vcf.gz.tbi"),     emit: tbi
        // Audit outputs: raw VCF with all FILTER tags (PASS/GERMLINE/RefCall/NoCall/PON)
        tuple val(meta), path("${meta.id}.deepsomatic.raw.vcf.gz"),     emit: vcf_raw
        tuple val(meta), path("${meta.id}.deepsomatic.raw.vcf.gz.tbi"), emit: tbi_raw
        // Filter accounting (one row per FILTER tag, for QC roll-ups)
        tuple val(meta), path("${meta.id}.deepsomatic.filter_counts.tsv"), emit: filter_counts
        path  "versions.yml",                                              emit: versions

    script:
        def model = task.ext.model_type ?: 'WES_TUMOR_ONLY'
        """
        mkdir -p logs intermediate

        # 1. DeepSomatic inference - writes raw VCF (all FILTER tags)
        run_deepsomatic \\
            --model_type=${model} \\
            --ref=${fasta} \\
            --reads_tumor=${bam} \\
            --output_vcf=${meta.id}.deepsomatic.raw.vcf.gz \\
            --sample_name_tumor=${meta.id} \\
            --num_shards=${task.cpus} \\
            --logging_dir=logs \\
            --intermediate_results_dir=intermediate \\
            --use_default_pon_filtering=true \\
            --regions=${bed}

        # Drop heavy intermediates - keep only final VCFs + tbis
        rm -rf intermediate logs

        # 2. Tally FILTER tag distribution for QC (raw VCF)
        zcat ${meta.id}.deepsomatic.raw.vcf.gz \\
            | awk 'BEGIN{OFS="\\t"; print "filter_tag","count"} \\
                   /^#/ {next} \\
                   {c[\$7]++} \\
                   END{for (k in c) print k, c[k]}' \\
            | sort -k2,2nr \\
            > ${meta.id}.deepsomatic.filter_counts.tsv

        # 3. PASS-only filter (matches production behavior)
        zcat ${meta.id}.deepsomatic.raw.vcf.gz \\
            | awk '/^#/ || \$7=="PASS"' \\
            | bgzip -c \\
            > ${meta.id}.deepsomatic.vcf.gz
        tabix -p vcf ${meta.id}.deepsomatic.vcf.gz

        # 4. Stderr summary so the Nextflow log shows what was filtered
        RAW_N=\$(zcat ${meta.id}.deepsomatic.raw.vcf.gz | grep -cv '^#' || echo 0)
        PASS_N=\$(zcat ${meta.id}.deepsomatic.vcf.gz     | grep -cv '^#' || echo 0)
        echo "[DEEPSOMATIC ${meta.id}] raw=\${RAW_N}  pass=\${PASS_N}" 1>&2
        echo "[DEEPSOMATIC ${meta.id}] filter tag breakdown:" 1>&2
        cat ${meta.id}.deepsomatic.filter_counts.tsv 1>&2

        cat <<-END_VERSIONS > versions.yml
        \"${task.process}\":
            deepsomatic: \$(run_deepsomatic --version 2>&1 | grep -oP 'DeepSomatic version \\K\\S+' | head -n1 || echo '1.10.0')
        END_VERSIONS
        """
}
