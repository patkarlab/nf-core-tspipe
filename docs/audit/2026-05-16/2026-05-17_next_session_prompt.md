# Session bootstrap — picking up from 2026-05-16

## Who I am, what we work on

Physician-scientist, beginner in Python, working on a targeted sequencing pipeline for hematology with a current focus on a **leukemia panel** (myeloid; lymphoma is out of scope). I prefer professional tone, no emojis, beginner-friendly explanations of any non-trivial code.

## What we just finished (2026-05-16)

Full structural port of the production orchestrator's **FLT3-ITD detection ensemble** from a Python pipeline to nf-core (Nextflow DSL2). 8 commits landed on `patkarlab/nf-core-tspipe` origin/main, ending at HEAD `cc1b138`.

Real-mode validation on 25NGS1307 (FLT3-ITD positive clinical sample) produces a consensus TSV with:
- **PASS_HIGH** row: 45 bp ITD, n_tools=3, vaf_pct_mean 14.08, ar_mean 0.123, c.1741_1785dup, p.581_595dup — matches production within float-rounding noise.
- **REVIEW_REQUIRED** row: 39 bp phantom from FLT3_ITD_EXT only, 0.58% VAF — also matches production.

Full session audit at `docs/audit/2026-05-16/2026-05-16_session_audit.md` (after I move it from the working tree root .draft).

## Infrastructure facts

**Server:** gandalf (192 cores, 1.5 TB RAM)

**Repos:**
- Production reference (read-only for porting): `/home/hemat/targeted-seq-pipeline/`
- nf-core port (active work): `/goast/hemat_data/nf-core-tspipe/`

**Singularity cache:** `/goast/hemat_data/targeted-seq-pipeline/singularity_cache/`

**Run outputs:** `/goast/hemat_data/nfcore_runs/<sample>_<runtype>_<timestamp>/`

**Containers built and live in cache:**
- `local/getitd:v0.1` (98 MB)
- `local/filt3r:v0.1` (553 MB)
- `local/flt3_itd_ext:v0.2` (784 MB) — overlay on zhkddocker/flt3_itd_ext:v1.1 with PATH wrapper

**Validation sample:** 25NGS1307. FASTQs at `/goast/hemat_data/targeted-seq-pipeline/sample_fastqs/25NGS1307-MyOPool_S5_R[12]_001.fastq.gz`. Production ground truth in `/home/hemat/targeted-seq-pipeline/results/25NGS1307/flt3/`. Validation samplesheet: `/tmp/cnv_wiring/validation_samplesheet.csv` (single sample, sex=male).

**Nextflow:** 25.10.4 in the targeted-seq conda env on gandalf.

## Operational habits

- **Multi-line commit messages:** `cat > /tmp/msg.txt; git commit -F /tmp/msg.txt` (avoids quoting hell)
- **Patches as Python `str_replace`, not sed:** save patches under `tools/patches/<date>/apply_*.py`. Each patch script should backup the target file, do the replacement, and print exactly what changed.
- **File transfer:** Claude writes to `/mnt/user-data/outputs/`, I move it to `~/inbox/from_claude/` on gandalf, then to the target path.
- **Verify before overwrite:** for any module replacement, run `grep + git log -- <file> + git diff HEAD -- <file>` first to see current state.
- **`${PIPESTATUS[0]}` for pipe exit codes**, captured immediately after the pipe (no intervening `echo` or other command).

## Lessons from today worth NOT relearning

1. **`conf/modules.config` overrides module-file `container` directives.** Any time I change a `container` line in `modules/local/*.nf`, also grep `conf/modules.config` for matching `withName:` selectors and update them too.

2. **After any change affecting container resolution: `rm -rf .nextflow/cache/`** before the next run. The cache persists across runs.

3. **`.command.run` is the authoritative record** of what Singularity actually executed. If container behavior seems wrong, this is the FIRST file to inspect, before chasing cache or config theories.

4. **Singularity does NOT support Docker's `-w` flag.** If a tool needs a specific CWD, build a thin wrapper image with a PATH script that handles `cd` internally. Module then passes input/output paths as absolute via `\$(pwd)/...`.

5. **`.join(remainder:true)` only fills nulls when at least one side has the key.** When both sides are empty for a sample, the join produces no output at all. Defensive pattern: start the join chain from a driver channel (like `ch_bam`) that has every sample by construction.

## Carry-forward priorities (in order)

### 1. Phase 1 annotation chain (next big block of work)

The `REPORTING(...)` call in `workflows/tspipe.nf` is commented out. To activate it I need to:
- Split `modules/local/vep_annotate.nf` into separate `vep.nf` + `annovar.nf` + `annotation_merge.nf` modules
- Wire `clinical_tier.nf` (port from `scripts/17c_clinical_tier.py`)
- Wire `flt3_to_variants.nf` (port from `scripts/17b_flt3_to_variants.py`) — FLT3 consensus is now available
- Wire `igv_reports.nf` (port from `scripts/16_igv_reports.py`)
- Add `dx` (diagnosis) column to samplesheet schema. Example at `assets/samplesheet_example.csv`.

### 2. Resource scaling for `conf/gandalf.config`

Currently `executor.cpus=16, memory=64.GB, queueSize=8`. Host is 192 cores / 1.5 TB. Today's single-sample real run took 35 minutes; for batch runs of 6+ this is too slow.

Suggested first iteration (benchmark-then-tune):
- `executor.cpus = 64`, `memory = 512.GB`, `queueSize = 16`
- Per-process overrides: BWA_MEM cpus=16, FASTP cpus=16, GATK4_BQSR cpus=8, GATK4_MUTECT2 cpus=8, STRELKA cpus=8, ABRA2 cpus=8

### 3. FLT3 subworkflow survivor-semantics redesign

Current `.join(remainder:true)` chain handles single-caller failure correctly but is brittle for arbitrary multi-failure cases. Clean implementation: `concat + groupTuple`. Not urgent — caller failure is rare on QC-passed clinical samples — but worth doing before production rollout.

### 4. Cleanup: move `.draft` files to `docs/audit/`

Two `.draft` files in working tree root from prior sessions:
- `2026-05-15_session_notes_actual.md.draft`
- `2026-05-16_session_prompt.md.draft`

Per my convention these belong at `docs/audit/<date>/`.

## Where to find things when answering my questions

- **Production scripts** (read-only reference): `/home/hemat/targeted-seq-pipeline/scripts/{01..17c}_*.py`
- **Production results** (validation ground truth): `/home/hemat/targeted-seq-pipeline/results/<sample>/`
- **nf-core modules:** `/goast/hemat_data/nf-core-tspipe/modules/local/*.nf`
- **nf-core subworkflows:** `/goast/hemat_data/nf-core-tspipe/subworkflows/local/*.nf`
- **nf-core workflows:** `/goast/hemat_data/nf-core-tspipe/workflows/{tspipe,build_pon}.nf`
- **nf-core configs:** `/goast/hemat_data/nf-core-tspipe/conf/{base,gandalf,modules,site_template,test}.config`
- **assets** (placeholder VCFs, samplesheet examples): `/goast/hemat_data/nf-core-tspipe/assets/`

## Tone and working style

I appreciate concise, prose explanations over heavy bullet-point formatting. When you propose a patch, I prefer to see the rationale in 1-2 paragraphs before the code, and I want the code commented for a Python beginner. Show me what you are about to do, then ask for the outputs I need to paste back. Don't run more than one major step ahead without confirmation.

If something fails, do not jump to "let me try a different approach" — diagnose first by reading `.command.err`, `.command.run`, `.nextflow.log`, the work dir contents. Tell me what the evidence says before proposing a fix.

When in doubt about the state of something on disk: ask me to run a `grep`, `git log`, `git diff`, or `ls -la`. Don't assume.
