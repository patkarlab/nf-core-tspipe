# BAF_V2 in-silico cnLOH dilution on 17p — 2026-09-10

The number behind any "BAF_V2 detects 17p LOH from about X %" statement. Handoff 2026-09-10 v2
section 2; detector `bin/baf_cnloh_detect.py` (BAF_V2, HEAD bb50be5) with its production
parameters unless stated (`--min-depth 20 --min-het-sites 10 --f-min 0.10 --noise-mult 2.5
--conf-min-het 20 --conf-mult 1.5`). Script `tools/patches/2026-09-10/simulate_17p_cnloh.py`,
driver `tools/patches/2026-09-10/run_dilution_17p.sh`; seed 20260910, so a re-run reproduces
these tables byte for byte.

## Set-up

Base sample 26CGH60-TwistMyVal (diploid 17; its real 9p deletion stays in every replicate).
- 26CGH60-TwistMyVal: 139 17p het sites in the unmodified sample (median depth 1342, min 106, max 2137); mode shift
- baseline 17p: verdict NEUTRAL f 0.068 n_het 139 noise_floor 0.0716 median_dev 0.0341
- baseline arms with a call: 9p:DEL(HIGH)

At each of those 139 sites the ALT count is redrawn as Binomial(depth, p), depth kept:

- **shift** (realistic): p = observed ALT fraction ± f/2, sign random per site (unphased). The
  sample's own site-level noise and reference bias are kept; the redraw adds one more round of
  counting noise (binomial sd 0.014 at 1,342x, small against the site noise below).
- **ideal** (counting noise only): p = cohort het centre ± f/2, where the centre is the cohort
  median ALT fraction when het-like (0.35–0.65) else 0.5, i.e. exactly what the detector
  subtracts. Shows what the panel would do if reference bias and site effects did not exist.

Every other site and every other arm is untouched, so the noise floor (2.5 x the median over
the other arms of their median mirrored deviation, 0.0286 for this sample) is the real one.
Level f = 0 redraws the same sites without a shift. 20 replicates per level. The four clean
run8 samples (26CGH1292, 26CGH1480, 26CGH799, 26CGH885) are run unmodified for the
false-positive side.

## Results

### shift, noise-mult 2.5 (production)

| imposed f | called / 20 | HIGH | LOW | f_estimate median (min–max) | median dev | noise floor | 17p het sites |
|---|---|---|---|---|---|---|---|
| 0.00 | 0 | 0 | 0 | 0.071 (0.061–0.078) | 0.036 | 0.072 | 139 |
| 0.02 | 0 | 0 | 0 | 0.071 (0.063–0.081) | 0.036 | 0.072 | 139 |
| 0.05 | 0 | 0 | 0 | 0.079 (0.068–0.093) | 0.040 | 0.072 | 138 |
| 0.08 | 0 | 0 | 0 | 0.098 (0.082–0.118) | 0.049 | 0.072 | 138 |
| 0.10 | 0 | 0 | 0 | 0.119 (0.095–0.128) | 0.059 | 0.072 | 138 |
| 0.12 | 2 | 0 | 2 | 0.133 (0.125–0.145) | 0.066 | 0.072 | 138 |
| 0.15 | 18 | 0 | 18 | 0.164 (0.140–0.193) | 0.082 | 0.072 | 137 |
| 0.20 | 20 | 3 | 17 | 0.210 (0.199–0.224) | 0.105 | 0.072 | 136 |
| 0.25 | 20 | 20 | 0 | 0.255 (0.242–0.270) | 0.127 | 0.072 | 135 |

Clean samples: no call on any arm (26CGH60 itself keeps only its 9p DEL HIGH f 0.20).

### ideal, noise-mult 2.5

| imposed f | called / 20 | HIGH | LOW | f_estimate median (min–max) | median dev | noise floor | 17p het sites |
|---|---|---|---|---|---|---|---|
| 0.00 | 0 | 0 | 0 | 0.020 (0.016–0.024) | 0.010 | 0.072 | 139 |
| 0.02 | 0 | 0 | 0 | 0.024 (0.021–0.030) | 0.012 | 0.072 | 139 |
| 0.05 | 0 | 0 | 0 | 0.052 (0.045–0.056) | 0.026 | 0.072 | 139 |
| 0.08 | 0 | 0 | 0 | 0.080 (0.071–0.086) | 0.040 | 0.072 | 139 |
| 0.10 | 0 | 0 | 0 | 0.100 (0.095–0.105) | 0.050 | 0.072 | 139 |
| 0.12 | 0 | 0 | 0 | 0.120 (0.117–0.125) | 0.060 | 0.072 | 139 |
| 0.15 | 20 | 0 | 20 | 0.150 (0.145–0.153) | 0.075 | 0.072 | 139 |
| 0.20 | 20 | 0 | 20 | 0.201 (0.194–0.205) | 0.101 | 0.072 | 139 |
| 0.25 | 20 | 20 | 0 | 0.251 (0.246–0.254) | 0.126 | 0.072 | 139 |

### shift, noise-mult 2.0

| imposed f | called / 20 | HIGH | LOW | f_estimate median (min–max) | median dev | noise floor | 17p het sites |
|---|---|---|---|---|---|---|---|
| 0.00 | 0 | 0 | 0 | 0.071 (0.061–0.078) | 0.036 | 0.057 | 139 |
| 0.05 | 0 | 0 | 0 | 0.077 (0.068–0.093) | 0.038 | 0.057 | 138 |
| 0.08 | 0 | 0 | 0 | 0.103 (0.087–0.113) | 0.051 | 0.057 | 138 |
| 0.10 | 12 | 0 | 12 | 0.117 (0.099–0.135) | 0.058 | 0.057 | 138 |
| 0.12 | 20 | 0 | 20 | 0.134 (0.118–0.150) | 0.067 | 0.057 | 138 |
| 0.15 | 20 | 1 | 19 | 0.161 (0.153–0.172) | 0.080 | 0.057 | 137 |
| 0.20 | 20 | 20 | 0 | 0.210 (0.188–0.235) | 0.105 | 0.057 | 137 |

Clean samples at 2.0:
- 26CGH1292-TwistMyVal: 17p NEUTRAL f 0.056; calls: none
- 26CGH1480-TwistMyVal: 17p NEUTRAL f 0.062; calls: 8q:CNLOH(LOW,f=0.122,n=82)
- 26CGH799-TwistMyVal: 17p NEUTRAL f 0.052; calls: none
- 26CGH885-TwistMyVal: 17p NEUTRAL f 0.064; calls: none

### shift, noise-mult 1.5

| imposed f | called / 20 | HIGH | LOW | f_estimate median (min–max) | median dev | noise floor | 17p het sites |
|---|---|---|---|---|---|---|---|
| 0.00 | 0 | 0 | 0 | 0.071 (0.061–0.078) | 0.036 | 0.050 | 139 |
| 0.05 | 0 | 0 | 0 | 0.077 (0.068–0.093) | 0.038 | 0.050 | 138 |
| 0.08 | 11 | 0 | 11 | 0.103 (0.087–0.113) | 0.051 | 0.050 | 138 |
| 0.10 | 19 | 0 | 19 | 0.117 (0.099–0.135) | 0.058 | 0.050 | 138 |
| 0.12 | 20 | 1 | 19 | 0.134 (0.118–0.150) | 0.067 | 0.050 | 138 |
| 0.15 | 20 | 20 | 0 | 0.161 (0.153–0.172) | 0.080 | 0.050 | 137 |
| 0.20 | 20 | 20 | 0 | 0.210 (0.188–0.235) | 0.105 | 0.050 | 137 |

Clean samples at 1.5:
- 26CGH1292-TwistMyVal: 17p NEUTRAL f 0.056; calls: 4q:CNLOH(LOW,f=0.109,n=62), Xp:CNLOH(LOW,f=0.105,n=18)
- 26CGH1480-TwistMyVal: 17p NEUTRAL f 0.062; calls: 8q:CNLOH(LOW,f=0.122,n=82)
- 26CGH799-TwistMyVal: 17p NEUTRAL f 0.052; calls: none
- 26CGH885-TwistMyVal: 17p NEUTRAL f 0.064; calls: none

## Reading

1. **Validated floor at production parameters (shift mode): a clonal 17p cnLOH is called from
   f ≈ 0.15 (18/20 at 0.15, LOW confidence, no consensus vote) and with HIGH confidence,
   i.e. a B vote in the consensus, from f ≈ 0.22 (3/20 HIGH at 0.20, 20/20 at 0.25).** Nothing
   is called at f ≤ 0.12 (2/20 LOW at 0.12). The "~10 %" figure used so far is therefore
   optimistic by about 5 points for any call and 12 points for a call that counts.
2. The floor is set by the threshold, not by the data. The estimator itself is unbiased once
   above the noise: at f = 0.15–0.25 the median f_estimate is within 0.01 of the imposed
   value, and the replicate spread is about ±0.02. The threshold is
   f_est ≥ 2 x noise floor = 0.143 for any call and ≥ 3 x noise floor = 0.215 for HIGH.
3. Where the noise comes from. With counting noise only (ideal mode) the null f_estimate is
   0.020; the real null is 0.071 (the pipeline's own value for this sample is 0.068). The
   per-site scatter of heterozygous ALT fractions on 17p is therefore about 3.5 x the
   binomial expectation at 1,342x — site-level reference bias and capture effects dominate,
   depth does not. More depth will not lower the floor; cleaner sites (A3 site classes and
   bias blacklist) and a per-site dispersion model (BAF_V2c beta-binomial) will.
4. The multiplier trade-off on this cohort: 2.0 brings any-call to f ≈ 0.10–0.12 and HIGH to
   ≈ 0.20 at the cost of one LOW call among the four clean samples (26CGH1480 8q CNLOH? f 0.12,
   82 het sites, copy ratio −0.01 — LOW casts no vote, but it appears on the CNV tab's called-arm
   table with a "?"); 1.5 brings any-call to ≈ 0.08 and HIGH to 0.15 with four LOW calls across
   three clean samples (5p, 4q, Xp, 8q). Whether 26CGH1480 8q is a real low-level cnLOH cannot
   be decided from this data.
5. Not simulated: hemizygous 17p deletion (BAF shift f/(2(2−f)), always smaller than cnLOH,
   but the depth arms K/G/H/P call a deletion independently of BAF, and DEL gets HIGH from the
   copy ratio), and sub-arm events (BAF_V2c segmentation). The 17p gain of 26CGH1250 behaves as
   the model predicts: a one-copy gain at f = 0.65 gives a mirrored deviation f/(2(2+f)) = 0.123,
   observed 0.128.

## Suggested statement for the memo / Twist letter

"On the current panel, BAF_V2 detects copy-neutral LOH of 17p from a clonal fraction of about
15 % (any call) and about 22 % (high confidence, consensus vote), limited by site-level noise
of the 17p SNP windows rather than by depth; validated in silico by resampling a diploid
sample's heterozygous sites (20 replicates per level), not yet on a wet-lab dilution."

## Reproduce on gandalf

    bash tools/patches/2026-09-10/run_dilution_17p.sh            # all four configurations, ~2 min at 8 threads
    bash tools/patches/2026-09-10/run_dilution_17p.sh docs/audit/2026-09-10/baf_v2_17p_dilution shift_nm2.5

Per configuration: `<tag>.summary.tsv` (this table), `<tag>.runs.tsv` (one row per replicate,
with any other arm whose verdict changed), `<tag>.baseline.summary.tsv`, `<tag>.clean/` (the
detector on the clean samples), `<tag>.dilution.png`, `<tag>.log`.
