# Session audit — 2026-05-16 (Phase 1 annotation + SomaticSeq diagnosis)

**Subject:** VEP_ANNOTATE port complete and committed; Path B (variant_filter
fix + ANNOTATION wiring) on disk uncommitted pending an upstream SomaticSeq
arbitrary-caller bug surfaced by clinical-variant diff against production.

**Repos touched:** patkarlab/nf-core-tspipe at /goast/hemat_data/nf-core-tspipe/

**Server:** gandalf

**HEAD at end of session:** 5cf6df6 (on origin/main)

---

## Outcome

Three commits landed cleanly. Path B (variant_filter.nf rewrite +
annotation.nf u2af1 wiring + ANNOTATION activation in tspipe.nf) is
applied to the working tree but uncommitted. The validation gate against
production on 25NGS1307 caught a real upstream divergence: SomaticSeq's
arbitrary-caller plumbing is dropping votes for FreeBayes, Platypus,
Pindel, and DeepSomatic, causing 6 clinically-significant variants
present in the production clinical TSV to be missing from the port's.

The annotation chain itself works correctly on the input it receives.
The bug is in `modules/local/somaticseq.nf` and must be fixed before
Path B can be safely committed.

---

## Commits landed (3)

| Hash    | Subject |
|---------|---------|
| cb3e7ff | docs(audit): relocate 2026-05-15 drafts to date-matched directory |
| 4f5351e | feat(config): scale resource envelope and label tiers for gandalf capacity |
| 5cf6df6 | feat(annotation): port VEP_ANNOTATE module + bin/annotate.py |

### cb3e7ff — draft cleanup

Moved `2026-05-15_session_notes_actual.md.draft` and
`2026-05-16_session_prompt.md.draft` out of `docs/audit/2026-05-16/`
into `docs/audit/2026-05-15/` per the directory-by-session-date
convention. Renames preserve git history via `git mv`.

### 4f5351e — resource scaling

Two-file change:

**conf/base.config** (portable, label-tier definitions):
- `process_medium`: 8 cpus / 32 GB → 24 cpus / 96 GB
- `process_high`: 16 cpus / 64 GB → 64 cpus / 256 GB
- `process_low` and time tiers unchanged

**conf/gandalf.config** (site-specific, executor + ceilings):
- `params.max_cpus`: 16 → 96
- `params.max_memory`: 128.GB → 512.GB
- `executor.cpus`: 16 → 160
- `executor.memory`: 64 GB → 1280 GB
- `executor.queueSize`: 8 → 32

Targets ~17% headroom on the 192-core / 1.5 TB host. Patch script at
`tools/patches/2026-05-16/apply_resource_scaling.py`.

**Measured impact** (single-sample run on 25NGS1307):

| Stage             | Before (8 cpu) | After (24 cpu) | Change           |
|-------------------|----------------|----------------|------------------|
| BWA_MEM           | 12m            | 3m 16s         | **−73%**         |
| FASTP             | 5m 55s         | 5m 55s         | unchanged (bug)  |
| GATK4_BQSR        | (not recorded) | 6m 56s         | 1.4 effective cpu|
| ABRA2             | (not recorded) | 4m 50s         | 7/24 cpu used    |
| SOMATICSEQ_ENSEMBLE | (~5-6m est.) | 5m 46s         | 37 effective cpu |
| VEP_ANNOTATE      | n/a            | 2m 43s         | first real run   |
| VARIANT_FILTER    | n/a            | 8.3s           | first real run   |
| **Total wall time** | **35m**      | **33m 58s**    | **−3%**          |

Total only dropped by 3% because BWA_MEM's 9-minute win was largely
masked by BQSR/FASTP/ABRA2 not scaling. BQSR is single-threaded
without Spark mode and is now the dominant per-task time. FASTP is
pinned to 2 threads by a hardcoded `-w 2` in its module script.
ABRA2 uses only 7 of 24 allocated cpus.

Followup payback estimates: FASTP `-w 2` fix → ~3-4 min; BQSR Spark
mode → ~4-5 min; ABRA2 thread tuning → ~1-2 min. Achievable single-
sample target with all three: ~24 min. None done today.

### 5cf6df6 — VEP_ANNOTATE port

Files changed:

- `bin/annotate.py` (new) — near-direct port of `scripts/13_annotate.py`
  with combined-VCF branch dropped, hardcoded paths converted to
  required CLI arguments (`--vep-cache`, `--annovar-script`,
  `--annovar-db`, `--reference`), output filename derived from
  `--sample-name`. Parsing and merging functions preserved bit-for-bit
  from production.
- `modules/local/vep_annotate.nf` — full rewrite from stub. Uses
  `conda run -n vep vep ...` inside `annotate.py` for VEP (the env's
  Perl @INC requires activation, bare PATH export not enough). ANNOVAR
  uses the targeted-seq env's perl via the gandalf.config beforeScript.
- `conf/gandalf.config` — `annovar_db` repointed from non-existent
  `references/annovar_db` to real `software/annovar/humandb`; new
  `annovar_script` param added.
- `nextflow.config` — `params.annovar_script = null` registered.

Patch script: `tools/patches/2026-05-16/apply_vep_annotate_port.py`.

Validation: stub run completed (27/27 success), but ANNOTATION was
still commented out in tspipe.nf so VEP_ANNOTATE itself was not
exercised. Real validation deferred to Path B.

---

## Path B (uncommitted)

Three files patched, on disk under `apply_annotation_wiring.py`:

| File                                | Change |
|-------------------------------------|--------|
| `modules/local/variant_filter.nf`   | Full rewrite. Fixed three latent bugs (CLI flag mismatch, wrong output names, no u2af1 input). Now accepts `tuple (meta, annotated_tsv, u2af1_tsv)`. Symlinks `annotated_tsv` to `${meta.id}.somaticseq.annotated.tsv` so `bin/variant_filter.py`'s filename-by-convention discovery works. |
| `subworkflows/local/annotation.nf`  | Added `u2af1_tsv_ch` as 3rd take parameter, threaded into VARIANT_FILTER via `VEP_ANNOTATE.out.tsv.join(u2af1_tsv_ch)`. |
| `workflows/tspipe.nf`               | Uncommented `ANNOTATION(...)` call with the 5-channel signature. |

Patch script: `tools/patches/2026-05-16/apply_annotation_wiring.py`

Validation results (stub: 32/32 success; real-mode on 25NGS1307: all
32 processes COMPLETED with exit 0, total wall 33m 58s):

| TSV          | Port keys | Prod keys | Common | Port-only | Prod-only |
|--------------|-----------|-----------|--------|-----------|-----------|
| annotated    | 1405      | 1863      | 1336   | 69        | **527**   |
| filtered     | 1338      | 1650      | 1281   | 57        | **369**   |
| clinical     | 15        | 21        | 15     | 0         | **6**     |

The 6 missing clinical variants are clinically important and the
trigger for not committing Path B yet.

---

## The 6 missing clinical variants and the diagnosis

| Gene  | Variant                | VAF   | Callers (port-side)         |
|-------|------------------------|-------|-----------------------------|
| CEBPA | c.288C>G (p.Gly96=)    | 13.4% | VarDict + FreeBayes         |
| RAD21 | p.Leu155Phe            | 22.3% | FreeBayes + Platypus        |
| SETD2 | p.Pro1916His           | 25.5% | FreeBayes + DeepSomatic     |
| TET2  | p.Ser142Tyr            | 21.5% | FreeBayes + DeepSomatic     |
| TET2  | p.Glu1250Ter           | 22.1% | FreeBayes + DeepSomatic     |
| UBTF  | c.1247_1248ins27bp     | 1.95% | VarScan + Platypus          |

Note: sample 25NGS1307 is clinically characterized as FLT3-ITD positive
(validated yesterday's commit), U2AF1 hotspot positive, and KMT2A-PTD
positive. The U2AF1 and KMT2A-PTD status was NOT validated in this
session's port output and remains untested.

### Diagnostic trail

Q1: Per-caller VCF row counts — port within ±5 of production for most
callers. Platypus port=454 vs prod=689 (34% deficit) is the only
non-trivial caller-level difference.

Q2: All 6 missing clinical variants ARE present in the port's per-caller
VCFs as expected from the table above. So individual callers detected
them; loss is downstream.

Q3: All 6 missing variants are in the port's SomaticSeq VCF
(`25NGS1307.somaticseq.vcf`). So SomaticSeq emits them. Loss is even
further downstream OR they are emitted with insufficient consensus
support to clear the filter.

Q4: SomaticSeq FILTER column comparison (decisive evidence):

| Gene  | Port (FILTER / NUM_TOOLS / MVDKFP)  | Prod (FILTER / NUM_TOOLS / MVDKFP)   |
|-------|-------------------------------------|--------------------------------------|
| CEBPA | REJECT / 1 / absent                 | REJECT / 2 / 0,0,1,0,1,0,0,0         |
| RAD21 | REJECT / 1 / absent                 | REJECT / 2 / 0,0,0,0,1,1,0,0         |
| SETD2 | REJECT / 1 / absent                 | REJECT / 2 / 0,0,0,0,1,0,0,1         |
| TET2-S| REJECT / 1 / absent                 | REJECT / 2 / 0,0,0,0,1,0,0,1         |
| TET2-E| REJECT / 1 / absent                 | REJECT / 2 / 0,0,0,0,1,0,0,1         |
| UBTF  | REJECT / 1 / absent                 | REJECT / 2 / 0,1,0,0,0,1,0,0         |

**Both port and production tag all 6 as REJECT**, so production has a
REJECT-rescue step downstream of `variant_filter.py` that we have not
found in either the port or the production scripts yet. Most likely
candidate: `15_oncovi.py` or `17c_clinical_tier.py` may include hotspot
rescue logic. NOT investigated this session.

**Port shows NUM_TOOLS=1 with MVDKFP absent**; production shows
NUM_TOOLS=2 with MVDKFP populated. MVDKFP encodes arbitrary-caller
votes (positions 5-8 = FreeBayes, Platypus, Pindel, DeepSomatic). Port
is registering zero arbitrary-caller support across all 6 variants.

### Root cause: somaticseq.nf arbitrary-caller plumbing is broken

Inspection of `modules/local/somaticseq.nf` script block (~line 134):

```bash
# NOTE 2026-05-17: pindel and deepsomatic temporarily dropped from
# the arbitrary-caller loop. Both produce valid VCFs upstream but the
# SomaticSeq preprocessing loop crashes during their iteration in ways
# that proved hard to pin down within a single debug session.
# Production's 07_somaticseq.py uses the 6-caller stable baseline.
# Revisit pindel+deepsomatic integration in a dedicated session.
for ENTRY in "freebayes:${freebayes_vcf}" "platypus:${platypus_vcf}"; do
```

(Date in the comment is "2026-05-17" but the change must have landed
earlier; possibly a typo for 2026-05-15 or off-by-one.)

Two distinct issues in that loop:

1. **Pindel and DeepSomatic deliberately removed from the loop scope.**
   Explains 3 of 6 missing variants directly (SETD2 + 2 TET2, all
   FreeBayes+DeepSomatic 2-caller support; without DeepSomatic count,
   they collapse to single-caller support).

2. **FreeBayes and Platypus votes also not registering despite being
   in the loop.** All 6 port variants show NUM_TOOLS=1 and MVDKFP
   absent — if FreeBayes/Platypus arbitrary-caller votes were
   reaching SomaticSeq's MVDKFP encoding, RAD21 should at minimum show
   NUM_TOOLS=2 with `0,0,0,0,1,1,0,0`. It doesn't. So the arbitrary-
   caller plumbing is broken even for the callers nominally in scope.

Suspected mechanism for issue 2: the bash subshell expansion of
`${ARB_SNV_LIST[@]}` and `${ARB_INDEL_LIST[@]}` inside the
`$( [ ... ] && echo "..." )` construct may not be passing the array
elements correctly through Nextflow's script-rendering layer. Or
`splitVcf.py` may be producing malformed VCFs that SomaticSeq silently
ignores. Needs runtime inspection of the SOMATICSEQ_ENSEMBLE work
dir's `.command.sh` and `.command.log` — not done this session
because `work/` was empty by the time we needed to look (cleared
between iterations).

---

## Resource scaling reality check

The 33m 58s total wall time on 25NGS1307 with the new envelope (160
cpu / 1280 GB) vs ~35 min on the old envelope (16 cpu / 64 GB) was a
modest 3% improvement, despite BWA_MEM dropping from 12m to 3m 16s.

Reason: per-task scaling now reveals other bottlenecks that didn't
matter before. BQSR (6m 56s, 1.4 effective cpu — single-threaded,
needs Spark mode for parallelism), FASTP (5m 55s, hardcoded `-w 2`
script bug), and ABRA2 (4m 50s, using 7 of 24 cpus — needs thread arg
tuning) collectively now account for ~18 minutes of serial-ish wall
time.

The new envelope WILL pay off for batch runs (6+ samples in parallel)
because the executor cap allows real concurrency. For single-sample
wall time, the next-priority tuning is FASTP `-w 2` followed by BQSR
Spark mode.

---

## Operational habits worth maintaining

Carrying forward from prior sessions, all still valid:

- Multi-line commit messages via `cat > /tmp/msg.txt; git commit -F /tmp/msg.txt`
- Python str_replace patches under `tools/patches/<date>/apply_*.py`
- File transfer via `/mnt/user-data/outputs/` → `~/inbox/from_claude/` → target
- Pre-flight `grep + git log + git diff` before any module replacement
- `rm -rf .nextflow/cache/` after any change affecting container/config resolution
- `.command.run` and `.command.err` are the authoritative records of
  what actually executed; check first when behavior is unexpected

New habit codified this session:

- **For long-running pipeline executions, use screen** (or tmux) so SSH
  disconnects don't kill the run. Start with `screen -S <name>`,
  detach with `Ctrl-a` `d`, reattach with `screen -r <name>`. The
  SIGHUP kill we hit at task 2 of the first real-mode run was the
  motivator.

- **When pasting Python code blocks**, write them to a file first
  (`/mnt/user-data/outputs/` then transfer) rather than pasting
  directly into bash. The bash interpreter mis-parses Python syntax
  in ways that can accidentally trigger package installation
  prompts.

---

## Carry-forward priorities for next session (in order)

### 1. SomaticSeq arbitrary-caller plumbing fix (BLOCKING)

This blocks Path B commit and all downstream validation. Two sub-issues:

**1a. Re-enable Pindel and DeepSomatic in the loop.** The comment
says "crashes during their iteration in ways that proved hard to pin
down" — needs investigation. Suggested approach: enable them one at
a time with verbose logging, capture the exact failure mode from
`.command.err`. Production's `07_somaticseq.py` handles 6 callers
(FreeBayes, Platypus + 4 native); the port adds Pindel and
DeepSomatic. If the crash is in `splitVcf.py` on Pindel's structural-
variant VCF format, may need a pre-filter to drop non-SNV/non-INDEL
records.

**1b. Diagnose why FreeBayes and Platypus arbitrary-caller votes
aren't reaching SomaticSeq's MVDKFP output**, despite both being in
the loop. Diagnostic step: run the pipeline, immediately copy the
SOMATICSEQ_ENSEMBLE work dir BEFORE re-running, inspect
`.command.sh` to see the actual rendered SomaticSeq invocation,
check whether `--arbitrary-snvs` and `--arbitrary-indels` are
present and well-formed in the executed command. The bash subshell
expansion `$( [ ${#ARB_SNV_LIST[@]} -gt 0 ] && echo "--arbitrary-snvs ${ARB_SNV_LIST[@]}" )`
is the prime suspect for misexpansion.

After fix: re-run real-mode validation on 25NGS1307, expect NUM_TOOLS
and MVDKFP to match production for the 6 variants. Variants should
now appear in port's clinical TSV (modulo the REJECT-rescue step,
see priority 2).

### 2. Find and port the REJECT-rescue step

Both port and production tag all 6 variants as SomaticSeq REJECT, yet
production's clinical TSV contains them. There must be a downstream
rescue step in production that promotes REJECT-tagged variants based
on consequence/hotspot/driver-gene criteria. Most likely candidates:

- `15_oncovi.py` (oncogenicity scoring may include rescue logic)
- `17c_clinical_tier.py` (clinical tiering, not yet ported, currently
  no module exists; this is the priority-1 module from the original
  Phase 1 scope)
- A separate post-filter pass somewhere we haven't inspected

Diagnostic: grep production scripts for "REJECT" / "rescue" / "tier"
to find the responsible code, then either port it as part of the
relevant module or as a new post-filter step.

### 3. Re-validate Path B against production

After (1) and (2) land: re-run real-mode on 25NGS1307 and recompute
the three-tier diff (annotated, filtered, clinical) against production
results. Expected outcome after fix: port-only and prod-only counts
should drop substantially. Acceptable threshold: clinical TSV should
have all production variants except any deliberately dropped (e.g.
synonymous CEBPA if the consequence filter is correct to exclude it).

Once validated: commit Path B as a feat patch with a commit message
that captures the SomaticSeq fix dependency.

### 4. Resume Phase 1 stub-filling and CLINICAL_TIER work

After Path B is committed and clinical-variant parity is achieved,
return to the remaining annotation/reporting stubs:

- VARIANT_VALIDATOR (port from `bin/variant_validator.py`, already in bin/)
- ONCOVI (port from `bin/oncovi.py`, already in bin/)
- FLT3_TO_VARIANTS (port from `bin/flt3_to_variants.py`, already in bin/)
- CLINICAL_TIER (NEW; port from production `scripts/17c_clinical_tier.py`,
  also requires creating `bin/clinical_tier.py`)
- IGV_REPORTS (port from `bin/igv_reports.py`)
- ORGANIZE_OUTPUT (port from `bin/organize_output.py`)
- Samplesheet schema: add `dx` (diagnosis) column for diagnosis-aware
  clinical tiering
- Activate `REPORTING(...)` call in tspipe.nf

### 5. Per-process resource tuning (lower priority)

If single-sample wall time becomes important again:

- FASTP `-w 2` script bug — change to `-w ${task.cpus}` in fastp.nf
- BQSR Spark mode or interval-split for parallelism
- ABRA2 explicit `--threads ${task.cpus}` if not already set

### 6. Validate U2AF1 and KMT2A-PTD detection (clinical correctness)

Sample 25NGS1307 has documented U2AF1 hotspot and KMT2A-PTD mutations
in addition to the FLT3-ITD validated yesterday. Once the SomaticSeq
arbitrary-caller fix lands and Path B is committed:

- U2AF1: verify the U2AF1_RESCUE module produces the expected
  hotspot calls and they make it through VARIANT_FILTER's u2af1
  merge into the clinical TSV.
- KMT2A-PTD: this is a structural rearrangement, normally caught
  by Pindel. With Pindel currently dropped from the SomaticSeq loop,
  KMT2A-PTD support is at risk. Verify after priority 1 fix lands.

---

## Source-of-truth references

- Production scripts: `/home/hemat/targeted-seq-pipeline/scripts/`
  (symlinked from `/goast/hemat_data/targeted-seq-pipeline/scripts/`;
  both paths resolve to the same files via the toplevel symlink).
- Production results (ground truth): `/home/hemat/targeted-seq-pipeline/results/<sample>/`
- nf-core port: `/goast/hemat_data/nf-core-tspipe/`
- Latest validation run output: `/goast/hemat_data/nfcore_runs/25NGS1307_real_20260516_210201/`
- VEP cache (verified populated): `/goast/hemat_data/targeted-seq-pipeline/references/vep_cache/` (15 GB, homo_sapiens/105_GRCh38)
- ANNOVAR install: `/goast/hemat_data/targeted-seq-pipeline/software/annovar/` (table_annovar.pl + humandb/ with 4 of 5 expected databases)

Patch scripts on disk for this session:

- `tools/patches/2026-05-16/apply_resource_scaling.py` (committed)
- `tools/patches/2026-05-16/apply_vep_annotate_port.py` (committed)
- `tools/patches/2026-05-16/apply_annotation_wiring.py` (NOT committed; Path B)
