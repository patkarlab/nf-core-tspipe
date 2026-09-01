# CNV application build -- twist_myeloid five-caller architecture

Date: 2026-09-01 (afternoon/evening; follows the PoN execution and chrX
correction memos of the same date)
Repo: patkarlab/nf-core-tspipe, commits 590b009..<commit 8>
Operator: Nikhil (review/execute); code authored by Claude

## Scope

The application layer for the Twist myeloid panel, built additively on
the v2.1 reference set: panel plumbing, four new CNV engines alongside
CNVkit, a five-caller consensus, and the frozen JSON schema for the
Phase-4 report. Every component lives in a gated block keyed on
params.cnv_gatk_pon (defined only in conf/twist_apply.config), so the
legacy myeloid/myeloid_cnv panels never evaluate any of it. Clinical-path
touches across the whole phase: one include + gated block in
workflows/tspipe.nf, two additive emits on CNV_CALLING (cnr,
genemetrics), one ext.args hook on the CNVKIT module, and the
backward-compatible --panel-gene-chroms argument on cnvkit_wrapper.py.

## Commits

- 590b009 plumbing: cnv_scatter_regions.txt (1,795 regions / 23
  chromosomes, generated from targets.exonwise.bed; parser verified
  label-agnostic), cnvkit_pon_female.cnn header-only sentinel,
  panel_gene_chroms.tsv draft curation (11 chromosome pages, REVIEW
  PENDING), PGC_ARG_V1 override, twist_apply.config overlay.
- e144175 TGC_V1: GATK somatic CNV path (CollectReadCounts on the
  PoN-matched intervals, OVERLAPPING_ONLY; DenoiseReadCounts vs
  gatk_rc_pon_male.hdf5; ModelSegments; CallCopyRatioSegments; gene
  projection + matplotlib genome plot -- the GATK R plotters are unused,
  R deps absent on the host).
- bc63e13 BAF_V1: CollectAllelicCounts over snp_sites.baf.bed;
  ModelSegments upgraded to joint copy-ratio + allelic segmentation;
  CNV_BAF_CNLOH 17p detector (bias correction against the 24-male
  background, mirrored-BAF deviation, f_est = 2*median(dev), verdict
  split on 17p CR median). Synthetic validation: neutral / cnLOH(0.40) /
  del all classify correctly, f_est 0.398. Thresholds are params; v1
  heuristics pending known del(17p)/cnLOH material.
- 937ec90 CMX_V1: CNV_CONSENSUS_MULTI -- per-gene support flags,
  consensus_call, LOO fp annotation, allelic_state for 17p genes,
  segment intersection, single JSON payload (schema
  twist_cnv_consensus4).
- commit 8 PCN_V1: PureCN 2.16.0 fifth caller. Dedicated conda env
  (envs/purecn.environment.yml); NormalDB built from the 24 male
  normals via tools/build_purecn_normaldb.sh (IntervalFile 5,782 rows,
  off-target off matching the empty-antitarget doctrine; seeded with
  purecn_normaldb.md5). Raw Mutect2 VCF as the purity-model input;
  --sex from meta. Purity-fit failure writes FAILED sentinels rather
  than killing the DAG (copy-flat held-out normals are the expected
  first consumers). Consensus v2: fifth flag P, p_call/p_C/p_loh,
  purity/ploidy in JSON meta, schema bumped to /v2.

## Validation ladder

Stub-run DAG growth under the twist overlay: 46 (plumbing + TGC) -> 48
(BAF) -> 49 (consensus) -> 51 (PureCN), each green before its commit.
Synthetic functional tests for every parser and detector; the flagship
composition verified end-to-end: EZH2 with triple-caller GKP LOSS
support and PureCN C=1 + LOH agreement; TP53 depth-neutral across all
three coverage engines yet carrying PureCN copy_neutral LOH and Route A
CNLOH_17P concordantly -- two independent methods on the same allelic
event, which is the clinical point of the architecture.

## Learnings recorded

- NF 25.10 -c configs are compiled outside the nextflow.config chain:
  eager params references fail as unknown attributes; lazy closures are
  fine. twist_apply.config therefore uses literals; this also explains
  the 31 Aug noncontainer config's literal path.
- bioconda PureCN lacks the R.utils soft dependency needed by
  data.table::fread for gz coverage files; added to the env and captured
  in the committed environment.yml.
- PureCN's coverage QC independently inferred sex M for all 24 normals
  -- a third orthogonal confirmation of stratum purity after filename
  labels and genotype verification.
- One normal runs at ~790x autosomal vs the cohort's 1,700-2,600x;
  absorbed by NormalDB interval weighting, identity to be checked
  (Male12 watch-list candidate).

## Carried items

1. Phase-4 three-view report against schema twist_cnv_consensus4/v2.
2. MoChA 17p comparator (Route B).
3. Real-data pilot = Phase-5 specificity arm: held-out normals through
   the full five-caller path (FASTQs under s3://hemat/FastqArchival2026/).
4. panel_gene_chroms.tsv clinical review; 18-gene driver-table extension
   + 79-hotspot merge (blocks tier assignment).
5. Twist correspondence (CHEK2 + PHIP + PTEN exon 3 + ANKRD26 spike-in;
   kinetics evidence strengthened by the three sentinel-passing females).
6. PureCN mapping-bias RDS (needs a combined normal VCF); female
  NormalDB via a --sex flag on the build script when re-hyb lands.
7. 17p-block sample identity / contamination tool (pileups now exist).
8. Consensus zscore call-column autodetect: pin exact column names after
   the first real run.
