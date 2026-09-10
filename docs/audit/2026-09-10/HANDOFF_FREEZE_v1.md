# HANDOFF — FREEZE and PORT (nf-core-tspipe), written 2026-09-10 ~14:00

For a new chat. Goal set by Nikhil today: **fix the pipeline to a FINAL version on gandalf, then a
detailed handoff SOP for Vishram to set it up on clinical-23.** Step one is the freeze.

## 0. Where things stand (10 Sep, ~14:00)

- Repo `/goast/hemat_data/nf-core-tspipe` (GitHub `patkarlab/nf-core-tspipe`), branch `main`, clean and
  pushed after the RUN_BUNDLE_V1 commit. Nextflow 25.10.4. Validation run: outdir
  `/goast/hemat_data/twist_val/tspipe_run8` (eight samples, `<id>-TwistMyVal`), resume session
  `abea2914-e2f9-44c0-961a-2f9c50eab4d9`, launch line
  `nextflow run . --input pon_samplesheets/twist_val_8_fastq.csv --outdir /goast/hemat_data/twist_val/tspipe_run8 -profile gandalf,singularity -c conf/twist_apply.config -resume abea2914-e2f9-44c0-961a-2f9c50eab4d9`
  (launched with `setsid … > /tmp/<log> 2>&1 < /dev/null & disown`, never while
  `pgrep -u hemat -af "nextflow.*\.jar run"` prints a process).
- Committed today, in order: TP53_OBS_V1 (TP53 / 17p observation card + rule asset, builder 0.5.2-tp53);
  `5574352` BAF_V2 in-silico 17p cnLOH dilution (floor: any call from f ≈ 0.15, HIGH from ≈ 0.22 at
  noise-mult 2.5; site noise, not depth, sets it); `28debd9` ARM17P_V1; `d13e2e5` the 17p page
  (chromosome page `chr17p`, TP53 card on it, SNP-window depth sample-normalised; eight-sample
  finding: −0.18 probe-batch offset of the 17p windows, `docs/audit/2026-09-10/17p_window_depth_medians.md`);
  RUN_BUNDLE_V1 (`<outdir>/<run>_reports.zip`: cohort index + assets once + one folder per sample,
  beside the per-sample `<S>_report.zip`). SOPs: `docs/sops/dashboard_cnv_v2.md` carries the addenda.
- Not yet written: memo 19 for 10 Sep (`docs/memos/memo19_2026-09-10_session.md`; draft delivered
  with this handoff), `docs/output.md` update (dashboard artefacts, `clinical/cnv/`, `<run>_reports.zip`).

## 1. Working conventions (unchanged)

- Claude writes code and patchers; Nikhil pastes one command block at a time and returns the output
  (paste-and-verify). Files travel through `~/inbox/from_claude/` (to gandalf) and
  `~/inbox/to_claude/` (recon archives back). Patchers live in `tools/patches/<date>/`, are
  anchor-based, MARKER-guarded, dry-run by default, `--apply` to write, leave `.bak_<tag>_<stamp>`
  files that are purged after verification. Never write anchors from memory; recon the file first.
- Module-script edits re-execute that process on resume; edits to `bin/`, templates or assets are
  unhashed and need `-c /tmp/dash_nocache.config`
  (`process { withName: 'DASHBOARD' { cache = false } }`) for a dashboard-only re-render.
- `singularity exec` on gandalf needs `-B /goast`. Gate every launch on its pre-flight (a `PRE=1`
  variable, not an `&&` chain). Nextflow 25.10 progress lines read `[hash] NAME | n of m ✔`.
- Environments on gandalf: GATK container (`broadinstitute/gatk:4.5.0.0`, Python 3.6, matplotlib 3.2)
  for CHROM_PAGES and plotting scripts; DASHBOARD/REPORT_BUNDLE/RUN_BUNDLE on the host
  (`/home/hemat/anaconda3/envs/targeted-seq/bin/python`, 3.10, pandas, jinja2, matplotlib 3.10);
  `params.legacy_python_env`; hmftools env (Java 21) for PURPLE; reconCNV env; four processes on
  bare host: VEP_ANNOTATE, VARIANT_VALIDATOR, FLT3_TO_VARIANTS, ONCOVI. clinical-23 runs Docker,
  has no S3; internet access there is NOT yet known (see §4).

## 2. What "FINAL" has to mean — the freeze checklist

1. **Feature freeze now.** Only portability fixes and two known one-liners: the U2AF1 pileup report
   never reaching `clinical/` (`modules/local/organize_output.nf` stages it as
   `NO_FILE_u2af1_report.txt`, which `organize_output.py` treats as a sentinel — drop the stageAs;
   one ORGANIZE re-run), and the unused detector PNG `clinical/cnv/baf/<S>.baf.png` (drop from
   ORGANIZE or keep as QC — Nikhil's call). Everything under "deferred" (§5) is v1.1 after the port.
2. **Every process on a declared runtime.** Containers for the four bare-host steps (A1) and,
   recommended, for every host-env step too (DASHBOARD, REPORT_BUNDLE, RUN_BUNDLE, RECONCNV, PURPLE,
   anything on `legacy_python_env`): one Dockerfile per env under `containers/<name>/`, images tagged
   `local/<name>:<tag>`, built with `docker build --network=host`, exported with `docker save` plus
   md5, and convertible to Singularity for gandalf (`singularity_cache/local-<name>-<tag>.img`) so
   both hosts run the same bytes. This removes conda from the SOP entirely.
3. **No literal paths.** A `clinical23` profile (docker, resource limits), references and assets via
   `params.ref_dir` / `params.asset_dir` (today `conf/twist_apply.config` carries `/goast` and
   `/home/hemat` literals), a `params.yaml` template, and a reference manifest (path, size, md5)
   checked by an install-verification script.
4. **Network dependencies named and decided.** Run-time calls: VariantValidator (annotation),
   GeneBe, MobiDetails and OncoKB (DASHBOARD annotation, OncoKB needs a token), VEP cache (local).
   Offline clinical-23 → cache-first / offline mode (A2 territory: local VariantValidator stack with
   watchdog or cache-first, `launch_tspipe.sh` as the only entry point).
5. **Release artefacts.** Version tag; pinned Nextflow 25.10.4; the image set with checksums;
   `docs/RELEASE_NOTES.md`; `docs/output.md` current; SOP set (preflight, `--annovar-allow-missing-db`,
   CAVA/MANE selection, blacklist V2 tiers, sex-check policy, spike-in tab, BAF_V2 + CNV sub-tabs,
   17p page, TP53 rule table, bundles); a stub-DAG test (`-stub`, `check_annovar_fatal.py`,
   `compare_annotated.py`, `-preview` bad-samplesheet case); and the **run8 golden regression**: the
   same eight FASTQs on clinical-23 must reproduce gandalf's clinical and consensus tables
   (VEP byte-identity, audit Q7, still unproven — two consecutive VEP runs of one input settle it).
6. **The SOP for Vishram**, written last from the inventory so it describes what shipped:
   install (Java, Nextflow 25.10.4, Docker, `docker load` of the image set) → references (manifest,
   md5 check) → verify (`-stub`, then run8) → run (`launch_tspipe.sh`, samplesheet format, params)
   → outputs (per-sample `clinical/`, `<S>_report.zip`, `<run>_reports.zip`, cohort index) →
   troubleshooting (where logs are, how to resume, what a failed task looks like).

## 3. First step: the generated portability inventory

Not written by hand. A script that lists, for every process: container / conda / `beforeScript` /
`executor`; every `/goast`, `/home/hemat`, `anaconda3` literal in `nextflow.config`, `conf/`,
`modules/`, `subworkflows/`, `workflows/`, `bin/`, `tools/`; every `params.*` used and where it is
defined; every reference/asset the configs point at, with existence and size on gandalf. Output
`docs/audit/<date>/portability_inventory.md` = the A1 work list and the SOP skeleton. Recon block
for it (repo untouched):

    cd /goast/hemat_data/nf-core-tspipe
    T=~/inbox/to_claude/recon_freeze_$(date +%Y%m%d_%H%M).tgz
    tar czf "$T" --exclude='*.pyc' --exclude='__pycache__' main.nf nextflow.config nextflow_schema.json conf modules subworkflows workflows \
        $(ls tools/*.sh launch_tspipe.sh 2>/dev/null) $(ls docs/*.md 2>/dev/null) $(ls containers/*/Dockerfile 2>/dev/null) 2>/dev/null
    ls -la "$T"; tar tzf "$T" | wc -l
    grep -rhoE "/goast/[^ '\"\)]+|/home/hemat/[^ '\"\)]+" nextflow.config conf modules subworkflows workflows 2>/dev/null | sort -u > /tmp/paths.txt; wc -l /tmp/paths.txt
    while read p; do if [ -e "$p" ]; then printf "OK   %10s  %s\n" "$(du -sh "$p" 2>/dev/null | cut -f1)" "$p"; else echo "MISSING           $p"; fi; done < /tmp/paths.txt > ~/inbox/to_claude/path_inventory.txt; head -5 ~/inbox/to_claude/path_inventory.txt; wc -l ~/inbox/to_claude/path_inventory.txt

Then A1 in this order: inventory → Dockerfiles for the four bare-host processes (validate each
against the host output on one run8 sample before switching the module) → host-env images →
`clinical23` profile and params → manifest and verify script → the two one-liners → tag →
run8 regression on clinical-23 → SOP.

## 4. Questions for Nikhil (answers shape §2 items 2 and 4 and the SOP)

- Does clinical-23 have internet access at run time (VariantValidator, GeneBe, MobiDetails, OncoKB)?
  Is there an OncoKB token for it? If offline: cache-first mode is a requirement, not an option.
- Docker only on clinical-23, or is Singularity/Apptainer available too? Cores and RAM there
  (resource limits for the profile). Where will references and the outdir live?
- Who is Vishram for the SOP's level: a bioinformatician comfortable with Docker and Nextflow, or
  someone who follows it step by step?
- What "final" includes: confirm that A3 / BAF_V2c / PoN and blacklist rebuild / window-depth
  calibration are v1.1 (recommended), and whether the detector PNG stays as QC.
- Still-open decisions from today (all data-backed): TP53 rule-table wording
  (`assets/twist_myeloid/tp53_interpretation_rules.tsv`, fields listed in its header, each card shows
  the sample's values); BAF_V2 noise-mult stays 2.5 (recommended; 2.0 = 10–12 % / 20 % with one LOW
  false call in eight); wet-lab 17p cnLOH sample for a validated floor.

## 5. Deferred to v1.1 (after the port)

A3 site-level assay model (GOOD/WEAK/BIASED/UNSTABLE/UNINFORMATIVE, bias blacklist) with the
48-normal re-run, blacklist and `baf_background.tsv` rebuild, per-run calibration of the 17p window
depth (−0.18 offset); BAF_V2c (beta-binomial, per-site dispersion shrunk to the panel estimate,
CBS-style segmentation); A4 female normals and PoN; A5 conformity gate; A6 asset reconciliation;
A7 ClinVar refresh; A8 FLT3_ITD_EXT final VCF; A9 clinical validation (Nikhil); B items (germline
lens, MNV guard, 50–75 % blacklist band, badge count, mosdepth median, standalone report default);
C items (CNVkit sensitivity, DECoN exon_flags, oncoanalyser/UMI); the dashboard-time VAF overlay on
the 17p page; a CNV-tab pointer line for TP53-relevant samples; Twist letter (phasing-by-distance
table; supplementary windows need matched control windows or per-batch calibration); off-target
depth line from HsMetrics (memo 18 §3b, never seen).

## 6. Where the detail lives

`docs/memos/` (memo 17 = 9 Sep session, memo 18 = MoChA feasibility, memo 19 = 10 Sep, draft
attached), `docs/sops/dashboard_cnv_v2.md` (all 10 Sep addenda), `docs/audit/2026-09-10/`
(dilution README and tables, window-depth medians, TP53 check), `tools/patches/2026-09-10/`
(every patcher and check script of the day, each with a docstring), HANDOFF_2026-09-10_v1/v2 (the
A1–A10 / B / C register and the loose ends).
