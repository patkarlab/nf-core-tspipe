# 2026-09-02 afternoon: alt-contig blind spot, KRAS germline CNV, DECoN

## 1. Six panel genes invisible to MAPQ-filtered callers
- hg38_broad reference carries 261 alt contigs; bwa-mem2 index used
  without an .alt file -> reads at alt-duplicated loci: half assigned to
  the alt contig, half to the chromosome at MAPQ 0.
- Affected (mosdepth MAPQ0 vs MAPQ20, Male3): PRPF8 43 exons, PARN 24,
  HRAS 6, ELANE 5, STAT5B 2, SUZ12 1 = 81 exons (evidence/mapq_loss_exons.tsv).
- Mutect2 all-variant VCF, Female16: 0 records in PRPF8 and HRAS (TP53 2).
- Coverage QC (mosdepth --flag 772, no MAPQ filter) reported them covered.
- The Broad .alt exists in the reference dir under its download name;
  the aligner needs Homo_sapiens_assembly38.masked.fasta.alt.
- Test (twist_pilot/altfix, renamed .alt beside a symlinked index,
  Female16 re-aligned with the pipeline command): HRAS 3,634 reads/0 at
  MAPQ20 -> 7,414/7,398; PRPF8 0 -> 7,946/7,942; ELANE -> 3,577/3,573;
  TP53 unchanged 5,205.
Decisions
- D1 Install Homo_sapiens_assembly38.masked.fasta.alt in the production
  reference dir (both pipelines, prospective). Gated on D3.
- D2 Coverage QC at MAPQ 20 (mosdepth --mapq 20), both pipelines.
- D3 Re-align the 48 normals alt-aware; rebuild every twist reference
  asset (CNVkit PoN, GATK PoN, PureCN normalDB, BAF background) before
  D1 goes live for CNV. Same dependency for the production myeloid_cnv PoN.
- D4 Retrospective review of archived cases for the six genes: Nikhil.

## 2. Male11: constitutional KRAS duplication
- DECoN: 5-exon duplication, ratio 1.45, BF 85 (evidence/*_KRAS.pdf);
  CNVkit LOO: 1/24 gain at KRAS; het AF chr12:25,264,214-484:
  0.33/0.33/0.66/0.68, diploid flanks 0.46 (23.7 Mb) and 0.42 (26.4 Mb).
Decisions
- D5 Exclude Male11 from exon-level reference pools on chr12; rebuild the
  LOO noisy-bin blacklist with Male11 masked at KRAS (it currently tags a
  KRAS bin as noise because of this CNV).
- D6 Incidental germline finding in a donor: handled under consent by Nikhil.

## 3. DECoN evaluation (24 males + Female16; 1,778 targets, 126 genes)
- QC gate: Female16 fails (max correlation 0.9727 < 0.98); males pass.
- Male leave-one-out: 36 calls / 24 = 1.5 per sample, BF 2.9-11.5, plus
  Male11 KRAS BF 85 (real). Recurrent: ELANE (MAPQ-dead), SUZ12,
  ANKRD26, ATM, SMC3, STAG2, BIRC3, CSMD1.
- Female16: chrX duplications BF 21-29 (ratio 1.54-1.62); 24 autosomal
  artefact deletions BF 2.5-11 at 12-16% expected reads (NPM1 3 exons 0.55).
- MAPQ-dead exons excluded by DECoN as failed (correct).
- First run mislabelled by one column (GC insertion); fixed, see tools/decon/README.md.
Decisions
- D7 Adopt DECoN as exon-level arm E, gated by its QC (0.98 / 100x);
  provisional reporting threshold BF >= 12; recurrence blacklist from the
  pool. Sensitivity for small/subclonal events pending positive controls.
- D8 reconCNV locked as CNV page one of the dashboard; styled CNVkit
  scatter with BAF panel replaces cnv_plots.py. Adapter, config and
  patches are in Claude outputs, not yet in the repo; wiring next session.
