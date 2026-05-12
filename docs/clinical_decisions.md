# Clinical decisions encoded in this pipeline

This document records intentional differences from the production
`targeted-seq-pipeline` (Python orchestrator) that are clinically motivated.
Reviewers comparing pipeline outputs should consult this list to understand
expected differences.

## Masked hg38 reference (used for ALL steps)

**Production behaviour**: aligned to masked hg38, but ran Mutect2 (and possibly
other callers) against UNMASKED hg38 (`resources_broad_hg38_v0_Homo_sapiens_assembly38.fasta`).

**This pipeline**: uses masked hg38 for everything, including variant calling.

**Why**: in unmasked hg38, U2AF1 shares >99% identity with its paralog U2AF1L5
on chr21. Reads from the canonical U2AF1 locus distribute evenly between the
two copies during alignment, MAPQ drops to 0, and variant callers discard the
reads. This causes silent loss of clinically important U2AF1 variants in MDS
and AML. Masking the paralog forces reads onto the canonical locus and
restores variant-calling sensitivity at U2AF1.

**Expected impact on parity testing**: Mutect2 (and other reference-sensitive
callers) will produce SLIGHTLY different output than production. Specifically:

  - U2AF1 variants: new pipeline calls them, production may not
  - Paralog-collapsed regions outside the panel: not relevant
  - Bulk of panel: identical or near-identical calls

**Validation criterion**: production-positive clinically-significant variants
must be called by new pipeline. Novel calls at U2AF1 are expected gains.

## Read-group format

**Production**: ID=AML (literal), LB=LIB-MIPS (legacy MIPS protocol name)

**This pipeline**: ID=${meta.id} (per-sample), LB=HC (hybrid capture)

**Why**: ID=AML literal violates SAM spec (RG IDs should be unique per
sequencing unit). LB=LIB-MIPS is a historical artifact from when the lab used
Molecular Inversion Probes; current protocol is hybrid capture.


## VarScan VAF threshold (3% instead of 0.3%)

**Production behaviour**: `varscan mpileup2snp/mpileup2indel --min-var-freq 0.003` (0.3%).

**This pipeline**: 3% VAF threshold via `conf/gandalf.config` ext.min_var_freq = '0.03'.

**Why**: clinical interest below 3% VAF is rare on the myeloid panel.
Production's 0.3% threshold generated significant noise that the SomaticSeq
ensemble had to filter out. Raising the threshold at the caller stage produces
cleaner intermediate VCFs without measurable loss of clinically reviewed
calls.

**Expected impact**: VarScan will report fewer low-VAF variants. Variants at
1-3% VAF that were called by VarScan alone in production may not appear in
new pipeline. Variants supported by 2+ callers above their respective
thresholds are unaffected.

**Override**: set `ext.min_var_freq = '0.003'` in the gandalf.config VARSCAN
block to restore production behaviour. Default module behaviour is 0.003 so
fresh servers without site config get production's setting.


## FreeBayes conservative tuning

**Production behaviour**: `freebayes -f ref -b bam -t bed` (bare defaults: MQ>=1,
BQ>=0, no multi-allele cap, no complex-gap limit).

**This pipeline (gandalf)**: adds `--min-mapping-quality 20 --min-base-quality 20
--use-best-n-alleles 4 --max-complex-gap 3` via `conf/gandalf.config` ext.args.

**Why**: production's bare-default FreeBayes emits ~1800 raw variants per
panel sample, the vast majority of which are noise that SomaticSeq filters
out. The conservative flags match the MQ/BQ filtering applied by Mutect2
(--minimum-mapping-quality 20, --min-base-quality-score 25) and produce
typically 600-800 calls per panel sample - same real variants, much less noise
for the ensemble to wade through. The --use-best-n-alleles 4 cap prevents
multi-allelic blow-up at hypermutated/repetitive sites.

**Expected impact**:
  - Total FreeBayes variant count drops ~50-60%
  - Real variants supported by 2+ callers: unchanged
  - Low-VAF noise-only-in-FreeBayes calls: dropped
  - Downstream SomaticSeq runtime: faster

**Override**: leave `ext.args` unset (or empty string) in site config to
restore production defaults. Module default is production behaviour.


### FreeBayes tuning - REVERTED 2026-05-12

The conservative tuning above was applied, validated against 25NGS1307,
and **reverted** the same day. Cross-caller analysis revealed that the
BQ20/MQ20 cutoffs dropped 15 real subclonal mutations in known AML/MDS
driver genes:

  - KMT2A (28.2% VAF)
  - DNMT3A (20.3%)
  - SETD2 x2 (25.5%, 21.2%)
  - CTCF (24.6%)
  - EED (21.6%)
  - GATA1 (16.6%)
  - CSF1R (14.0%)
  - KIT (13.7%)
  - NF1 (12.7%)
  - BRAF (12.0%)
  - TET2 (9.3%)
  - chr1, chr16, chr3, chrX positions in driver-panel regions

All 15 were supported by another somatic caller (Mutect2/VarDict/VarScan),
confirming they were real biology, not 8-oxoguanine artifacts.

The 909 FreeBayes-only G>T/C>A calls (1.6% of the total being 80% of dropped
variants) appear to be 8-oxoG artifacts that the SomaticSeq ensemble vote
would have filtered anyway. Pre-filtering them at the caller stage was
not worth the cost in driver-gene sensitivity.

**Current behaviour**: FreeBayes runs with production's bare defaults. Trust
the ensemble to filter downstream.
