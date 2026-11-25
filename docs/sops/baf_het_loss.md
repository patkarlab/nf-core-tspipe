# BAF_HETLOSS_V1 -- arms that have lost their heterozygous sites -- 2026-11-25

This note describes the heterozygosity-loss test added to the per-arm B-allele detector, `bin/baf_cnloh_detect.py`. The test carries the marker `BAF_HETLOSS_V1`. The exact rules and thresholds are in the header of the script; this note gives the reasoning, the outputs, the limits and the state of validation. The defect that led to it is recorded in `docs/memos/memo21_high_fraction_loss_of_heterozygosity.md`.

## The defect

The detector measures each chromosome arm on the heterozygous sites of the sample, and it counts a site as heterozygous when its allele fraction lies between 0.10 and 0.90. Under a copy-neutral loss of heterozygosity present in a fraction f of the cells, a heterozygous site moves to (1 - f) / 2 or to (1 + f) / 2. Once f exceeds 0.80, both values lie outside the range from 0.10 to 0.90. For a hemizygous deletion the same happens once f exceeds about 0.89. The arm is then left with fewer than ten heterozygous sites, usually none, and the detector wrote `INDETERMINATE`. That is also what it writes for an arm it cannot assess for want of sites, so nothing in the output distinguished an arm that was nearly entirely abnormal from an arm that was merely uninformative. The more complete the event, the more certainly it was missed.

The dilution study of 10 September 2026 (`docs/audit/2026-09-10/baf_v2_17p_dilution/`) established the lower limit of the detector and tested fractions up to 0.25. The upper limit was not examined.

## The reasoning of the test

Everything the detector did before is unchanged. One step is added, for the autosomal arms.

An arm that has lost heterozygosity in most cells differs from a normal arm in two ways that can be counted. It has far fewer heterozygous sites than a person normally has there. And many of its sites, although no longer between 0.10 and 0.90, still show a small amount of the second allele, because the remaining normal cells contribute it. The test measures both.

Sites are placed in three classes. A site is heterozygous exactly as before. A site is residual when it is not heterozygous but its minor allele makes up at least 2 percent of the reads and is carried by at least ten reads; both alleles are then demonstrably present and one is nearly gone. Every other site is homozygous.

Sites that lie within 20 kilobases of each other are inherited together and are not independent observations, so they are counted once, as a locus. A locus is heterozygous if any of its sites is, residual if any of its sites is residual and none heterozygous, and homozygous otherwise. Sites that are heterozygous in more than three quarters of the 48 normals are left out, because no true polymorphism is heterozygous in more than half of a population. Such sites are differences between two copies of a duplicated sequence, they look heterozygous in everyone, and they never lose heterozygosity. This is why an arm can list a few heterozygous sites and no heterozygous locus.

The number of heterozygous loci to expect on an arm is the sum, over its loci, of the frequency with which each locus is heterozygous in the normals. The frequency comes from the columns `n_het_like` and `n_pass_depth` of `baf_background.tsv`. The sum is multiplied by the sample's own ratio of observed to expected heterozygous loci on its other autosomal arms, which allows for a person who is more or less heterozygous than the cohort; the ratio is kept between 0.6 and 1.25. The probability of finding as few heterozygous loci as the arm shows, or fewer, is taken from the Poisson distribution and written to the column `het_loss_p`. An arm with fewer than ten expected heterozygous loci is not tested.

Residual sites also occur on normal arms, as artefacts, so the number on an arm is judged against the rate at which the sample's other arms show them.

## The three outcomes

The first outcome is the one the defect concerned: heterozygosity is lost and the mixture is demonstrated. Within the arm the test finds the run of consecutive loci that is most consistently without heterozygosity. The run qualifies when its heterozygous loci are significantly fewer than expected, when its residual loci exceed the sample's background rate by at least five loci and beyond chance, and when the heterozygous and the excess residual loci together reach at least two fifths of the expected number, which means that the residual loci account for the heterozygous loci that are missing. When the run covers at least four fifths of the arm's loci, the arm is called. The clonal fraction is twice the median distance from 0.5 of the heterozygous and residual sites of the run, measured on the raw allele fraction. The verdict follows the arm's copy ratio as it always has: `CNLOH` at a neutral copy ratio, `DEL` for a loss, `GAIN` for a gain. Confidence is rated by the existing rule, with the heterozygous and residual sites counted together. The column `evidence` reads `het_loss_residual`.

Between about 80 and 85 percent a few sites still lie just inside the heterozygous range, among the residual ones, and there is no clean run. The arm is then called in the same way when its heterozygous loci are fewer than expected, when none of its remaining heterozygous sites is balanced, and when its residual loci meet the same conditions over the whole arm. An arm that the existing statistic already calls keeps its result unless its heterozygous loci are significantly depleted. Where they are, the fraction is taken from the heterozygous and residual sites together, because the few sites that remain in the heterozygous range are the ones that deviate least and understate the fraction.

The second outcome is a run that covers less than four fifths of the arm. It is reported with scope `segment`, with its coordinates and with the copy ratio of the bins inside it. In this version such a call is advisory: its confidence is `LOW`, it is shown with a question mark, and it casts no vote in the consensus. It is only made on an arm for which the existing statistic gave no call.

The third outcome is that heterozygosity is absent and nothing is left to measure. The arm has no more than one heterozygous locus, or one in twenty of the expected number where that is larger, the deficit is far beyond chance, and its residual loci do not account for the missing ones. The column `evidence` reads `het_loss_complete`, the fraction is written as 1.000, and the column `f_lower` gives what the depth can actually exclude, which is 0.96 at the usual depth. With a loss in the copy ratio the verdict is `DEL`, with a gain `GAIN`. At a neutral copy ratio the verdict is `ROH`, a region of homozygosity, and not `CNLOH`. A constitutional homozygous arm, from parental relatedness or constitutional uniparental disomy, and an acquired loss of heterozygosity in every cell give exactly this picture, and this sample alone cannot tell them apart. `ROH` is therefore shown and casts no vote in the consensus. Which of the two it is, is a question for the reporting pathologist, with the variant allele fractions on the arm and, where needed, a second tissue.

## A second genome in the sample

Contamination, and chimerism after a transplant, place a small amount of a second allele on homozygous sites of every arm alike. The test does not mistake this for an event, because the residual sites are judged against the sample's own background rate and a contaminated sample keeps its balanced heterozygous sites. Two things follow, however. A real event can be hidden, because the residual loci of the affected arm no longer stand out. And the existing statistic itself calls balanced arms once the second genome reaches about 10 percent; this was already so before the change.

The background rate is written for every tested arm to the column `residual_rate_ctrl`. When its median over the arms reaches 0.10 the detector prints a warning, the dashboard shows it above the arm table, and no lower bound of the fraction is given for an arm without heterozygosity. The threshold of 0.10 has not been checked against real samples.

## What does not change

An arm that is not called by the new test has exactly the result it had before, in every column that existed before. The parameter `baf_het_loss`, set to `false`, switches the test off and restores the previous verdicts for every arm. The sex chromosomes are not tested; a male has no heterozygous site on the X chromosome by constitution.

## Outputs

The summary `<sample>.baf.summary.tsv` keeps its 18 columns in place and gains 14 after them: `n_residual`, `n_loci`, `het_loci`, `het_loci_expected`, `residual_loci`, `het_loss_p`, `evidence`, `f_lower`, `ev_lo`, `ev_hi`, `ev_ends`, `ev_cr_log2`, `het_ratio_ctrl` and `residual_rate_ctrl`. The column `verdict` can now read `ROH` and the column `scope` can read `segment`. The sites table `<sample>.baf.sites.tsv` gains the column `site_class`.

The consensus gives a verdict of the new test only to the genes that lie inside the run; a gene elsewhere on the arm receives no B call, and its `allelic_state` says that it lies outside. `ROH` appears as a B call and casts no vote. In the consensus rules a copy-neutral loss of heterozygosity seen by the B-allele detector alone is rated `TIER_2`, and `TIER_1` when PureCN or PURPLE agrees.

The dashboard lists, for each called arm, the heterozygous loci observed against expected, the basis of the verdict and the extent of the run. The genome-wide figure, the chromosome pages and the 17p page draw the residual sites of a called arm in the colour of the verdict; before, they were drawn in the grey of homozygous sites, which is why the affected arm looked homozygous.

## Limits

An event over part of an arm at a fraction that leaves its sites inside the heterozygous range is seen by the existing statistic only when it covers more than half of the arm's heterozygous sites. This is unchanged.

A complete loss over part of an arm is not called. A homozygous segment without residual sites is what parental relatedness produces, and such segments are common.

On this panel 18p, with about 6 expected heterozygous loci, and 21p, with fewer than 1, are not tested, and 20p, with about 10, is tested only in a sample at least as heterozygous as the cohort. The other 37 autosomal arms that carry sites have between about 12 and 90 expected heterozygous loci.

At reduced depth the residual sites fall below the ten reads required. On synthetic samples at a quarter of the usual depth, a copy-neutral loss in 90 percent of the cells was still called with its fraction, and one in 95 percent was labelled `ROH` in about half of the replicates. At a tenth of the usual depth, a loss in 90 percent of the cells was labelled `ROH` in half of the replicates and was not called in most of the others.

For `DEL` and `GAIN` the column `f_estimate` is twice the median deviation, as it was before, which is the clonal fraction only for a copy-neutral event. For a deletion it understates the clone: a deletion in half of the cells reads 0.33. This convention predates the change and is left as it was; it deserves a decision of its own.

## State of validation

The test has been checked on synthetic samples only. The simulator builds a sample from the panel's own background table and gives it the noise that was measured around balanced heterozygous sites on the validation run. What it assumes about homozygous sites, namely a residual second allele at about one site in a hundred, is an assumption. The real rate decides how clearly the residual sites of an event stand out, and it has to be read on real samples.

The record of the synthetic validation is `docs/audit/2026-11-25/baf_hetloss_v1_validation.md`. It also lists what remains to be done on the analysis server before the change can be released: the sample in which the defect was found, the titration planted in a real sample, and the golden regression with `tools/compare_baf_arms.py`.

## Files

The detector is `bin/baf_cnloh_detect.py` and its module `modules/local/cnv_baf_cnloh.nf`; the switch `baf_het_loss` is set in `conf/twist_apply.config`. The readers of its output are `bin/cnv_consensus_multi.py`, `bin/plot_genome_overview.py`, `bin/plot_targets_trio.py`, `bin/plot_arm_17p.py` and, in the dashboard builder, `parsers/cnv_v2.py`, `parsers/tp53.py` and `templates/sample_report.html.j2`. The tests are in `tests/baf/` and are described in the README there. `tools/compare_baf_arms.py` compares two runs across the change.
