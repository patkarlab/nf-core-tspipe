# Gap register -- nf-core-tspipe / Twist myeloid -- 2026-09-06

Source: every project chat from 2026-02-15 to 2026-09-06, read against
HANDOFF_twist_cnv_2026-09-06.md open items 1-18. Section A lists what the
handoff does not carry. Section B re-orders the handoff items with the
dependencies that section A exposes. "Verify" marks claims that need a
grep on gandalf before they are treated as fact.

## A. Not in the handoff

A1. Sex inference. TSPIPE has no SEX_CHECK; meta.sex comes only from the
    samplesheet. Everything downstream keys on it: CNVkit PoN selection,
    GATK PoN and LOO files (item 4), PureCN --sex (item 5), DECoN pool
    (item 6), chrX/chrY interpretation in every arm. The validation cases
    arrive without sex; clinical samples will too. Build: chrY and chrX
    depth relative to autosomes from the existing mosdepth output ->
    inferred sex, plus a MISMATCH flag against the samplesheet value.
    Half a day. Prerequisite for item 4, not a follow-on.

A2. Dashboard CNV parser is bound to cnv_plots.py output. parsers/cnv.py
    reads overview/ combined/ per_chromosome/ per_gene/ PNGs and the
    primary_genome_scatter slot. Item 12 retires cnv_plots.py; without a
    parser and template change the CNV tab renders blank. Item 12 must
    include: reconCNV HTML as page one (iframe), styled-scatter galleries,
    and the consensus table (see A3).

A3. CNV_CONSENSUS_MULTI schema v3 not implemented (verify). Agreed 09-02/03:
    per-bin weight, depth and noisy-bin flag; tracks.het_sites genome-wide;
    segments.purecn from _loh.csv. Prototyped in Claude's sandbox only
    (Female16.cnv_consensus4.v3.json). The D3 report built on it was
    shelved for reconCNV, but the schema is what BAF_V2 (item 9) and the
    dashboard consensus table consume. grep bin/cnv_consensus_multi.py (or
    equivalent) for "weight" and "het_sites" before planning item 9.

A4. Visualization decisions that exist only in the shelved D3 report:
    bin area 46w^2+2; opacity by depth vs class median; hollow blacklisted
    bins; guides at +/-0.5 and +/-1.0 with clamp at +/-1.25; caller floors
    as hairlines; transcript-axis gene view (exons proportional, introns
    collapsed, weighted mean per exon); BAF panel with depth alpha and 2D
    binning; state track only from a QC-passing model (PureCN flagged fits
    drawn as advisory outlines). reconCNV config covers point size and
    colour only. Decision needed: accept reconCNV as-is for page one, or
    port the gene view and bin encoding into the styled scatter.

A5. DECoN has no Nextflow module. tools/decon/ is run by hand. The TIER_1
    rule in item 7 counts arm E, but E is not produced in a TSPIPE run.
    DECON module (R container, per-sex pool file, filter_decon_calls.py)
    is a prerequisite for items 6 and 7.

A6. Verify that arms E (DECoN) and P (PureCN) actually reach the consensus
    TSV and the clinical CNV table in a pipeline run, not only in the
    manual evaluations.

A7. Identity and contamination checker from the 17p het block (v3 plan,
    decision 3). Pileups for all normals exist; a sample-swap /
    contamination estimator is a small tool. Not queued anywhere.

A8. Gene-count reconciliation (v3 plan, decision 5): manifest vs BED vs
    driver table. Chore, unowned.

A9. Twist redesign/spike-in letter: CHEK2 + PHIP + PTEN exon 3 + ANKRD26
    as one order. Pending since 08-21.

A10. Cell-line positive control on the Twist panel (OCI-AML3 or other):
    "controls being sequenced on new panel" on 09-02; no status since.
    The eight archived cases are patient positives; a cell line with a
    published karyotype is the CNV sensitivity control the arms lack.

A11. oncoanalyser comparison arm (SAGE/PAVE vs SomaticSeq; ESVEE on
    FLT3-ITD and KMT2A-PTD; panel_resource_creation with --umi_type twist):
    discussed 09-03, queued nowhere. Open question underneath it: do the
    Twist libraries carry UMIs, and does anything in TSPIPE use them? If
    yes, MarkDuplicates without UMI grouping is discarding signal for
    low-VAF calling. Needs one answer from the wet lab.

A12. Older nf-core items never closed: ch_bed queue-channel safety in
    multi-sample runs; CNV_LOO_QC publishDir creating an empty
    references/<panel>/ in outdir; docs/output.md silent on dashboard
    artifacts; standalone report by default (make_standalone_report.py
    still manual); PANEL_GENE_CHROMS configurability; silent filename
    fallback in dashboard parsers; CDKN2A/B whitelist.

A13. FLT3_ITD_EXT: the June sentinel fix separated no-ITD exits from real
    failures. Item 14 failures on Male1/6/21/24 and Female2 are therefore
    either a regression or a different exit path. Read .command.log
    before assuming the June fix is intact.

A14. TSPIPE-vs-production CNVkit comparison (memory open item): moot now
    that MyOPool is retired. Close it in the 09-06 memo.

A15. 17c_clinical_tier port: handoff says blocked on curation. The v3 plan
    named an 18-gene driver-table extension and a 79-hotspot merge; the
    09-06 commit added myeloid_hotspots.tsv (68 rows) and
    myeloid_driver_genes.tsv. Confirm whether the 09-06 assets are the
    curated versions or the pre-curation copies.

A16. MNV merging (item 16, one line in the handoff). Design on record
    09-03: between SomaticSeq and VEP, merge adjacent PASS calls sharing a
    Mutect2 phase set (PGT/PID), with a read-level co-occurrence check
    from the BAM where no phase is given; VarDict's native MNV calls as
    the cross-check.

A17. CAVA (item 16, one line). Design on record 09-03: alongside VEP, CSN
    column into the dashboard variant table, ALTFLAG for left/right
    alignment-dependent indels; container must be Python 3 (original was
    Python 2); pin transcript DB to the same Ensembl release as VEP.

## B. Handoff items re-ordered by dependency

Block 1 -- sex
    A1 SEX_CHECK -> item 4 sex-stratified wiring (GATK PoN, LOO, consensus
    inputs by meta.sex) -> item 5 PureCN --sex and female normalDB ->
    item 6 DECoN female pool.

Block 2 -- consensus
    A5 DECON module -> item 7 z-score removal and TIER_1 on K/G/BAF/P/E ->
    A3 schema v3 in the consensus builder -> A6 verification.

Block 3 -- visualization
    Item 12 reconCNV + cnvkit_scatter_styled wiring, including A2 parser
    and template change and the A4 decision.

Block 4 -- allele-specific
    Item 9 BAF_V2 -> item 10 MoChA Route B -> item 11 AMBER/COBALT/PURPLE
    (sixth arm at most) -> A11 oncoanalyser comparison when disk allows.

Block 5 -- gating
    Item 2 conformity gate in TSPIPE -> item 3 gate validation on the 16
    excluded females.

Block 6 -- SNV annotation
    A16 MNV merge -> A17 CAVA -> item 16 17c port once A15 is settled.

Block 7 -- housekeeping
    Item 13 tree rename; item 15 containerise VV/FLT3_TO_VARIANTS/ONCOVI;
    item 14 FLT3_ITD_EXT (A13); A12 list; item 17 memos incl. A14 closure.

Non-code, Nikhil
    A9 letter; A10 control status; A11 UMI answer; A15 curation status;
    validation-case sex now covered by A1.

## C. The validation run

Running the eight cases now costs no development time and produces the
inputs every block above needs on aberrant material rather than normals:
alt-aware BAMs, .cnr/.cns, allelic counts, modelFinal.seg, Mutect2 VCFs.
It is also the first in-pipeline exercise of VV v2 and the consequence
filter. The comparison table against known findings is not final until
blocks 1-4 land; that final pass is a -resume that re-executes only the
changed modules. Recommendation: launch, develop against the outputs,
re-run for the table at the end.
