# HMF_PANEL_V1 -- hmftools panel resources for the twist_myeloid panel -- 2026-09-07

Prerequisite: tools/hmftools/setup_hmftools.sh (env 'hmftools': AMBER 4.3,
COBALT 3.0, PURPLE 4.4; bundle hmf_pipeline_resources.38_v3.0.0--8).

tools/hmftools/build_panel_resources.sh (run from the repo root) trains the
COBALT target-regions normalisation on the 31 include_in_pon normals
(both strata; the sample-id CSV carries Gender, so AMBER is not needed for
training), prepares the sorted primary-contig target BED, and builds a
driver-gene-panel TSV for our genes from HMF's file (bin/make_driver_gene_panel.py:
HMF rows copied, missing genes templated with the role from
myeloid_driver_genes.tsv). Outputs in assets/twist_myeloid/hmftools/:
    target_regions.twist_myeloid.38.bed
    target_regions.cobalt_normalisation.twist_myeloid.38.tsv
    DriverGenePanel.twist_myeloid.38.tsv (+ .provenance.tsv)
    hmftools_panel.md5, versions.txt
Workdir /goast/hemat_data/pon_twist/hmftools_panel (COBALT per normal kept).

    setsid bash -c 'cd /goast/hemat_data/nf-core-tspipe; bash tools/hmftools/build_panel_resources.sh' > /tmp/hmf_panel_build.log 2>&1 & disown

Caveat recorded: training on normals assumes median copy number = ploidy,
which holds exactly for normals; HMF's cohort-percentile option
(--enable_cn_norm_with_wgs_pct) is for solid-tumour training sets and not used.
