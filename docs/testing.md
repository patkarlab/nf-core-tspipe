# Testing on gandalf

This is a phased plan. Don't skip ahead. Each phase verifies one thing; jumping
straight to the full pipeline on a real sample will produce confusing failures
that are hard to debug.

## Phase 0 — Prerequisites (15 min)

```bash
# 1. Check Java (Nextflow needs Java 11+)
java -version
# If missing or older than 11, install via your conda env:
#   conda install -n targeted-seq -c conda-forge openjdk=17

# 2. Install Nextflow (one-time, downloads ~50MB)
cd /goast/hemat_data/
curl -s https://get.nextflow.io | bash
# Move into PATH
mkdir -p /home/hemat/bin
mv nextflow /home/hemat/bin/
export PATH=/home/hemat/bin:$PATH
echo 'export PATH=/home/hemat/bin:$PATH' >> ~/.bashrc

# 3. Verify
nextflow -version
# Should print: nextflow version 24.x.x or similar

# 4. Singularity available?
which singularity
# If not, this will fail on FLT3_ITD_EXT. Either install singularity or
# set params.flt3_container = 'docker' in conf/gandalf.config.
```

## Phase 1 — Drop the scaffold into place (5 min)

```bash
# Untar the pipeline somewhere persistent
cd /goast/hemat_data/
tar -xzf /path/to/nf-core-tspipe.tar.gz

# Quick look at the structure
cd nf-core-tspipe/
ls -la
# You should see: main.nf, nextflow.config, workflows/, subworkflows/,
# modules/, conf/, bin/, assets/, docs/
```

## Phase 2 — Validate the parse (2 min)

This catches syntax errors WITHOUT actually running anything.

```bash
cd /goast/hemat_data/nf-core-tspipe/

# Show resolved configuration. If this fails, the config has a typo.
nextflow config -profile gandalf

# Try parsing main.nf without executing.
# DAG validation may flag missing files for stubs -- that's expected.
nextflow run main.nf -profile gandalf --help 2>&1 | head -40
```

If `nextflow config -profile gandalf` succeeds, the configuration is syntactically valid.

## Phase 3 — Sanity-test ONE preprocessing run (30 min, real data)

The faithful modules are: fastp, BWA, MarkDup, BQSR, ABRA2. These are enough to
go from raw FASTQ to a final BAM. Test them on a sample you've already processed
with the Python runner so you have a known-good output to compare against.

Pick a sample whose original output you trust -- 25NGS1307 is in the results/
directory.

```bash
cd /goast/hemat_data/nf-core-tspipe/

# Create a tiny samplesheet with ONE sample
mkdir -p test_run
cat > test_run/samplesheet.csv <<EOF
sample,fastq_1,fastq_2,sex
25NGS1307,/goast/hemat_data/targeted-seq-pipeline/sample_fastqs/25NGS1307_R1.fastq.gz,/goast/hemat_data/targeted-seq-pipeline/sample_fastqs/25NGS1307_R2.fastq.gz,unknown
EOF

# Adjust the FASTQ paths above to match where your fastqs actually live on gandalf!

# Dry-run first: prints the DAG without executing
nextflow run main.nf \
    -profile gandalf \
    --input test_run/samplesheet.csv \
    --outdir test_run/results \
    -preview

# If the dry-run looks clean, the real run:
nextflow run main.nf \
    -profile gandalf \
    --input test_run/samplesheet.csv \
    --outdir test_run/results \
    -resume \
    -with-report test_run/report.html \
    -with-trace test_run/trace.txt \
    -with-timeline test_run/timeline.html \
    2>&1 | tee test_run/nextflow.log
```

The trace.txt file is your best friend -- it shows per-process status, runtime,
peak memory, exit code. If something fails:

```bash
# Find the failed process
grep -E "FAILED|ABORTED" test_run/trace.txt

# Look at the work dir of the failed task
ls -la work/<hash_dir>/
cat work/<hash_dir>/.command.sh    # the script that ran
cat work/<hash_dir>/.command.err   # stderr from the tool
cat work/<hash_dir>/.command.log   # Nextflow's wrapper log
```

### Compare against the Python-runner output

```bash
# Old BAM
ls -lh /goast/hemat_data/targeted-seq-pipeline/results/25NGS1307/abra2/25NGS1307.final.bam

# New BAM
ls -lh test_run/results/25NGS1307/abra2/25NGS1307.final.bam

# Are they bit-identical?
md5sum /goast/.../25NGS1307.final.bam test_run/results/25NGS1307/abra2/25NGS1307.final.bam

# They probably won't md5-match exactly because read-group lines or sort order
# may differ -- but they should have the SAME number of reads and the same
# coverage profile:
samtools flagstat /goast/.../25NGS1307.final.bam > old.stats
samtools flagstat test_run/results/25NGS1307/abra2/25NGS1307.final.bam > new.stats
diff old.stats new.stats
```

If the BAM flagstats match, preprocessing is wired correctly.

## Phase 4 — Add variant calling (60 min)

Once preprocessing works, fill in the variant-caller stubs ONE AT A TIME. Start
with Mutect2 (already faithful) -- comment out the others temporarily:

```groovy
// In subworkflows/local/variant_calling.nf, comment everything except Mutect2:
GATK4_MUTECT2(bam_ch, reference_ch, bed_ch)
// VARDICT(bam_ch, reference_ch, bed_ch)
// VARSCAN(bam_ch, reference_ch, bed_ch)
// ...
```

Run, verify the Mutect2 VCF matches the original. Then uncomment VarDict,
fill in its module body from scripts/06_variant_callers.py, run, verify. Repeat.

## Phase 5 — Full pipeline on one sample (3-4h)

Once all callers and CNV/SV/annotation are filled in, run end-to-end on
25NGS1307 and compare:

```bash
# Run full pipeline
nextflow run main.nf -profile gandalf --input test_run/samplesheet.csv \
                                       --outdir test_run/full_results -resume

# Compare clinical TSVs
diff <(sort /goast/.../25NGS1307.somaticseq.clinical.tsv) \
     <(sort test_run/full_results/25NGS1307/annotation/25NGS1307.clinical.tsv) \
     | head -50

# FLT3-ITD: the headline result for 25NGS1307 is a 45bp ITD (p.Val581_Arg595dup)
# detected by 3 of 3 length-based tools. Confirm:
grep "Val581_Arg595" test_run/full_results/25NGS1307/flt3/25NGS1307_flt3_consensus.tsv
```

## Phase 6 — Multi-sample batch (overnight)

The whole point of moving to Nextflow is parallelism across samples. Test that
works:

```bash
# Build a 4-sample samplesheet covering the validation set
cat > test_run/batch_samplesheet.csv <<EOF
sample,fastq_1,fastq_2,sex
25NGS1307,/path/.../25NGS1307_R1.fastq.gz,/path/.../25NGS1307_R2.fastq.gz,unknown
25NGS1058,/path/.../25NGS1058_R1.fastq.gz,/path/.../25NGS1058_R2.fastq.gz,unknown
25RSEQ86,/path/.../25RSEQ86_R1.fastq.gz,/path/.../25RSEQ86_R2.fastq.gz,unknown
26CGH40,/path/.../26CGH40_R1.fastq.gz,/path/.../26CGH40_R2.fastq.gz,female
EOF

nextflow run main.nf -profile gandalf --input test_run/batch_samplesheet.csv \
                                       --outdir test_run/batch_results -resume
```

This will validate the two pending items from the original notes:
- FLT3 ensemble on 25NGS1058 and 25RSEQ86 (samples where the old pipeline
  missed real ITDs)
- 4-sample throughput on gandalf

## Phase 7 — PoN build (one-off, only if rebuilding)

If you need to rebuild the CNV PoN against a new reference or new normals:

```bash
# Build a normals samplesheet
cd /goast/hemat_data/nf-core-tspipe/

cat > test_run/normals.csv <<EOF
sample,fastq_1,fastq_2,sex,exclude
BNC1,/path/.../BNC1_R1.fastq.gz,/path/.../BNC1_R2.fastq.gz,female,false
BNC2,/path/.../BNC2_R1.fastq.gz,/path/.../BNC2_R2.fastq.gz,male,false
...
OCIAML3,/path/.../OCIAML3_R1.fastq.gz,/path/.../OCIAML3_R2.fastq.gz,female,true
EOF

# Run the PoN-build workflow
nextflow run main.nf -entry BUILD_PON -profile gandalf \
    --input test_run/normals.csv \
    --outdir test_run/pon_results \
    -resume
```

See docs/usage_pon.md for details.

## Common errors and what they mean

| Error                                                | Means                                              | Fix                                  |
| ---------------------------------------------------- | -------------------------------------------------- | ------------------------------------ |
| `nextflow: command not found`                        | Step 0.2 wasn't done                               | Install nextflow                     |
| `error: Java version not supported`                  | Java 8 in PATH                                      | Java 11+ via conda                   |
| `tool not found in $PATH`                            | Conda env not on PATH inside process               | Check `process.beforeScript` in conf/gandalf.config |
| `singularity: command not found`                     | Singularity not installed                          | Set `flt3_container = 'docker'` in gandalf.config |
| `Process FAILED with exit status 247`                | Out of memory                                       | Bump `max_memory` or that label's resource tier |
| `Cannot find any reads matching: ...`                | FASTQ path wrong in samplesheet                    | Check path, no symlink shenanigans   |
| `Reference dictionary file does not exist`           | .dict missing next to FASTA                        | `gatk CreateSequenceDictionary -R fasta` |
