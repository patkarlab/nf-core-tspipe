/*
 * modules/local/cava.nf  (CAVA_V1b, N3)
 *
 * Annotate the post-MNV SomaticSeq consensus VCF with CAVA 2.0.15 (Clinical
 * Annotation of VAriants; sicotteh/CAVA, the maintained Python 3 successor of
 * RahmanTeam/CAVA). CAVA echoes every input record back with CAVA_* INFO
 * tags: CSN (clinical sequencing nomenclature), full HGVSc/HGVSp/HGVSg, CLASS
 * / SO / IMPACT, and ALTANN, the alternative annotation for indels whose HGVS
 * depends on left- versus right-alignment. VEP_ANNOTATE takes this VCF as a
 * second input and annotate.py merges the tags into CAVA_* columns.
 *
 * Transcript catalog: MANE 1.5 GRCh38 RefSeq (assets/cava/mane-1.5-grch38-refseq,
 * fetched by tools/fetch_cava_catalog.py; see PROVENANCE.txt there). This is the
 * same MANE 1.5 the clinical table already reports on, so the two agree on
 * transcript identity by construction.
 *
 * Container: 'local/cava:v2.0.15', built from containers/cava/Dockerfile. Under
 * the docker profile that tag is used directly; under the singularity profile
 * Nextflow looks in singularity.cacheDir for the converted image
 * local-cava-v2.0.15.img before attempting a pull (same convention as
 * local/flt3_itd_ext:v0.2). See the Dockerfile header for both commands.
 *
 * Inputs:
 *   vcf            -- SomaticSeq consensus VCF (MNV_MERGE output)
 *   fasta+fai+dict -- reference genome
 *   catalog_dir    -- directory holding the four catalog files (.gz .gz.tbi .txt .cesis)
 *   config_tpl     -- assets/cava/cava_config.template.txt
 *
 * Output:
 *   ${meta.id}.cava.vcf  -- input VCF with CAVA_* INFO tags
 *   versions.yml
 */

process CAVA {
    tag        "${meta.id}"
    label      'process_low'
    container  'local/cava:v2.0.15'

    input:
        tuple val(meta), path(vcf)
        tuple path(fasta), path(fai), path(dict)
        path catalog_dir
        path config_tpl

    output:
        tuple val(meta), path("${meta.id}.cava.vcf"), emit: vcf
        path "versions.yml",                          emit: versions

    stub:
        """
        cp ${vcf} ${meta.id}.cava.vcf
        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            stub: true
        END_VERSIONS
        """

    script:
        """
        # CAVA_V1b (N3): CAVA 2.0.15, MANE 1.5 RefSeq catalog; config from the asset template
        CATALOG=\$(ls ${catalog_dir}/*.gz | head -n 1)
        sed -e "s#__REFERENCE__#\$(readlink -f ${fasta})#" \\
            -e "s#__CATALOG__#\$(readlink -f \${CATALOG})#" \\
            ${config_tpl} > cava_config.txt

        cava -c cava_config.txt -i ${vcf} -o ${meta.id}.cava

        # CAVA writes <prefix>.vcf; fail loudly if it silently produced nothing
        test -s ${meta.id}.cava.vcf

        cat <<-END_VERSIONS > versions.yml
        "${task.process}":
            cava: \$(cava --version 2>&1 | tail -n 1)
            cava_catalog: \$(basename \${CATALOG})
        END_VERSIONS
        """
}
