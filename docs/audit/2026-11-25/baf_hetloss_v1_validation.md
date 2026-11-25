# BAF_HETLOSS_V1 — record of the checks on synthetic samples, and the validation that remains — 2026-11-25

This is the record behind `docs/sops/baf_het_loss.md` and `docs/memos/memo21_high_fraction_loss_of_heterozygosity.md`. It states what was run, what came out, what the synthetic samples cannot show, and what has to be done on the analysis server before the change is released. No patient data were used for anything recorded here.

## What was run

The detector is `bin/baf_cnloh_detect.py` at commit b25554e, which contains the test (commit 002a274) and the decision of the same day that two of its findings vote in the consensus. The titration tables and the test logs in this directory were produced from a clean clone at that commit. They replace the tables first recorded at commit 02aa42e, which remain in the history of this directory; between the two, the only difference is the confidence of the calls in the distal 11q series, described below.

```bash
bash tests/baf/run_validation_set.sh <output directory> all      # events.txt, specificity.txt, titration_runs/
python3 tests/baf/run_baf_tests.py                               # regression_tests.txt
bash tests/baf/run_module_test.sh                                # module_test.txt
bash tests/stub/run_stub_site.sh                                 # stub_site_test.txt
python3 tests/baf/fuzz_baf_detector.py --rounds 400 --seed 1     # fuzz.txt
python3 tests/baf/fuzz_baf_detector.py --rounds 400 --seed 2
```

Every titration runs the detector twice on each synthetic sample: once with `--no-het-loss`, which is the detector as it was, and once with its defaults. In the tables the first is labelled BAF_V2 and the second BAF_HETLOSS_V1. Seeds are fixed, so a re-run reproduces the tables. The simulator, its model and its assumptions are described in the header of `tests/baf/simulate_baf_sample.py`.

## Planted events

The full tables are in `events.txt` and every single run in `titration_runs/`. Each level has 20 replicates.

A copy-neutral loss of heterozygosity over 11q was planted at twelve fractions from 0 to 1. The previous detector called all 20 replicates at every level from 0.20 to 0.80 and none at 0.85, 0.90, 0.95, 0.98 and 1.00, where it wrote `INDETERMINATE`. The corrected detector gave results identical to the previous one, in every column, at every level up to 0.75. At 0.80 both called all replicates; the corrected detector replaced the fraction in 16 of them, and its median fraction was 0.800 against 0.792. At 0.85, 0.90 and 0.95 it called all 20 replicates as `CNLOH` with high confidence, with median fractions of 0.850, 0.898 and 0.946 and a spread of at most 0.02. At 0.98 and 1.00 it called all 20 as `ROH`.

On 17p, which carries the most sites, the previous detector called all replicates at 0.60, 0.80 and 0.85 and none at 0.90, 0.95 and 1.00. At 0.85 the fraction it wrote ranged from 0.413 to 0.898 with a median of 0.789. The corrected detector called all replicates at every level, with median fractions of 0.798, 0.849, 0.897 and 0.944 at 0.80, 0.85, 0.90 and 0.95, and `ROH` at 1.00.

On 9p the previous detector called 17 of 20 replicates at 0.80 and none above. The corrected detector called all 20 at every level, as `CNLOH` up to 0.95 and as `ROH` at 1.00.

20q is the smallest arm that was tested, with about 14 expected heterozygous loci. The previous detector called 9 of 20 replicates at 0.80 and none above. The corrected detector called 16 at 0.80, 19 at 0.85, 20 at 0.90, 20 at 0.95, of which 2 as `ROH`, and 20 as `ROH` at 1.00, 3 of them with low confidence.

A deletion of 7q in a male sample was called as `DEL` by the previous detector at 0.50, 0.80 and 0.90 and missed at 0.95 and 1.00. The corrected detector called all 20 replicates as `DEL` at every level. A gain of 8q at 0.50 and 1.00 gave identical results with both.

With 5 percent of a second genome mixed into the sample, an 11q event at 0.80 was called by both detectors. At 0.90 the corrected detector left 18 of 20 replicates `INDETERMINATE` and the previous one 19. At 0.95 the corrected detector called 17 as `ROH` and at 1.00 all 20. A second genome hides the residual sites of an event; this is a limit of the method.

At a quarter of the usual depth, the 11q event at 0.90 was called in all replicates with a median fraction of 0.895. At 0.95, 9 replicates were called as `CNLOH` and 11 as `ROH`. At a tenth of the usual depth, the event at 0.90 was called as `CNLOH` in 2 replicates, as `ROH` in 10, and not called in 8.

An event over the distal part of 11q, from 90 megabases to the end of the arm, was called by the corrected detector at 0.90 in all 20 replicates and at 0.95 in 19, as a segment, with a median fraction of 0.898 and 0.944. Every one of these calls has high confidence under the rule that applies since the decision on votes, and therefore votes for the genes inside the run; as first written, all of them were low confidence by definition. The previous detector called none of these. At 1.00 neither called it; a complete loss over part of an arm is not called by design. At 0.60 and 0.80 the existing statistic called most replicates as an event of the whole arm, as it did before the change; at 0.80 the corrected detector added 3 segment calls to the 14 of the previous one, 2 of them with high confidence, and replaced the fraction in 3.

In all of these series, no arm other than the planted one was called by either detector, and the corrected detector changed no row of any other arm.

## Samples without events

The tables are in `specificity.txt`. In 200 female and 200 male synthetic samples without any event, neither detector called any arm. The same held with 2 and 5 percent of a second genome, 100 samples each, and at a quarter and a tenth of the usual depth, 100 samples each. At a twentieth of the usual depth one arm was called in 100 samples, by both detectors alike.

With 10 percent of a second genome the previous detector called 18 arms in 100 samples, and with 20 percent 30 arms. The corrected detector called exactly the same arms. These calls come from the existing statistic and predate the change. The detector now warns of such a sample, and the dashboard shows the warning.

Across all 1,300 samples without events, the corrected detector changed no row. In particular it made no call over part of an arm and reported no region of homozygosity in any of them, so the decision that both vote adds no false call on synthetic samples.

## The decision on votes

The vote of a region of homozygosity is given in the consensus and does not show in the tables of the detector, which are unchanged for those rows. Checks 10h and 10h2 of the regression test pin it down: a region of homozygosity on 11q gives the genes of that arm the consensus call `CNLOH` at `TIER_2` with the B call `ROH`, and with the detector's switch `--roh-advisory` it is shown with low confidence and gives no call. Checks 6a, 6a2, 10e, 10f and 10f2 do the same for a call over part of an arm, and checks 11i and 11j for the statement in the TP53 block of whether a call over part of 17p includes the gene.

What the synthetic samples do not contain is a constitutionally homozygous arm, which the detector will report as a region of homozygosity and the consensus will count. How often that occurs in patients is not known from anything recorded here.

## Tests

The regression test has 50 checks and all pass (`regression_tests.txt`). The module test has 11 checks and all pass (`module_test.txt`). The fuzz test ran 800 rounds with 1,422 planted events without a failure, a quarter of the rounds with both advisory switches (`fuzz.txt`). The stub run of the whole workflow for a throw-away site passes (`stub_site_test.txt`).

## What the synthetic samples cannot show

The simulator takes the positions, the depths and the frequency of heterozygosity of every site from the panel's own background table, and the noise around balanced heterozygous sites from the validation run. What it assumes about homozygous sites is its own: a sequencing error of about 0.15 percent, and a systematic residual second allele of 2 to 8 percent at one site in a hundred.

The test judges the residual sites of an arm against the rate at which the sample's other arms show them. If real samples show residual sites at homozygous positions more often than the simulator assumes, the test does not call falsely, because it adapts to the sample, but it loses sensitivity, and the warning for a second genome may appear in clean samples. The column `residual_rate_ctrl` is written for every tested arm so that this rate can be read on real samples.

The simulator treats a site as a paralogue difference when more than three quarters of the normals are heterozygous there, which is also the rule by which the detector sets such sites aside. Real sites of this kind that fall below that frequency will remain heterozygous on an affected arm and may delay or prevent a call.

## Validation that remains, on the analysis server

These steps need patient data and have not been done. The expectations stated are those from the synthetic samples. Acceptance criteria are for the custodian to set.

The first step is the sample in which the defect was found. `tools/rescan_baf_arms.py` runs the corrected detector over the stored files of the run that contains it, without re-running the pipeline. The expected result is one arm for that sample, 11q, called `CNLOH` with high confidence over the whole arm from its first sites near the centromere, with a fraction near 0.90, and no call on any other arm of that sample. The `residual_rate_ctrl` values of the samples of that run should be noted; they answer the open question above.

The second step is the titration planted in a real sample. `tests/baf/run_validation_set.sh` with the argument `real` plants copy-neutral events on four arms, a deletion of 7q and a distal 11q event into the allelic counts of a sample without events, and compares both detectors. The base sample of the dilution study of 10 September 2026 is suitable for the arms it does not carry an event on. The expected result is that of the tables here: identical results up to 0.75, and calls with an accurate fraction from 0.80 to 0.95.

The third step is the rescan of earlier runs described in memo 21. Besides serving the look-back, it measures specificity on real samples: every arm it lists should be explicable from the figure of that sample. It is also the evidence on which the decision on votes can be reviewed. The arms it lists as `ROH` show how often an arm without heterozygosity occurs and whether those cases look acquired or constitutional, and the calls it lists with scope `segment` show whether runs over part of an arm are real.

The fourth step is the golden regression. The eight validation samples are run from a checkout of the branch as in Part D of WI-TSPIPE-003 and compared with the accepted reference run. `tools/compare_runs.py` will report every B-allele summary and sites table as different, because of the added columns. `tools/compare_baf_arms.py` is to be run on the same two directories; it must end with PASS, and every arm it lists as explained is to be reviewed. Because the branch is based on `main`, the variant tables can also differ from the reference run through the unreleased change to the variant filter recorded in memo 22.

The fifth step concerns the configuration change of memo 22 and is independent of the detector: `tools/verify_install.sh` on gandalf and on clinical-23 with their profiles, and on clinical-23 one launch without the parameter file.

## Files in this directory

`events.txt` and `specificity.txt` are the tables of the validation set, and `titration_runs/` holds one row per run of every sample. `regression_tests.txt`, `module_test.txt`, `stub_site_test.txt` and `fuzz.txt` are the logs of the tests. `gandalf_resolved_configuration.diff` and `clinical23_resolved_configuration.diff` compare the resolved configuration of the two named profiles with the Twist overlay at tag v1.0.2 and at this branch; they belong to memo 22.
