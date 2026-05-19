# 2026-05-19 — Backlog detail: KMT2A-PTD, PINDEL_FLT3_FILTER, IGV_REPORTS

Carried-forward items from the 2026-05-18 bootstrap that survived today's
review. Each section has: clinical/technical background, current state in
the nf-core port, what production does, files to touch, sketch of approach,
known unknowns, and effort estimate. None of these is a 30-minute job; each
is a real session.

Cross-references:
- Morning findings (today): `docs/audit/2026-05-19/morning_findings.md`
- B1 closed (per-caller VCF discrepancy was a phantom — see today's findings)
- B5 reframed (`Rescue_Note` column missing from production schema too,
  not a port regression)

---

## B4 — KMT2A-PTD detection

### Background

KMT2A partial tandem duplication (PTD) is a recurrent somatic alteration in
AML, typically duplicating exons 2–8 (or 2–10) in tandem on the same allele.
Clinical impact:
- AML adverse risk modifier per ELN 2022.
- Targetable by **revumenib** (FDA approved Nov 2024 for R/R KMT2A-rearranged
  leukemia). KMT2A-PTD shares the menin-MLL dependency with rearrangements,
  and revumenib is being evaluated for PTD specifically. Detection therefore
  has direct therapeutic consequences.

KMT2A-PTD is a copy-neutral or low-copy-gain partial gene event — read-depth
CNV callers (CNVKit, GATK CNV) can miss it because the affected exons stay
within normal-looking diploid depth when averaged across the whole gene.
Production detection usually relies on **per-exon depth ratios** comparing
the typical PTD region (exons 2–8/10) against the rest of KMT2A in the same
sample.

### Current state in nf-core port

From `docs/audit/2026-05-16/session_notes.md`, KMT2A-PTD was **intentionally
deferred to human scatter-plot review** during the CNV wiring session:

> *"EXON_CNV (`bin/exon_cnv.py`, production `12g_exon_cnv.py`) was
> intentionally dropped from the per-sample DAG. Partial gene events
> (KMT2A-PTD, IKZF1 Ik6, focal CDKN2A/CDKN2B) are now surfaced via the
> combined per-chromosome scatter plots produced by CNV_PLOTS for human
> review."*

So the current behavior is: per-chromosome scatter plots for chr11 are
generated for every sample, and a human reviewer is expected to look for the
PTD pattern (elevated depth on early exons relative to late exons of KMT2A).
There is no automated PTD call in the nf-core port's clinical TSV.

The KMT2A region in the panel BED (`MYOPOOL_240125_UBTF_hg38.bed`):
- KMT2A_Ex_1A through KMT2A_Ex_36 spanning chr11:118,436,462–118,522,227
- Exon 3 is heavily tiled (~25+ probes) consistent with PTD breakpoint
  hotspot — useful signal for any automated detector

### Production status (need to confirm in a real session)

Open question: does production actually compute a KMT2A-PTD call, or is it
also a manual scatter-plot review? `bin/exon_cnv.py` exists (and was
soft-deleted from nf-core) — it should be read to find out what it produced
for KMT2A specifically. The script is preserved at
`bin/exon_cnv.py.bak_apply_nfcore_cnv_wiring_part1_<ts>` in the nf-core repo
and lives as `scripts/12g_exon_cnv.py` in production at
`/goast/hemat_data/targeted-seq-pipeline/`.

If production does compute a PTD score, the work is **porting that logic**.
If production also leaves it to human review, the work is **adding an
automated PTD score that production never had** — bigger ask.

### Files to touch (estimated)

- `bin/kmt2a_ptd.py` (new) — a per-sample script that takes the CNVKit `.cnr`
  bin-level file and emits a per-sample PTD score: ratio of mean log2 of
  bins overlapping KMT2A exons 2–8/10 to mean log2 of bins overlapping
  exons 11–36, plus a simple call (`PTD_positive`, `PTD_indeterminate`,
  `PTD_negative`) with thresholds calibrated against the LOO PoN.
- `modules/local/kmt2a_ptd.nf` (new) — Nextflow module wrapping the script.
- `subworkflows/local/cnv_calling.nf` — wire `KMT2A_PTD` after `CNVKIT`.
- `bin/cnv_clinical_report.py` — extend to consume the PTD score and emit
  a clinical row when positive.
- Optional: extend `bin/organize_output.py` to surface the PTD score in
  `clinical/`.

### Sketch of approach

1. **Confirm production behavior first.** Read `12g_exon_cnv.py` and the
   resulting outputs for a known KMT2A-PTD-positive sample. If production
   already calculates a score, mirror it. If not, design fresh.
2. **Choose a metric.** Mean log2 ratio over exons 2-8 vs exons 11-36 is
   the standard heuristic but underperforms on subtle PTDs. Better: per-bin
   log2 with a Wilcoxon test between PTD region and rest-of-gene bins,
   adjusted for sex (KMT2A is autosomal — sex shouldn't matter, but the
   `loo_summary.tsv` bin variance differs by sex due to upstream
   normalization).
3. **Calibrate thresholds.** Use the 55 LOO normals as the negative
   distribution. Define `PTD_positive` as score > 99th percentile of LOO
   normals, `PTD_indeterminate` as 95th-99th. Avoid hardcoded thresholds.
4. **Validate** against any historical KMT2A-PTD-positive samples in the
   lab archive before declaring the detector ready for clinical use.

### Known unknowns / gotchas

- Whether the panel BED has enough KMT2A exon 2-10 coverage for a stable
  per-region depth estimate. From the BED, exons 2-10 have ~5-15 probes
  each, which is borderline. Exon 3 is well-tiled (the PTD breakpoint
  hotspot); the rest may be noisy.
- KMT2A-PTD breakpoints are typically intronic. SV callers (manta, severus)
  might catch them if the breakpoint reads happen to fall in adjacent
  exonic capture regions. Worth checking the production SV pipeline before
  building a depth-only detector.
- Clinically calibrating "indeterminate" thresholds requires positive
  controls. If the lab archive has zero historical PTD-positive samples,
  this becomes a literature-and-simulation exercise instead.

### Effort estimate

- Reading production `12g_exon_cnv.py` + design decision: 1-2 hours.
- Implementation if production score exists: 3-4 hours.
- Implementation if designing from scratch: 1-2 days.
- Validation against positive controls (gated on archive samples
  existing): variable.

**Net: half-day to two days depending on what production currently does.**

---

## D1 — PINDEL_FLT3_FILTER (bcftools view by region)

### Background

Pindel is run genome-wide (or panel-wide) and emits a VCF with all detected
indels and structural variants. For the FLT3-ITD ensemble call, we only care
about Pindel's output in the FLT3 exon 14-15 region (the canonical ITD
hotspot). Currently the entire Pindel VCF flows into SomaticSeq, which then
has to figure out which Pindel calls are FLT3-relevant.

The fix is conceptually trivial: subset the Pindel VCF to the FLT3 region
before it reaches SomaticSeq (or, alternatively, emit two Pindel outputs —
one full, one FLT3-only — and route them differently).

### Current state in nf-core port

- `modules/local/pindel.nf` runs Pindel and emits a single VCF
  (`25NGS1307.pindel.vcf` per the run_184438 output we looked at today —
  271 variants from a single Pindel call across the panel).
- No filter step exists between Pindel and SomaticSeq.

### Production status

The bootstrap said "real production has this" but we haven't confirmed
exactly where. Need to grep production for the bcftools-view-by-region step:

```bash
grep -rln "bcftools view.*FLT3\|chr13.*28033877\|pindel.*filter" \
    /goast/hemat_data/targeted-seq-pipeline/ 2>/dev/null
grep -rln "bcftools" /goast/hemat_data/targeted-seq-pipeline/scripts/ \
    2>/dev/null
```

### The FLT3 region

From the panel BED, FLT3 exon 14 (the JM-ITD region) covers chr13:28033877-
28034411. The conservative ITD region is chr13:28033877-28034411 (covers
Ex_14, Ex_15). A slightly wider window of chr13:28028000-28036000 picks up
the full hotspot context including exon 16.

### Files to touch

- `modules/local/pindel_flt3_filter.nf` (new) — bcftools view wrapper.
- `subworkflows/local/variant_calling.nf` — insert the filter between
  PINDEL and the somaticseq ensemble. Or alternatively, emit two Pindel
  channels from the PINDEL module: the full VCF (kept for human review)
  and the FLT3-filtered VCF (fed to SomaticSeq).
- `nextflow.config` — add a `params.flt3_region` default
  (`chr13:28033877-28034411` or wider) so the region is configurable per
  panel.

### Sketch of module

```groovy
process PINDEL_FLT3_FILTER {
    tag "$meta.id"
    container 'quay.io/biocontainers/bcftools:1.20--h8b25389_0'
    publishDir "${params.outdir}/${meta.id}/variant_callers/pindel",
        mode: 'copy', pattern: "*.flt3.vcf.gz*"

    input:
    tuple val(meta), path(vcf)
    val region

    output:
    tuple val(meta), path("${meta.id}.pindel.flt3.vcf.gz"),
                     path("${meta.id}.pindel.flt3.vcf.gz.tbi"), emit: vcf
    path "versions.yml", emit: versions

    script:
    """
    # Pindel emits uncompressed VCF; bgzip + index first, then view-by-region.
    bgzip -c ${vcf} > ${vcf}.gz
    tabix -p vcf ${vcf}.gz
    bcftools view -r ${region} -O z -o ${meta.id}.pindel.flt3.vcf.gz ${vcf}.gz
    tabix -p vcf ${meta.id}.pindel.flt3.vcf.gz
    cat <<-EOF > versions.yml
    "${task.process}":
        bcftools: \$(bcftools --version | head -1 | awk '{print \$2}')
    EOF
    """

    stub:
    """
    touch ${meta.id}.pindel.flt3.vcf.gz
    touch ${meta.id}.pindel.flt3.vcf.gz.tbi
    cat <<-EOF > versions.yml
    "${task.process}":
        stub: true
    EOF
    """
}
```

### Known unknowns / gotchas

- The region: confirm with the clinical team whether the existing FLT3-ITD
  ensemble (`FLT3_ITD_EXT`, `filt3r`, `getITD`) uses the same coordinates
  Pindel should be filtered to. Mismatched windows would create a
  systematic blind spot at the boundary.
- Index handling: if Pindel emits VCFs with unsorted records (it sometimes
  does), `bgzip` + `tabix` will fail. May need `bcftools sort` first.
- Does SomaticSeq want both filtered and unfiltered Pindel? Currently it
  consumes the whole VCF and decides per-position; filtering upstream
  changes what SomaticSeq has to work with. Worth confirming SomaticSeq
  configuration doesn't expect chrom/pos outside the FLT3 region.

### Effort estimate

- Confirm production's exact region + region width: 30 minutes.
- Module + wiring + stub block: 1 hour.
- Run on 25NGS1307 (known FLT3-ITD positive) and diff against production
  output: 1 hour.

**Net: half-day, mostly diligence-driven.**

---

## D2 — IGV_REPORTS real implementation (currently stub)

### Background

`igv-reports` is a Python package that takes a VCF + BAM + reference FASTA
and produces a standalone HTML page with embedded IGV.js views of each
variant. Clinically essential for case review — the molecular pathologist
wants to look at the read pileup for any variant before signing it out,
especially for hotspot calls, low-VAF variants, and anything in a high-noise
region.

Production has a real implementation. The nf-core port currently has only a
stub module.

### Current state in nf-core port

- `modules/local/igv_reports.nf` exists with a `stub:` block (added in
  `3a2c4ce`, 2026-05-16) but no real `script:` block, or one that doesn't
  produce useful output.
- Need to confirm by reading the current file:
  ```bash
  cat /goast/hemat_data/nf-core-tspipe/modules/local/igv_reports.nf
  ```

### Production status

Production has a working invocation. To find it:

```bash
grep -rln "create_report\|igv-reports\|igv_reports" \
    /goast/hemat_data/targeted-seq-pipeline/ 2>/dev/null
```

The production wrapper most likely lives at `scripts/19_igv_reports.py` or
similar (it would follow the numerical ordering convention).

### What the module needs

1. **Inputs:** the per-sample BAM (`.final.bam`), the clinical TSV (or the
   underlying SomaticSeq filtered VCF), and the reference FASTA + index.
2. **Output:** a single HTML report per sample, ideally in the
   `clinical/` subdirectory.
3. **Container:** `igv-reports` is pip-installable
   (`pip install igv-reports`). Either build a small container, find an
   existing biocontainer (search quay.io/biocontainers), or use a python
   environment.

### Sketch of module

```groovy
process IGV_REPORTS {
    tag "$meta.id"
    container 'quay.io/biocontainers/igv-reports:1.13.0--pyh7cba7a3_0'  // verify exact tag
    publishDir "${params.outdir}/${meta.id}/clinical",
        mode: 'copy', pattern: "*.html"

    input:
    tuple val(meta), path(clinical_tsv), path(bam), path(bai)
    path reference_fasta
    path reference_fai

    output:
    tuple val(meta), path("${meta.id}.igv_report.html"), emit: report
    path "versions.yml", emit: versions

    script:
    """
    # igv-reports expects a "sites" BED or VCF; convert TSV to BED on the fly.
    awk -F'\\t' 'NR>1 {print \$2"\\t"\$3-1"\\t"\$4"\\t"\$7":"\$5">"\$6}' \\
        ${clinical_tsv} > sites.bed

    create_report sites.bed \\
        --fasta ${reference_fasta} \\
        --tracks ${bam} \\
        --output ${meta.id}.igv_report.html

    cat <<-EOF > versions.yml
    "${task.process}":
        igv-reports: \$(create_report --version 2>&1 | awk '{print \$NF}')
    EOF
    """

    stub:
    """
    touch ${meta.id}.igv_report.html
    cat <<-EOF > versions.yml
    "${task.process}":
        stub: true
    EOF
    """
}
```

### Files to touch

- `modules/local/igv_reports.nf` — replace stub with real script.
- `workflows/tspipe.nf` (or `subworkflows/local/annotation.nf`,
  whichever currently owns the post-clinical-TSV steps) — wire
  IGV_REPORTS to consume the clinical TSV + final BAM.
- `bin/organize_output.py` — already places clinical artifacts; confirm
  it'll pick up the new `*.igv_report.html` without changes.
- `nextflow.config` — confirm reference FASTA/FAI are exposed as
  `params.fasta` / `params.fai` (they should be).

### Known unknowns / gotchas

- **Container availability.** `igv-reports` is on bioconda but biocontainer
  builds occasionally lag releases. If quay.io doesn't have a recent tag,
  options are: (a) build a small Dockerfile, (b) use a venv inside an
  existing python container, (c) install via conda inside a generic conda
  container.
- **HTML size.** igv-reports embeds BAM regions inline. For samples with
  many variants (50+), the HTML can exceed 10 MB and become slow to open.
  Production may have a config knob (region padding, max variants per
  report); read its wrapper to find out.
- **Path resolution inside HTML.** igv-reports stores relative paths to
  the reference. When the report is published to `clinical/`, those paths
  break. Production likely re-writes paths or uses inline (base64) data.
  Worth checking.
- **TSV column ordering.** The awk one-liner above assumes columns
  `Sample, Chr, Start, End, Ref, Alt, Gene, ...` matching the nf-core
  port's clinical TSV from today. The production TSV has a different
  column order — if the IGV report is generated from a different upstream
  artifact in production, may need to align.

### Effort estimate

- Find production wrapper + read it: 30 minutes.
- Module + wiring: 1-2 hours.
- Verify container availability + test on 25NGS1307: 1 hour.
- Visual review of an output HTML against production's: 30 minutes.

**Net: half-day.**

---

## Suggested order if all three are tackled

1. **D1 (PINDEL_FLT3_FILTER) first** — smallest, most contained, easiest
   to validate. Good warm-up for the next session.
2. **D2 (IGV_REPORTS) second** — moderate complexity, clear ground truth
   (production's HTML output), satisfying to land because clinical
   reviewers want this immediately.
3. **B4 (KMT2A-PTD) last** — biggest, most open-ended. Needs investigation
   of production behavior before any code is written. May expand
   significantly if no production script exists to port.

---

## Preconditions for next session

Confirm these before starting any of the above:

- VV REST stack still running. `curl -i http://localhost:8000/` should
  return 200. If not, follow recovery runbook in
  `docs/audit/2026-05-19/morning_findings.md`.
- `/home` still has reasonable headroom (`df -h /home` shows ≤95% used).
  If approaching 97% again, look first at `~/docker-data/volumes/`
  for new anonymous volumes that should be named.
- `git status` clean on the nf-core repo, on `main`, up-to-date with
  `origin/main` (today's last commit was `3268744`).
