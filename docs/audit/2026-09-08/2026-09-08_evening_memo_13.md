# Memo 13 — 2026-09-08 evening — D13 Spike-in tab (SPIKEIN_V1 / V1b)

Repo /goast/hemat_data/nf-core-tspipe, start HEAD f830536 (memo 12). Run8 session
abea2914-e2f9-44c0-961a-2f9c50eab4d9; two resumes this session, 18 tasks each
(SPIKEIN_SITES 8, ORGANIZE_OUTPUT 8, DASHBOARD, REPORT_BUNDLE), 408 cached.

## 1. Design corrections made before writing code

- The spike-in design table exists only in GRCh37 (17 rows, Twist target windows). In the
  hg38 Main probe BED (probes_ok_ACTREC_Myeloid_TE-99430185_hg38_Main_260602213057.bed,
  still untracked at the repo root) each `*_SNP_rs*` probe is centred on its SNP: position =
  probe start + 61 (1-based). The positions in the 09-09 handoff and N8 (8059903, 61950284,
  61963757, 50398545) were probe starts, not SNP positions. Verified against dbSNP GRCh38:
  rs3781093 chr10:8059964, rs10994982 chr10:61950345, rs11978267 chr7:50398606.
- The probe labelled rs63723577 is centred on chr10:61963818 = rs10821936, the canonical
  ARID5B childhood-ALL risk SNP; rs63723577 is treated as an alias.
- The GATA3_intronic probe (chr10:8062184–8062304) is centred on rs3824662 (chr10:8062245),
  the BCR::ABL1-like ALL risk SNP. It has no probe of its own and is the fifth genotype site.
- Region coverage already flows through targets.exonwise.bed → MOSDEPTH → exon_coverage.tsv
  (8 rows with Exon "-"), so SPIKEIN_SITES needs no mosdepth call. The handoff's mosdepth arm
  was dropped.
- The "ANKRD26 5'UTR indel" chr10:27066474 CCATAG>C in the handoff is in the ANKRD26_exon_11
  interval (27066464–27066584), 34 kb from ANKRD26_5UTR. It is correctly outside the tab; it
  belongs to the consequence-filtered-calls-at-exons question (N2/N3), not D13.

## 2. What was built (commit after memo 12)

New: assets/twist_myeloid/spikein_regions.tsv (SPIKEIN_V1; 8 regions named as in exonwise,
5 SNP sites, risk alleles filled for rs3824662 A, rs10821936 C, rs11978267 G);
modules/local/spikein_sites.nf; bin/spikein_sites.py (stdlib, Python 3.6, GATK container);
bin/dashboard_builder/parsers/spikein.py; docs/sops/spikein_tab.md;
tools/patches/2026-09-08/patch_spikein_v1.py (7 files, 20 single-line anchors) and
patch_spikein_v1b.py.

Patched: preprocessing.nf (include, SPIKEIN_SITES on ABRA2.out.bam + reference_ch + asset-or-[],
withResolvedSex, emit spikein); tspipe.nf (.join(PREPROCESSING.out.spikein) last on ch_organize);
organize_output.nf (path(spikein) last in the tuple, --spikein-snps, stub touch);
organize_output.py (hardlink to clinical/<S>.spikein_snps.tsv); dashboard.nf
(--spikein-regions when assets/<panel>/spikein_regions.tsv exists); build.py
(ctx["spikein"], None without the asset); sample_report.html.j2 (nav item, tab with three
tables, DataTable init).

V1b: alt allele reported only at ≥ 2% AF. CollectAllelicCounts reports the commonest
non-reference base, so hom_ref sites at 1100x showed "C>T" from error reads (26CGH799/885).

Offline check before the first resume: CollectAllelicCounts + spikein_sites.py in the GATK
image against the cached 26CGH1250 final BAM, from the SEX_CHECK task directory (found by
its *.sexcheck.allelicCounts.tsv output — the ORGANIZE task also stages sex_check.tsv and
sorts first by mtime; and the reference is the -R argument of .command.sh, not a *.fa in the
task directory). Result reproduced exactly by the pipeline run.

## 3. Run8 results

- 40/40 sites OK at 1000–1900x. Genotypes: 1043 GATA3 het / ARID5B rs10821936 het;
  1250 IKZF1 het, rs10821936 C/C (2 risk copies); 1292 IKZF1 het; 132 GATA3 A/A, rs10821936 het,
  IKZF1 het; 1480 GATA3 A/A; 60 GATA3 het, rs10821936 het; 799 none; 885 rs10821936 het,
  IKZF1 G/G. rs3824662 and rs3781093 track in all eight (LD) — an internal position check.
- No region below 200x in any sample (DKC1_5UTR clears it in males).
- Calls inside regions, 3–5 per sample, all TERC plus one GATA2 intron 4 2% single-caller
  blip: chr3:169764547 T>C COMMON_POLYMORPHISM (gnomAD 0.57; 1043, 60, 799) and two
  systematic artefacts in 8/8 tumours — chr3:169765047 A>C (1 caller, 7–9%) and
  chr3:169765728 A>AT / AT>A (homopolymer, up to 3 callers, 5–12%) — both LOW_IMPACT, both
  absent from references/variant_pon_cohort_table.tsv and blacklist_file.tsv.

## 4. Register deltas

Closed: D13.
N8: replace the four probe-start coordinates with the five centred SNP positions above when
adding the sites to targets.exonwise.bed.
N13 (new follow-up): the two TERC loci are in 8/8 tumours but not in the 48-normal cohort
table — establish whether the normals' filtered tables never carried them (LOW_IMPACT rows
dropped before the builder read them) or the builder's disposition rules excluded them.
N10: the two probes_ok_*.bed files are now cited as provenance by the asset; decision on
tracking them (suggested assets/twist_myeloid/probes/) still pending. Delete
/goast/hemat_data/tmp_spikein.
A-list (Nikhil): risk alleles for rs3781093 and rs10994982 (asset column, 18-task resume);
whether the germline risk genotypes should appear on the Reporting page or stay on the tab.

## 5. Operating notes added

- A second `nextflow run -resume` on the same session fails on the cache LOCK; kill the Java
  process of the stale run (pgrep pattern) and confirm `lsof …/db/LOCK` is empty before
  relaunching. `setsid … & disown` keeps Ctrl-C on a foreground `sleep` from touching the run.
- Verification commands must carry resolved paths; a placeholder such as `<run8 outdir>` breaks
  the shell line and empties every glob after it. The outdir is recoverable from
  `.nextflow.log` (`--outdir` argument of the launch line).
