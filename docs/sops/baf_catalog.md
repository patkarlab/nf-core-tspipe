# BAF_CATALOG_V1 -- genome-wide BAF site catalog from the normals -- 2026-09-07

Evidence: one normal carries 1,550 heterozygous SNPs at >= 50x across the
panel's incidental SNPs (19-127 per chromosome), so arm-level allelic
verdicts are possible genome-wide without new probes. The 17p block stays.

Files
    bin/discover_hets.sh            per-BAM het SNP candidates (bcftools; per chromosome in parallel)
    bin/merge_het_sites.py          catalog merge rule; base 17p windows preserved; 1-bp intervals for new sites
    modules/local/bpt_discover_hets.nf, modules/local/bpt_merge_het_sites.nf
    tools/patches/2026-09-07/patch_baf_catalog_v1.py   workflows/build_pon_twist.nf

Rule: kept when het (alt fraction 0.20-0.80, depth >= 50) in >= 3 include_in_pon
normals; chrX counted from females only; chrY skipped; PARALOG_LIMITED exons
excluded; sites inside base windows not duplicated. Background cohort -> 'all'
(per-site depth filter; chrX informative from the females).

Build (resume of the v4 session; discovery runs on all 48 rows, then allelic
counts and aggregation re-execute; the strata references are cached):
    setsid bash -c 'cd /goast/hemat_data/nf-core-tspipe; NXF_CACHE_DIR=/home/hemat/.nextflow_cache_bpt nextflow run main.nf -entry BUILD_PON_TWIST -profile gandalf -c conf/twist_pon_noncontainer.config --pon_input pon_samplesheets/twist_normals_48_v4.csv --outdir /goast/hemat_data/pon_twist/build_v4 --keep_intermediates true -w /goast/hemat_data/pon_twist/work_v4 -resume 08e829f0-0a33-4cd3-b60a-d1ae8f9f889e' > /tmp/pon_build_bafcat.log 2>&1 & disown

Outputs to seed into assets/twist_myeloid/ (with md5 and versions note):
snp_sites.baf.bed (v2), het_catalog.tsv, baf_background.tsv (v2). The
existing 17p detector keeps working on the v2 catalog (it filters chr17
itself); BAF_V2 detector follows.
