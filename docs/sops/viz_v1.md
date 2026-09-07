# VIZ_V1 -- styled CNVkit scatters and reconCNV in the pipeline and the CNV tab -- 2026-09-07

STYLED_SCATTER (CNVkit container): bin/cnvkit_scatter_styled.py --batch on the
CNVkit ratio, call.cns, annotated genemetrics and the raw Mutect2 VCF (BAF
panel) -> styled_scatter/{overview,per_chromosome,per_gene}/.
RECONCNV (host env 'reconCNV', py3.6 + bokeh 1.4): bin/prep_reconcnv_inputs.py
with assets/reconcnv/reconcnv_config_twist_myeloid.json, then
tools/reconcnv/reconCNV.py -> reconcnv/<sample>.reconcnv.html; a failure leaves
a placeholder HTML with the reason (never fatal).
Both published under <sample>/cnv_consensus_multi/, routed by ORGANIZE_OUTPUT
into clinical/cnv/{styled_scatter,reconcnv}/, parsed by parsers/cnv_v2.py and
shown between the tables and the chromosome pages: genome-wide scatter cards,
reconCNV iframe with an open-in-new-tab link, collapsed per-chromosome and
per-gene scatter galleries.

Files
    modules/local/styled_scatter.nf, modules/local/reconcnv.nf
    tools/patches/2026-09-07/patch_viz_v1.py   (tspipe.nf, twist_apply.config, organize_output.nf/.py, cnv_v2.py, template)

Placement (repo root)
    cp <bundle>/modules/local/styled_scatter.nf <bundle>/modules/local/reconcnv.nf modules/local/
    cp <bundle>/tools/patches/2026-09-07/patch_viz_v1.py tools/patches/2026-09-07/
    python3 tools/patches/2026-09-07/patch_viz_v1.py [--apply]
Prerequisite: conda env reconCNV (created 2026-09-07 from tools/reconcnv/environment.yml).
