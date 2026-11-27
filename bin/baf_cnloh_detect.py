#!/usr/bin/env python3
"""Genome-wide per-arm BAF-shift / cnLOH detector for the Twist myeloid panel (BAF_V2 + BAF_HETLOSS_V1).

BAF_V1 (7 Sep 2026) evaluated chr17 only. BAF_V2 (9 Sep 2026) evaluates every chromosome
arm that carries informative sites in the cohort background (snp_sites.baf.bed v2 catalog,
4,193 intervals; baf_background.tsv built from the 48 normals), with the same statistic.
BAF_HETLOSS_V1 (25 Nov 2026) adds the test for an arm whose heterozygous sites have left the
0.10-0.90 band altogether (step 7); steps 1-6 are unchanged. BAF_HETLOSS_V1B (same day, decision
of the custodian): a call over part of an arm and an arm without heterozygosity (ROH) both vote
in the consensus; --loh-segment-advisory and --roh-advisory restore the advisory behaviour.

Method (unchanged from V1 per arm; thresholds are CLI args):
  1. Background: per-position median_alt_fraction, mad_alt_fraction, informative flag.
  2. Sample: CollectAllelicCounts; positions with depth >= --min-depth.
  3. Sample-het sites: informative positions with raw AF in [0.10, 0.90].
  4. Per site: AF_adj = AF - (bg_median - 0.5) when the cohort median is het-like
     (0.35-0.65; at a common SNP the cohort distribution is trimodal 0/0.5/1 and the
     median then carries no bias information), else AF_adj = AF. Mirrored deviation
     d = |AF_adj - 0.5|; under an allelic imbalance of clonal fraction f, d ~ f/2 (cnLOH)
     or f/(2(2-f)) (hemizygous loss); f_est = 2*median(d).
  5. Per arm (p/q split at the hg38 centromere; --cytoband overrides the built-in table):
     shift when n_het >= --min-het-sites, f_est >= --f-min and median(d) >= noise_floor,
     where noise_floor = max(--f-min/2, --noise-mult * median over the OTHER arms of their
     per-arm median d). The sample's own diploid arms calibrate the noise; the cohort MAD
     (trimodal off 17p) is reported but not used for the test.
     Copy state from the arm's denoised log2 copy-ratio median:
        <= --cr-del  -> DEL          (hemizygous loss)
        >= --cr-gain -> GAIN         (gain with allelic imbalance)
        otherwise    -> CNLOH        (copy-neutral LOH / UPD)
        no bins      -> IMBALANCE    (allelic imbalance, copy state unknown)
     No shift -> NEUTRAL. Too few het sites -> INDETERMINATE (n_het reported).
  6. confidence: DEL / GAIN are HIGH (the copy ratio corroborates the shift). CNLOH / IMBALANCE,
     where BAF is the only evidence, are HIGH when n_het >= --conf-min-het and median(d) >=
     --conf-mult * noise_floor, or median(d) >= 3 * noise_floor; else LOW (shown with '?',
     casts no B vote in the consensus).
     scope: 'chromosome' when both arms carry the same verdict with |f_p - f_q| < 0.15,
     else 'arm'. ctrl_median_dev: median over the other arms of their median d.
  7. Heterozygosity-loss test (BAF_HETLOSS_V1; autosomes only; --no-het-loss switches it off).
     Why: step 3 only looks at sites between 0.10 and 0.90. A copy-neutral LOH in more than
     80 % of the cells (a hemizygous loss in more than 89 %) moves every heterozygous site of
     the arm to below 0.10 / above 0.90, where step 3 counts it as homozygous: the arm then
     has no het site left and came out INDETERMINATE, however clear the picture.
       a. Site classes. het as in step 3. residual: not het, minor allele fraction >=
          --res-min-frac (0.02) carried by >= --res-min-reads (10) reads, i.e. both alleles
          are demonstrably present but one is nearly gone. Everything else is homozygous.
       b. Loci. Informative sites within --loh-locus-span (20 kb) of the first site of a group
          form one locus (they are in linkage disequilibrium and are not independent
          observations); a locus is het if any of its sites is het, else residual if any is
          residual, else homozygous. Sites that are heterozygous in more than
          --loh-max-site-het (0.75) of the normals are left out (no true SNP exceeds 0.5;
          these are paralogue differences that never lose heterozygosity).
       c. Expectation. Expected heterozygous loci = sum over the covered loci of the cohort's
          heterozygous frequency (n_het_like / n_pass_depth of the background), multiplied by
          the sample's own observed/expected ratio on the other autosomal arms (median, kept
          within 0.6-1.25; het_ratio_ctrl). het_loss_p = Poisson P(observed or fewer |
          expected) on the arm. Background rate of residual loci among non-het loci: pooled
          over the other arms that still have their heterozygous loci (at least 0.005).
       d. The stretch without heterozygosity: the contiguous run of loci with the best score,
          a residual locus counting 1, a homozygous locus its cohort het frequency and a
          heterozygous locus -2; trimmed to its first and last residual locus unless it runs
          to the end of the arm's loci. It qualifies when, inside it: expected het loci >=
          --loh-min-expected (10); het loci significantly fewer than expected (Poisson P <=
          --loh-alpha-residual, 0.01); residual loci above the background rate by at least
          --loh-min-residual (5) loci with Poisson P <= 1e-4; and het plus excess residual
          loci reaching --loh-min-accounted (0.4) of the expected het loci, i.e. the
          residual loci account for the missing heterozygous ones (a handful of residual
          artefacts on a homozygous arm does not, nor does the upper tail of an arm whose
          sites mostly sit below the residual floor). A contaminated or chimeric sample
          shows residual sites on every arm and keeps its balanced het sites, so it
          produces no such stretch.
       e. Residual mode -- heterozygosity lost, mixture demonstrated (evidence =
          het_loss_residual). f_est = 2 x median(d) over the het and residual sites inside
          the stretch, with d = |AF - 0.5| on the raw fraction (the additive bias term of
          step 4 is sized for sites near 0.5 and would distort fractions near 0 and 1).
          - Stretch over at least --loh-arm-share (0.8) of the arm's loci: arm-level call,
            verdict from the arm's copy ratio as in step 5 (DEL, GAIN, CNLOH, IMBALANCE),
            confidence as in step 6 with the het and residual sites counted together. It
            replaces the step 5 verdict of the arm.
          - Shorter stretch: scope 'segment', verdict from the copy ratio of the bins inside
            the stretch (ev_cr_log2), confidence by the same rule as the arm-level call. The
            copy state needs at least --loh-segment-min-bins (10) bins inside the stretch;
            with fewer it is left open and the verdict is IMBALANCE, which casts no vote. A
            segment is only called where steps 1-6 gave no call, and the consensus gives
            its vote to the genes inside the stretch only (BAF_HETLOSS_V1B). With
            --loh-segment-advisory a call over part of an arm is advisory instead:
            confidence LOW, shown with '?', no vote.
       f. Around 80-85 % a few sites still sit just inside the het band, between the residual
          ones, and there is no clean stretch. The arm is then called in residual mode when
          its het loci are fewer than expected, the median d of its het sites is >= 3 x
          noise_floor (none of them is balanced), and its residual loci meet the excess and
          accounting conditions of (d) over the whole arm. Where steps 1-6 already made a
          call, this applies only if the arm's het_loss_p is <= --loh-alpha-residual: an arm
          BAF_V2 can call keeps its BAF_V2 numbers until its het loci are significantly
          depleted.
       g. Complete mode -- heterozygosity absent, nothing left to measure (evidence =
          het_loss_complete). Arm-level only: het_loss_p <= --loh-alpha-complete (1e-4),
          heterozygous loci <= 5 % of expected (at least 1 tolerated), and (e) arm-level not
          met. f_est is written as 1.000 and f_lower gives what the depth can actually
          exclude (1 - 2 x the smallest resolvable minor fraction); f_lower is NA when
          the sample shows the second-genome pattern of (i), because a remainder of normal
          cells would then not stand out from the background. Copy ratio at or below
          --cr-del -> DEL, at or above --cr-gain -> GAIN, no bins -> IMBALANCE. At neutral
          copy ratio the verdict is ROH (region of homozygosity), not CNLOH: a constitutional
          stretch of homozygosity (parental relatedness, constitutional UPD) and an acquired
          LOH in every cell give exactly this picture and cannot be told apart in this
          sample. ROH is HIGH confidence at het_loss_p <= 1e-6, and a HIGH ROH counts as
          copy-neutral LOH in the consensus (TIER_2 on its own; BAF_HETLOSS_V1B) while
          keeping its own label, so that the report still says what was observed. With
          --roh-advisory every ROH is LOW: shown with '?', no vote.
       h. ev_lo / ev_hi: first and last position of the stretch; ev_ends says which end of
          the arm's loci it runs to (both, start, end, none). The consensus gives the verdict
          only to genes inside the stretch.
       i. residual_rate_ctrl is the background rate of (c) before its lower limit is applied.
          A second genome in the sample (contamination, chimerism after transplant) puts a
          residual allele on homozygous loci of every arm alike; when the median over the
          arms reaches 0.10 the script warns that BAF verdicts are unreliable, and the
          dashboard says so above the arm table. Such a sample can hide a real event from
          this test (the residual loci of the arm no longer stand out) and, at 10 % and
          more of a second genome, steps 1-6 call arms that are balanced.
          BAF_SECOND_GENOME_V2: from about a quarter of the cells the alleles of the second
          genome sit inside the het band (0.10-0.90) instead of among the residual sites, and
          the residual rate is normal again. What shows then is an excess of heterozygous
          loci: the sample's observed/expected ratio before the 0.6-1.25 limit (median over the
          arms) is far above that of a single genome. On 32 patient samples of 27 Nov 2026
          it was 1.10-1.22 in thirty and 1.47 and 1.62 in two, in which planted events up to
          60 % of the cells went uncalled; the warning is also given at 1.35 and above.
     An arm that meets none of (e)-(g) keeps its step 5 verdict. Not covered: an event over
     part of an arm at a fraction below the het band's edge (steps 1-6 see it only when it
     covers more than half of the arm's het sites), and a complete loss over part of an arm
     (a homozygous segment without residual sites is what parental relatedness produces).

Outputs (prefix from --out-prefix, e.g. <sample>.baf):
  <prefix>.summary.tsv   one row per arm with informative sites; the 18 BAF_V2 columns, then
                         n_residual, n_loci, het_loci, het_loci_expected, residual_loci,
                         het_loss_p, evidence, f_lower, ev_lo, ev_hi, ev_ends, ev_cr_log2,
                         het_ratio_ctrl, residual_rate_ctrl; scope gains the value 'segment'
  <prefix>.sites.tsv     per-site detail (contig, position, arm, depth, af_raw, af_adj,
                         mirrored_dev, bg_mad, sample_het, site_class) -- consumed by the
                         consensus and the chromosome pages; the first nine columns are
                         unchanged from BAF_V2
  <prefix>.png           genome-wide AF panel coloured by arm verdict (non-fatal)
"""

import argparse
import math
import os
import statistics
import sys

HET_LO, HET_HI = 0.10, 0.90

# hg38 centromeres (UCSC cytoBand acen bands): p arm < start, q arm > end.
CENTROMERE_HG38 = {
    "chr1": (121700000, 125100000), "chr2": (91800000, 96000000), "chr3": (87800000, 94000000),
    "chr4": (48200000, 51800000), "chr5": (46100000, 51400000), "chr6": (58500000, 62600000),
    "chr7": (58100000, 62100000), "chr8": (43200000, 47200000), "chr9": (42200000, 45500000),
    "chr10": (38000000, 41600000), "chr11": (51000000, 55800000), "chr12": (33200000, 37800000),
    "chr13": (16500000, 18900000), "chr14": (16100000, 18200000), "chr15": (17500000, 20500000),
    "chr16": (35300000, 38400000), "chr17": (22700000, 27400000), "chr18": (15400000, 21500000),
    "chr19": (24200000, 28100000), "chr20": (25700000, 30400000), "chr21": (10900000, 13000000),
    "chr22": (13700000, 17400000), "chrX": (58100000, 61000000), "chrY": (10300000, 10600000),
}
CHROM_ORDER = ["chr%d" % i for i in range(1, 23)] + ["chrX", "chrY"]
SEX_CHROMS = ("chrX", "chrY")
VERDICT_COLOUR = {"NEUTRAL": "#9e9e9e", "DEL": "#c0392b", "CNLOH": "#2471a3", "GAIN": "#1e8449",
                  "IMBALANCE": "#8e44ad", "INDETERMINATE": "#d5d5d5", "ROH": "#b9770e"}
NO_CALL = ("NEUTRAL", "INDETERMINATE")
# BAF_HETLOSS_V1: fixed parts of the heterozygosity-loss test (the rest are CLI args)
HET_RATIO_CLAMP = (0.6, 1.25)     # allowed range of the sample's observed/expected het-locus ratio
RESIDUAL_RATE_FLOOR = 0.005       # smallest background rate of residual loci assumed for a sample
COMPLETE_MAX_HET_SHARE = 0.05     # complete mode tolerates this share of the expected het loci (at least 1)
RESIDUAL_EXCESS_P = 1e-4          # Poisson P(residual loci or more | background rate) for residual mode
ROH_HIGH_P = 1e-6                 # ROH is HIGH confidence at or below this het_loss_p
MIN_CONTROL_ARMS = 5              # fewer control arms than this: the sample ratio is taken as 1
SECOND_GENOME_RATE = 0.10         # background residual rate at or above this: warn that a second genome is present
SECOND_GENOME_HET_RATIO = 1.35    # MARKER BAF_SECOND_GENOME_V2: unbounded observed/expected het-locus ratio at or above this: same warning


def fail(msg):
    sys.stderr.write("[error] {0}\n".format(msg))
    sys.exit(1)


def read_background(path):
    """-> ({(contig, pos): (median_alt_fraction, mad_alt_fraction, het_frequency or None)}, has_het_frequency)

    het_frequency = n_het_like / n_pass_depth (share of the normals heterozygous at the site);
    None when the table lacks those columns, in which case the heterozygosity-loss test is skipped."""
    sites = {}
    header = None
    with open(path) as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            if header is None:
                header = parts
                need = ["contig", "position", "median_alt_fraction", "mad_alt_fraction", "informative"]
                missing = [c for c in need if c not in header]
                if missing:
                    fail("background missing columns: {0}".format(",".join(missing)))
                idx = dict((c, header.index(c)) for c in need)
                has_freq = "n_het_like" in header and "n_pass_depth" in header
                if has_freq:
                    i_het, i_pass = header.index("n_het_like"), header.index("n_pass_depth")
                continue
            if parts[idx["informative"]] != "true":
                continue
            freq = None
            if has_freq:
                try:
                    n_pass = float(parts[i_pass])
                    freq = float(parts[i_het]) / n_pass if n_pass > 0 else None
                except (ValueError, IndexError):
                    freq = None
            sites[(parts[idx["contig"]], int(parts[idx["position"]]))] = (
                float(parts[idx["median_alt_fraction"]]), float(parts[idx["mad_alt_fraction"]]), freq)
    if not sites:
        fail("no informative background sites in {0}".format(path))
    return sites, has_freq


def read_allelic(path):
    counts = {}
    header_seen = False
    with open(path) as fh:
        for line in fh:
            if line.startswith("@"):
                continue
            parts = line.rstrip("\n").split("\t")
            if not header_seen:
                if parts and parts[0] == "CONTIG":
                    header_seen = True
                continue
            if len(parts) < 4:
                continue
            try:
                counts[(parts[0], int(parts[1]))] = (int(parts[2]), int(parts[3]))
            except ValueError:
                fail("malformed allelic record in {0}: {1}".format(path, line[:100]))
    if not header_seen:
        fail("no CONTIG header in {0}".format(path))
    return counts


def read_denoised(path):
    bins = []
    header = None
    with open(path) as fh:
        for line in fh:
            if line.startswith("@"):
                continue
            parts = line.rstrip("\n").split("\t")
            if header is None:
                header = parts
                idx = dict((c, header.index(c)) for c in ["CONTIG", "START", "END", "LOG2_COPY_RATIO"])
                continue
            if len(parts) < len(header):
                continue
            bins.append((parts[idx["CONTIG"]], int(parts[idx["START"]]), int(parts[idx["END"]]),
                         float(parts[idx["LOG2_COPY_RATIO"]])))
    if not bins:
        fail("no denoised bins in {0}".format(path))
    return bins


def read_centromeres(cytoband_path):
    """UCSC cytoBand.txt -> {chrom: (acen_start, acen_end)}; falls back to the built-in table."""
    cen = dict(CENTROMERE_HG38)
    if not cytoband_path:
        return cen
    acen = {}
    with open(cytoband_path) as fh:
        for line in fh:
            p = line.rstrip("\n").split("\t")
            if len(p) >= 5 and p[4] == "acen":
                lo, hi = acen.get(p[0], (None, None))
                s, e = int(p[1]), int(p[2])
                acen[p[0]] = (s if lo is None else min(lo, s), e if hi is None else max(hi, e))
    cen.update(acen)
    return cen


def arm_of(chrom, pos, cen):
    c = cen.get(chrom)
    if c is None:
        return None
    if pos < c[0]:
        return "p"
    if pos > c[1]:
        return "q"
    return None   # inside the centromere


def fmt(x, nd=4):
    return "NA" if x is None or x != x else "{0:.{1}f}".format(x, nd)


def fmt_p(x):
    return "NA" if x is None or x != x else "{0:.2e}".format(x)


# ---------------------------------------------------------------- BAF_HETLOSS_V1 helpers
def _log_poisson(i, lam):
    return -lam + i * math.log(lam) - math.lgamma(i + 1.0)


def poisson_cdf(k, lam):
    """P(X <= k) for X ~ Poisson(lam), summed in log space."""
    if k < 0:
        return 0.0
    if lam <= 0.0:
        return 1.0
    logs = [_log_poisson(i, lam) for i in range(int(k) + 1)]
    top = max(logs)
    return min(1.0, math.exp(top) * sum(math.exp(v - top) for v in logs))


def poisson_sf(k, lam):
    """P(X >= k) for X ~ Poisson(lam); the upper tail is summed directly so that small values keep their precision."""
    if k <= 0:
        return 1.0
    if lam <= 0.0:
        return 0.0
    k = int(k)
    logs = [_log_poisson(i, lam) for i in range(k, k + 400 + int(10.0 * math.sqrt(lam)))]
    top = max(logs)
    return min(1.0, math.exp(top) * sum(math.exp(v - top) for v in logs))


def build_loci(rows, bg, span, max_site_het):
    """Arm site rows -> loci for the heterozygosity-loss test.

    rows: the arm's covered site tuples in position order (see evaluate()). Sites closer than
    `span` to the first site of a locus join it. Returns a list of dicts with lo, hi, cls
    ('het' | 'res' | 'hom'), p (largest cohort het frequency among its sites) and depth (median).
    Sites without a cohort frequency, and sites heterozygous in more than max_site_het of the
    normals, are left out."""
    loci = []
    start = None
    for r in rows:
        contig, pos, depth, cls = r[0], r[1], r[2], r[8]
        freq = bg[(contig, pos)][2]
        if freq is None or freq > max_site_het:
            continue
        if start is None or pos - start > span:
            loci.append({"lo": pos, "hi": pos, "cls": cls, "p": freq, "depths": [depth]})
            start = pos
            continue
        cur = loci[-1]
        cur["hi"] = pos
        cur["p"] = max(cur["p"], freq)
        cur["depths"].append(depth)
        if cls == "het" or (cls == "res" and cur["cls"] == "hom"):
            cur["cls"] = cls
    for cur in loci:
        cur["depth"] = statistics.median(cur.pop("depths"))
    return loci


def best_stretch(loci):
    """Stretch of an arm without heterozygosity: the contiguous run of loci with the best score,
    a residual locus counting 1, a homozygous locus its cohort het frequency (what it would
    have contributed had it been heterozygous) and a heterozygous locus -2, so that the run
    stops at heterozygous loci but may step over an isolated one. -> (first, last) locus index
    or None."""
    best, best_span = 0.0, None
    cur, cur_start = 0.0, None
    for i, loc in enumerate(loci):
        score = 1.0 if loc["cls"] == "res" else (-2.0 if loc["cls"] == "het" else loc["p"])
        if cur <= 0.0:
            cur, cur_start = 0.0, i
        cur += score
        if cur > best:
            best, best_span = cur, (cur_start, i)
    return best_span


def stretch_counts(loci, i0, i1, ratio):
    """Counts over loci[i0..i1]: n, het, res, expected het loci (cohort frequency x sample ratio), median depth."""
    part = loci[i0:i1 + 1]
    return {"n": len(part), "het": sum(1 for x in part if x["cls"] == "het"),
            "res": sum(1 for x in part if x["cls"] == "res"),
            "exp": ratio * sum(x["p"] for x in part),
            "depth": statistics.median([x["depth"] for x in part])}


def main():
    ap = argparse.ArgumentParser(description="Genome-wide per-arm BAF/cnLOH detector (BAF_V2 + BAF_HETLOSS_V1)")
    ap.add_argument("--allelic", required=True)
    ap.add_argument("--denoised", required=True)
    ap.add_argument("--background", required=True)
    ap.add_argument("--snp-bed", required=True, help="kept for provenance; sites come from the background")
    ap.add_argument("--sample", required=True)
    ap.add_argument("--cytoband", default=None, help="UCSC cytoBand file; overrides the built-in hg38 centromeres")
    ap.add_argument("--min-depth", type=int, default=20)
    ap.add_argument("--min-het-sites", type=int, default=10)
    ap.add_argument("--f-min", type=float, default=0.10)
    ap.add_argument("--cr-del", type=float, default=-0.15)
    ap.add_argument("--cr-gain", type=float, default=0.15)
    ap.add_argument("--noise-mult", type=float, default=2.5,
                    help="noise floor = this x the median of the other arms' median deviations (default 2.5)")
    ap.add_argument("--conf-min-het", type=int, default=20, help="HIGH confidence needs >= this many het sites (default 20)")
    ap.add_argument("--conf-mult", type=float, default=1.5, help="HIGH confidence needs median d >= this x noise floor (default 1.5)")
    # BAF_HETLOSS_V1 (step 7 of the method)
    ap.add_argument("--no-het-loss", action="store_true",
                    help="skip the heterozygosity-loss test: verdicts are then exactly those of BAF_V2")
    ap.add_argument("--res-min-frac", type=float, default=0.02,
                    help="residual site: minor allele fraction at or above this and below the het band (default 0.02)")
    ap.add_argument("--res-min-reads", type=int, default=10,
                    help="residual site: minor allele carried by at least this many reads (default 10)")
    ap.add_argument("--loh-locus-span", type=int, default=20000,
                    help="informative sites within this distance form one locus (default 20000)")
    ap.add_argument("--loh-max-site-het", type=float, default=0.75,
                    help="sites heterozygous in more than this share of the normals are left out of the test (default 0.75)")
    ap.add_argument("--loh-min-expected", type=float, default=10.0,
                    help="arms with fewer expected heterozygous loci are not tested (default 10)")
    ap.add_argument("--loh-alpha-residual", type=float, default=0.01,
                    help="het_loss_p at or below this for residual mode (default 0.01)")
    ap.add_argument("--loh-alpha-complete", type=float, default=1e-4,
                    help="het_loss_p at or below this for complete mode (default 1e-4)")
    ap.add_argument("--loh-min-residual", type=float, default=5.0,
                    help="residual mode needs at least this many residual loci above the background rate (default 5)")
    ap.add_argument("--loh-arm-share", type=float, default=0.8,
                    help="a stretch over at least this share of the arm's loci is an arm-level call, a shorter one a segment (default 0.8)")
    ap.add_argument("--loh-min-accounted", type=float, default=0.4,
                    help="residual mode needs het + excess residual loci to reach this share of the expected het loci (default 0.4)")
    ap.add_argument("--loh-segment-min-bins", type=int, default=10,
                    help="a call over part of an arm takes its copy state from the copy-ratio bins inside its stretch "
                         "when there are at least this many; with fewer the verdict is IMBALANCE (default 10)")
    # BAF_HETLOSS_V1B: both findings vote by default; these two restore the advisory behaviour
    ap.add_argument("--loh-segment-advisory", action="store_true",
                    help="a heterozygosity-loss call over part of an arm is advisory: confidence LOW, no vote "
                         "(default: rated like an arm-level call, votes for the genes inside its stretch)")
    ap.add_argument("--roh-advisory", action="store_true",
                    help="an arm without heterozygosity at neutral copy ratio (ROH) is advisory: confidence LOW, no vote "
                         "(default: HIGH at het_loss_p <= 1e-6, counted as copy-neutral LOH in the consensus)")
    ap.add_argument("--no-plot", action="store_true", help="do not write <prefix>.png (tests and titrations)")
    ap.add_argument("--out-prefix", required=True)
    args = ap.parse_args()

    for p in (args.allelic, args.denoised, args.background, args.snp_bed):
        if not os.path.isfile(p):
            fail("input not found: {0}".format(p))

    bg, has_freq = read_background(args.background)
    counts = read_allelic(args.allelic)
    bins = read_denoised(args.denoised)
    cen = read_centromeres(args.cytoband)
    het_loss_on = not args.no_het_loss
    if het_loss_on and not has_freq:
        sys.stderr.write("[warn] background has no n_het_like / n_pass_depth columns; "
                         "heterozygosity-loss test skipped (verdicts as BAF_V2)\n")
        het_loss_on = False

    # group informative sites by arm
    arm_sites = {}
    for (contig, pos) in bg:
        a = arm_of(contig, pos, cen)
        if a is None:
            continue
        arm_sites.setdefault((contig, a), []).append(pos)

    def evaluate(contig, positions):
        rows, devs, mads = [], [], []
        for pos in sorted(positions):
            med, mad = bg[(contig, pos)][0], bg[(contig, pos)][1]
            rc = counts.get((contig, pos))
            if rc is None:
                continue
            depth = rc[0] + rc[1]
            if depth < args.min_depth:
                continue
            af = rc[1] / float(depth)
            is_het = HET_LO <= af <= HET_HI
            af_adj = af - (med - 0.5) if 0.35 <= med <= 0.65 else af   # het-like cohort median only
            d = abs(af_adj - 0.5)
            if is_het:
                cls = "het"
            elif min(af, 1.0 - af) >= args.res_min_frac and min(rc[0], rc[1]) >= args.res_min_reads:
                cls = "res"    # BAF_HETLOSS_V1: both alleles present, one nearly gone
            else:
                cls = "hom"
            rows.append((contig, pos, depth, af, af_adj, d, mad, is_het, cls))
            if is_het:
                devs.append(d)
                mads.append(mad)
        return rows, devs, mads

    results = {}   # (chrom, arm) -> dict
    all_rows = []
    keys = sorted(arm_sites, key=lambda k: (CHROM_ORDER.index(k[0]) if k[0] in CHROM_ORDER else 99, k[1]))
    evaluated = {}
    for key in keys:
        rows, devs, mads = evaluate(key[0], arm_sites[key])
        evaluated[key] = (rows, devs, mads)
        for r in rows:
            all_rows.append(r + (key[1],))
    arm_med = dict((k, statistics.median(v[1])) for k, v in evaluated.items() if len(v[1]) >= args.min_het_sites)
    for key in keys:
        chrom, arm = key
        rows, devs, mads = evaluated[key]
        c0, c1 = cen[chrom]
        arm_lo, arm_hi = (0, c0) if arm == "p" else (c1, 10 ** 9)
        cr = [l for c, s, e, l in bins if c == chrom and e > arm_lo and s < arm_hi]
        cr_med = statistics.median(cr) if cr else float("nan")
        n_het = len(devs)
        med_d = mad_scale = f_est = floor = float("nan")
        others = [m for k2, m in arm_med.items() if k2 != key]
        ctrl_med = statistics.median(others) if others else float("nan")
        if n_het >= args.min_het_sites:
            med_d = statistics.median(devs)
            mad_scale = statistics.median(mads) if mads else 0.0
            f_est = 2.0 * med_d
            floor = max(args.f_min / 2.0, args.noise_mult * ctrl_med) if ctrl_med == ctrl_med else args.f_min / 2.0
            shifted = f_est >= args.f_min and med_d >= floor
            if not shifted:
                verdict = "NEUTRAL"
            elif not cr:
                verdict = "IMBALANCE"
            elif cr_med <= args.cr_del:
                verdict = "DEL"
            elif cr_med >= args.cr_gain:
                verdict = "GAIN"
            else:
                verdict = "CNLOH"
        else:
            verdict = "INDETERMINATE"
        if verdict in NO_CALL:
            confidence = "NA"
        elif verdict in ("DEL", "GAIN"):
            confidence = "HIGH"   # the arm's copy ratio corroborates the shift; site count already >= min
        elif (n_het >= args.conf_min_het and med_d >= args.conf_mult * floor) or med_d >= 3.0 * floor:
            confidence = "HIGH"   # BAF is the only evidence: many sites at a clear shift, or a very strong shift
        else:
            confidence = "LOW"
        results[key] = {"confidence": confidence, "chrom": chrom, "arm": arm, "arm_lo": arm_lo, "arm_hi": arm_hi,
                        "site_lo": min(arm_sites[key]), "site_hi": max(arm_sites[key]),
                        "n_informative": len(arm_sites[key]), "n_covered": len(rows), "n_het": n_het,
                        "med_d": med_d, "mad_scale": mad_scale, "f_est": f_est, "floor": floor,
                        "cr_med": cr_med, "n_cr": len(cr), "verdict": verdict, "devs": devs, "ctrl_med": ctrl_med,
                        # BAF_HETLOSS_V1 columns; filled in below for the arms the test looks at
                        "n_res": sum(1 for r in rows if r[8] == "res"),
                        "n_loci": None, "het_loci": None, "het_exp": float("nan"), "res_loci": None,
                        "p_loss": float("nan"), "evidence": "NA" if verdict in NO_CALL else "shift",
                        "f_lower": float("nan"), "ev_lo": None, "ev_hi": None, "ev_ends": "NA",
                        "ev_cr": float("nan"), "het_ratio": float("nan"), "res_rate": float("nan")}

    # ---- BAF_HETLOSS_V1: heterozygosity-loss test (autosomes; method step 7) ----
    if het_loss_on:
        hl = {}
        for key in keys:
            if key[0] in SEX_CHROMS:
                continue
            loci = build_loci(evaluated[key][0], bg, args.loh_locus_span, args.loh_max_site_het)
            hl[key] = {"loci": loci, "n": len(loci),
                       "het": sum(1 for x in loci if x["cls"] == "het"),
                       "res": sum(1 for x in loci if x["cls"] == "res"),
                       "exp_raw": sum(x["p"] for x in loci)}
        ratios = dict((k, v["het"] / v["exp_raw"]) for k, v in hl.items() if v["exp_raw"] >= args.loh_min_expected)
        for key, v in hl.items():
            ctrl = [x for k2, x in ratios.items() if k2 != key]
            v["ratio"] = min(HET_RATIO_CLAMP[1], max(HET_RATIO_CLAMP[0], statistics.median(ctrl))) \
                if len(ctrl) >= MIN_CONTROL_ARMS else 1.0
            v["exp"] = v["ratio"] * v["exp_raw"]
            v["p_loss"] = poisson_cdf(v["het"], v["exp"]) if v["exp"] > 0 else float("nan")
            v["depleted"] = v["exp"] >= args.loh_min_expected and v["p_loss"] <= args.loh_alpha_residual

        def residual_evidence(c, rate):
            """Do the residual loci of a set of loci (counts c) stand in for its missing het loci?
            Clearly above the sample's background rate, and together with the remaining het loci at
            least --loh-min-accounted of the expected number. When they are fewer, most of the set
            sits below the residual floor (or the residual loci are a handful of artefacts on a
            homozygous arm) and there is no fraction to measure."""
            expected_res = rate * (c["n"] - c["het"])
            excess = c["res"] - expected_res
            return (c["exp"] >= args.loh_min_expected
                    and excess >= args.loh_min_residual
                    and poisson_sf(c["res"], expected_res) <= RESIDUAL_EXCESS_P
                    and c["het"] + excess >= args.loh_min_accounted * c["exp"])

        for key, v in hl.items():
            r = results[key]
            r.update({"n_loci": v["n"], "het_loci": v["het"], "het_exp": v["exp"], "res_loci": v["res"],
                      "p_loss": v["p_loss"], "het_ratio": v["ratio"]})
            if v["exp"] < args.loh_min_expected:
                continue
            chrom = key[0]
            loci = v["loci"]
            rows, devs = evaluated[key][0], evaluated[key][1]
            # background rate of residual loci among non-het loci, from the other arms that still have their hets
            num = sum(w["res"] for k2, w in hl.items() if k2 != key and not w["depleted"])
            den = sum(w["n"] - w["het"] for k2, w in hl.items() if k2 != key and not w["depleted"])
            rate = max(RESIDUAL_RATE_FLOOR, num / float(den)) if den > 0 else RESIDUAL_RATE_FLOOR
            r["res_rate"] = num / float(den) if den > 0 else float("nan")
            floor = max(args.f_min / 2.0, args.noise_mult * r["ctrl_med"]) if r["ctrl_med"] == r["ctrl_med"] else args.f_min / 2.0

            # (d) the stretch without heterozygosity, trimmed to its residual loci unless it runs to the end of the arm
            stretch = None
            span = best_stretch(loci)
            if span is not None:
                i0, i1 = span
                at_start, at_end = i0 == 0, i1 == len(loci) - 1
                marked = [i for i in range(i0, i1 + 1) if loci[i]["cls"] != "hom"]
                if marked:
                    j0 = i0 if at_start else marked[0]
                    j1 = i1 if at_end else marked[-1]
                    c = stretch_counts(loci, j0, j1, v["ratio"])
                    c.update({"lo": loci[j0]["lo"], "hi": loci[j1]["hi"], "at_start": at_start, "at_end": at_end,
                              "share": c["n"] / float(len(loci))})
                    if residual_evidence(c, rate) and poisson_cdf(c["het"], c["exp"]) <= args.loh_alpha_residual:
                        stretch = c

            call = None   # (mode, scope, first position, last position, ends of the arm it runs to)
            whole = stretch is not None and stretch["share"] >= args.loh_arm_share
            complete_ok = (v["p_loss"] <= args.loh_alpha_complete
                           and v["het"] <= max(1.0, COMPLETE_MAX_HET_SHARE * v["exp"]))
            # (f) around 80-85 % a few sites still sit just inside the het band, between the residual ones,
            # so there is no clean stretch over the arm: its het sites are then all far from 0.5 (in a
            # contaminated or chimeric sample, and next to an event over part of the arm, they stay
            # balanced) and its residual loci stand in for the rest
            arm_counts = {"n": v["n"], "het": v["het"], "res": v["res"], "exp": v["exp"]}
            mixed_ok = (v["het"] < v["exp"] and bool(devs) and statistics.median(devs) >= 3.0 * floor
                        and residual_evidence(arm_counts, rate)
                        # an arm steps 1-6 have called keeps that result unless its het loci are
                        # significantly fewer than expected
                        and (r["verdict"] in NO_CALL or v["p_loss"] <= args.loh_alpha_residual))
            if whole:
                # (e) the stretch is the arm
                call = ("het_loss_residual", "arm", stretch["lo"], stretch["hi"],
                        "both" if stretch["at_start"] and stretch["at_end"] else
                        ("start" if stretch["at_start"] else ("end" if stretch["at_end"] else "none")))
            elif complete_ok:
                # (g) no heterozygous locus left on the arm and nothing to measure
                call = ("het_loss_complete", "arm", loci[0]["lo"], loci[-1]["hi"], "both")
            elif mixed_ok:
                marked = [x for x in loci if x["cls"] != "hom"]
                call = ("het_loss_residual", "arm", marked[0]["lo"], marked[-1]["hi"], "both")
            elif stretch is not None and r["verdict"] in NO_CALL:
                # (e) part of an arm: advisory, and only where steps 1-6 made no call
                call = ("het_loss_residual", "segment", stretch["lo"], stretch["hi"],
                        "start" if stretch["at_start"] else ("end" if stretch["at_end"] else "none"))
            if call is None:
                continue
            mode, scope, ev_lo, ev_hi, ends = call

            ev_cr = float("nan")
            if mode == "het_loss_residual":
                ev_rows = [x for x in rows if x[8] in ("het", "res") and ev_lo <= x[1] <= ev_hi]
                # d on the raw allele fraction: the additive cohort-bias term of step 4 is sized for sites
                # near 0.5 and would move a site at 0.05 by half of its own distance from the edge
                med_d = statistics.median([abs(x[3] - 0.5) for x in ev_rows])
                f_est = 2.0 * med_d
                if not (f_est >= args.f_min and med_d >= floor):
                    continue   # cannot happen with sites below 0.10 / above 0.90; kept so the rule reads as step 5
                f_lower = float("nan")
                mad_scale = statistics.median([x[6] for x in ev_rows])
            else:
                ev_rows, med_d, f_est, mad_scale = [], float("nan"), 1.0, float("nan")
                depth_med = statistics.median([x["depth"] for x in loci])
                # The bound says: a larger remainder of normal cells would show as residual loci above the
                # background. With a second genome in the sample the homozygous loci of every arm carry a
                # residual allele anyway, such a remainder would not stand out, and no bound can be given.
                if r["res_rate"] == r["res_rate"] and r["res_rate"] >= SECOND_GENOME_RATE:
                    f_lower = float("nan")
                else:
                    f_lower = max(0.0, 1.0 - 2.0 * max(args.res_min_frac, args.res_min_reads / float(depth_med)))

            if scope == "segment":
                # copy ratio of the stretch itself, extended to the arm end it runs to
                seg_lo = r["arm_lo"] if ends == "start" else ev_lo
                seg_hi = r["arm_hi"] if ends == "end" else ev_hi
                seg_cr = [l for c_, s_, e_, l in bins if c_ == chrom and e_ > seg_lo and s_ < seg_hi]
                ev_cr = statistics.median(seg_cr) if seg_cr else float("nan")
                # BAF_HETLOSS_V1B: a segment can carry a vote, so its copy state has to rest on enough bins of
                # its own -- the median of two or three bins crosses --cr-del / --cr-gain by noise alone. With
                # fewer the copy state is left open: IMBALANCE, shown, no vote.
                cr_use, has_cr = ev_cr, len(seg_cr) >= args.loh_segment_min_bins
            else:
                cr_use, has_cr = r["cr_med"], bool(r["n_cr"])
            if not has_cr:
                verdict = "IMBALANCE"
            elif cr_use <= args.cr_del:
                verdict = "DEL"
            elif cr_use >= args.cr_gain:
                verdict = "GAIN"
            else:
                verdict = "CNLOH" if mode == "het_loss_residual" else "ROH"

            if scope == "segment" and args.loh_segment_advisory:
                confidence = "LOW"    # advisory on request: shown, no vote in the consensus
            elif verdict in ("DEL", "GAIN"):
                confidence = "HIGH"   # the copy ratio corroborates the loss of heterozygosity
            elif verdict == "ROH":
                # BAF_HETLOSS_V1B: a HIGH ROH counts as copy-neutral LOH in the consensus
                confidence = "HIGH" if (v["p_loss"] <= ROH_HIGH_P and not args.roh_advisory) else "LOW"
            elif mode == "het_loss_complete":
                confidence = "LOW"    # IMBALANCE with nothing to measure and no copy ratio
            else:
                n_ev = len(ev_rows)
                confidence = "HIGH" if n_ev >= args.min_het_sites and (
                    (n_ev >= args.conf_min_het and med_d >= args.conf_mult * floor) or med_d >= 3.0 * floor) else "LOW"
            r.update({"verdict": verdict, "confidence": confidence, "med_d": med_d, "mad_scale": mad_scale,
                      "f_est": f_est, "floor": floor, "evidence": mode, "f_lower": f_lower,
                      "ev_lo": ev_lo, "ev_hi": ev_hi, "ev_ends": ends, "ev_cr": ev_cr, "scope": scope})

    # scope and leave-one-arm-out control
    for key, r in results.items():
        if r.get("scope") == "segment":
            continue   # BAF_HETLOSS_V1: a call over part of an arm stays a segment
        other = results.get((key[0], "q" if key[1] == "p" else "p"))
        r["scope"] = "arm"
        if other and other.get("scope") != "segment" \
                and r["verdict"] == other["verdict"] and r["verdict"] not in NO_CALL \
                and r["f_est"] == r["f_est"] and other["f_est"] == other["f_est"] \
                and abs(r["f_est"] - other["f_est"]) < 0.15:
            r["scope"] = "chromosome"

    ordered = sorted(results.values(), key=lambda r: (CHROM_ORDER.index(r["chrom"]) if r["chrom"] in CHROM_ORDER else 99, r["arm"]))

    with open(args.out_prefix + ".sites.tsv", "w") as out:
        out.write("contig\tposition\tarm\tdepth\taf_raw\taf_adj\tmirrored_dev\tbg_mad\tsample_het\tsite_class\n")
        for contig, pos, depth, af, af_adj, d, mad, is_het, cls, arm in all_rows:
            out.write("{0}\t{1}\t{2}\t{3}\t{4:.4f}\t{5:.4f}\t{6:.4f}\t{7:.4f}\t{8}\t{9}\n".format(
                contig, pos, arm, depth, af, af_adj, d, mad, "true" if is_het else "false", cls))

    def count(x):
        return "NA" if x is None else x

    with open(args.out_prefix + ".summary.tsv", "w") as out:
        out.write("sample\tarm\tregion\tsite_lo\tsite_hi\tn_informative\tn_covered\tn_het\t"
                  "median_mirrored_dev\tbg_mad_scale\tnoise_floor\tf_estimate\tcr_median_log2\tn_cr_bins\t"
                  "verdict\tconfidence\tscope\tctrl_median_dev\t"
                  "n_residual\tn_loci\thet_loci\thet_loci_expected\tresidual_loci\thet_loss_p\tevidence\t"
                  "f_lower\tev_lo\tev_hi\tev_ends\tev_cr_log2\thet_ratio_ctrl\tresidual_rate_ctrl\n")
        for r in ordered:
            out.write("\t".join(str(x) for x in [
                args.sample, r["chrom"].replace("chr", "") + r["arm"],
                "{0}:{1}-{2}".format(r["chrom"], r["arm_lo"], r["arm_hi"]),
                r["site_lo"], r["site_hi"], r["n_informative"], r["n_covered"], r["n_het"],
                fmt(r["med_d"]), fmt(r["mad_scale"]), fmt(r["floor"]), fmt(r["f_est"], 3), fmt(r["cr_med"]), r["n_cr"],
                r["verdict"], r["confidence"], r["scope"], fmt(r["ctrl_med"]),
                r["n_res"], count(r["n_loci"]), count(r["het_loci"]), fmt(r["het_exp"], 1), count(r["res_loci"]),
                fmt_p(r["p_loss"]), r["evidence"], fmt(r["f_lower"], 3), count(r["ev_lo"]), count(r["ev_hi"]),
                r["ev_ends"], fmt(r["ev_cr"]), fmt(r["het_ratio"], 3), fmt(r["res_rate"], 3)]) + "\n")

    def call_text(r):
        """'11q CNLOH f=0.90'; a complete loss is written with its lower bound, 'f>=0.96'."""
        if r["evidence"] == "het_loss_complete":
            f_txt = "f>=" + fmt(r["f_lower"], 2) if r["f_lower"] == r["f_lower"] else "f not measurable"
        else:
            f_txt = "f=" + fmt(r["f_est"], 2)
        return "{0}{1} {2}{3} {4}".format(r["chrom"].replace("chr", ""), r["arm"], r["verdict"],
                                           "?" if r["confidence"] == "LOW" else "", f_txt)

    # a second genome in the sample (contamination, chimerism after transplant) shows as residual signal
    # at homozygous loci on every arm; allelic verdicts are then unreliable, with or without step 7
    rates = [r["res_rate"] for r in ordered if r["res_rate"] == r["res_rate"]]
    raw_ratio = statistics.median(list(ratios.values())) if het_loss_on and len(ratios) >= MIN_CONTROL_ARMS else float("nan")
    if raw_ratio >= SECOND_GENOME_HET_RATIO and not (rates and statistics.median(rates) >= SECOND_GENOME_RATE):
        sys.stderr.write("[warn] {0}: {1:.2f} times the expected number of heterozygous loci, on the arms taken together "
                         "(threshold {2:.2f}). This is the pattern of a second genome in a large share of the cells "
                         "(contamination, chimerism after transplant). BAF verdicts for this sample are unreliable.\n".format(
                             args.sample, raw_ratio, SECOND_GENOME_HET_RATIO))
    if rates and statistics.median(rates) >= SECOND_GENOME_RATE:
        sys.stderr.write("[warn] {0}: {1:.0f} % of the homozygous loci carry a residual second allele, on every arm alike "
                         "(threshold {2:.0f} %). This is the pattern of a second genome in the sample (contamination, "
                         "chimerism after transplant). BAF verdicts for this sample are unreliable.\n".format(
                             args.sample, 100.0 * statistics.median(rates), 100.0 * SECOND_GENOME_RATE))

    called = [r for r in ordered if r["verdict"] not in NO_CALL]
    print("[ok] {0}: {1} arms evaluated, {2} with a call: {3}".format(
        args.sample, len(ordered), len(called), ", ".join(call_text(r) for r in called) or "none"))
    for r in called:
        if r["evidence"].startswith("het_loss"):
            print("[ok] {0}: {1}{2} heterozygosity lost ({3}, {4}): {5} het loci where {6} expected on the arm (p {7}), "
                  "{8} residual loci, stretch {9}:{10}-{11}".format(
                      args.sample, r["chrom"].replace("chr", ""), r["arm"], r["evidence"], r["scope"], r["het_loci"],
                      fmt(r["het_exp"], 1), fmt_p(r["p_loss"]), r["res_loci"], r["chrom"], r["ev_lo"], r["ev_hi"]))

    if args.no_plot:
        return
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        chroms = [c for c in CHROM_ORDER if any(r["chrom"] == c for r in ordered)]
        offsets, spans, x0 = {}, {}, 0.0
        for c in chroms:
            hi = max([r["site_hi"] for r in ordered if r["chrom"] == c] +
                     [e for cc, s_, e, l in bins if cc == c])
            offsets[c] = x0
            spans[c] = hi / 1e6
            x0 += hi / 1e6 + 5.0
        fig, (ax0, ax1) = plt.subplots(2, 1, figsize=(18, 7), sharex=True,
                                       gridspec_kw={"height_ratios": [1, 1.2], "hspace": 0.08})
        # depth track: denoised log2 copy ratio per bin, arm medians
        for c, s_, e, l in bins:
            if c in offsets:
                ax0.scatter(offsets[c] + (s_ + e) / 2e6, l, s=3, c="#8c8c8c", linewidths=0)
        for r in ordered:
            if r["cr_med"] == r["cr_med"]:
                x_lo = offsets[r["chrom"]] + r["arm_lo"] / 1e6
                x_hi = offsets[r["chrom"]] + min(r["arm_hi"], spans[r["chrom"]] * 1e6) / 1e6
                col = "#c0392b" if r["cr_med"] <= args.cr_del else ("#1e8449" if r["cr_med"] >= args.cr_gain else "#333333")
                ax0.plot([x_lo, x_hi], [r["cr_med"], r["cr_med"]], color=col, lw=1.8)
        ax0.axhline(0.0, color="#555555", lw=0.6)
        ax0.set_ylim(-1.5, 1.5)
        ax0.set_ylabel("denoised log2 copy ratio")
        # BAF track: het sites in the arm's verdict colour; on an arm called by the heterozygosity-loss
        # test the residual sites carry it too, and on a ROH arm every site does (BAF_HETLOSS_V1)
        for contig, pos, depth, af, af_adj, d, mad, is_het, cls, arm in all_rows:
            if contig not in offsets:
                continue
            res = results[(contig, arm)]
            v = res["verdict"]
            if res["evidence"].startswith("het_loss"):
                inside = res["ev_lo"] <= pos <= res["ev_hi"]
                coloured = inside and (cls != "hom" or res["evidence"] == "het_loss_complete")
                if is_het and not coloured:
                    v, coloured = "NEUTRAL", True   # a het site outside the stretch is a balanced one
            else:
                coloured = is_het
            ax1.scatter(offsets[contig] + pos / 1e6, af, s=6, linewidths=0,
                        c=VERDICT_COLOUR.get(v, "#9e9e9e") if coloured else "#e0e0e0")
        for c in chroms:
            for ax in (ax0, ax1):
                ax.axvline(offsets[c] - 2.5, color="#bbbbbb", lw=0.5)
                cs, ce = cen[c]
                ax.axvspan(offsets[c] + cs / 1e6, offsets[c] + ce / 1e6, color="#f2f2f2", lw=0)
        ax1.axhline(0.5, color="#555555", lw=0.6)
        ax1.set_ylim(0, 1)
        ax1.set_xlim(-3, x0)
        ax1.set_xticks([offsets[c] + spans[c] / 2 for c in chroms])
        ax1.set_xticklabels([c.replace("chr", "") for c in chroms], fontsize=8)
        ax1.tick_params(axis="x", length=0)
        ax1.set_xlabel("chromosome")
        ax1.set_ylabel("ALT allele fraction")
        from matplotlib.lines import Line2D
        handles = [Line2D([0], [0], marker="o", color="w", markerfacecolor=col, markersize=6, label=lab) for lab, col in [
            ("DEL", VERDICT_COLOUR["DEL"]), ("CNLOH", VERDICT_COLOUR["CNLOH"]), ("GAIN", VERDICT_COLOUR["GAIN"]),
            ("imbalance", VERDICT_COLOUR["IMBALANCE"]), ("ROH", VERDICT_COLOUR["ROH"]),
            ("balanced het", "#9e9e9e"), ("homozygous", "#e0e0e0")]]
        ax1.legend(handles=handles, loc="upper left", ncol=1, fontsize=7, frameon=True, framealpha=0.9,
                   bbox_to_anchor=(1.004, 1.0), borderaxespad=0.0)   # beside the panel: inside it hid the 0.9-1.0 band
        ax0.set_title("{0} -- depth and BAF by arm: {1}".format(
            args.sample, ", ".join(call_text(r) for r in called) or "no call"), fontsize=10, pad=14)
        fig.savefig(args.out_prefix + ".png", dpi=130, bbox_inches="tight")
        print("[ok] {0}: plot -> {1}.png".format(args.sample, args.out_prefix))
    except Exception as exc:
        sys.stderr.write("[warn] plot generation failed (non-fatal): {0}\n".format(exc))


if __name__ == "__main__":
    main()
