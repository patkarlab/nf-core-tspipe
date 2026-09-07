# HMF_PURPLE_V1 -- AMBER/COBALT/PURPLE as consensus arm H (item 11) -- 2026-09-07

Per sample, tumour-only targeted mode, host env 'hmftools':
  HMF_AMBER   BAF at HMF germline het sites within 300 bp of a target (panel filters)
  HMF_COBALT  1 kb read-depth ratios, GC-normalised, corrected by the panel
              normalisation trained on the 31 normals, PCF gamma 50
  HMF_PURPLE  purity/ploidy fit, absolute + allele-specific CN per segment and
              gene, QC; charts off; no somatic/SV VCF in v1 (not used in the
              tumour-only fit). bin/purple_gene_table.py -> arm H contract:
              gene, h_call (sex-aware vs expected cn), h_cn_min/max, h_macn_min,
              h_loh; summary with status, purity, ploidy, gender, trusted.
Consensus (CMX schema v4): H is an independent arm like P (trusted unless the
PURPLE status has FAIL_); h_loh with neutral cn is cnLOH support. Gated in
tspipe.nf on params.hmf_resources and the normalisation asset existing;
empty placeholders otherwise. Outputs under <sample>/cnv_hmftools/.

Files
    bin/purple_gene_table.py
    modules/local/hmf_amber.nf, hmf_cobalt.nf, hmf_purple.nf
    tools/patches/2026-09-07/patch_hmf_purple_v1.py  (consensus script + module, tspipe.nf, twist_apply.config)

Placement (repo root)
    cp <bundle>/bin/purple_gene_table.py bin/ && chmod +x bin/purple_gene_table.py
    cp <bundle>/modules/local/hmf_*.nf modules/local/
    cp <bundle>/tools/patches/2026-09-07/patch_hmf_purple_v1.py tools/patches/2026-09-07/
    python3 tools/patches/2026-09-07/patch_hmf_purple_v1.py [--apply]

Known unknowns for the first real run: AMBER 4.3's -loci with the
AmberGermlineSites TSV (if it insists on a VCF, convert); COBALT/PURPLE
argument names in 3.0/4.4; the sex-chromosome handling on our alt-aware
BAMs. Each tool writes <id>.<tool>.log in its task directory.
