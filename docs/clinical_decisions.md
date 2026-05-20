# Clinical decisions encoded in this pipeline

This document records intentional differences from the production
`targeted-seq-pipeline` (Python orchestrator) that are clinically
motivated. Reviewers comparing pipeline outputs should consult this list
to understand expected differences and which differences are gains
versus operational changes.

Cross-references:

- [`docs/usage.md`](usage.md) — CLI flag reference (every override mentioned below is wired through `ext.*` config or a `--flag`)
- [`docs/output.md`](output.md) — output layout for cross-checking which caller produced which file
- [`docs/usage_pon.md`](usage_pon.md) — sex-stratified PoN construction (relevant to the sex-from-samplesheet decision)
- [`docs/INSTALL.md`](INSTALL.md) — install context and container catalogue

Decisions covered below:

| Decision | Driver | Net effect vs production |
|---|---|---|
| Masked hg38 used for all steps | U2AF1 paralog collapse | Restores U2AF1 sensitivity; otherwise near-identical |
| Sex declared per-sample, not inferred | CNV background confounding | Cleaner sex-chromosome CNV calls; fewer false chrX/chrY events |
| Read-group format | SAM-spec compliance + protocol accuracy | Cosmetic in downstream files; no variant-level impact |
| VarScan VAF threshold at 3% | Caller-stage noise reduction | Fewer VarScan-only sub-3% calls; ensemble-supported calls unaffected |
| FreeBayes runs with bare defaults | Subclonal driver-gene sensitivity | More raw FreeBayes calls; ensemble filters noise downstream |
| DeepSomatic GERMLINE flag is informational | Built-in PoN flags hotspots | GERMLINE-flagged variants remain in the VCF for ensemble voting |
| FLT3-ITD 4-caller ensemble | Consensus confidence on real ITDs | Higher PPV on positive calls; one more independent witness |

## Masked hg38 reference (used for ALL steps)

**Production behaviour**: aligned to masked hg38, but ran Mutect2 (and
possibly other callers) against unmasked hg38
(`resources_broad_hg38_v0_Homo_sapiens_assembly38.fasta`).

**This pipeline**: uses masked hg38 for everything, including variant
calling.

**Why**: in unmasked hg38, U2AF1 shares >99% identity with its paralog
U2AF1L5 on chr21. Reads from the canonical U2AF1 locus distribute evenly
between the two copies during alignment, MAPQ drops to 0, and variant
callers discard the reads. This causes silent loss of clinically
important U2AF1 variants in MDS and AML. Masking the paralog forces
reads onto the canonical locus and restores variant-calling sensitivity
at U2AF1.

**Expected impact on parity testing**:

- U2AF1 variants: new pipeline calls them, production may not
- Paralog-collapsed regions outside the panel: not relevant
- Bulk of panel: identical or near-identical calls

**Validation criterion**: production-positive clinically significant
variants must be called by the new pipeline. Novel calls at U2AF1 are
expected gains.

> **[verify against `modules/local/u2af1_rescue.nf`]** A `U2AF1_RESCUE`
> step is visible in the per-sample workflow. Confirm whether this is a
> separate paralog-rescue mechanism (in addition to the masked
> reference) or a defence-in-depth safety net, and document the actual
> behaviour here.

## Sex declared per-sample, not inferred from coverage

**Production behaviour**: sex was inferred at the CNV stage from chrX
coverage log2. A sex-stratified PoN was then selected based on the
inferred sex.

**This pipeline**: sex is declared in the samplesheet (`sex` column,
values `male`, `female`, or `unknown`) and propagates as `meta.sex`
through the workflow. The CNVKit module selects the matching
sex-stratified PoN before invoking the script. Samples with
`sex=unknown` fall back to the female PoN with a warning logged.

**Why**: sex is a critical confounder for CNV background. Misclassifying
a female as male (or vice versa) flips the expected chrX/chrY copy
state, generating false copy-number events on the sex chromosomes that
clinicians must then visually exclude. Declaring sex upstream removes
the inference uncertainty and lets the PoN selection happen
deterministically.

**Operational consequence**: the samplesheet now requires a `sex` column.
Sites coming from the production pipeline will need to extend their
samplesheet generation to populate it. See
[`docs/usage.md`](usage.md#samplesheet-format) for the column reference.

**Expected impact on parity testing**: for samples where production
inferred sex correctly, calls are unchanged. For samples where
production inferred wrong (rare but documented), the new pipeline
produces cleaner sex-chromosome calls.

## Read-group format

**Production**: `ID=AML` (literal), `LB=LIB-MIPS` (legacy MIPS protocol
name).

**This pipeline**: `ID=${meta.id}` (per-sample), `LB=HC` (hybrid
capture).

**Why**: `ID=AML` literal violates the SAM specification (RG IDs should
be unique per sequencing unit). `LB=LIB-MIPS` is a historical artefact
from when the lab used Molecular Inversion Probes; the current protocol
is hybrid capture.

**Clinical impact**: none on variant calling. Downstream tools that key
on RG ID (for example, MultiQC sample-level grouping) will see per-sample
identities in the new pipeline where they saw `AML` in the old.

## VarScan VAF threshold at 3%

**Production behaviour**: `varscan mpileup2snp / mpileup2indel
--min-var-freq 0.003` (0.3%).

**This pipeline**: 3% VAF threshold via
`conf/<yoursite>.config` → `ext.min_var_freq = '0.03'`.

**Why**: clinical interest below 3% VAF is rare on the myeloid panel.
Production's 0.3% threshold generated significant noise that the
SomaticSeq ensemble had to filter out. Raising the threshold at the
caller stage produces cleaner intermediate VCFs without measurable loss
of clinically reviewed calls.

**Expected impact**: VarScan reports fewer low-VAF variants. Variants at
1–3% VAF that were called by VarScan alone in production may not appear
in the new pipeline. Variants supported by 2+ callers above their
respective thresholds are unaffected.

**Override**: set `ext.min_var_freq = '0.003'` in your site config's
VARSCAN block to restore production behaviour. The module default is
`0.003` so fresh servers without a site override get production's
setting.

## FreeBayes runs with bare defaults

**Current behaviour**: FreeBayes runs with `freebayes -f ref -b bam -t
bed` (bare defaults: MQ ≥ 1, BQ ≥ 0, no multi-allele cap, no
complex-gap limit), matching production.

**Why bare defaults**: in May 2026, conservative tuning (`--min-mapping-quality 20 --min-base-quality 20 --use-best-n-alleles 4 --max-complex-gap 3`) was applied and validated. The aim was to reduce the
~1800 raw variants per sample to the ~600–800 that SomaticSeq would
have kept anyway. Cross-caller analysis on the validation sample
revealed that the BQ20 / MQ20 cutoffs dropped **15 real subclonal
mutations in known AML/MDS driver genes** (KMT2A 28.2% VAF, DNMT3A
20.3%, SETD2 ×2, CTCF 24.6%, EED, GATA1, CSF1R, KIT, NF1, BRAF, TET2,
and several driver-panel chr1/chr3/chr16/chrX positions). All 15 were
independently supported by Mutect2/VarDict/VarScan, confirming they
were real biology rather than 8-oxoguanine artefacts. The conservative
tuning was reverted the same day.

The ~909 FreeBayes-only G>T/C>A calls (the 1.6% that would otherwise
have made up ~80% of the dropped variants) appear to be 8-oxoG artefacts
that the SomaticSeq ensemble vote filters anyway. Pre-filtering at the
caller stage was not worth the cost in driver-gene sensitivity.

**Decision**: trust the ensemble. FreeBayes runs with bare defaults; let
SomaticSeq filter downstream.

**Override**: set `ext.args` in your site config's FREEBAYES block to
re-apply conservative tuning. Not recommended without re-validating
driver-gene retention on your panel and cohort.

## DeepSomatic v1.10 WES_TUMOR_ONLY: GERMLINE-flag interpretation

DeepSomatic is the 8th somatic caller. Two quirks worth knowing:

**1. GERMLINE-flagged calls are kept, not dropped.** The FILTER column
flag is informational, not a drop. DeepSomatic's built-in PoN
(`PON_dbsnp138_gnomad_ILMN1000g_pon.vcf.gz`) labels positions where the
variant appears in dbSNP / gnomAD / 1000G as `GERMLINE`. This includes
recurrent somatic hotspots like U2AF1 p.S34F (rs371769427, also
COSV52341059) and the FLT3-ITD region. On the validation sample
(25NGS1307):

- U2AF1 chr21:43104346 G>A → `GERMLINE` (in dbSNP as rs371769427)
- FLT3-ITD chr13:28034132 → `GERMLINE` (region noise in 1000G)

These appear in the DeepSomatic VCF with `FILTER=GERMLINE`. SomaticSeq
ingests them as evidence and votes alongside the other callers'
PASS/FAIL.

**2. WES_TUMOR_ONLY model has limited PASS sensitivity on panel data.**
On 25NGS1307, the model returned 5 PASS variants out of 532 candidates
— all in C>A / G>T pattern (8-oxoguanine signature), all unsupported by
the other 6 callers, all called as `1/1` homozygous-alt despite VAF
6–16%. These are DeepSomatic artefacts that the SomaticSeq ensemble
vote discounts.

**Net contribution to the ensemble**: positive. The 191 GERMLINE calls
+ 70 NoCall + 265 RefCall on 25NGS1307 provide independent neural-net
evidence at every panel position. SomaticSeq's ML model handles the
cross-caller disagreements.

**Future improvements to consider**:

- Custom PoN that excludes oncogenic hotspots (U2AF1, IDH1, IDH2, NPM1,
  FLT3, KRAS, NRAS, etc.) so DeepSomatic does not flag them as
  `GERMLINE`
- WGS_TUMOR_ONLY vs WES_TUMOR_ONLY performance comparison on the
  myeloid panel
- `--use_default_pon_filtering=false` and see whether SomaticSeq
  downstream filtering is sufficient on its own

## FLT3-ITD 4-caller ensemble

**Production behaviour**: 3-caller ensemble — FLT3_ITD_EXT, getITD,
filt3r.

**This pipeline**: 4-caller ensemble — FLT3_ITD_EXT, getITD, filt3r, and
**Pindel-region** (added 2026-05-19).

**Why**: each FLT3-ITD caller has known systematic blind spots
(length-range bias, region-edge effects, repeat-context failures).
Adding Pindel in ITD-detection mode provides a fourth independent
witness, raising the precision of consensus calls without changing
recall on the high-confidence positives.

**Expected impact**:

- Samples with a real ITD: the consensus row will now have 3 or 4
  supporting callers (vs 2 or 3 in production); higher confidence.
- Samples without an ITD: unchanged. (Note the documented FLT3_ITD_EXT
  failure mode on ITD-negative specimens; see the *Status and known
  limitations* section of the README.)

## CDKN2A/B clinical-rescue whitelist

> **[verify against current `bin/` CNV-annotation scripts]** Production's
> `18_cnv_annotate.py` carries a CDKN2A/B whitelist that rescues
> clinically essential homozygous deletion calls even when they fall in
> noisy bins. As of the 2026-05-15 session notes, this had not yet been
> ported into the nf-core CNV subworkflow. Before publishing this doc,
> confirm whether the whitelist is now wired into the nf-core port and
> document the current behaviour; if it is still pending, list it under
> *Known gaps* in the README rather than here.
