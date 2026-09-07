# 2026-09-07 evening -- memo 8 (7b: legacy CNV chain retired, CNV_RETIRE_7B)

Start HEAD a2bc0b1. Patcher tools/patches/2026-09-07/patch_cnv_retire_7b.py;
SOP docs/sops/cnv_calling.md. Resume target tspipe_run8, session abea2914.

## 1. Decision

Retire ZSCORE_CNV, CNV_PLOTS, CNV_CONCORDANCE, CNV_CLINICAL_REPORT and
CNV_ANNOTATE (handoff item 7b). CNV_ANNOTATE included because nothing in the
dashboard rendered the annotated table any more (only parsers/cnv.py produced
it; build.py kept a fallback key) and cnv_annotate.py was written against the
old four-caller schema (consensus_type, zscore_call, cnmops_call, ifcnv_call).
Follow-up: add cytoband, ClinGen HI/TS and gene role as columns of the
consensus genes.tsv inside cnv_consensus_multi.py, where they are seen.

ClassifyCNV (Gurbich and Ilinsky, Sci Rep 2020) was looked at and set aside:
it scores constitutional CNVs under the 2019 ACMG/ClinGen rubric (dosage
sensitivity, DGV/gnomAD frequency); somatic panel events in myeloid disease
are tiered by disease context, not population frequency. Its packaged ClinGen
dosage BEDs are reusable for the follow-up annotation.

## 2. What changed

- CNV_CALLING is CNVKIT alone; emits call_cns, cnr, cns, genemetrics.
- tspipe.nf: ch_cnv_noise_profile, ch_cytoband, ch_clingen, ch_scatter_regions
  removed; CNV_CALLING call reduced to nine inputs; consensus join starts from
  cnvkit_cnr; ORGANIZE assembly loses five joins.
- CNV_CONSENSUS_MULTI: concordance input and --concordance argument removed;
  cnv_consensus_multi.py accepts --concordance and ignores it; the legacy
  passthrough block is gone (legacy = {}).
- ORGANIZE_OUTPUT / organize_output.py: five inputs and arguments removed;
  clinical/cnv_consensus/ and clinical/cnvkit_plots/ no longer produced.
- conf/modules.config: five publishDir blocks removed.
- build.py: parsers/cnv.py import and parse removed; ctx.cnv from cnv_v2 only.
- Deleted: modules/local/{zscore_cnv,cnv_plots,cnv_concordance,
  cnv_clinical_report,cnv_annotate}.nf, bin/{zscore_cnv,cnv_plots,
  cnv_concordance,cnv_clinical_report,cnv_annotate}.py,
  bin/dashboard_builder/parsers/cnv.py.
- Left in place: assets loo_bin_noise_profile.tsv, cnv_scatter_regions.txt,
  cytoBand_hg38.txt, ClinGen list; params cnv_noise_profile/cytoband/clingen
  (accepted, unused); bin/README.md rows; tools/build_artefacts and
  cnvkit_scatter_styled.py references to the cnv_plots layout (tools, not DAG).

## 3. Result

Commits 6b7778c (retirement, 21 files, -4,370/+703 lines) and 272a4b9
(bundler fix). Stub retire7b_stub green end to end without the five
processes.

First resume of abea2914 after 6b7778c: CNV_CONSENSUS_MULTI, EXON_PLOTS,
CHROM_PAGES and ORGANIZE_OUTPUT re-executed for all eight inside two
minutes; DASHBOARD passed; REPORT_BUNDLE failed x3 because
tools/make_report_bundle.py still required and copied clinical/cnvkit_plots/.
Fix: the required tree is clinical/cnv/ (always produced), cnvkit_plots/
dropped, bundler version 0.3 in report_bundle.nf (the script lives under
tools/ and is referenced by absolute path, so only the version string busts
its cache). Second resume: 2 succeeded (DASHBOARD rebuilt because the
previous run had it at cache=false, REPORT_BUNDLE), 416 cached, no errors.

Per-sample check on 26CGH1250: clinical/ carries cnv/{chrom_pages,consensus,
decon,exon_plots,purple,reconcnv,sex_check}; cnv_consensus/, cnvkit_plots/,
cnv/zscore, cnv/annotated absent; report has 48 chrom-page ids, the
consensus table, PURPLE PASS 0.65, 13 chrX GAIN rows; bundle lists 60 cnv/
entries and none of the retired paths, 17 MB. One dead DataTable init for
#cnv-clinical-table in sample_report.html.j2 removed with this memo.

## 4. Follow-ups opened by 7b

- Consensus genes.tsv annotation columns: cytoband, ClinGen HI/TS, gene role
  (from the assets that CNV_ANNOTATE used), inside cnv_consensus_multi.py.
- Optional per-gene problematic-region flag (segdup/centromere overlap),
  borrowed from the Jacquemont CNV-Annotation idea; low priority.
- bin/README.md rows for the deleted scripts; tools/build_artefacts and
  cnvkit_scatter_styled.py still describe the cnv_plots layout (tools only).
