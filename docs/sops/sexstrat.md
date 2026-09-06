# SEXSTRAT_V1 -- sex-stratified reference selection (item 4) -- 2026-09-06

One patcher, nine files, one marker per file (two in tspipe.nf). Dry run by
default; --apply writes with .bak_sexstrat_<ts> backups only if every anchor
matched in every file.

What changes
- nextflow.config: params cnv_loo_summary_female, cnv_noisy_bins_female
  (null -> assets/<panel>/*_female.* fallback) and cnv_sex_fallback ('male').
- conf/twist_apply.config: cnv_gatk_pon_female -> gatk_rc_pon_female.hdf5.
- workflows/tspipe.nf: sexstratFemale() resolves each female asset, falling
  back to the male file with one log.warn when a panel has no _female asset
  (legacy panels keep today's behaviour); three call sites gain the extra
  channels at the END of their argument lists.
- subworkflows: cnv_calling.nf and gatk_cnv_calling.nf take and pass through.
- modules: CNVKIT (PoN + LOO + noisy bins), CNV_ANNOTATE (LOO),
  CNV_CONSENSUS_MULTI (LOO), GATK_CNV_DENOISE (PoN) each gain a second
  input staged under female_stratum/ and choose the stratum per sample:
      stratum = meta.sex if male/female else params.cnv_sex_fallback
  Each task echoes "[SEXSTRAT] <id>: sex=... stratum=... pon=..." to
  .command.log; CNVKIT warns to stderr when the fallback was used.
- Unchanged on purpose: ZSCORE_CNV and CNV_PLOTS (both scheduled for
  removal, items 7 and 12) keep the male LOO summary until then.

Consequences
- Task hashes of the four modules change; -resume on an existing run
  re-executes the CNV block (not preprocessing or SNV calling).
- Editing these files does not affect a run already in progress; Nextflow
  compiled its DAG at launch.

Apply (repo root)
    cp <inbox>/tools/patches/2026-09-06/patch_sexstrat_v1.py tools/patches/2026-09-06/
    python3 tools/patches/2026-09-06/patch_sexstrat_v1.py          # dry run
    python3 tools/patches/2026-09-06/patch_sexstrat_v1.py --apply

Validate
    -stub-run on pon_samplesheets/twist_val_1_fastq.csv: exit 0, no Error
    lines, and `ls` of a CNVKIT stub task dir shows female_stratum/ with the
    female LOO and noisy-bin files beside the male ones.
    Real: grep "[SEXSTRAT]" in the CNVKIT / GATK_CNV_DENOISE .command.log
    of the validation run; stratum must match the resolved sex.

Follow-ups
- Item 5: PureCN normalDB by sex (tools/build_purecn_normaldb.sh --sex,
  purecn.nf selection) -- same pattern.
- Item 7: remove ZSCORE_CNV, CNV_CONCORDANCE, CNV_CLINICAL_REPORT; TIER_1
  on K/G/BAF/P/E in cnv_consensus_multi.py and the dashboard table.
