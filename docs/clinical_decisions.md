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
