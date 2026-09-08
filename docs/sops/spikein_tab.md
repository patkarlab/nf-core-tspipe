# SOP — Spike-in tab (SPIKEIN_V1 / V1b, D13)

Written 2026-09-08. Applies to nf-core-tspipe with the twist_apply.config overlay.

## Purpose

The Twist myeloid panel carries non-exonic spike-in targets: regulatory regions
(promoters, 5'UTRs, an intronic enhancer, TERC) and germline B-ALL risk SNPs. Calls
in these regions are removed from the clinical table by the consequence filter, and
the SNPs are germline sites that no somatic caller reports as such. The Spike-in tab
on the sample report makes both visible without changing the clinical table.

## Asset

`assets/<panel>/spikein_regions.tsv`, tab-separated, `#` comments allowed. One row per
target, `class` is `regulatory` or `germline_snp`.

| column | regulatory row | germline_snp row |
|---|---|---|
| name | must equal the `Gene` value in targets.exonwise.bed / exon_coverage.tsv | free, unique |
| chrom, start, end | BED 0-based half-open interval | pos-1, pos |
| pos | `-` | 1-based SNP position (hg38) |
| gene, rsid, rsid_alias | gene; `-`; `-` | gene; primary rsID; merged/legacy rsID or `-` |
| risk_allele | `-` | plus-strand risk allele from the association literature, or `-` |
| description | free text shown in the tab | free text shown in the tab |

Twist myeloid (TE-99430185): 8 regions (MLH1_5UTR, KLHDC8B_5UTR, GATA2_intron4, TERC,
GATA3_intronic, ANKRD26_5UTR, FANCI_intron31, DKC1_5UTR) and 5 SNPs. In the hg38 Main
probe BED every `*_SNP_rs*` probe is centred on its SNP: position = probe start + 61
(1-based). Positions were verified against dbSNP GRCh38 on 2026-09-08:

| site | rsID | hg38 | risk allele | note |
|---|---|---|---|---|
| GATA3_rs3824662 | rs3824662 | chr10:8062245 | A | centre of the GATA3_intronic probe; no probe of its own |
| GATA3_rs3781093 | rs3781093 | chr10:8059964 | not curated | tight LD with rs3824662 |
| ARID5B_rs10994982 | rs10994982 | chr10:61950345 | not curated | |
| ARID5B_rs10821936 | rs10821936 (probe label rs63723577) | chr10:61963818 | C | C is the hg38 reference: hom_ref = 2 risk copies |
| IKZF1_rs11978267 | rs11978267 | chr7:50398606 | G | |

A panel without this asset skips the tab; SPIKEIN_SITES still runs and writes a
header-only table so the ORGANIZE join is unaffected.

## Pipeline

- `SPIKEIN_SITES` (modules/local/spikein_sites.nf, GATK container, in PREPROCESSING next
  to SEX_CHECK): `CollectAllelicCounts` on the ABRA2 final BAM at the SNP positions, then
  `bin/spikein_sites.py` writes `<sample>.spikein_snps.tsv`. Output goes through
  `withResolvedSex` and is emitted as `PREPROCESSING.out.spikein`.
- `ORGANIZE_OUTPUT`: `--spikein-snps` hardlinks the table to `clinical/<sample>.spikein_snps.tsv`.
- `DASHBOARD`: passes `--spikein-regions assets/<panel>/spikein_regions.tsv` when it exists;
  `parsers/spikein.py` builds `ctx["spikein"]`; the tab is rendered only when the asset is set.
- Region coverage is NOT computed here. It comes from targets.exonwise.bed through MOSDEPTH
  and `<sample>_exon_coverage.tsv` (rows with Exon `-`), so a region must be in exonwise
  to show coverage. The SNP sites are not in exonwise (N8).

## Genotype rule (bin/spikein_sites.py)

depth = REF_COUNT + ALT_COUNT from CollectAllelicCounts (MAPQ and base-quality filtered by
GATK defaults; duplicates excluded — this is not the mosdepth --flag 772 convention).

- depth < 20 → status LOW_DEPTH, no genotype
- alt AF < 0.15 → hom_ref; > 0.85 → hom_alt; otherwise het
- alt allele is reported only at ≥ 2% AF (V1b); below that it is `-`
- risk_copies = number of risk-allele copies implied by the genotype (0/1/2), `-` when the
  asset has no risk allele, `?` when the observed alleles do not include it

These are germline calls read from a tumour BAM. A somatic CNV or copy-neutral LOH on the
site's chromosome moves the allele fraction (chr7 and chr10 are both common targets in
myeloid disease); the tab says so, the script does not adjust. Cross-check against the CNV
tab before interpreting an unexpected hom_alt or a het at 0.2/0.8.

## Tab contents

1. Regions — interval, length, mean coverage, % ≥100/250/500x, a PASS/BELOW badge against
   the 200x reportability tier (same tier as the QC verdict), number of calls, note.
2. Calls inside spike-in regions — every `somaticseq.filtered.tsv` row inside a region, with
   its Filter value. Nothing here is reviewed for reporting; PASS rows are still filtered-table
   rows and would need promotion through the normal route.
3. Germline risk SNP genotypes — counts, AF, genotype, risk allele, risk copies, status, and
   the Filter of the filtered-table call at the site if one exists (a COMMON_POLYMORPHISM
   row there is the caller-side confirmation of a het/hom_alt).

The nav badge is the number of calls inside regions (all Filter values).

## Verification (run8, 2026-09-08)

- All 40 sites at 1000–1900x, status OK; no region below 200x in any sample, DKC1_5UTR
  included in males.
- rs3824662 and rs3781093 genotypes track in all eight samples (LD), an internal check on
  both positions.
- Region calls in run8: TERC chr3:169764547 T>C (COMMON_POLYMORPHISM, gnomAD 0.57) and
  two systematic TERC artefacts present in 8/8 tumours at 5–12% (chr3:169765047 A>C,
  chr3:169765728 A>AT/AT>A) that are absent from references/variant_pon_cohort_table.tsv —
  an N13 follow-up, not a spike-in finding.

## Maintenance

- Adding a region: add it to targets.exonwise.bed first (coverage), then to the asset with
  the identical name; costs a full MOSDEPTH → coverage re-run.
- Adding a SNP: asset row with the verified hg38 position; 18-task resume
  (SPIKEIN_SITES 8, ORGANIZE 8, DASHBOARD, BUNDLE).
- Filling a risk allele: edit the asset only; same 18-task resume (the asset is a
  SPIKEIN_SITES input).
- Offline check pattern (no resume): CollectAllelicCounts and spikein_sites.py in the GATK
  image against a cached final BAM — see memo 13 §2 for the exact commands.
