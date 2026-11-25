# Tests for the per-arm B-allele detector

These tests cover `bin/baf_cnloh_detect.py` and the programs that read its output: the consensus, the genome-wide figure, the 17p page and the dashboard. They were written with the heterozygosity-loss test (marker BAF_HETLOSS_V1, 25 November 2026) and are the place to add a case when the detector changes again.

Everything here except one optional mode runs on synthetic samples. The simulator builds a made-up sample from the panel's own background table and interval list, so the tests need no patient data, no container and no network, and they run on any machine with Python 3.6 or later. Synthetic samples test the logic of the detector. They do not validate the assay: the noise at homozygous sites, which decides how clearly the residual sites of an event stand out, is whatever the simulator was given. That question is answered on real samples, with the last two commands below.

The regression test is the one to run after any change. It takes about a minute and prints one line per check. Two of its checks draw figures and need matplotlib; `--skip-plots` leaves them out.

```bash
python3 tests/baf/run_baf_tests.py
```

The module test runs the Nextflow module with its real script and the thresholds of the panel overlay, and fails if the module's command line and the script's options have drifted apart. It needs `nextflow` on the path.

```bash
bash tests/baf/run_module_test.sh
```

The fuzz test sends random samples through the detector, the consensus and the dashboard parser, and checks what must hold whatever the sample: no program fails, an arm without a heterozygosity-loss call has exactly the previous result, a call never lands on a sex chromosome, and a gene outside the stretch of a call never receives it.

```bash
python3 tests/baf/fuzz_baf_detector.py --rounds 400 --seed 1
```

The titration plants one event at a series of clonal fractions and runs the detector with and without the new test on every replicate. The validation set is a fixed list of such titrations together with a specificity series on samples without any event. Its tables for the change that introduced the test are kept in `docs/audit/2026-11-25/`; the seeds are fixed, so a re-run reproduces them.

```bash
python3 tests/baf/titrate_het_loss.py --arm 11q --type cnloh
bash tests/baf/run_validation_set.sh /path/to/output_directory all
```

The titration can also plant its events in a real sample, which keeps its own noise at every site that is not redrawn. This is the mode that measures the test on the assay's real data, and it is run on the analysis server because it reads patient data. `BASE` is the prefix of the sample's allelic counts and denoised copy-ratio files, which are in the `cnv_gatk` directory of its run output. Choose a sample without copy-number or allelic events on the arms named in `ARMS`.

```bash
BASE=/path/to/SAMPLE/cnv_gatk/SAMPLE bash tests/baf/run_validation_set.sh /path/to/output_directory real
```

The last tool compares two complete runs, a reference run made before the change and a new one. The golden regression of the standard operating procedure expects the B-allele summaries of two runs to be identical line by line, which they can no longer be, because the summary now carries additional columns in every sample. `tools/compare_baf_arms.py` compares those files on the columns that existed before, lists every arm the new test calls, with the genes it affects in the consensus, and fails on any other difference.

```bash
python3 tools/compare_baf_arms.py --a /path/to/reference_run --b /path/to/new_run --out comparison.txt
```
