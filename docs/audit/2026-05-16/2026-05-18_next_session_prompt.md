# Session bootstrap — picking up from 2026-05-16

## Who I am, what we work on

Physician-scientist, beginner in Python, working on a targeted sequencing
pipeline for hematology with current focus on a **leukemia panel**
(myeloid; lymphoma is out of scope). I prefer professional tone, no
emojis, beginner-friendly explanations of any non-trivial code.

## What we just finished (2026-05-16)

Three commits landed on `patkarlab/nf-core-tspipe` origin/main, ending
at HEAD `5cf6df6`:

- `cb3e7ff` — docs(audit): relocate 2026-05-15 drafts to date-matched directory
- `4f5351e` — feat(config): scale resource envelope and label tiers for gandalf capacity
- `5cf6df6` — feat(annotation): port VEP_ANNOTATE module + bin/annotate.py

**Path B (variant_filter rewrite + annotation.nf u2af1 wiring + ANNOTATION
activation) is on disk uncommitted.** Patch script:
`tools/patches/2026-05-16/apply_annotation_wiring.py`. Files changed:

- `modules/local/variant_filter.nf` (full rewrite, fixed three latent bugs)
- `subworkflows/local/annotation.nf` (added u2af1_tsv_ch take parameter)
- `workflows/tspipe.nf` (uncommented ANNOTATION call with 5 channels)

Real-mode validation on 25NGS1307 completed end-to-end (32/32 success,
33m 58s wall time). But the diff against production caught **6
clinically-significant variants missing from the port's clinical TSV**:
CEBPA c.288C>G (synonymous), RAD21 p.Leu155Phe, SETD2 p.Pro1916His,
TET2 p.Ser142Tyr, TET2 p.Glu1250Ter, UBTF c.1247_1248ins27bp.

**Root cause: `modules/local/somaticseq.nf` arbitrary-caller plumbing
is broken.** See "Priority 1" below. This is the blocker for Path B
commit.

Full audit at `docs/audit/2026-05-16/2026-05-16_session_audit.md`.

## Infrastructure facts

Unchanged from yesterday's bootstrap:

**Server:** gandalf (192 cores, 1.5 TB RAM)

**Repos:**
- Production reference (read-only for porting): `/home/hemat/targeted-seq-pipeline/`
  (symlink to `/goast/hemat_data/targeted-seq-pipeline/`)
- nf-core port (active work): `/goast/hemat_data/nf-core-tspipe/`

**Resource scaling now active** (committed in 4f5351e):
- executor: 160 cpus, 1280 GB, queueSize 32
- process_medium: 24 cpus / 96 GB
- process_high: 64 cpus / 256 GB
- max_cpus = 96, max_memory = 512.GB

**Validation sample:** 25NGS1307. FASTQs at
`/goast/hemat_data/targeted-seq-pipeline/sample_fastqs/25NGS1307-MyOPool_S5_R[12]_001.fastq.gz`.
Production ground truth in `/home/hemat/targeted-seq-pipeline/results/25NGS1307/`.
Validation samplesheet: `/tmp/cnv_wiring/validation_samplesheet.csv`
(single sample, sex=male). Clinical reality: this sample is FLT3-ITD
positive (validated), U2AF1 hotspot positive (not yet validated in
port), KMT2A-PTD positive (not yet validated in port).

## Operational habits

All carried forward unchanged. New addition this session:

- **For long-running pipeline executions, use `screen`** so SSH
  disconnects don't kill the run:
  ```
  screen -S tspipe          # start named session
  # ...run nextflow inside...
  Ctrl-a then d             # detach (run keeps going)
  screen -r tspipe          # reattach later
  screen -d -r tspipe       # force-detach then reattach
  ```

- **Python code blocks must be transferred as files**, not pasted
  into bash. Write to `/mnt/user-data/outputs/`, transfer via
  `~/inbox/from_claude/`, then move into the repo. Pasting Python
  source directly into bash mis-parses syntax and can accidentally
  trigger package installation prompts.

## Carry-forward priorities (in order)

### Priority 1 (BLOCKING): Fix SomaticSeq arbitrary-caller plumbing

**Symptom:** Port's SomaticSeq output shows NUM_TOOLS=1 and missing
MVDKFP for variants that production correctly tags as NUM_TOOLS=2
with MVDKFP populated. This causes a 28% deficit in annotated
variants downstream and drops 6 clinically-significant variants from
the clinical TSV.

**Location:** `modules/local/somaticseq.nf`, script block.

**Two distinct sub-issues in that module:**

**1a.** Pindel and DeepSomatic were deliberately removed from the
arbitrary-caller loop in some prior session:

```bash
# NOTE 2026-05-17: pindel and deepsomatic temporarily dropped from
# the arbitrary-caller loop. Both produce valid VCFs upstream but the
# SomaticSeq preprocessing loop crashes during their iteration in ways
# that proved hard to pin down within a single debug session.
for ENTRY in "freebayes:${freebayes_vcf}" "platypus:${platypus_vcf}"; do
```

Re-enable Pindel and DeepSomatic. For Pindel specifically, may need a
pre-filter to drop non-SNV/non-INDEL records since Pindel emits SVs
that may crash splitVcf.py. Production handles 6 callers; the port
adds Pindel and DeepSomatic but never properly integrated them.

**1b.** Even FreeBayes and Platypus (nominally in the loop) aren't
producing arbitrary-caller votes in SomaticSeq's output. RAD21 should
show NUM_TOOLS=2 with MVDKFP `0,0,0,0,1,1,0,0` but instead shows
NUM_TOOLS=1 with MVDKFP absent. Suspect the bash subshell expansion:

```bash
$( [ ${#ARB_SNV_LIST[@]} -gt 0 ] && echo "--arbitrary-snvs ${ARB_SNV_LIST[@]}" )
```

The array expansion inside `$(...)` inside Nextflow's script
rendering may be dropping elements. Diagnostic: run the pipeline,
copy SOMATICSEQ_ENSEMBLE work dir immediately, inspect `.command.sh`
to see the literal SomaticSeq invocation that was executed. Check
whether `--arbitrary-snvs` and `--arbitrary-indels` appear with all
expected file paths.

**Verification after fix:** re-run real-mode on 25NGS1307, expect:
- Port's `25NGS1307.somaticseq.vcf` for the 6 missing variants should
  show NUM_TOOLS=2 (or higher) with MVDKFP positions matching the
  production values in the audit table.
- Annotated TSV port-only and prod-only counts should drop
  substantially.
- Clinical TSV should retain the 6 variants (modulo the REJECT-rescue
  question in priority 2).

### Priority 2: Find and port the REJECT-rescue step

Both port and production tag all 6 missing variants as SomaticSeq
**REJECT**, yet production's clinical TSV contains them. So production
has a rescue layer downstream of `variant_filter.py` that we haven't
located. Suspect candidates:

- `bin/oncovi.py` (oncogenicity scoring; may rescue REJECT variants
  scored as oncogenic)
- Production's `scripts/17c_clinical_tier.py` (not yet ported; this
  is also the CLINICAL_TIER module on the original Phase 1 todo list)
- Some other downstream filter pass

Diagnostic: grep production scripts for `REJECT`, `rescue`, `tier`,
and inspect the production clinical TSV's content for hints (does it
have a Rescue_Note column? what tier? what's in the row that
distinguishes it from a typical PASS variant?).

### Priority 3: Re-validate Path B end-to-end against production

After (1) and (2) land, re-run real-mode on 25NGS1307 and recompute
the three-tier diff. Acceptance criterion: clinical TSV common keys =
production keys minus any variants the port's filter is correctly
dropping for documented reasons (e.g. synonymous variants if the
consequence filter excludes them by design).

Once validated: commit Path B as a feat patch.

### Priority 4: Continue Phase 1 — remaining stubs + CLINICAL_TIER

After Path B commits, return to the original Phase 1 scope. From the
2026-05-16 audit:

- VARIANT_VALIDATOR module (port from `bin/variant_validator.py`, exists)
- ONCOVI module (port from `bin/oncovi.py`, exists)
- FLT3_TO_VARIANTS module (port from `bin/flt3_to_variants.py`, exists)
- CLINICAL_TIER (NEW; port `scripts/17c_clinical_tier.py` to
  `bin/clinical_tier.py`, create `modules/local/clinical_tier.nf`,
  wire into annotation.nf after FLT3_TO_VARIANTS)
- IGV_REPORTS module (port from `bin/igv_reports.py`)
- ORGANIZE_OUTPUT module (port from `bin/organize_output.py`)
- Samplesheet schema: add `dx` column (diagnosis) for CLINICAL_TIER
- Activate `REPORTING(...)` call in tspipe.nf

### Priority 5: Wall-time tuning followups (lower priority)

The new resource envelope cut BWA_MEM from 12m to 3m 16s but total
wall time only dropped 3% (35m → 34m). Three known fixes would
realistically take it to ~24m:

- FASTP: change hardcoded `-w 2` to `-w ${task.cpus}` in `modules/local/fastp.nf`
- BQSR: enable Spark mode or interval-split for parallelism
- ABRA2: ensure `--threads ${task.cpus}` is explicit

### Priority 6: U2AF1 and KMT2A-PTD validation

Sample 25NGS1307 has documented U2AF1 hotspot and KMT2A-PTD mutations
in addition to the validated FLT3-ITD. Once priority 1 lands (Pindel
re-enabled), verify both flow through correctly into the clinical
output.

## Where to find things when answering my questions

- **Production scripts** (read-only reference): `/home/hemat/targeted-seq-pipeline/scripts/{01..17c}_*.py`
- **Production results** (validation ground truth): `/home/hemat/targeted-seq-pipeline/results/<sample>/`
- **nf-core modules:** `/goast/hemat_data/nf-core-tspipe/modules/local/*.nf`
- **nf-core subworkflows:** `/goast/hemat_data/nf-core-tspipe/subworkflows/local/*.nf`
- **nf-core workflows:** `/goast/hemat_data/nf-core-tspipe/workflows/{tspipe,build_pon}.nf`
- **nf-core configs:** `/goast/hemat_data/nf-core-tspipe/conf/{base,gandalf,modules,site_template,test}.config`
- **assets:** `/goast/hemat_data/nf-core-tspipe/assets/`
- **patches from today:** `/goast/hemat_data/nf-core-tspipe/tools/patches/2026-05-16/`
- **latest validation run output:** `/goast/hemat_data/nfcore_runs/25NGS1307_real_20260516_210201/`

## Tone and working style

Concise prose over heavy bullet-point formatting. When proposing a
patch, rationale in 1-2 paragraphs before the code, commented for a
Python beginner. Show what you are about to do, then ask for the
outputs needed to paste back. Don't run more than one major step
ahead without confirmation.

If something fails, diagnose first by reading `.command.err`,
`.command.run`, `.nextflow.log`, the work dir contents. Tell me what
the evidence says before proposing a fix.

When in doubt about state on disk: ask me to run a `grep`, `git log`,
`git diff`, or `ls -la`. Don't assume.
