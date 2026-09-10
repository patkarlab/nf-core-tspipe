# Memo 18 — MoChA on 17p: feasibility test, negative at the current site density (2026-09-09, evening)

Repo `/goast/hemat_data/nf-core-tspipe`, base dc05523. Everything below was run offline under
`/tmp/mocha17/` on run8 sample 26CGH1250-TwistMyVal (clonal 17p and 17q GAIN, purity 0.65 —
the positive control the handoff named) and 26CGH60-TwistMyVal (diploid 17, control).
Artefacts are committed with this memo; the outputs are under `docs/audit/2026-09-09/mocha17p/`.

## 1. What was built

- `containers/mocha/Dockerfile` → `local/mocha:v1` (bcftools 1.20 + MoChA plugins at
  freeseek/mocha commit 95686b7, plugin version 2025-08-19; SHAPEIT5 5.1.1 from bioconda;
  python3). Sources are fetched on the host into `containers/mocha/src/` (gitignored,
  md5-checked) because GitHub is unreliable from inside `docker build` on gandalf.
  Exported as `singularity_cache/local-mocha-v1.img` (227 MB) by
  `tools/patches/2026-09-09/build_mocha_v1.sh`; smoke tests pass under Docker and Singularity.
- 1000G high-coverage phased panel, chr17 (20220422_3202 release, 861,943,967 bytes + .tbi)
  and the SHAPEIT b38 chr17 genetic map under `/goast/hemat_data/references/1000G_hg38_phased/`.
  The EBI transfer stalled repeatedly at 0.1–0.5 MB/s; `tools/patches/2026-09-09/
  fetch_1kg_chr17_parallel.sh` finished it with eight parallel HTTP ranges (~1 MB/s).
- `assets/twist_myeloid/snp_sites.baf.chr17.panel_alleles.tsv`: the 1,277 biallelic 1000G SNPs
  inside the 470 chr17 catalog intervals (REF/ALT/ID from the panel).
- `bin/baf_genotypes_vcf.py` v1.3: single-sample genotype VCF (GT:AD:DP:RAD) at catalog sites
  from the GATK allelic counts. Sites: 1-bp backbone rows as such; the 370 `Twist17p_rs*` rows
  are 120-bp windows, so their sites are the panel SNPs inside each window (fallback: background
  informative rows, then window centre). Alleles: name → panel table → counts. Reference-bias
  correction: cohort het-like median where usable (≈42 sites), otherwise a sample-level global
  term (median raw AF of ~1,480 het backbone sites on the other autosomes: 0.473 / 0.475, i.e.
  ~2.6 % reference bias). Sites absent from the panel are dropped (`--require-alleles`).
- `tools/patches/2026-09-09/mocha17_offline.sh`: bgzip + `+fill-tags AC,AN` (SHAPEIT5 requires
  them) → `phase_common` against the panel → AD/DP/RAD annotated back (phase_common keeps GT only)
  → INFO/GC (`+mochatools`) → `+mocha -g GRCh38 --LRR-weight 0` → per-arm phased-BAF summary.

## 2. Result

26CGH1250: 1,234 sites written (149 het), all phased in 251 s on 8 threads; 2,072,390
reference-only sites dropped by SHAPEIT5. MoChA (417 sites after its 400-bp thinning, 71 hets)
returned no call. Its BAF concordance statistic was 0.500 (random). Per arm, with
pBAF = ±(BAF − 0.5) signed by the phased genotype:

| arm | phased hets | mean pBAF | mean \|pBAF\| |
|---|---|---|---|
| 17p | 115 | −0.021 | 0.124 |
| 17q | 34 | +0.028 | 0.092 |

The allelic imbalance is present at full strength (0.124 is the expected deviation of a clonal
gain at purity 0.65); its sign is random, i.e. the phase carries no haplotype information at
the spacing of the hets. Sign concordance of consecutive 17p hets by distance (the clonal
gain acts as ground truth for the sign, so concordance ≈ phasing accuracy):

| distance | pairs | concordance |
|---|---|---|
| < 1 kb | 23 | 1.00 |
| 1–20 kb | 5 | 1.00 |
| 20–100 kb | 42 | 0.71 |
| > 100 kb | 44 | 0.59 |

Phasing is correct locally and decays with distance; a given sample is het at about one 17p
site per 190 kb, so nearly every consecutive pair sits in the ≥ 20 kb bins. This is a property
of the site density (reference-panel phasing can only follow haplotype matches at genotyped
positions), not of the tool, the panel or the population.

## 3. Conclusion

- The phased-BAF advantage of MoChA does not exist on this panel; at the fractions it does
  detect (clonal), BAF_V2, PURPLE and PureCN already agree. A seventh arm M would be a
  correlated vote on the same allelic counts, empirically weaker (no call on a clonal event).
  **M is parked; no module is wired.**
- What would revive it: (a) common SNPs every 3–5 kb across 17p in the next panel design
  (goes into the Twist letter with the table above as the evidence line); (b) phasing from the
  off-target reads (GLIMPSE2-style imputation against the same panel) if the off-target depth
  is ≥ ~0.5× — one measurement on a run8 BAM, not yet done.
- BAF_V2's own floor: the noise arithmetic (per-het σ ≈ 0.06 on 17p from the control after
  correction; n ≈ 115) puts unphased detection at ~10 % cell fraction now and ~5 % if the
  per-site σ halves after A3. **These are estimates; no dilution series has been run, and no
  sensitivity or false-positive rate at 10 % has been measured.**

## 4. Follow-ups (handoff v2)

1. TP53 observation block on the dashboard (variant + VAF; 17p total CN, allelic state,
   fraction, informative SNPs, scope, confidence; interpretation line per Nikhil's rules).
2. In-silico dilution of BAF_V2 on 17p (resampled ALT counts at het sites of a diploid sample
   at 2/5/10/15/20 %; false positives on the clean run8 samples) — the number behind "10 %".
3. A3 as a site-level assay model (het-only background, site classes, bias blacklist).
4. BAF_V2c: beta-binomial on counts with per-site φ shrunk towards the panel estimate;
   sub-arm segmentation.
