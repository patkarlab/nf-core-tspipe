# 2026-05-16 — nf-core CNV subworkflow wiring + stub baseline

## Session goals

Pick up item 1 from the 2026-05-15 handoff: wire the six remaining CNV
.nf modules in the nf-core port into a functional `CNV_CALLING`
subworkflow consumed by `workflows/tspipe.nf`. Validate the wiring
with a stub-mode end-to-end run on validation sample 25NGS1307 before
committing to a real sample run next session.

## Scope of work delivered

### nf-core repo (`patkarlab/nf-core-tspipe`)

Two commits landed on top of `b41e6b4`:

- `3a2c4ce` — stub: add stub blocks to all 40 modules in modules/local/
- `41cccf6` — feat(cnv): wire 6 CNV modules into per-sample pipeline

Three apply scripts under `/tmp/cnv_wiring/`:

| Script | Scope |
|---|---|
| `apply_nfcore_cnv_wiring_part1.py` | `nextflow.config`, `conf/modules.config`, `workflows/tspipe.nf`, `subworkflows/local/cnv_calling.nf`, 5 module rewrites, `exon_cnv` soft-delete |
| `apply_nfcore_cnv_wiring_part2.py` | New `bin/cnvkit.py` (port of `scripts/12_cnv_calling.py`), `modules/local/cnvkit.nf` rewrite |
| `apply_nfcore_add_stub_blocks.py`  | `stub:` blocks across all 40 modules in `modules/local/` |

No production-side patches today — all work was on nf-core.

### Modules wired

Six modules joined into a single `CNV_CALLING` subworkflow with the
correct dependency DAG:

```
CNV_LOO_QC (already wired in build_pon.nf) produces panel-namespaced refs
   |
   v
CNVKIT  (bin/cnvkit.py)
   |
   +-> ZSCORE_CNV (bin/zscore_cnv.py)
   +-> CNV_PLOTS  (bin/cnv_plots.py)
   |
   +-> CNV_CONCORDANCE (bin/cnv_concordance.py)
         |
         +-> CNV_CLINICAL_REPORT (bin/cnv_clinical_report.py)
         +-> CNV_ANNOTATE        (bin/cnv_annotate.py)
```

EXON_CNV (`bin/exon_cnv.py`, production `12g_exon_cnv.py`) was
intentionally dropped from the per-sample DAG. Partial gene events
(KMT2A-PTD, IKZF1 Ik6, focal CDKN2A/CDKN2B) are now surfaced via the
combined per-chromosome scatter plots produced by CNV_PLOTS for human
review. `cnv_concordance.py` and `cnv_clinical_report.py` both treat
exon input as optional (`argparse default=None`), so dropping
EXON_CNV required no bin/ script changes. `modules/local/exon_cnv.nf`
and `bin/exon_cnv.py` were soft-deleted (renamed to
`.bak_apply_nfcore_cnv_wiring_part1_<ts>`).

### bin/cnvkit.py port

New file ported from production `scripts/12_cnv_calling.py` with three
notable simplifications:

- `infer_sex_from_cnr()` and `select_pon()` removed. Sex is now
  resolved upstream via `meta.sex` from the samplesheet; the CNVKIT
  .nf module selects the matching sex-specific PoN before invoking
  the script.
- `--pon`, `--blacklist`, and `--loo-summary` are required (no
  fallback defaults).
- `--sex` accepts `male`, `female`, or `unknown` (no `auto`). The
  module's script block warns when `meta.sex == 'unknown'` and falls
  back to the female PoN.
- One `cnvkit.py batch` invocation instead of two. The production
  wrapper ran batch with the default PoN, inferred sex, then re-ran
  with the sex-specific PoN; that's no longer necessary when sex is
  known up front.

`PANEL_GENE_CHROMS` is preserved hardcoded for the myeloid panel
(chr5/8/13/17/21). Future panels will need a `--panel-gene-chroms`
override hook; flagged as open item.

### Stub blocks across all 40 modules

Every module in `modules/local/` now has a `stub:` block. This was a
prerequisite for any meaningful DAG validation: without stubs,
`-stub` mode falls through to the real `script:` block, which on
gandalf hangs on the first process (FASTP) trying to pull and run a
singularity container. This explains why prior `-stub` attempts in
earlier sessions never seemed useful.

Each stub `mkdir -p`s declared directory outputs and `touch`es
declared file outputs. `versions.yml` outputs get a minimal valid
YAML payload (`"${task.process}":\n    stub: true`) so MultiQC's
version aggregation doesn't choke on empty files.

### conf/gandalf.config cleanup

Four CNV-path assignments pinned to production paths were removed:

```
cnv_pon            = "${params.pipeline_root}/references/cnvkit_pon/pon_reference.cnn"
cnv_loo_summary    = "${params.pipeline_root}/references/cnvkit_loo_summary.tsv"
cnv_noise_profile  = "${params.pipeline_root}/pon_normals/cnvkit_loo_qc_masked/loo_bin_noise_profile.tsv"
cnv_noisy_bins     = "${params.pipeline_root}/references/cnvkit_noisy_bins.bed"
```

These had been shadowing the asset-default fallback I added to
`workflows/tspipe.nf` in part 1. With them gone, the asset-default
path `${projectDir}/assets/${params.panel}/...` fires cleanly, with
`--cnv_loo_summary` and friends still available as CLI overrides
when a non-asset path is required. Backup at
`conf/gandalf.config.bak_cnv_param_removal_20260514_144820`.

### Asset seeding

Five files copied from production into nf-core's asset directories:

| Source (production) | Destination (nf-core) |
|---|---|
| `references/cytoBand_hg38.txt`                                | `assets/references/cytoBand_hg38.txt` |
| `references/ClinGen_gene_curation_list_GRCh38.tsv`            | `assets/references/ClinGen_gene_curation_list_GRCh38.tsv` |
| `references/cnvkit_hg38_pon_male.cnn`                         | `assets/myeloid/cnvkit_pon_male.cnn` |
| `references/cnvkit_hg38_pon_female.cnn`                       | `assets/myeloid/cnvkit_pon_female.cnn` |
| `pon_normals/cnvkit_loo_qc_masked/loo_bin_noise_profile.tsv`  | `assets/myeloid/loo_bin_noise_profile.tsv` |

These are currently untracked in nf-core. Tracking decision (Git LFS
vs `.gitignore` plus deployment doc) is deferred to next session —
files total ~5.5 MB, all binary or large TSV.

## Key findings during the session

### Container declaration for pure-Python modules

I had set `container 'quay.io/biocontainers/pandas:2.1.4'` on the four
pandas-only modules (ZSCORE_CNV, CNV_CONCORDANCE, CNV_CLINICAL_REPORT,
CNV_ANNOTATE). That image does not exist on quay.io:

```
FATAL:   While making image from oci registry: error fetching image:
         failed to get checksum for docker://quay.io/biocontainers/pandas:2.1.4:
         MANIFEST_UNKNOWN: manifest unknown
```

Biocontainers does not publish a standalone pandas image; pandas
ships inside other tool images. Fix: reuse the cnvkit image
(`quay.io/biocontainers/cnvkit:0.9.10--pyhdfd78af_0`) which already
bundles pandas, numpy, and matplotlib. Cost: zero, since the image
was already pulled and cached by CNVKIT.

### gandalf.config shadowed asset defaults

The first stub-validation attempt failed with:

```
No such file or directory:
/goast/hemat_data/targeted-seq-pipeline/references/cnvkit_loo_summary.tsv
```

Root cause: `conf/gandalf.config` was authored before BUILD_PON
existed and pinned the four CNV params to production paths. The
fallback `params.cnv_loo_summary ?: "${projectDir}/assets/..."` in
`tspipe.nf` never fired because the elvis operator's left side was
always truthy.

Worth a wider review at some point: any other params in
`gandalf.config` pointing at production paths that should now resolve
to asset defaults? The `pipeline_root = '/goast/hemat_data/targeted-seq-pipeline'`
itself is fine (it is the legacy production tree, deliberately
referenced for dbsnp, vep_cache, annovar_db that haven't been ported
to assets).

### No nf-core modules had stub blocks

All 40 modules lacked `stub:` blocks. In `-stub` mode, Nextflow falls
through to the real `script:` block, which on gandalf hangs on the
first process (FASTP) trying to pull and run a singularity container.
This explains why prior `-stub` attempts in earlier sessions never
seemed useful for validation work. Fix is mechanical and was applied
in one pass to all 40 modules.

### Female PoN age mismatch

`cnvkit_hg38_pon_female.cnn` is dated Feb 14, 2026; `cnvkit_hg38_pon_male.cnn`
is May 14, 2026. The male PoN was rebuilt against the masked
reference in the recent realign work but the female PoN was not. For
female samples, calls may have a subtly different background until a
matching female-PoN rebuild lands. Not a blocker for the wiring;
flagged for the real validation pass against 25NGS1307.

### CNVKIT output basenames match production exactly

From `/goast/hemat_data/targeted-seq-pipeline/results/25NGS1307/cnvkit/`:

```
25NGS1307.final-diagram.pdf     (from cnvkit batch --diagram)
25NGS1307.final-scatter.png     (from cnvkit batch --scatter)
25NGS1307.scatter.png           (from cnvkit.py scatter step 6)
25NGS1307.scatter.chr*.png      (from per-chrom scatter step 7)
```

All declared as named emits on the CNVKIT .nf module so downstream
modules (CNV_PLOTS) consume by exact basename. Module shape verified
on the stub run.

### `ch_bed` is a queue channel consumed by many processes

`workflows/tspipe.nf` line 38 constructs `ch_bed` via
`Channel.fromPath(params.bed, checkIfExists: true)` — a queue
channel with a single element. Multiple downstream processes
(FASTP-side aside; variant callers, CNV modules) all consume from
this same channel. Strictly speaking only the first consumer should
receive the file; subsequent consumers should block on an empty
queue.

Stub mode passed cleanly with this in place because stubs do not
actually read inputs (`touch` only). A real (non-stub) run could
deadlock. Flagged for the next session: convert to
`Channel.value(file(params.bed))` defensively before the real
validation run.

## Validation evidence

Stub-mode end-to-end run on 25NGS1307 (samplesheet at
`/tmp/cnv_wiring/validation_samplesheet.csv`, sex='unknown' →
female-PoN fallback):

```
[c1/c5acd7] FASTP                              [100%] 1 of 1, cached: 1 ✔
[4a/f412f8] BWA_MEM                            [100%] 1 of 1, cached: 1 ✔
[af/46d6cf] PICARD_MARKDUPLICATES              [100%] 1 of 1, cached: 1 ✔
[04/04b3a6] GATK4_BQSR                         [100%] 1 of 1, cached: 1 ✔
[44/b72e43] ABRA2                              [100%] 1 of 1, cached: 1 ✔
[c6/281f2f] GATK4_MUTECT2                      [100%] 1 of 1, cached: 1 ✔
[94/9d6ba3] U2AF1_RESCUE                       [100%] 1 of 1, cached: 1 ✔
[05/96f0b4] VARDICT                            [100%] 1 of 1, cached: 1 ✔
[1a/4412dc] VARSCAN                            [100%] 1 of 1, cached: 1 ✔
[d8/d0884a] FREEBAYES                          [100%] 1 of 1, cached: 1 ✔
[ce/b2302a] STRELKA                            [100%] 1 of 1, cached: 1 ✔
[9a/ae8d43] PLATYPUS                           [100%] 1 of 1, cached: 1 ✔
[8c/1839fb] PINDEL                             [100%] 1 of 1, cached: 1 ✔
[01/cbf5b8] DEEPSOMATIC                        [100%] 1 of 1, cached: 1 ✔
[b6/ed19aa] SOMATICSEQ_ENSEMBLE                [100%] 1 of 1, cached: 1 ✔
[23/ec3d61] CNV_CALLING:CNVKIT                 [100%] 1 of 1, cached: 1 ✔
[7e/fe5d28] CNV_CALLING:ZSCORE_CNV             [100%] 1 of 1 ✔
[cc/d30695] CNV_CALLING:CNV_PLOTS              [100%] 1 of 1, cached: 1 ✔
[c0/edcbc6] CNV_CALLING:CNV_CONCORDANCE        [100%] 1 of 1 ✔
[35/10e070] CNV_CALLING:CNV_CLINICAL_REPORT    [100%] 1 of 1 ✔
[3d/cc4ffb] CNV_CALLING:CNV_ANNOTATE           [100%] 1 of 1 ✔
```

21/21 processes green. Validates:

- Channel joins in `subworkflows/local/cnv_calling.nf` all resolve
- CNVKIT's 12-emit declaration matches downstream consumers' shapes
- Sex-specific PoN selection compiles (real selection logic not
  exercised in stub mode but the GString resolves cleanly)
- Asset-default fallback `${projectDir}/assets/${params.panel}/...`
  fires for all six reference channels
- Panel-namespaced layout (`myeloid/`) is consistent across
  BUILD_PON and the per-sample workflow

Stub validation log: `/tmp/cnv_wiring/stub_validation_v5.log`.
Apply logs: `/tmp/cnv_wiring/{part1,part2,stubs}_apply.log`.

## What's still open

The real validation gate is a non-stub run on 25NGS1307 with side-by-side
comparison against `/goast/hemat_data/targeted-seq-pipeline/results/25NGS1307/cnvkit/`.
That's the next session.

Carrying forward from the 2026-05-14 handoff:

1. **End-to-end run on 25NGS1307** vs production cnvkit outputs.
   Stub mode validates topology only; bin/ scripts have not been
   exercised in nf-core yet.
2. **`ch_bed` channel type** — convert to `Channel.value(file(params.bed))`
   before the real run (see Key findings).
3. **CDKN2A/B whitelist** — still pending from 2026-05-14; rescue
   logic in `18_cnv_annotate.py` handles clinical safety today.
4. **Female PoN rebuild** against masked reference (see Key findings).
5. **`PANEL_GENE_CHROMS` configurability** for non-myeloid panels.
6. **Asset file tracking** — Git LFS vs `.gitignore` + deployment
   doc decision for the 5 newly-seeded asset files.
7. **Sex-stratified LOO refactor** — still open from 2026-05-15.
8. **Bug 2** (three tier-label systems in 12e/12f/18) — design
   unification, deferred from 2026-05-15.
9. **Bug 5** (per-chromosome baseline in 12g) — moot now that 12g is
   out of the nf-core DAG; production-only concern.
10. **Bug 7** (genemetrics CI aggregation) — informational note.

## Conda environment

No production-side scripts touched today. nf-core port uses
container images where declared; the production pipeline conda env
remains `/home/hemat/anaconda3/envs/targeted-seq/` (Python 3.10.14,
CNVKit 0.9.12). The nf-core container is CNVKit 0.9.10.

## Git references

- production: `ca4d291` (unchanged today; previous handoff carried
  the audit-note commit on top of `bb2d2ee`)
- nf-core:    `41cccf6` (main, two commits ahead of `b41e6b4`):
   - `3a2c4ce` — stub: add stub blocks to all 40 modules in modules/local/
   - `41cccf6` — feat(cnv): wire 6 CNV modules into per-sample pipeline
