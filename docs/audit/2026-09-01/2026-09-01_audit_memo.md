# Audit memo — 2026-09-01 — Twist myeloid CNV rebuild: exclusion criteria derived, assets rebuilt

Session scope: derivation of the BED-level exclusion lists for
`panel.combined.filtered.bed` (the single shared depth-pipeline artifact for
`BUILD_PON_TWIST`), which uncovered and attributed a capture batch effect in
the 48-normal cohort and replaced two recorded panel decisions with measured
criteria.

Prior sessions 2026-08-30/31 have no committed audit trail. Their record is
`2026-08-30_cnv_rebuild_plan.md` (design doc v3) and
`HANDOFF_build_pon_twist.md`; recommend committing both under
`docs/audit/2026-08-30/` to close that gap.

---

## 1. Finding of record: capture batch effect, attributed to plex

The handoff asserted all 48 normals were protocol-matched (16 hr overnight
hybridisation). Measurement falsified this for half the cohort:

- Per-exon depth survey (24M + 24F, `targets.exonwise.bed`, mosdepth
  `--flag 772`) showed a sex-boundary depth collapse confined to kinetically
  sensitive (AT-rich internal/terminal) exons: 94 exons with female median
  under 25% of male; sentinel NPM1_exon_11 at F median ~47x vs M ~400x.
  Autosomal loci, so not donor biology; 1,525/1,795 exons within 25% of male
  depth, so not throughput.
- Wet-lab records (Swapnali Joshi, 2026-09-01): males captured 8-plex (the
  validated condition), females 12-plex. Single-variable attribution.
  Mechanism: fixed probe mass per reaction; at higher plex, fast-hybridising
  targets saturate probes early and slow AT-rich duplexes are starved.
- Insert-size check across all 48 BAMs excluded fragmentation as the driver
  (F mean 164.4 bp vs M 172.6 bp, fully overlapping ranges).
- Within-male tiering (Male1-8 ~790x, Male9-16 ~300x, Male17-24 mixed at the
  sentinel) is within-8-plex batch variation; pool-mean insert length is
  rank-concordant and a plausible secondary contributor. Not actionable;
  absorbed by the spread criterion and per-stratum LOO blacklist.
- The pooled-reference LOO's 93 truly-absent exonic labels are explained:
  CNVkit's reference filter discarded bins whose female-vs-male bimodality
  exceeded its spread ceiling. Only 2 bins in the LOO table are compound
  merges (the book-ended chrY backbone pair; HNRNPK_exon_14/15).

Consequences adopted:
- Female captures are unusable for any reference purpose. Female arm of
  BUILD_PON_TWIST is gated on conforming female normals. Cheapest repair is
  re-hybridising existing female libraries at 8-plex if pre-capture material
  exists — inventory question open with wet lab.
- SOP: capture plex pinned at 8 until a deliberate titration says otherwise.
- Proposed per-batch conformity gate (normals and clinical): NPM1_exon_11
  depth, JAK2_exon_15 depth, mean insert size — three numbers per library.
- Open provenance question: whether Male1-8 are the clinical-23 validation-
  arm libraries (naming and ~790x tier suggest yes).

## 2. `qc/twist_early` voided

The early backbone QC (source of the recorded GC<0.35 / 830-tile rule) is
void three times over: cohort was all-female (nonconforming 12-plex);
BAM discovery in `backbone_depth_qc.py` counted Nextflow staging symlinks,
inflating 6 unique samples to 14 processed paths (4 samples triple-weighted);
run fired mid-pipeline (2026-08-31 13:51) so only early-finishing females
were present. The GC column is sequence-derived and remains valid as
annotation. `backbone_depth_qc.py` needs the real-file+dedup discovery from
`exon_depth_survey.py` before any rerun (queued, not done).

## 3. Replaced decisions (both formally supersede recorded ones)

### 3a. Exon exclusion — two-axis criterion replaces the 8-exon flag list

The recorded list (CCNC x2, ANKRD26 x2, HRAS, AKT1, JAK2_exon_15,
PTEN_exon_3) had no surviving on-disk provenance and was an undercount
assembled from partial views. Replacement, derived on the 24 conforming
males:

    EXCLUDE if ratio < 0.075
          OR (ratio < 0.50 AND max_spread > 0.75)
    ratio  = male exon median depth / male gene median depth
    spread = per-label max from cnvkit_pon_male.cnn (male-only reference)

Thresholds sit in empty intervals of the measured distributions (ratio gap
0.042-0.117; spread gap 0.61-0.76). Two failure modes excluded: dead
(capture ~zero; log2 is Poisson noise) and irreproducible (adequate mean,
per-library wobble exceeding the signal sought — a het deletion at 30-50%
blasts is only -0.2 to -0.4 log2). Consistently-suppressed CpG first exons
(low ratio, low spread) are RETAINED: suppression is thermodynamic and
uniform; CNVkit down-weights by depth; per-stratum LOO blacklist adjudicates
residuals.

Derived set (8): ANKRD26_exon_5/19/28/29, CCNC_exon_6/7, AKT1_exon_1,
PTEN_exon_3. Membership deltas vs the recorded list: JAK2_exon_15 RETAINED
(256x, spread 0.23 — consistent suppression), HRAS_exon_1 RETAINED (69x,
spread 0.45); ANKRD26 contributes four exons, not two; CCNC's dead pair is
exons 6/7 (exons 9/12 are noisy-but-alive, correctly blacklist-held).
Retentions are encoded as DOCUMENTED_RETENTIONS in the derive script; a
criterion or data change that would catch them aborts derivation.
Weakest exclusion: ANKRD26_exon_28 (spread 0.756, clears by 0.006).
Closest retention: BIRC3_exon_8 (0.209 / 0.613).

### 3b. Backbone exclusion — measured 30x male floor replaces GC<0.35

Male-only backbone depth (24 BAMs over `backbone.hg38.bed`): 71 of 3,047
tiles below 30x median (101 below 50x, 147 below 100x). Of the 830
GC-flagged tiles, 760 are alive under conforming capture — the "GC cliff"
was the 12-plex batch's AT-dropout, and GC was a correlate, never the
criterion (exactly 1 dead tile sits outside the GC<0.35 set). Backbone
usability on conforming data: 2,976/3,047 = 97.7%; effective mean spacing
~856 kb vs designed 836 kb — essentially design spec, superseding the
~1.15 Mb planning figure.

Notable excluded tiles: dead-median-with-extreme-max signatures
(bb.chr9.64881493 med 4.1x/max 478x, gc 0.375; bb.chr10.209693;
bb.chrX.117473417; bb.chrX.90982562) — multi-mapping pileup, sequence-
context failures, the correct examples for Twist correspondence.

Logged caveat: 12 of 71 excluded tiles are chrX, where male hemizygosity
makes the 30x floor ~60x diploid-equivalent — correct for the male stratum,
likely over-exclusive for a future conforming female stratum. Whether the
filtered BED stays single or goes per-stratum is deferred to the female
re-derivation session.

## 4. Tooling delivered (all verified in sandbox before handover)

- `tools/exon_depth_survey.py` — per-exon depth across normals; real-file +
  dedup BAM discovery (48/48 asserted); LOO-status decomposition; anchors.
- `tools/derive_exclusion_list.py` — applies both criteria; prints excluded
  tables, near-threshold band, retention checks; --expect-exons/--expect-
  tiles guards; provenance headers with input md5s; dry-run default.
- `tools/patches/2026-09-01/patch_builder_filtered_bed.py` — anchor-based,
  idempotent, compile-checked patch to `bin/build_panel_assets.py`: adds
  --exclude-exons/--exclude-backbone, drift-fatal validation, filtered-BED
  emission, manifest `exclusions` section. Backup:
  `bin/build_panel_assets.py.bak_filtered_bed_20260901_095030`.

## 5. Asset state after rebuild (2026-09-01 09:53 apply)

- `assets/twist_myeloid/exclusions.exons.tsv` (8 rows) and
  `exclusions.backbone.tsv` (71 rows) — panel-definition data with
  criterion, cohort, and input-md5 provenance headers.
- `panel.combined.filtered.bed`: 8,821 rows = 8,902 (combined) - 10 probes
  (8 labels; AKT1_exon_1 spans 3 probes) - 71 tiles. Single shared artifact
  for CNVkit targets and GATK interval list.
- `panel_manifest.json` gains `exclusions` (labels, sources, md5s,
  provenance verbatim).
- Determinism verified: rewritten unfiltered assets byte-identical to their
  `.bak_build_panel_assets_20260901_095309` backups (md5 check = 1).
- Prior-session QC artifacts retained: `qc/twist_pon48/exon_depth_survey.tsv`,
  `gene_depth_summary.tsv`, kept mosdepth temp (`exsurvey__jsoadxr/`),
  `backbone_male/`.

## 6. Carried forward

1. BUILD_PON_TWIST workflow scaffold (next major step). Live decision at
   scaffold time: consume the existing 48 final BAMs directly vs re-derive
   from FASTQ (~7 h). Every new process needs an explicit conda `withName`
   block in `conf/modules.config`.
2. Mirror to clinical-23: patch script + both exclusion TSVs there, rerun
   builder, verify manifest md5 parity.
3. Female arm: pre-capture library inventory (wet lab) decides
   re-hybridise vs male-only-now.
4. Twist correspondence: claims from male 8-plex data only; ~70 backbone
   tiles, not 830; exon list per 3a; multi-mapping tiles cited separately.
5. `backbone_depth_qc.py` BAM-discovery fix before any rerun.
6. Watch item: Male12 (shortest insert, 131.8 bp) in the per-stratum LOO.
7. Pool-membership confirmation for the male tiers; Male1-8 validation-arm
   identity.

Addendum 2026-09-01: clinical-23 mirror closed by independent rebuild; cross-machine manifest digest 7b3d3a537f37d95364d3f6157a746192 (11/11 outputs identical). Builder now committed in-tree on clinical-23 for the first time.

Addendum 2026-09-01 (batch records, Twist_Normals.xlsx): capture batches B1=M1-8 (seq 19.08), B2=M9-16, B3=M17-24, B4=F1-12, B5=F13-24 (seq 26.08); plex 8/8/8/12/12 confirmed. Male sentinel tiers map to batches exactly (796/304/452x NPM1_e11 medians) -- within-8-plex batch variation 2.6x. Female sentinel depth vs post-library concentration Spearman -0.75 (males -0.06): signature of mass-normalised pooling with quantification under-read over-representing F10/11/12/18. Pool-membership question CLOSED. Remaining asks: female library residual volumes; whether B1 males are the validation-arm libraries.
