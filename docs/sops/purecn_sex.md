# PCN_SEX_V1 -- PureCN NormalDB by sex (item 5) -- 2026-09-06

Two patchers, one marker (MARKER PCN_SEX_V1):

1. tools/patches/2026-09-06/patch_build_purecn_normaldb_sex.py
   -> tools/build_purecn_normaldb.sh gains --sex male|female (default male;
   default sheet twist_normals_48_v4.csv). Per-stratum: BAM selection,
   coverage list (from the sheet, not ls of the shared coverage/ dir),
   NormalDB output dir $WORKDIR/normaldb_<sex>, --assay twist_myeloid /
   twist_myeloid_female, md5 purecn_normaldb[_female].md5. Coverage files
   are per sample and shared between strata; existing male ones are reused.
   Female floor n>=6 (we have 8); PureCN runs with --force. Caveat: eight
   normals give less stable interval weights than the male 23.

2. tools/patches/2026-09-06/patch_purecn_sex_v1.py (three files, all-or-nothing)
   -> conf/twist_apply.config: purecn_normaldb_female
   -> workflows/tspipe.nf: ch_purecn_normaldb_female via sexstratFemale();
      the male file is used with one log.warn until the female asset exists
   -> modules/local/purecn.nf: second input staged under female_stratum/;
      stratum = meta.sex or params.cnv_sex_fallback; [SEXSTRAT] echo.
   Requires SEXSTRAT_V1 (applied earlier today).

Order: apply both patchers (dry run first), stub-run, then build the female
DB; the pipeline picks the new asset up on the next launch (value channel
resolved at start).

Female build (about 10-15 min: 8 Coverage.R in parallel + NormalDB.R):
    setsid bash -c 'cd /goast/hemat_data/nf-core-tspipe; bash tools/build_purecn_normaldb.sh --sex female' > /tmp/purecn_female_build.log 2>&1 & disown
Expected in assets/twist_myeloid/: normalDB_twist_myeloid_female_hg38.rds,
interval_weights_twist_myeloid_female_hg38.png, purecn_normaldb_female.md5.
