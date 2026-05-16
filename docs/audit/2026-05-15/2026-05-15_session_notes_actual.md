# 2026-05-15 (evening) — SomaticSeq BAM cross-pairing bug fix + publishDir gap fix

## Session goals

Pick up from the handoff: fix the SOMATICSEQ_ENSEMBLE positional-channel
bug that caused 5 of 6 samples' somaticseq outputs in this morning's
6-sample batch to be biologically invalid (caller VCFs from one sample
integrated with read evidence from another). Re-run the affected samples
and verify the fix.

## Scope of work delivered

### nf-core repo (`patkarlab/nf-core-tspipe`)

Two commits landed on top of `89db80d`:

- `3bf7eb4` — fix(somaticseq): join BAM by meta key to prevent cross-sample BAM/VCF pairing
- `7e64666` — fix(somaticseq): publish SOMATICSEQ_POSTPROCESS outputs to results dir

No production-side patches today — all work was on nf-core.

### Files modified

| File | Commit | Change |
|---|---|---|
| `workflows/tspipe.nf`           | `3bf7eb4` | Chain `.join(ch_final_bam, by: 0)` onto `ch_somaticseq_in`; drop `ch_final_bam` from call args |
| `modules/local/somaticseq.nf`   | `3bf7eb4` | Fold `path(bam), path(bai)` into the meta-keyed tuple; remove redundant `tuple val(_meta_bam), path(bam), path(bai)` input |
| `conf/modules.config`           | `7e64666` | Add `withName: 'SOMATICSEQ_POSTPROCESS' { publishDir = [...] }` block mirroring the SOMATICSEQ_ENSEMBLE block |

### Patch tooling

One patch script at `/tmp/apply_somaticseq_bam_join.py` — Python
`difflib`-based dry-run + apply tool with `.bak_*` backups, used for
the two-file `3bf7eb4` patch. The modules.config publishDir fix was a
direct edit (already present in working tree from earlier in the day).

## The bug

### What it was

`SOMATICSEQ_ENSEMBLE` accepted the per-sample BAM as a *separate*
meta-keyed tuple input:
And `workflows/tspipe.nf` passed `ch_final_bam` positionally to the
process:
When two meta-keyed queue channels are passed positionally to one
process, Nextflow pairs them **by queue order, not by meta key**. With
multiple samples in flight, the Nth somaticseq task received the Nth
BAM regardless of which sample's VCFs it was processing.

### Evidence from this morning's batch
was symlinked into `26CGH260`'s somaticseq workdir. 5 of 6 samples'
ensemble outputs were biologically invalid. 25NGS1307's was correct
only by coincidence — its workdir happened to receive its own BAM.

### Code smell that should have been caught earlier

The original module declared the second tuple as
`tuple val(_meta_bam), path(bam), path(bai)`. The underscore prefix
on `_meta_bam` is the conventional way to silence "unused variable"
warnings in linters. The original author saw the meta key was unused
and silenced the warning rather than asking *why* it was unused — the
answer was that it should have been used to join, not ignored.

Heuristic for future work: if you find yourself silencing an unused-arg
warning in a Nextflow process input, the right action is usually to
either (a) use the arg, or (b) restructure so the arg isn't needed at
all. Never silence-and-leave.

## The fix (Option A: meta-key join)

`workflows/tspipe.nf` — chain BAM into the same join cascade:
`modules/local/somaticseq.nf` — collapse to one meta-keyed tuple:
## VARIANT_CALLING audit

Same paste of `subworkflows/local/variant_calling.nf:1-50` confirms
each caller takes one meta-keyed queue (`bam_ch`) plus value /
single-element channels (`reference_ch`, `bed_ch`, `pindel_bed_ch`,
`gnomad_ch`, `gnomad_tbi_ch`). The cross-pairing bug shape (two
meta-keyed queues passed positionally) does not occur. No fix
needed there.

## FLT3_ITD foreshadowed bug

`workflows/tspipe.nf:146` (currently commented out, scheduled for
Phase 2):
This has the same bug shape pre-formed: two meta-keyed queue channels
passed positionally. When uncommented, must use
`.join(by: 0)` instead. Captured in the `3bf7eb4` commit message as a
note to future-self.

## Why the second fix (publishDir) was needed

During verification of the BAM-join fix, the published somaticseq
directory contained the ensemble intermediates (Consensus.sSNV.vcf,
Consensus.sINDEL.vcf, the workdir) but not the merged final VCF
(`${sample}.somaticseq.vcf` / `.vcf.gz` produced by
SOMATICSEQ_POSTPROCESS). The downstream ANNOTATION subworkflow consumes
that merged VCF and won't have a problem (it reads via the Nextflow
channel, not the published file), but for manual inspection and
production-side comparison the final VCF needs to land under
`${outdir}/${sample}/somaticseq/`.

Fix: added matching `withName: 'SOMATICSEQ_POSTPROCESS'` publishDir
directive in `conf/modules.config`, mirroring the existing
`SOMATICSEQ_ENSEMBLE` block.

## Verification methodology

### Pre-launch (commit hygiene)

- Working tree clean for both fix files via `git status --short`
- `HEAD` advanced past `89db80d` to `3bf7eb4` then `7e64666`
- Two-file diff stat checked: `2 files changed, 7 insertions(+), 5 deletions(-)` for `3bf7eb4`; `1 file changed, 7 insertions(+)` for `7e64666`
- Commit messages stored intact (terminal paste-wrapping mangled the first attempt; recovered via `git commit --amend -F /tmp/<msg>.txt`)

### Mid-flight (correct check)

For each active SOMATICSEQ_ENSEMBLE workdir, compare:
- **Task tag** (derived from the output directory name
  `<sample>.somaticseq_workdir`) against
- **Staged BAM `@RG SM:` tag** (via `samtools view -H`)

The task tag is the sample Nextflow is *supposed* to be processing.
The `@RG SM:` is the sample the staged read data is *actually* from.
If they disagree, the BAM bug is still present. If they agree for
every task, the fix is verified.

Result for the first task (26CGH260, workdir
`c8/df143223915795feb76f32a392ff52`):
Matches. Bug is fixed for this sample. Same task completed with exit=0.

### Insufficient check (false-positive risk)

An earlier verification script derived the "task sample" from the
staged BAM filename (`<sample>.final.bam`) and compared to the BAM's
SM tag. After Nextflow stages the BAM, filename and SM agree by
construction — the script always reports OK regardless of whether
upstream pairing was correct. The output-directory-derived task tag is
the only ground truth.

## Re-run execution

- Cleared stale published outputs for the 5 invalid samples:
for `s in 25NGS1736 25NGS1860 26CGH18 26CGH260 26CGH57`.
- 25NGS1307's prior somaticseq output was kept (its BAM happened to
  pair correctly, so its result is biologically valid). Its
  somaticseq task will re-run anyway because the input channel shape
  changed, producing a new task hash.
- Cleared `.nextflow/cache/*/db/LOCK` files.
- Launch via daemon screen:
- Log file: `/tmp/cnv_wiring/batch_6samples_bamfix_20260515_190817.log`.

### Cache behavior (validates the fix is real)

After launch:
- All 14 upstream processes per sample (FASTP, BWA_MEM, MARKDUPLICATES,
  BQSR, ABRA2, all 8 callers, U2AF1_RESCUE) showed
  `6 of 6, cached: 6 ✔` for all 6 samples.
- All 6 CNV_CALLING subworkflow steps also showed `6 of 6, cached: 6 ✔`.
- SOMATICSEQ_ENSEMBLE showed `0 of 6` (fresh hashes, expected — the
  channel shape change invalidated the task hash even for 25NGS1307).
- SOMATICSEQ_POSTPROCESS showed `0 of 1` after the first ensemble
  finished (it picks up tasks as they arrive).

If somaticseq had reported `cached: N > 0` we'd know the channel
join hadn't actually changed the task hash — a sign the fix didn't
land at the workflow level. It didn't, so the channel-shape change
took effect end-to-end.

### Mid-run status (snapshot at ~19:15)

| Sample | SOMATICSEQ_ENSEMBLE | BAM-tag match | Postprocess |
|---|---|---|---|
| 26CGH260   | DONE exit=0 | OK (SM:26CGH260) | queued |
| 26CGH57    | RUNNING     | (to verify when done) | - |
| 25NGS1307  | queued      | - | - |
| 25NGS1736  | queued      | - | - |
| 25NGS1860  | queued      | - | - |
| 26CGH18    | queued      | - | - |

Run is ongoing; ETA roughly 3-7 more hours given local-executor
sequential somaticseq execution.

## Open items for tomorrow

1. **Per-sample post-completion verification (mandatory).** Once all
   6 finish:
   - All 6 `task-tag = staged-BAM-SM` pairings confirmed OK.
   - All 6 `${sample}.somaticseq.vcf*` files published under
     `/tmp/nfcore_batch_6samples/${s}/somaticseq/`.
   - Variant counts non-zero per sample.

2. **Production-side parity comparison.** The success criterion from
   the prior session was 100% production PASS recall — verified on
   25NGS1307 only (and by coincidence). Need the same check across
   all 6 samples against
   `/goast/hemat_data/targeted-seq-pipeline/results/${s}/somaticseq/`.

3. **gandalf profile under-utilization (parallelism opportunity).**
   Current `conf/gandalf.config`:
   - `executor.cpus = 16`, `executor.memory = '64 GB'`,
     `queueSize = 8` — capping all of nextflow at 16 cores / 64 GB.
   - Gandalf has 192 cores, 1.5 TB RAM.
   - Effect: somaticseq runs 1-at-a-time (it requests
     `process_high`, which fills the 16-core budget).
   - Proposed tuning (separate commit, post-validation):
     `max_memory = '512.GB'`, `max_cpus = 32`,
     `executor.cpus = 128`, `executor.memory = '512 GB'`,
     `queueSize = 16`. Leaves ~64 cores and ~1 TB free for other
     gandalf users.
   - Tune only after current batch validates so we have a clean
     baseline.

4. **`conf/modules.config` `SOMATICSEQ_POSTPROCESS` publishDir
   effective for current run?** Nextflow re-reads config on launch,
   so the publishDir change should apply to tonight's run. If the
   published `*.somaticseq.vcf*` is missing from any sample's
   directory tomorrow morning, a `-resume` re-run will republish
   without re-executing the heavy work.

5. **Date inconsistency in audit tree.** Production HEAD already
   contains:
   - `ca4d291 docs(audit): 2026-05-15 session notes`
   - `5645657 docs(audit): 2026-05-16 session — nf-core CNV subworkflow wiring + stub baseline`
   - `dfc829b docs(audit): 2026-05-17 session — nf-core SomaticSeq port + parity validation`
   These are dated for sessions on 2026-05-15, -16, -17 — but today
   is the evening of 2026-05-15. The content of the existing
   `ca4d291` 2026-05-15 placeholder describes CNV BED-parser cleanup,
   not today's SomaticSeq bug fix. This file (`actual.md`) is the
   real record of today's evening session and should be reconciled
   with the production audit tree once we figure out the date math.
   Recommend keeping this file in `/tmp/` until tomorrow.

6. **Carry-forward from previous handoffs** (not addressed today):
   - Phase 1: VEP -> ANNOVAR -> final variant report
   - Phase 2: FLT3-ITD 4-tool ensemble (with the foreshadowed join bug above)
   - Phase 3: HsMetrics + SV callers (Manta/Delly) + SV annotation
   - Phase 4: PanelCN.MOPS (SKIP)
   - Female PoN rebuild against masked reference
   - PANEL_GENE_CHROMS configurability
   - Asset file tracking (Git LFS vs .gitignore + deployment doc)

## Lessons from tonight

1. **Two meta-keyed queue channels passed positionally to one Nextflow
   process is a bug shape.** The signal is the *receiving* process
   declaring two `tuple val(meta), ...` inputs and the *call site*
   passing both arguments separately rather than joining them. Audit
   all current and future process call sites for this shape.

2. **Underscore-prefixed unused args in process inputs are a red
   flag.** They mean the original author silenced a warning. Ask
   whether the arg should have been used, not "is the linter happy".

3. **`-m "..."` with a multi-paragraph commit message is fragile in
   terminal paste.** Long lines wrap at column boundaries and re-stitch
   in the wrong order, producing garbled commit messages that look fine
   at the command line. Use `git commit -F /tmp/msg.txt` for any
   message over a single line. Recovery via `git commit --amend -F`
   is safe only while the commit is local.

4. **For verifying meta-keyed channel joins worked, compare task tag
   to staged data identity.** Not staged-file basename to staged-file
   metadata (those agree by construction after staging). The task tag
   is the question, the staged metadata is the answer.

## Conda environment

No production-side scripts touched today. nf-core port uses container
images per declared process. SOMATICSEQ_ENSEMBLE runs in
`lethalfang/somaticseq:3.7.4`; SOMATICSEQ_POSTPROCESS runs in the
gatk4 container declared in the postprocess module (which has bcftools
on PATH for the final concat/rename steps).

## Git references

- production: `dfc829b` (unchanged today; pre-existing placeholder
  commits already span 2026-05-15 through -17 in main)
- nf-core:    `7e64666` (main, two commits ahead of origin `89db80d`):
   - `3bf7eb4` — fix(somaticseq): join BAM by meta key to prevent cross-sample BAM/VCF pairing
   - `7e64666` — fix(somaticseq): publish SOMATICSEQ_POSTPROCESS outputs to results dir

Both nf-core commits are local-only (not pushed). Push after
post-batch validation tomorrow.

## Active run state at end of session

- Screen session: `3565219.nfbatch_bamfix` (Detached)
- Log: `/tmp/cnv_wiring/batch_6samples_bamfix_20260515_190817.log`
- Workdir: `/goast/hemat_data/nf-core-tspipe/work`
- Outdir: `/tmp/nfcore_batch_6samples`
- Samplesheet: `/tmp/cnv_wiring/batch_6samples.csv` (6 samples)
- Progress at ~19:15: 1 of 6 SOMATICSEQ_ENSEMBLE done (26CGH260,
  exit=0, BAM-tag verified), 1 active (26CGH57), 4 queued.
