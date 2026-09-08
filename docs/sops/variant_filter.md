# SOP — variant filtering to the clinical table (VARIANT_FILTER; 2026-09-08)

## Inputs
`<S>.somaticseq.annotated.tsv` from VEP_ANNOTATE (`bin/annotate.py`: SomaticSeq VCF + VEP + ANNOVAR
merged on the VCF record — ANNOVAR rows keyed on the `-vcfinput` Otherinfo columns since
ANNOVAR_KEY_V1; the log line "ANNOVAR merge: … orphan" must read 0 or near 0),
`references/blacklist_file.tsv`, `assets/myeloid_hotspots.tsv`.

## Outputs
`<S>.somaticseq.filtered.tsv` (every variant, `Filter` and `Variant_Class` columns, blacklist reason
and date) and `<S>.somaticseq.clinical.tsv` (`Filter == PASS`, sorted by gene), both published to
`clinical/`.

## Filter priority (bin/variant_filter.py, apply_filters)
0. BLACKLIST — matched an entry of `references/blacklist_file.tsv` (curated rows or the cohort rows below).
1. COMMON_POLYMORPHISM — `Max_AF` (VEP) > 0.01.
2. LOW_IMPACT — VEP IMPACT MODIFIER without a splice term.
2a. CLINVAR_BENIGN (D15) — ClinVar Benign / Likely_benign / Benign/Likely_benign; a hotspot residue is never demoted.
2b. NON_REPORTABLE_CONSEQUENCE — no reportable term (missense, nonsense, frameshift, in-frame, protein-altering,
    coding-sequence, canonical splice, and since D14 coding synonymous), unless ClinVar P/LP or a hotspot residue.
3. LOW_CALLERS — fewer than 2 callers (U2AF1 hotspots exempt).
4. LOW_DEPTH — fewer than 10 alt reads (U2AF1 hotspots exempt).
PASS otherwise. `Variant_Class` = nonsynonymous | splice | synonymous | other, from the VEP consequence.

## Cohort blacklist (VARIANT_PON_V1, N13)
Built from the 48 normals' `somaticseq.filtered.tsv` under `/goast/hemat_data/pon_twist/realign_v4{,_female}`:

    python3 tools/build_variant_pon_blacklist.py \
        --normals-dir /goast/hemat_data/pon_twist/realign_v4 --normals-dir /goast/hemat_data/pon_twist/realign_v4_female \
        --hotspots assets/myeloid_hotspots.tsv --blacklist references/blacklist_file.tsv \
        --report references/variant_pon_cohort_table.tsv          # add --dry-run to preview

Rules (same allele; coding/splice consequences; ≥ 5/48 normals): UBIQUITOUS_IN_NORMALS ≥ 50% of
normals at any VAF (caller-supported when median VAF < 25%); RECURRENT_IN_NORMALS_LOWVAF median
VAF < 25% with ≥ 2 callers in ≥ 5 normals; POPULATION_POLYMORPHISM_LOCAL median VAF ≥ 35%.
Single-caller-only loci and the 25–35% band are reported in the cohort table but not blacklisted.
Hotspot residues are never blacklisted and are printed for review (CHIP in normals is real).
Auto rows carry `[auto:VARIANT_PON_V1]` and are replaced on every rebuild; curated rows are kept.
Rebuild whenever the normal cohort, the panel or the callers change; commit the blacklist and the
cohort table together. Current build 2026-09-08: 259 rows (149 / 5 / 105).

## Reviewing what was removed
Sample report → "Blacklisted" tab (D16): every BLACKLIST row with reason, cohort count and VAF
range, date; the badge is the number with ≥ 2 callers. `somaticseq.filtered.tsv` has the same rows.

## Verifying a change offline (no Nextflow)
    A=$(ls -t work/*/*/<S>.annotated.tsv | head -1)             # newest annotated table
    mkdir -p /tmp/vf && cp -L $A /tmp/vf/<S>.somaticseq.annotated.tsv
    cd /tmp/vf && PATH=/goast/hemat_data/nf-core-tspipe/bin:$PATH \
      /home/hemat/anaconda3/envs/targeted-seq/bin/python /goast/hemat_data/nf-core-tspipe/bin/variant_filter.py \
      --sample <S> --outdir /tmp/vf --blacklist /goast/hemat_data/nf-core-tspipe/references/blacklist_file.tsv
Use `ls -t`, not `nextflow log`, to find the newest task: the log listing lags behind resumes.

## Re-running
`variant_filter.py` and `annotate.py` are unhashed `bin/` scripts: bump the bash comment in
`modules/local/variant_filter.nf` / `vep_annotate.nf`. A blacklist change re-executes VARIANT_FILTER
and everything downstream (VV, ONCOVI, FLT3_TO_VARIANTS, IGV_REPORTS, ORGANIZE, DASHBOARD, BUNDLE);
an `annotate.py` change adds VEP_ANNOTATE (long).
