# CNV_BLACKLIST_V1 -- panel gene blacklist for CNV calling -- 2026-09-07

assets/twist_myeloid/cnv_gene_blacklist.tsv (gene, reason, evidence, added):
genes listed get consensus_call BLACKLISTED, tier NA, support 0 in
CNV_CONSENSUS_MULTI; every arm's raw value stays in the row for audit.
EXON_PLOTS never draws a chromosome because of a blacklisted gene. The file
is optional per panel; adding a gene is one line.

Initial entries: SUZ12 (SUZ12P1 paralog; fixed-exon duplication in 3/8
validation cases, LOO calls in both directions in 5/23 male normals) and
ELANE (GC-rich 19p13.3; CNVkit-only +0.2 in 2/8 with GATK flat). BTG1 is
deliberately not listed: varying magnitude across cases and clean normals.

Placement (repo root):
    cp <bundle>/assets/twist_myeloid/cnv_gene_blacklist.tsv assets/twist_myeloid/
    cp <bundle>/tools/patches/2026-09-07/patch_cnv_gene_blacklist.py tools/patches/2026-09-07/
    python3 tools/patches/2026-09-07/patch_cnv_gene_blacklist.py [--apply]
Files patched: bin/cnv_consensus_multi.py, modules/local/cnv_consensus_multi.nf,
bin/plot_exon_ratio_batch.py, modules/local/exon_plots.nf, workflows/tspipe.nf.
Module inputs change, so a resume by session uuid re-runs the consensus and
the plots for every case.
