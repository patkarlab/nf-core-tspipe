# WI-TSPIPE-003 — Running an analysis on gandalf

Document number: WI-TSPIPE-003  
Version: 1.0, 18 November 2026  
Applies to: nf-core-tspipe v1.0.2, gandalf installation, Twist myeloid panel (TE-99430185)  
Parent document: SOP-TSPIPE-001  
Companion document: WI-TSPIPE-002, the same procedure on clinical-23  
Time required: about 15 minutes to prepare and launch, about two and a half hours unattended for eight samples, about 15 minutes to review  
Prepared by:  
Reviewed by:  
Approved by:  
Effective date:  

---

## Purpose and scope

This instruction describes how to run a batch of Twist myeloid panel samples through nf-core-tspipe on gandalf, from FASTQ files to reviewed reports.

clinical-23 is the routine production installation, described in Annex A of SOP-TSPIPE-001 and operated through WI-TSPIPE-002. gandalf is the development and reference installation. The accepted reference run for v1.0.2, `/goast/hemat_data/twist_val/tspipe_run9`, was produced on gandalf, and clinical-23 was qualified by comparison against gandalf. Use this instruction when a batch has to be run on gandalf, for example while clinical-23 is unavailable, and record in the run record that the batch was run on gandalf and why.

This instruction covers the Twist myeloid panel only. nf-core-tspipe v1.0.2 does not analyse the older MYOPOOL panel. MYOPOOL batches are analysed with the production targeted-seq-pipeline under its own procedure.

Follow the steps in order. Each step states its expected result. If a step does not give that result, stop there and record what you saw. Do not change configuration, paths or scripts to get past a step: a result obtained that way cannot be used clinically. Everything in this instruction runs as the user `hemat` on gandalf.

## Locations

The release checkout, `/goast/hemat_data/tspipe_release/nf-core-tspipe-v1.0.2`, holds the frozen pipeline at tag v1.0.2. Every clinical run on gandalf is launched from this directory.

The run area, `/goast/hemat_data/tspipe_runs`, holds everything belonging to a batch: the FASTQ files under `fastq/<run>/`, the samplesheet as `samplesheets/<run>.csv`, the outputs under `<run>/`, Nextflow's working files under `work_<run>/`, and the run log as `<run>.log`.

The development tree, `/goast/hemat_data/nf-core-tspipe`, is the custodian's working copy. Clinical batches are never run from it. It can carry changes that belong to no release, and other people launch development runs from it, which share its session history and log files.

---

# Part 0 — Prepare the release checkout

This part is done once per release, by the pipeline custodian or with the custodian's agreement. Skip it if `/goast/hemat_data/tspipe_release/nf-core-tspipe-v1.0.2` already exists and step A2 passes there.

## 0.1 Create the checkout

```bash
cd /goast/hemat_data/tspipe_release
git -c advice.detachedHead=false clone --branch v1.0.2 \
    https://github.com/patkarlab/nf-core-tspipe nf-core-tspipe-v1.0.2
cd nf-core-tspipe-v1.0.2
git describe --tags
git rev-parse HEAD
```

Expected: `v1.0.2`, then `09027482e14c0e7204a630ac6ddc403cb3879983`.

The checkout contains the pipeline and all of its panel assets. The container images, reference data and credentials are not part of it; they are already installed on gandalf and are found through the gandalf profile.

## 0.2 Create the run area

```bash
mkdir -p /goast/hemat_data/tspipe_runs/fastq /goast/hemat_data/tspipe_runs/samplesheets
ls -ld /goast/hemat_data/tspipe_runs
```

Expected: the directory exists and is owned by `hemat`.

## 0.3 Verify the installation

Perform step A3 from the new checkout. Expected: `VERIFY PASSED`.

## 0.4 Qualification

The reference run `tspipe_run9` was produced on this machine from the same pipeline code, with the same container images and reference data. Perform Part D once from the new checkout before its first clinical batch when time allows. If that is not possible, for example during an outage of clinical-23, the custodian records the decision and Part D is performed at the first opportunity.

---

# Part A — Prepare

## A1. Log in and confirm the machine and the account

```bash
ssh hemat@10.100.95.36
hostname -I | tr ' ' '\n' | grep -x 10.100.95.36
whoami
ls -l ~/.config/nf-core-tspipe/credentials.config
```

Expected: `10.100.95.36`, then `hemat`, then the credentials file listed with permissions `-rw-------` and owner `hemat`.

The account matters. The OncoKB token is held in `hemat`'s credentials file, and the gandalf profile gives the containers access to `/home/hemat/programs`. Under any other account the run either fails or produces reports without OncoKB annotation.

## A2. Go to the release checkout and confirm the version

```bash
cd /goast/hemat_data/tspipe_release/nf-core-tspipe-v1.0.2
git describe --tags
git status --short
```

Expected: `v1.0.2`, and `git status` prints nothing.

Stop if `git status` prints any line beginning with `M` or ` M`: a file of the frozen release has been modified. Record which file. Samplesheets and logs belong in the run area, not here, so this directory should stay clean.

## A3. Verify the installation

```bash
cd /goast/hemat_data/tspipe_release/nf-core-tspipe-v1.0.2
bash tools/verify_install.sh -profile gandalf,singularity -c conf/twist_apply.config 2>&1 | tail -15
```

Expected: a line `[OK  ] panel completeness: every probe interval is callable`, and the output ends with `VERIFY PASSED`. Warnings about images that are absent and not used by the run are normal.

Stop if any line begins with `[FAIL]`, or the output ends `VERIFY FAILED`.

This checks the toolchain, every container image against its checksum, every reference file against the reference manifest, and that the calling intervals cover every probe on the panel. Run it before every batch. It takes under a minute, and it is what stands between a corrupted or wrong reference and a wrong clinical result.

## A4. Stage the FASTQ files

Choose a short name for the batch, using letters, digits and underscores only. It names the output directory and the run bundle.

```bash
RUN=batch_20261118
ROOT=/goast/hemat_data/tspipe_runs
mkdir -p $ROOT/fastq/$RUN
# copy the batch's FASTQ files into $ROOT/fastq/$RUN, then:
ls $ROOT/fastq/$RUN/*.fastq.gz | wc -l
du -sh $ROOT/fastq/$RUN
```

Expected: an even number of files, one read 1 and one read 2 file per sample, and a total size consistent with the batch, roughly 3 GB per sample for this panel.

Files must be gzipped FASTQ (`.fastq.gz`); do not decompress them. Keep them under `/goast/hemat_data`. That is the tree the gandalf profile makes visible inside the containers, and it is the arrangement the release was validated with.

## A5. Build the samplesheet

The samplesheet tells the pipeline which samples to run, where their reads are, and each sample's sex. It is a comma-separated file with the header line `sample,fastq_1,fastq_2,sex` and one line per sample, for example:

```
sample,fastq_1,fastq_2,sex
26ABC123-Twist,/goast/hemat_data/tspipe_runs/fastq/batch_20261118/26ABC123_R1.fastq.gz,/goast/hemat_data/tspipe_runs/fastq/batch_20261118/26ABC123_R2.fastq.gz,male
26ABC124-Twist,/goast/hemat_data/tspipe_runs/fastq/batch_20261118/26ABC124_R1.fastq.gz,/goast/hemat_data/tspipe_runs/fastq/batch_20261118/26ABC124_R2.fastq.gz,unknown
```

The `sample` column is the sample identifier. It becomes the output directory name and appears in every report and table, so use the laboratory accession exactly. It may contain letters, digits, hyphens and underscores only, and must be unique within the batch. The `fastq_1` and `fastq_2` columns are the absolute paths of the read 1 and read 2 files. The `sex` column is `male`, `female` or `unknown`; it selects the sex-matched panel of normals for copy-number calling. Supply it when known. `unknown` is permitted, and the pipeline then reports the sex it infers.

To generate the samplesheet for files named `<sample>_R1.fastq.gz` and `<sample>_R2.fastq.gz`:

```bash
RUN=batch_20261118
ROOT=/goast/hemat_data/tspipe_runs
SHEET=$ROOT/samplesheets/${RUN}.csv

{ echo "sample,fastq_1,fastq_2,sex"
  for r1 in $ROOT/fastq/$RUN/*_R1*.fastq.gz; do
      r2=${r1/_R1/_R2}
      s=$(basename "$r1"); s=${s%%_R1*}
      if [ ! -f "$r2" ]; then echo "NO MATE for $r1" >&2; continue; fi
      echo "$s,$r1,$r2,unknown"
  done
} > $SHEET

cat $SHEET
```

If the files follow another naming convention, for example `_1.fastq.gz` and `_2.fastq.gz`, or Illumina's `_S1_L001_R1_001.fastq.gz`, adjust the two `_R1` and `_R2` patterns and check the resulting sample names before continuing.

The generator writes `unknown` in the sex column for every sample. Edit the file and enter the sex wherever it is known:

```bash
nano $SHEET
```

Then check the samplesheet:

```bash
head -1 $SHEET
grep -c $'\r' $SHEET
awk -F, 'NR>1{print $1}' $SHEET | sort | uniq -d
awk -F, 'NR>1{print $4}' $SHEET | sort | uniq -c
awk -F, 'NR>1{print $2"\n"$3}' $SHEET | while read f; do [ -f "$f" ] || echo "MISSING $f"; done
echo "samples: $(( $(grep -c . $SHEET) - 1 ))"
```

Expected: the header reads exactly `sample,fastq_1,fastq_2,sex`; the carriage-return count is `0`; the duplicate check prints nothing; the sex values are only `male`, `female` or `unknown`; there are no `MISSING` lines; and the sample count is the number expected.

The usual problems have simple causes. A carriage-return count above zero means the file passed through Windows or Excel; remove them with `sed -i 's/\r$//' $SHEET`. A `MISSING` line means a wrong path, a typing error or a copy that did not finish. Duplicate sample names usually mean two lanes of one sample; merge the lane files first, because the pipeline treats every line as a separate sample. A sample name with a space came from a file name with a space; rename the files and generate the samplesheet again.

## A6. Pre-run checks

```bash
df -h /goast | tail -1
pgrep -u hemat -af "nextflow.*\.jar run"
curl -s -m 15 -o /dev/null -w '%{http_code}\n' https://rest.variantvalidator.org/
```

Expected: at least 28 GB free per sample; `pgrep` prints nothing; the VariantValidator check prints `200`.

Stop if `pgrep` prints a process. Another Nextflow run is active on gandalf. Each run assumes it may use up to 160 of the server's 192 cores, so two together slow each other and everything else on the machine. Ask the custodian whether to wait.

Stop if the VariantValidator check prints anything other than `200`. The annotation step needs that service; try again later.

---

# Part B — Run

## B1. Launch

```bash
cd /goast/hemat_data/tspipe_release/nf-core-tspipe-v1.0.2
RUN=batch_20261118
ROOT=/goast/hemat_data/tspipe_runs

setsid nextflow run . \
    --input  $ROOT/samplesheets/${RUN}.csv \
    --outdir $ROOT/${RUN} \
    -w       $ROOT/work_${RUN} \
    -profile gandalf,singularity \
    -c conf/twist_apply.config \
    -ansi-log false \
    > $ROOT/${RUN}.log 2>&1 < /dev/null &
disown
```

Every line of this command is required, and nothing may be added to it.

The line `-c conf/twist_apply.config` selects the Twist myeloid panel. Without it the pipeline falls back to the retired MYOPOOL defaults, logs warnings that mention `assets/myeloid`, and stops at once with `Access to 'GATK_CNV_CALLING.out' is undefined`.

Do not add `-resume` to a first launch. In a directory with earlier runs it would attach this batch to the last recorded session. Do not add `-params-file`; the parameter file exists only on clinical-23, where it redirects reference paths that are already correct on gandalf.

Wait about a minute and a half, then confirm the run has started correctly:

```bash
sleep 90
pgrep -u hemat -af "nextflow.*work_${RUN}" | head -1
grep -c "assets/myeloid" $ROOT/${RUN}.log
grep -E "ERROR|undefined" $ROOT/${RUN}.log | head -3
grep -c "Submitted process" $ROOT/${RUN}.log
```

Expected: one Nextflow process line; `0`; nothing; and a count above zero.

Stop if the second command prints anything other than `0` or the third prints any line. Go to "If something goes wrong".

You can log out now; the run continues.

Two other launch routes exist in the checkout and are not used on gandalf. `launch_tspipe.sh` in the repository root was written for development: it leaves out the panel configuration and checks a local VariantValidator service that is not running. `tools/launch_clinical23.sh` refuses to run anywhere but the clinical-23 login node.

## B2. Monitor

Check every 20 to 30 minutes:

```bash
RUN=batch_20261118
ROOT=/goast/hemat_data/tspipe_runs
grep -c "Submitted process" $ROOT/${RUN}.log
grep -E "ERROR|terminated with" $ROOT/${RUN}.log | tail -3
pgrep -u hemat -af "nextflow.*work_${RUN}" | wc -l
```

Expected: the task count climbs, to roughly 56 tasks per sample; there are no `ERROR` lines; the process count is above zero while the run is in progress.

Two stages look stalled and are not. VARSCAN runs `samtools mpileup` for 20 to 30 minutes per sample and writes a temporary file of one to two gigabytes, and the task count moves little meanwhile. VARIANT_VALIDATOR is deliberately limited to one request at a time against a public service, so it progresses slowly.

Stop if a line reads `Error executing process`. Record the process name and the work directory path it prints.

## B3. Confirm completion

```bash
RUN=batch_20261118
ROOT=/goast/hemat_data/tspipe_runs
grep "Cleanup complete" $ROOT/${RUN}.log
grep -ciE "error executing" $ROOT/${RUN}.log
pgrep -u hemat -af "nextflow.*work_${RUN}" | wc -l
ls $ROOT/${RUN}/
```

Expected: the line `Cleanup complete. Final per-sample layout: <outdir>/<sample>/clinical/`; an error count of `0`; no Nextflow process for this run; and a listing with one directory per sample plus `assets`, `cohort_index.html`, `pipeline_info` and `${RUN}_reports.zip`.

A run that ends without the completion line did not finish. Treat it as a failure and see "If something goes wrong".

---

# Part C — After the run

## C1. Outputs

Everything is under `/goast/hemat_data/tspipe_runs/<run>/`. For each sample, the `clinical/` directory holds the final annotated clinical variant table (`<sample>.somaticseq.clinical.final.tsv`), the full filtered variant table (`<sample>.somaticseq.filtered.tsv`), the reports for review (`<sample>_report.html` and the dashboard), the read-level view of reported variants (`<sample>_igv_report.html`), the analysis-ready alignment (`<sample>.final.bam`), and the copy-number results under `cnv/` (consensus, B-allele frequency, PURPLE, CNVkit, DECoN and reconCNV). Each sample directory also holds `<sample>_report.zip`, a self-contained bundle for distribution. At the top level, `cohort_index.html` indexes the batch and `<run>_reports.zip` combines every sample's reports.

## C2. Review before release

```bash
RUN=batch_20261118
ROOT=/goast/hemat_data/tspipe_runs
ls $ROOT/${RUN}/*/clinical/*_report.html | wc -l
ls $ROOT/${RUN}/*/clinical/*oncokb_cache.json 2>/dev/null | wc -l
for d in $ROOT/${RUN}/*/; do s=$(basename $d); [ -f $d/clinical/$s.somaticseq.clinical.final.tsv ] && printf "%-24s %s variants\n" "$s" "$(( $(wc -l < $d/clinical/$s.somaticseq.clinical.final.tsv) - 1 ))"; done
```

Confirm one report per sample, one OncoKB cache per sample, and a plausible variant count for each. Confirm that quality-control metrics are within the laboratory's acceptance criteria. Open `cohort_index.html` and one sample's dashboard in a browser and check that the variant tables, the copy-number tab and the annotation columns are populated.

Empty GeneBe, MobiDetails or OncoKB sections indicate a network or credentials fault, not an absence of findings. Do not release such a report; record it and escalate.

## C3. Records and cleanup

```bash
RUN=batch_20261118
ROOT=/goast/hemat_data/tspipe_runs
cp $ROOT/${RUN}.log $ROOT/samplesheets/${RUN}.csv $ROOT/${RUN}/
git -C /goast/hemat_data/tspipe_release/nf-core-tspipe-v1.0.2 describe --tags > $ROOT/${RUN}/pipeline_version.txt
du -sh $ROOT/${RUN} $ROOT/work_${RUN}
```

The run record states the run name, the samples, the pipeline version, that the batch was run on gandalf, the reason, and the date. The output directory and the run log are retained according to laboratory policy for clinical records.

Once the outputs have been reviewed and archived, delete the work directory. It holds most of the space used by the run; deleting it also makes the run impossible to resume, which is intended at that point.

```bash
rm -rf /goast/hemat_data/tspipe_runs/work_${RUN}
```

The outputs are independent copies, not links, and are not affected. Remove the batch's FASTQ files from the run area only once they are confirmed to be archived elsewhere.

---

# Part D — Validation and re-qualification runs

Perform this part when a new release checkout is created (Part 0), after any change to gandalf that could affect the pipeline (Nextflow, the container runtime, the image cache or the reference data), and periodically to confirm the installation still behaves as qualified.

The inputs are already on gandalf: the eight validation FASTQ pairs in `/goast/hemat_data/twist_val/fastq/`, and the samplesheet `pon_samplesheets/twist_val_8_fastq.csv` inside the release checkout. Steps A4 and A5 are not needed. Perform A1 to A3 and A6, then launch:

```bash
cd /goast/hemat_data/tspipe_release/nf-core-tspipe-v1.0.2
RUN=val_$(date +%Y%m%d)
ROOT=/goast/hemat_data/tspipe_runs

setsid nextflow run . \
    --input  pon_samplesheets/twist_val_8_fastq.csv \
    --outdir $ROOT/${RUN} \
    -w       $ROOT/work_${RUN} \
    -profile gandalf,singularity \
    -c conf/twist_apply.config \
    -ansi-log false \
    > $ROOT/${RUN}.log 2>&1 < /dev/null &
disown
```

Monitor and confirm completion as in B2 and B3. Then compare against the accepted reference run:

```bash
cd /goast/hemat_data/tspipe_release/nf-core-tspipe-v1.0.2
RUN=val_20261118                      # the name used at launch
ROOT=/goast/hemat_data/tspipe_runs
python3 tools/compare_runs.py \
    --a /goast/hemat_data/twist_val/tspipe_run9 \
    --b $ROOT/${RUN} \
    --label-a accepted --label-b new \
    --out $ROOT/${RUN}_vs_accepted.md
sed -n 1,12p $ROOT/${RUN}_vs_accepted.md
grep "^### " $ROOT/${RUN}_vs_accepted.md | sed -E 's/26CGH[0-9]+-TwistMyVal/<S>/g' | sort | uniq -c | sort -rn | head -10
```

Expected: the large majority of files identical, with differences confined to three kinds. Timestamped logs differ (`amber.log`, `cobalt.log`, `purple.log`, `_hsmetrics.txt`, `quickcheck.txt`). Files that embed a creation time differ (`.zip`, `.pdf`, `.rds` and the HTML reports). Annotation caches may differ (`_genebe_cache.json`, `_mobidetails_cache.json`, `_oncokb_cache.json`), because the external services change their content over time. Files whose names carry the run name or the launch time, the combined `<run>_reports.zip` and the files under `pipeline_info/`, appear on one side only.

The following must be identical. If any of them appears under "Real text differences", stop, record it and escalate: each sample's `clinical/<sample>.somaticseq.clinical.final.tsv` and `clinical/<sample>.somaticseq.filtered.tsv`, the consensus gene tables under `clinical/cnv/consensus/`, the B-allele frequency summaries under `clinical/cnv/baf/`, and the PURPLE, CNVkit, DECoN and GATK copy-number tables.

A difference in any clinical table means the installation has changed since qualification. Retain the comparison report as the qualification record.

---

# If something goes wrong

Nextflow names the failing process and its work directory. That directory holds `.command.sh` (the exact command), `.command.log` (its output), `.command.run` (the wrapper, including the container invocation) and `.exitcode`.

```bash
RUN=batch_20261118
grep -A25 "Error executing process" /goast/hemat_data/tspipe_runs/${RUN}.log | head -35
```

The failures seen so far, with their meaning and the action to take:

`Access to 'GATK_CNV_CALLING.out' is undefined`, preceded by warnings mentioning `assets/myeloid`. The run was launched without `-c conf/twist_apply.config`. Nothing ran and nothing needs cleaning up. Launch again exactly as in B1.

`No such file or directory` naming a path under `/scratch` or `/home/patkarlab-clinical`. The clinical-23 profile or parameter file was used on gandalf. Launch again exactly as in B1.

`Nextflow version does not match` or a similar version message. gandalf's Nextflow is not the pinned 25.10.4. Escalate; do not change the version.

`exit status (137)`. The task was killed, usually for exceeding its memory allocation. Record the process name and escalate.

`Unable to acquire lock on session`. A previous Nextflow for this run is still exiting. Wait until `pgrep -u hemat -af "nextflow.*work_${RUN}"` prints nothing, then resume.

A VariantValidator task failed. The public service was unreachable or limiting requests. Three automatic retries are configured. If it still fails, test the service with the `curl` line from A6, and resume once it returns `200`.

Reports with empty annotation sections. The annotation services were unreachable when the dashboard step ran. Escalate; the results are incomplete and must not be released.

A task fails once and succeeds on resume. A transient fault; acceptable. Record it.

To resume an interrupted run, keep the first log, then repeat the B1 command from the same directory with `-resume` added. The run name, samplesheet and work directory must be the same as at launch.

```bash
cd /goast/hemat_data/tspipe_release/nf-core-tspipe-v1.0.2
RUN=batch_20261118
ROOT=/goast/hemat_data/tspipe_runs
mv $ROOT/${RUN}.log $ROOT/${RUN}.attempt1.log

setsid nextflow run . \
    --input  $ROOT/samplesheets/${RUN}.csv \
    --outdir $ROOT/${RUN} \
    -w       $ROOT/work_${RUN} \
    -profile gandalf,singularity \
    -c conf/twist_apply.config \
    -ansi-log false \
    -resume \
    > $ROOT/${RUN}.log 2>&1 < /dev/null &
disown
```

Completed tasks are reused and reported as `Cached process`; only what failed or had not yet run is executed. If a run has failed more than once, rename each earlier log in turn (`attempt2`, and so on).

Do not modify the pipeline, the container images, the reference data or the parameters to work around a failure. A result obtained through an undocumented change cannot be used clinically and invalidates the installation's qualification.

To escalate, provide the run name, the run log, the failing process name and its work directory, the output of step A3, and the output of `git describe --tags` from step A2.

---

# Notes

Why there is no launcher on gandalf. Release v1.0.2 includes a launcher only for clinical-23. On gandalf, the command in B1 is the defined way to start a run, and steps A1 to A6 perform the checks that the clinical-23 launcher performs automatically. A gandalf launcher, and a pipeline that refuses to start without the panel configuration, are candidates for the next release.

gandalf is shared. Other people use it for development and for other pipelines. A run uses up to 160 cores and 1,280 GB of memory while its busiest steps are active. Avoid starting other heavy work on the server during a run.

Three pipeline trees exist on gandalf. The release checkout at `/goast/hemat_data/tspipe_release/nf-core-tspipe-v1.0.2` is the one this instruction uses. The development tree at `/goast/hemat_data/nf-core-tspipe` is for the custodian's development work. The production targeted-seq-pipeline serves the MYOPOOL panel. They are independent of each other, and nothing in this instruction applies to the other two.

---

# Revision history

Version 1.0, 18 November 2026: first issue, written when clinical-23 was unavailable and a batch had to be run on gandalf.
