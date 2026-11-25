# Memo 21 — The per-arm allelic detector made no call for a loss of heterozygosity present in most cells

Date: 25 November 2026

Pipeline: nf-core-tspipe, Twist myeloid panel

Affects: every case analysed with releases v1.0.0 to v1.0.2, in which the per-arm B-allele detector (marker BAF_V2) has been in use since 9 September 2026

Corrected in: commits 002a274 and b25554e, merged into `main` on 25 November 2026; not in a tagged release

Status: corrected in code and checked on synthetic samples; validation on patient data, the look-back over earlier cases and the release under change control are outstanding

---

## 1. Summary

The per-arm B-allele detector could not call a loss of heterozygosity that was present in more than about 80 percent of the cells, or a deletion present in more than about 89 percent. It wrote `INDETERMINATE` for the arm, which is the verdict it also gives to an arm that has too few sites to assess. The more complete the event, the more certainly it was missed.

The cause is the definition of a heterozygous site. The detector judges an arm by the sites whose allele fraction lies between 0.10 and 0.90, and an event in most of the cells moves every heterozygous site of the arm out of that range.

A heterozygosity-loss test has been added to the detector. It is described in `docs/sops/baf_het_loss.md`. It has been checked on synthetic samples only and is not released.

## 2. How it was found

On 25 November 2026 the genome-wide figure of a case was seen to be titled "arm calls: none", although the sites of 11q lay at about 0.05 and 0.95 and the PURPLE track of the same figure showed a minor allele copy number of 0 along that arm. The figure drew the 11q sites in the light grey it uses for homozygous sites.

No automated control could have found this. The golden regression compares two runs of the same detector. The dilution study of 10 September 2026, which established from what clonal fraction the detector calls an arm, tested fractions up to 0.25 and did not look at the upper end.

## 3. Root cause

Under a copy-neutral loss of heterozygosity in a fraction f of the cells, a heterozygous site moves from 0.5 to (1 - f) / 2 or to (1 + f) / 2. The detector counts a site as heterozygous when its allele fraction lies between 0.10 and 0.90, and it needs ten such sites to assess an arm. Once f exceeds 0.80 both values lie outside the range, the arm has no heterozygous site left, and the verdict is `INDETERMINATE`. For a hemizygous deletion the limit is about 0.89.

The verdict `INDETERMINATE` therefore stood for two different things: an arm that carries too few sites to say anything, such as an acrocentric short arm or the X chromosome of a male, and an arm that has lost nearly all of its heterozygosity. Nothing in the output told them apart.

## 4. What was affected

For an affected arm the summary read `INDETERMINATE`, its genes received no B call in the consensus, the genome-wide figure and the chromosome pages drew its sites as homozygous, and the dashboard listed it among all arms without highlight. When no other arm was called, the B-allele tab of the dashboard carried the badge "all arms balanced".

Deletions and gains were still called, because the depth-based callers do not depend on the allele fractions. What was missing was the B-allele vote, so that such an event could be rated one tier lower than it should have been.

Copy-neutral events are invisible to the depth-based callers. Without the B-allele vote the consensus could call such an event only from PureCN and PURPLE, each of which counts only when its fit is trusted; one of them alone is rated `TIER_3`. A copy-neutral loss of heterozygosity in more than 80 percent of the cells could therefore appear at a lower tier than it should have, or not appear in the consensus at all.

The TP53 and 17p observation block of the report takes its allelic line from the 17p row of the detector. A 17p event of this kind would have read `INDETERMINATE` there.

Events below 80 percent were called as before and are not affected. At 80 to 85 percent the detector could still make a call on an arm with many sites, from the few sites that remained in range. Those are the sites that deviate least, so the fraction written for such an arm could be too low. On synthetic 17p samples with a true fraction of 0.85, the fraction written ranged from 0.41 to 0.90.

## 5. Look-back over earlier cases

Every run keeps, for each sample, the two files the detector reads: the allelic counts and the denoised copy ratios, under `<run>/<sample>/cnv_gatk/`. The corrected detector can therefore be run over the stored files of every earlier run in a few seconds per sample, without re-running the pipeline.

```bash
python3 tools/rescan_baf_arms.py --out /path/to/rescan_output /path/to/run1 /path/to/run2
```

The script lists every arm that the new test calls and every sample that shows the pattern of a second genome. It writes to its own output directory and nothing into the runs. Its output is a screen for review and not a result: the detector it runs is not yet validated on patient data, and an arm listed as `ROH` can be constitutional. Whether a listed case needs an amended report is for the reporting pathologist to decide. The same output shows how often a region of homozygosity or a call over part of an arm occurs in real samples, which is the evidence on which the decision that both vote can be reviewed.

## 6. The correction

The steps of the detector that existed before are unchanged. A further step judges each autosomal arm on the number of its heterozygous loci against the number expected from the 48 normals, and on its residual sites, which are sites outside the heterozygous range where the minor allele is still measurable at 2 percent or more.

Where the residual sites account for the missing heterozygous loci, the arm is called, the clonal fraction is read from those sites, and the verdict follows the copy ratio as before. Where nothing is left to measure, the verdict at a neutral copy ratio is `ROH`, a region of homozygosity, with a lower bound for the fraction; a constitutional homozygous arm gives the same picture as an acquired loss in every cell. A run that covers only part of an arm is reported with its coordinates.

As first written, the last two findings were shown without a vote in the consensus. The custodian decided on 25 November 2026 that both vote (commit b25554e, marker BAF_HETLOSS_V1B). A region of homozygosity keeps its label and counts as copy-neutral loss of heterozygosity, rated `TIER_2` on its own. A call over part of an arm is rated like an arm-level call and votes for the genes inside its run. The parameters `baf_roh_votes` and `baf_segment_votes`, set to `false`, make either advisory again. A constitutionally homozygous arm will therefore appear in the consensus as copy-neutral loss of heterozygosity, and the gene table and the dashboard say that it is not excluded.

The alternative of taking the arm call from the minor allele copy number of PURPLE was not used. PURPLE is already a separate vote in the consensus, and its fit is not trusted in every sample; the B-allele arm has to see the event in the allele fractions themselves if the two votes are to remain independent.

The summary table gains 14 columns after its existing 18, and the sites table gains one. The parameter `baf_het_loss`, set to `false`, restores the previous verdicts.

## 7. What was checked

All checks so far are on synthetic samples, which test the logic of the detector and not the assay. The record is `docs/audit/2026-11-25/baf_hetloss_v1_validation.md`.

In clone-fraction titrations with 20 replicates per level, the previous detector called a copy-neutral 11q event at every level up to 0.80 and at no level from 0.85. The corrected detector gave the same result at every level up to 0.75, called every replicate from 0.80 to 0.95 with a median fraction within 0.005 of the truth, and called every replicate at 0.98 and 1.00 as `ROH`. The same pattern held on 17p and 9p. On 20q, the smallest arm tested, it called 16 of 20 replicates at 0.80 and 19 of 20 at 0.85, where the previous detector called 9 and none. A 7q deletion, which the previous detector missed at 0.95 and 1.00, was called at every level.

In 400 synthetic samples without any event, neither detector called an arm. In samples contaminated with 10 and 20 percent of a second genome the previous detector called 18 and 30 arms per 100 samples; the corrected detector called the same arms and no others. That weakness predates the change and is now flagged by a warning.

## 8. What remains before release

The change falls under section 11 of SOP-TSPIPE-001: authorisation by the custodian, a golden regression with the comparison report retained, a new version tag and a revision of the standard operating procedure. Four things are specific to this change.

The case in which the defect was found has to be re-analysed with the corrected detector, and the result compared with what the figure shows.

The titration has to be repeated with the events planted in a real sample, which keeps its own noise at every site that is not redrawn. `tests/baf/run_validation_set.sh` does this with the argument `real`; the README in `tests/baf/` gives the command. This answers the question the synthetic samples cannot: how many homozygous sites of a real sample carry a residual second allele, and therefore how clearly the residual sites of an event stand out.

The golden regression of section 7.10 expects the B-allele summaries of the reference run and of the new run to be identical. They can no longer be identical line by line, because the summary carries 14 additional columns in every sample. `tools/compare_baf_arms.py` compares them on the 18 columns that existed before, lists every arm the new test calls and fails on any other difference. Section 7.10 of the standard operating procedure and Part D of WI-TSPIPE-003 need a sentence to this effect in the revision that accompanies the release.

Before this change `main` was already three commits ahead of v1.0.2. The last of them is labelled as documentation but also changes the variant filter (marker HOTSPOT_EXEMPT_V1), the hotspot table and the dashboard. A comparison of a run of `main` against the reference run of v1.0.2 will show the effect of those changes on the variant tables as well. Memo 22 records this.

## 9. Why it was not seen earlier

The validation of the detector asked from what fraction an event becomes visible and did not ask up to what fraction it remains visible. The test set in `tests/baf/` now covers the whole range from 0 to 1 and is the place to add a level when the detector changes.

The verdict for "cannot be assessed" was reused for "nothing left to assess". The corrected detector separates the two: an autosomal arm that has enough sites and no heterozygosity is called, and `INDETERMINATE` is left for arms that carry too few sites.
